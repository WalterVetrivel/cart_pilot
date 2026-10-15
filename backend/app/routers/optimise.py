"""POST /rank and /optimise (SPEC §8.2, §8.3, §9)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agents.explainer import Explainer, get_explainer, template_explanation
from app.auth import AuthUser
from app.db import Repository, get_repository
from app.errors import ApiError
from app.models.schemas import CartPlan, RankedItem, ScoredCandidate, ShoppingList, Voucher, Weights
from app.services.matching import match_list
from app.services.optimiser import DEFAULT_EXTRA_DELIVERY_PENALTY, optimise
from app.services.ranking import rank_candidates

router = APIRouter(tags=["deals"])
log = logging.getLogger(__name__)

Repo = Annotated[Repository, Depends(get_repository)]


class RankRequest(BaseModel):
    list_id: str
    weights: Weights = Field(default_factory=Weights)


class RankResponse(BaseModel):
    items: list[RankedItem]


class OptimiseRequest(RankRequest):
    extra_delivery_penalty: float = Field(DEFAULT_EXTRA_DELIVERY_PENALTY, ge=0, le=1000)
    explain: bool = True


class OptimiseResponse(BaseModel):
    plans: list[CartPlan]
    unavailable_items: list[str]


def _ranked(uid: str, list_id: str, weights: Weights, repo: Repository):
    stored = repo.get_list(uid, list_id)
    if stored is None:
        raise ApiError(404, "list_not_found", "That list doesn't exist.")
    shopping = ShoppingList.model_validate(stored)
    stores = {s["store_id"]: s for s in repo.stores()}
    matches = match_list(shopping.items, repo.products())
    ranked: dict[str, list[ScoredCandidate]] = {
        item.id: rank_candidates(matches[item.id], stores, weights) for item in shopping.items
    }
    return shopping, stores, ranked


@router.post("/rank", response_model=RankResponse)
def rank(body: RankRequest, user: AuthUser, repo: Repo) -> RankResponse:
    shopping, _, ranked = _ranked(user.uid, body.list_id, body.weights, repo)
    return RankResponse(items=[RankedItem(item_id=i.id, candidates=ranked[i.id]) for i in shopping.items])


@router.post("/optimise", response_model=OptimiseResponse)
async def optimise_cart(
    body: OptimiseRequest,
    user: AuthUser,
    repo: Repo,
    explainer: Annotated[Explainer, Depends(get_explainer)],
) -> OptimiseResponse:
    shopping, stores, ranked = _ranked(user.uid, body.list_id, body.weights, repo)
    vouchers = [Voucher.model_validate(v) for v in repo.vouchers(user.uid)]
    result = optimise(shopping.items, ranked, list(stores.values()), vouchers, body.extra_delivery_penalty)
    if not result.plans:
        raise ApiError(
            422,
            "no_valid_plan",
            "No store combination can deliver this list (minimum order not met, or an item is out of stock "
            "everywhere it's sold). Try adding items, or mark hard-to-find ones as optional.",
        )

    for plan in result.plans:
        plan.explanation = template_explanation(plan, stores)
    if body.explain:
        result.plans[0].explanation = await explainer.explain(result.plans, stores, shopping.detected_language)

    weights = body.weights.normalised().model_dump()
    for plan in result.plans:
        repo.save_plan(
            user.uid,
            plan.plan_id,
            {
                **plan.model_dump(),
                "list_id": body.list_id,
                "weights": weights,
                "extra_delivery_penalty": body.extra_delivery_penalty,
            },
        )
    best = result.plans[0]
    log.info("Optimised list %s: best ₹%s over %d store(s)", body.list_id, best.grand_total, len(best.stores))
    return OptimiseResponse(plans=result.plans, unavailable_items=result.unavailable_items)
