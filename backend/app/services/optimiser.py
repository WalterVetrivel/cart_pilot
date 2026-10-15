"""Split-cart optimiser (SPEC §8.3). All money is computed here, never by a model."""

from dataclasses import dataclass
from datetime import date
from itertools import combinations

from app.models.schemas import AppliedVoucher, CartPlan, PlanLine, ScoredCandidate, ShoppingItem, StorePlan, Voucher

DEFAULT_EXTRA_DELIVERY_PENALTY = 30.0


@dataclass
class OptimiseResult:
    plans: list[CartPlan]  # best, then single_store and fastest when they exist
    unavailable_items: list[str]


def _money(x: float) -> float:
    return round(x + 0.0, 2)


def delivery_fee(store: dict, subtotal: float) -> float:
    if store["free_delivery_at"] and subtotal >= store["free_delivery_at"]:
        return 0.0
    fee = float(store["delivery_fee"])
    if store.get("small_cart_below") and subtotal < store["small_cart_below"]:
        fee += store.get("small_cart_fee", 0)
    return fee


def voucher_discount(voucher: Voucher, lines: list[tuple[PlanLine, str]], today: date) -> float:
    """Discount this voucher gives on a store's lines; 0 if it doesn't apply. lines = (line, category)."""
    if voucher.status != "active" or voucher.store_id is None:
        return 0.0
    if voucher.expiry and date.fromisoformat(voucher.expiry) < today:
        return 0.0
    subtotal = sum(line.line_price for line, _ in lines)
    if voucher.min_spend and subtotal < voucher.min_spend:
        return 0.0
    base = subtotal
    if voucher.applies_to_category:
        base = sum(line.line_price for line, cat in lines if cat == voucher.applies_to_category)
    if base <= 0:
        return 0.0
    if voucher.discount_type == "percent":
        discount = base * voucher.value / 100
        if voucher.max_discount:
            discount = min(discount, voucher.max_discount)
    else:
        discount = min(voucher.value, base)
    return _money(discount)


def _best_voucher(
    store_id: str, lines: list[tuple[PlanLine, str]], vouchers: list[Voucher], today: date
) -> AppliedVoucher | None:
    best: AppliedVoucher | None = None
    for v in vouchers:
        if v.store_id != store_id:
            continue
        d = voucher_discount(v, lines, today)
        if d > 0 and (best is None or d > best.discount):
            best = AppliedVoucher(code=v.code, discount=d, email_id=v.email_id, voucher_id=v.id or None)
    return best


def _build_plan(
    store_ids: tuple[str, ...],
    items: list[ShoppingItem],
    ranked: dict[str, list[ScoredCandidate]],
    unavailable: set[str],
    stores: dict[str, dict],
    vouchers: list[Voucher],
    penalty: float,
    today: date,
) -> CartPlan | None:
    by_store: dict[str, list[tuple[PlanLine, str]]] = {}
    skipped: list[str] = []
    for item in items:
        if item.id in unavailable:
            continue
        options = [c for c in ranked.get(item.id, []) if c.in_stock and c.store_id in store_ids]
        if not options:
            if item.optional:
                skipped.append(item.canonical_name)
                continue
            return None
        pick = max(options, key=lambda c: (c.score, -c.line_price))
        line = PlanLine(
            item_id=item.id,
            item_name=item.canonical_name,
            product_id=pick.product_id,
            name=pick.name,
            qty=pick.qty,
            line_price=pick.line_price,
        )
        by_store.setdefault(pick.store_id, []).append((line, item.category))

    if not by_store:
        return None

    store_plans = []
    for store_id in sorted(by_store, key=list(stores).index):
        store = stores[store_id]
        lines = by_store[store_id]
        subtotal = _money(sum(line.line_price for line, _ in lines))
        if subtotal < store["min_order"]:
            return None
        fee = delivery_fee(store, subtotal)
        voucher = _best_voucher(store_id, lines, vouchers, today)
        total = _money(subtotal + fee - (voucher.discount if voucher else 0))
        store_plans.append(
            StorePlan(
                store_id=store_id,
                lines=[line for line, _ in lines],
                subtotal=subtotal,
                delivery_fee=fee,
                voucher=voucher,
                total=total,
                eta=store["eta_label"],
                eta_minutes=store["eta_minutes"],
            )
        )

    grand = _money(sum(sp.total for sp in store_plans))
    return CartPlan(
        label="best",
        stores=store_plans,
        grand_total=grand,
        effective_total=_money(grand + penalty * (len(store_plans) - 1)),
        unavailable_items=skipped,
    )


def optimise(
    items: list[ShoppingItem],
    ranked: dict[str, list[ScoredCandidate]],
    stores: list[dict],
    vouchers: list[Voucher],
    extra_delivery_penalty: float = DEFAULT_EXTRA_DELIVERY_PENALTY,
    today: date | None = None,
) -> OptimiseResult:
    today = today or date.today()
    store_map = {s["store_id"]: s for s in stores}
    # Items no store has in stock can't be bought anywhere: report them, don't let them sink every plan.
    unavailable = {i.id for i in items if not any(c.in_stock for c in ranked.get(i.id, []))}
    unavailable_names = [i.canonical_name for i in items if i.id in unavailable]

    plans: dict[tuple[str, ...], CartPlan] = {}
    ids = list(store_map)
    for size in range(1, len(ids) + 1):
        for subset in combinations(ids, size):
            plan = _build_plan(subset, items, ranked, unavailable, store_map, vouchers, extra_delivery_penalty, today)
            if plan is None:
                continue
            key = tuple(sp.store_id for sp in plan.stores)  # unused stores collapse to a smaller subset
            if key not in plans or plan.effective_total < plans[key].effective_total:
                plans[key] = plan

    if not plans:
        return OptimiseResult(plans=[], unavailable_items=unavailable_names)

    def finish(plan: CartPlan, label: str) -> CartPlan:
        return plan.model_copy(
            deep=True,
            update={"label": label, "unavailable_items": unavailable_names + plan.unavailable_items},
        )

    candidates = list(plans.values())
    best = min(candidates, key=lambda p: (p.effective_total, len(p.stores)))
    singles = [p for p in candidates if len(p.stores) == 1]
    single = min(singles, key=lambda p: p.grand_total) if singles else None
    fastest = min(candidates, key=lambda p: (max(sp.eta_minutes for sp in p.stores), p.effective_total))

    result = [finish(best, "best")]
    if single is not None:
        result[0].savings_vs_single_store = _money(max(single.grand_total - best.grand_total, 0))
        result.append(finish(single, "single_store"))
    result.append(finish(fastest, "fastest"))
    return OptimiseResult(plans=result, unavailable_items=unavailable_names)
