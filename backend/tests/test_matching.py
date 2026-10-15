import pytest

from app.models.schemas import ShoppingItem
from app.services.matching import match_item, packs_needed, resolve_item
from seed.generate_seed import generate

_, PRODUCTS = generate()
NAMES = sorted({p["canonical_item"] for p in PRODUCTS})


@pytest.mark.parametrize(
    ("name", "expected"),
    [("tomato", "tomato"), ("Tomatoes", "tomato"), (" wheat flour ", "wheat flour"), ("dragon fruit", None)],
)
def test_resolve_item(name, expected):
    assert resolve_item(name, NAMES) == expected


@pytest.mark.parametrize(
    ("qty", "unit", "pack_size", "pack_unit", "packs"),
    [
        (2, "kg", 1, "kg", 2),
        (1.5, "kg", 1, "kg", 2),
        (500, "g", 1, "kg", 1),
        (1, "kg", 500, "g", 2),
        (2, "l", 500, "ml", 4),
        (12, "pcs", 6, "pcs", 2),
        (3, None, 1, "kg", 3),
        (2, "pack", 1, "pack", 2),
        (2, "pcs", 1, "kg", 2),  # incomparable units -> packs
    ],
)
def test_packs_needed(qty, unit, pack_size, pack_unit, packs):
    assert packs_needed(qty, unit, pack_size, pack_unit) == packs


def test_match_item_prices_and_orders_candidates():
    item = ShoppingItem(canonical_name="onion", original_text="vengayam 2 kg", quantity=2, unit="kg")
    cands = match_item(item, PRODUCTS, NAMES)
    assert cands and all(c.product_id.split("-")[1] == "onion" for c in cands)
    for c in cands:
        assert c.line_price == round(c.qty * c.price, 2)
    in_stock = [c for c in cands if c.in_stock]
    assert in_stock == cands[: len(in_stock)], "in-stock candidates come first"


def test_brand_preference_is_flagged():
    item = ShoppingItem(canonical_name="rice", original_text="Golden Harvest rice", brand_preference="golden harvest")
    cands = match_item(item, PRODUCTS, NAMES)
    assert any(c.brand_match for c in cands)
    assert all(c.brand_match == (c.brand == "Golden Harvest") for c in cands)


def test_unknown_item_has_no_candidates():
    assert match_item(ShoppingItem(canonical_name="caviar", original_text="caviar"), PRODUCTS, NAMES) == []


def test_oversized_packs_are_dropped_per_store():
    one_kg = ShoppingItem(canonical_name="sugar", original_text="sugar 1 kg", quantity=1, unit="kg")
    cands = match_item(one_kg, PRODUCTS, NAMES)
    assert cands and all(c.pack_size * c.qty == 1 for c in cands), "no 5 kg packs for a 1 kg request"

    five_kg = ShoppingItem(canonical_name="sugar", original_text="sugar 5 kg", quantity=5, unit="kg")
    sizes = {(c.qty, c.pack_size) for c in match_item(five_kg, PRODUCTS, NAMES)}
    assert (1, 5) in sizes and (5, 1) in sizes, "both ways of buying exactly 5 kg are kept"

    no_unit = ShoppingItem(canonical_name="sugar", original_text="sugar")
    assert {c.pack_size for c in match_item(no_unit, PRODUCTS, NAMES)} == {1, 5}
