"""ExplainerAgent (SPEC §6.3): restates the optimiser's numbers in plain language.

The model only rewords figures computed in Python. Any number in its output that isn't in the
input is treated as a hallucination and the deterministic template is used instead.
"""

import json
import logging
import re
from functools import lru_cache
from typing import Protocol

from google.adk.agents import LlmAgent
from google.genai import types

from app.agents.model import model_name
from app.agents.runner import run_structured
from app.models.schemas import CartPlan, Explanation

log = logging.getLogger(__name__)

LANGUAGES = {"ta": "Tamil", "hi": "Hindi"}

INSTRUCTION = """You explain a shopping cart plan to an Indian household in one glance.
You get JSON with the recommended plan and alternatives. All numbers are already computed.

Write:
- headline: at most 90 characters, the key decision and the saving, e.g.
  "Split across 2 stores and save ₹212 — one extra delivery."
- bullets: at most 4 short lines covering which store gets what, delivery fees, vouchers used and
  anything unavailable.

Rules:
- Use only numbers that appear in the JSON. Never calculate, round differently or estimate.
- Write rupee amounts as ₹ followed by the number, e.g. ₹1,250.
- Be plain and friendly. No marketing language.
"""


def _rupees(x: float) -> str:
    return f"₹{x:,.0f}" if float(x).is_integer() else f"₹{x:,.2f}"


def _store_name(stores: dict[str, dict], store_id: str) -> str:
    return stores.get(store_id, {}).get("name", store_id)


def template_explanation(plan: CartPlan, stores: dict[str, dict]) -> Explanation:
    """Deterministic explanation, used for alternatives and whenever Gemini is unavailable."""
    n = len(plan.stores)
    if n == 1:
        headline = f"Everything from {_store_name(stores, plan.stores[0].store_id)} for {_rupees(plan.grand_total)}"
    elif plan.savings_vs_single_store > 0:
        headline = f"Split across {n} stores and save {_rupees(plan.savings_vs_single_store)}"
    else:
        headline = f"Split across {n} stores for {_rupees(plan.grand_total)}"
    bullets = []
    for sp in plan.stores[:3]:
        fee = "free delivery" if sp.delivery_fee == 0 else f"{_rupees(sp.delivery_fee)} delivery"
        voucher = f", {sp.voucher.code} saves {_rupees(sp.voucher.discount)}" if sp.voucher else ""
        count = f"{len(sp.lines)} item{'s' if len(sp.lines) != 1 else ''}"
        bullets.append(f"{_store_name(stores, sp.store_id)}: {count}, {_rupees(sp.total)} ({fee}{voucher}), {sp.eta}")
    if plan.unavailable_items:
        bullets.append("Not available: " + ", ".join(plan.unavailable_items[:4]))
    return Explanation(headline=headline[:90], bullets=bullets[:4])


def _numbers(text: str) -> set[float]:
    return {float(m.replace(",", "")) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def explainer_input(plans: list[CartPlan], stores: dict[str, dict]) -> dict:
    def describe(plan: CartPlan) -> dict:
        return {
            "label": plan.label,
            "grand_total": plan.grand_total,
            "number_of_stores": len(plan.stores),
            "extra_deliveries": len(plan.stores) - 1,
            "savings_vs_single_store": plan.savings_vs_single_store,
            "unavailable_items": plan.unavailable_items,
            "stores": [
                {
                    "store": _store_name(stores, sp.store_id),
                    "items": [line.item_name for line in sp.lines],
                    "item_count": len(sp.lines),
                    "subtotal": sp.subtotal,
                    "delivery_fee": sp.delivery_fee,
                    "voucher": sp.voucher.model_dump(exclude={"email_id"}) if sp.voucher else None,
                    "total": sp.total,
                    "delivery_time": sp.eta,
                }
                for sp in plan.stores
            ],
        }

    return {"recommended": describe(plans[0]), "alternatives": [describe(p) for p in plans[1:]]}


class Explainer(Protocol):
    async def explain(self, plans: list[CartPlan], stores: dict[str, dict], language: str) -> Explanation: ...


class GeminiExplainer:
    def __init__(self) -> None:
        self.agent = LlmAgent(
            name="explainer",
            model=model_name(),
            description="Explains a computed cart plan in plain language.",
            instruction=INSTRUCTION,
            output_schema=Explanation,
            generate_content_config=types.GenerateContentConfig(temperature=0.3),
        )

    async def explain(self, plans: list[CartPlan], stores: dict[str, dict], language: str) -> Explanation:
        fallback = template_explanation(plans[0], stores)
        data = explainer_input(plans, stores)
        lang = LANGUAGES.get(language, "English")
        prompt = f"Reply in {lang}.\n\n{json.dumps(data, ensure_ascii=False)}"
        try:
            result = await run_structured(self.agent, [types.Part.from_text(text=prompt)], Explanation)
        except Exception:
            log.exception("Explainer failed; using template")
            return fallback
        allowed = _numbers(json.dumps(data)) | set(range(10))
        said = _numbers(" ".join([result.headline, *result.bullets]))
        if not said <= allowed:
            log.warning("Explainer invented numbers %s; using template", sorted(said - allowed))
            return fallback
        return result


@lru_cache
def get_explainer() -> Explainer:
    return GeminiExplainer()
