"""POST/GET /orders: sandbox checkout after explicit approval (SPEC §8.4, screens 7-8)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import AuthUser
from app.config import Settings, get_settings
from app.db import Repository, get_repository
from app.models.schemas import Order
from app.services.checkout import place_orders

router = APIRouter(tags=["orders"])

Repo = Annotated[Repository, Depends(get_repository)]


class OrderRequest(BaseModel):
    plan_id: str
    approved: bool
    displayed_total: float


class OrdersResponse(BaseModel):
    orders: list[Order]
    grand_total: float


@router.post("/orders", response_model=OrdersResponse)
def create_orders(
    body: OrderRequest, user: AuthUser, repo: Repo, settings: Annotated[Settings, Depends(get_settings)]
) -> OrdersResponse:
    orders = place_orders(user.uid, body.plan_id, body.approved, body.displayed_total, settings.max_order_inr, repo)
    return OrdersResponse(orders=orders, grand_total=round(sum(o.total for o in orders), 2))


@router.get("/orders", response_model=OrdersResponse)
def list_orders(user: AuthUser, repo: Repo) -> OrdersResponse:
    orders = [Order.model_validate(o) for o in repo.orders(user.uid)]
    return OrdersResponse(orders=orders, grand_total=round(sum(o.total for o in orders), 2))
