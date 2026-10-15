"""Catalogue matching (SPEC §8.1): shopping-list item -> candidate products."""

import math

from rapidfuzz import fuzz, process

from app.models.schemas import Candidate, ShoppingItem

FUZZY_CUTOFF = 80

# Everything converts to grams, millilitres or pieces.
_TO_BASE = {"kg": ("g", 1000), "g": ("g", 1), "l": ("ml", 1000), "ml": ("ml", 1), "pcs": ("pcs", 1)}


def resolve_item(name: str, canonical_names: list[str]) -> str | None:
    """Exact canonical match first, then fuzzy (score >= 80)."""
    key = name.strip().lower()
    if key in canonical_names:
        return key
    hit = process.extractOne(key, canonical_names, scorer=fuzz.WRatio, score_cutoff=FUZZY_CUTOFF)
    return hit[0] if hit else None


def packs_needed(quantity: float, unit: str | None, pack_size: float, pack_unit: str) -> int:
    """How many packs cover the requested quantity.

    With no unit (or "pack"), quantity is read as a number of packs. Units that
    can't be compared (e.g. 2 pcs of a 1 kg pack) also fall back to that.
    """
    quantity = max(quantity, 0) or 1
    req, have = _TO_BASE.get(unit or ""), _TO_BASE.get(pack_unit)
    if req and have and req[0] == have[0]:
        return max(1, math.ceil(round(quantity * req[1] / (pack_size * have[1]), 6)))
    return max(1, math.ceil(quantity))


def covered_amount(qty: int, unit: str | None, pack_size: float, pack_unit: str) -> float | None:
    """Total amount bought in base units, or None when the request has no comparable unit."""
    req, have = _TO_BASE.get(unit or ""), _TO_BASE.get(pack_unit)
    if req and have and req[0] == have[0]:
        return qty * pack_size * have[1]
    return None


def _drop_oversized(item: ShoppingItem, candidates: list[Candidate]) -> list[Candidate]:
    """Per store, keep the variants that buy the least extra (1 kg asked: skip the 5 kg pack).

    Brand matches are always kept, and nothing is dropped when the request has no unit.
    """
    best: dict[str, float] = {}
    amounts: dict[str, float | None] = {}
    for c in candidates:
        amount = covered_amount(c.qty, item.unit, c.pack_size, c.pack_unit)
        amounts[c.product_id] = amount
        if amount is not None:
            best[c.store_id] = min(best.get(c.store_id, amount), amount)
    return [
        c
        for c in candidates
        if c.brand_match or amounts[c.product_id] is None or amounts[c.product_id] <= best[c.store_id] * 1.001
    ]


def match_item(item: ShoppingItem, products: list[dict], canonical_names: list[str]) -> list[Candidate]:
    canonical = resolve_item(item.canonical_name, canonical_names)
    if canonical is None:
        return []

    brand = (item.brand_preference or "").lower()
    candidates = []
    for p in products:
        if p["canonical_item"] != canonical:
            continue
        qty = packs_needed(item.quantity, item.unit, p["pack_size"], p["pack_unit"])
        candidates.append(
            Candidate(
                product_id=p["product_id"],
                store_id=p["store_id"],
                name=p["name"],
                brand=p["brand"],
                pack_size=p["pack_size"],
                pack_unit=p["pack_unit"],
                price=p["price"],
                qty=qty,
                line_price=round(qty * p["price"], 2),
                rating=p["rating"],
                rating_count=p["rating_count"],
                in_stock=p["in_stock"],
                brand_match=bool(brand) and brand in p["brand"].lower(),
            )
        )
    candidates = _drop_oversized(item, candidates)
    candidates.sort(key=lambda c: (not c.in_stock, not c.brand_match, c.line_price))
    return candidates


def match_list(items: list[ShoppingItem], products: list[dict]) -> dict[str, list[Candidate]]:
    canonical_names = sorted({p["canonical_item"] for p in products})
    return {item.id: match_item(item, products, canonical_names) for item in items}
