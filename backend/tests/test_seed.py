import json
from collections import defaultdict
from pathlib import Path

from app.models.schemas import Voucher
from seed.generate_seed import generate

SEED_DIR = Path(__file__).parent.parent / "seed"


def test_seed_is_deterministic():
    assert generate() == generate()


def test_catalogue_shape():
    stores, products = generate()
    assert {s["store_id"] for s in stores} == {"freshmart", "quickbasket", "megabazaar", "kiranaconnect"}
    assert len({p["canonical_item"] for p in products}) == 75
    assert 500 <= len(products) <= 700
    assert len({p["product_id"] for p in products}) == len(products)

    out_of_stock = sum(not p["in_stock"] for p in products) / len(products)
    assert 0.04 <= out_of_stock <= 0.12

    carriers = defaultdict(set)
    for p in products:
        carriers[p["canonical_item"]].add(p["store_id"])
    assert all(len(s) >= 2 for s in carriers.values())
    assert any(len(s) < 4 for s in carriers.values()), "some items must be missing from some stores"


def test_committed_seed_json_matches_generator():
    stores, products = generate()
    assert json.loads((SEED_DIR / "data" / "stores.json").read_text()) == stores
    assert json.loads((SEED_DIR / "data" / "products.json").read_text()) == products


def test_demo_vouchers_cover_spec_cases():
    vouchers = [Voucher.model_validate(v) for v in json.loads((SEED_DIR / "demo_vouchers.json").read_text())]
    assert any(v.discount_type == "percent" and v.max_discount for v in vouchers)
    assert any(v.discount_type == "flat" and v.min_spend for v in vouchers)
    assert any(v.expiry and v.expiry < "2026-10-15" for v in vouchers)
    assert any(v.store_id is None for v in vouchers)
    assert len(list((SEED_DIR / "demo_emails").glob("*.json"))) == 6
