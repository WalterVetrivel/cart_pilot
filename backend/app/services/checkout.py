"""Sandbox checkout (SPEC §8.4). No real store, order or payment is ever touched.

Only the UI's approval step reaches this: no agent has a tool that calls it.
"""

import logging
import uuid
from datetime import UTC, datetime

from app.db import Repository
from app.errors import ApiError
from app.models.schemas import CartPlan, Order

log = logging.getLogger(__name__)

TOTAL_TOLERANCE = 0.01


def place_orders(
    uid: str, plan_id: str, approved: bool, displayed_total: float, max_order_inr: float, repo: Repository
) -> list[Order]:
    if approved is not True:
        raise ApiError(400, "approval_required", "Tick “I approve this order” before placing it.")

    stored = repo.get_plan(uid, plan_id)
    if stored is None:
        raise ApiError(404, "plan_not_found", "That plan doesn't exist. Find deals again.")
    if stored.get("ordered"):
        raise ApiError(409, "already_ordered", "You've already placed this order. See your orders.")
    plan = CartPlan.model_validate(stored)

    if abs(plan.grand_total - displayed_total) > TOTAL_TOLERANCE:
        raise ApiError(409, "total_changed", "The total changed since you last saw it. Check the plan again.")
    if plan.grand_total > max_order_inr:
        raise ApiError(
            422,
            "over_spending_cap",
            f"This order is ₹{plan.grand_total:,.0f}, over the ₹{max_order_inr:,.0f} limit per order. "
            "Remove some items or split it into smaller lists.",
        )

    # A voucher used by an earlier order can't be applied twice.
    vouchers = {v["id"]: v for v in repo.vouchers(uid)}
    used_ids = [sp.voucher.voucher_id for sp in plan.stores if sp.voucher and sp.voucher.voucher_id]
    if any(vouchers.get(vid, {}).get("status") != "active" for vid in used_ids):
        raise ApiError(409, "voucher_unavailable", "A voucher in this plan has already been used. Update the plan.")

    wanted: dict[str, int] = {}
    for sp in plan.stores:
        for line in sp.lines:
            wanted[line.product_id] = wanted.get(line.product_id, 0) + line.qty
    short = repo.take_stock(wanted)
    if short:
        names = {line.product_id: line.name for sp in plan.stores for line in sp.lines}
        raise ApiError(
            409,
            "out_of_stock",
            "Sold out since your plan was made: " + ", ".join(names[p] for p in short) + ". Update the plan.",
        )

    repo.mark_vouchers_used(uid, used_ids)
    created = datetime.now(UTC).isoformat()
    orders = []
    for sp in plan.stores:
        order = Order(
            order_id=str(uuid.uuid4()),
            plan_id=plan_id,
            list_id=stored.get("list_id"),
            store_id=sp.store_id,
            lines=sp.lines,
            subtotal=sp.subtotal,
            delivery_fee=sp.delivery_fee,
            voucher=sp.voucher,
            total=sp.total,
            eta=sp.eta,
            payment_id=f"sandbox_pay_{uuid.uuid4().hex}",
            created_at=created,
        )
        repo.save_order(uid, order.order_id, order.model_dump())
        orders.append(order)
    repo.update_plan(uid, plan_id, {"ordered": True})
    log.info("Sandbox orders placed for plan %s: %d store(s), ₹%s", plan_id, len(orders), plan.grand_total)
    return orders
