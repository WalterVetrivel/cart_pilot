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
