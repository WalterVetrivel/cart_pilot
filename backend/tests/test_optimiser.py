"""SPEC §8.3 required cases plus plan selection, on a small hand-built catalogue."""

from datetime import date

import pytest

from app.models.schemas import Candidate, PlanLine, ShoppingItem, Voucher, Weights
from app.services.optimiser import delivery_fee, optimise, voucher_discount
from app.services.ranking import rank_candidates

TODAY = date(2026, 10, 15)

STORES = [
    {
        "store_id": "freshmart",
        "eta_label": "Next day",
        "eta_minutes": 1440,
        "delivery_fee": 40,
        "free_delivery_at": 600,
        "min_order": 200,
        "small_cart_fee": 0,
        "small_cart_below": 0,
    },
    {
        "store_id": "quickbasket",
        "eta_label": "12 min",
        "eta_minutes": 12,
        "delivery_fee": 25,
        "free_delivery_at": 399,
        "min_order": 99,
        "small_cart_fee": 15,
        "small_cart_below": 199,
    },
    {
        "store_id": "megabazaar",
        "eta_label": "2 days",
        "eta_minutes": 2880,
        "delivery_fee": 49,
        "free_delivery_at": 499,
        "min_order": 0,
        "small_cart_fee": 0,
        "small_cart_below": 0,
    },
    {
        "store_id": "kiranaconnect",
        "eta_label": "45 min",
        "eta_minutes": 45,
        "delivery_fee": 20,
        "free_delivery_at": 300,
        "min_order": 150,
        "small_cart_fee": 0,
        "small_cart_below": 0,
    },
]
STORE_MAP = {s["store_id"]: s for s in STORES}
CHEAPEST = Weights(price=1, rating=0, delivery=0, availability=0)


def cand(store: str, price: float, *, item: str = "x", in_stock: bool = True, rating: float = 4.0) -> Candidate:
    return Candidate(
        product_id=f"{store}-{item}",
        store_id=store,
        name=f"{item} at {store}",
        brand="B",
        pack_size=1,
        pack_unit="kg",
        price=price,
        qty=1,
        line_price=price,
        rating=rating,
        rating_count=100,
        in_stock=in_stock,
    )


def item(name: str, optional: bool = False, category: str = "staples") -> ShoppingItem:
    return ShoppingItem(id=name, canonical_name=name, original_text=name, optional=optional, category=category)


def run(items, offers, vouchers=(), penalty=30.0, weights=CHEAPEST):
    ranked = {i.id: rank_candidates(offers.get(i.id, []), STORE_MAP, weights) for i in items}
    return optimise(items, ranked, STORES, list(vouchers), penalty, today=TODAY)


def voucher(**kw) -> Voucher:
    base = dict(
        email_id="e1",
        store_name_raw="S",
        store_id="megabazaar",
        code="C",
        discount_type="flat",
        value=50,
        confidence=0.9,
    )
    return Voucher(**{**base, **kw})


def lines(*prices: float, category: str = "staples"):
    return [
        (PlanLine(item_id=str(i), product_id="p", name="n", qty=1, line_price=p), category)
        for i, p in enumerate(prices)
    ]


# --- voucher rules -----------------------------------------------------------
def test_voucher_min_spend_boundary_is_inclusive():
    v = voucher(min_spend=499)
    assert voucher_discount(v, lines(499), TODAY) == 50
    assert voucher_discount(v, lines(498.99), TODAY) == 0


def test_percent_voucher_respects_max_discount():
    v = voucher(discount_type="percent", value=10, max_discount=100)
    assert voucher_discount(v, lines(800), TODAY) == 80
    assert voucher_discount(v, lines(2500), TODAY) == 100


def test_expired_voucher_is_ignored():
    assert voucher_discount(voucher(expiry="2026-10-14"), lines(600), TODAY) == 0
    assert voucher_discount(voucher(expiry="2026-10-15"), lines(600), TODAY) == 50


def test_used_unknown_store_and_category_vouchers():
    assert voucher_discount(voucher(status="used"), lines(600), TODAY) == 0
    assert voucher_discount(voucher(store_id=None), lines(600), TODAY) == 0
    v = voucher(discount_type="percent", value=10, applies_to_category="dairy")
    assert voucher_discount(v, lines(300, category="staples") + lines(200, category="dairy"), TODAY) == 20
    assert voucher_discount(v, lines(300), TODAY) == 0


def test_flat_voucher_never_exceeds_spend():
    assert voucher_discount(voucher(value=500), lines(120), TODAY) == 120


# --- delivery fees ---------------------------------------------------------
@pytest.mark.parametrize(
    ("store", "subtotal", "fee"),
    [
        ("freshmart", 599.99, 40),
        ("freshmart", 600, 0),
        ("megabazaar", 498, 49),
        ("megabazaar", 499, 0),
        ("quickbasket", 150, 40),
        ("quickbasket", 199, 25),
        ("quickbasket", 399, 0),
    ],
)
def test_free_delivery_threshold(store, subtotal, fee):
    assert delivery_fee(STORE_MAP[store], subtotal) == fee


# --- plan selection ----------------------------------------------------------
def test_min_order_invalidates_a_store():
    # Only FreshMart sells it, at ₹150 < ₹200 minimum: no valid plan at all.
    result = run([item("rice")], {"rice": [cand("freshmart", 150)]})
    assert result.plans == []


def test_item_missing_in_all_stores_is_reported_not_fatal():
    items = [item("rice"), item("caviar")]
    offers = {"rice": [cand("megabazaar", 300)], "caviar": [cand("freshmart", 999, in_stock=False)]}
    result = run(items, offers)
    assert result.unavailable_items == ["caviar"]
    best = result.plans[0]
    assert best.unavailable_items == ["caviar"]
    assert [sp.store_id for sp in best.stores] == ["megabazaar"]
    assert best.grand_total == 300 + 49


def test_optional_item_can_be_dropped_from_a_plan():
    items = [item("rice"), item("ghee", optional=True)]
    offers = {"rice": [cand("megabazaar", 520, item="rice")], "ghee": [cand("kiranaconnect", 100, item="ghee")]}
    result = run(items, offers, penalty=1000)
    single = next(p for p in result.plans if p.label == "single_store")
    assert single.unavailable_items == ["ghee"]
    assert single.grand_total == 520


def test_split_cart_beats_single_store_and_reports_savings():
    items = [item("rice"), item("dal")]
    offers = {
        "rice": [cand("megabazaar", 500, item="rice"), cand("kiranaconnect", 800, item="rice")],
        "dal": [cand("megabazaar", 400, item="dal"), cand("kiranaconnect", 160, item="dal")],
    }
    result = run(items, offers, penalty=30)
    best, single, fastest = result.plans
    assert (best.label, single.label, fastest.label) == ("best", "single_store", "fastest")
    # Split: MegaBazaar 500 (free delivery) + Kirana 160 + ₹20 fee = 680 vs MegaBazaar alone 900.
    assert [sp.store_id for sp in best.stores] == ["megabazaar", "kiranaconnect"]
    assert best.grand_total == 680
    assert best.effective_total == 710
    assert single.grand_total == 900
    assert best.savings_vs_single_store == 220
    assert [sp.store_id for sp in fastest.stores] == ["kiranaconnect"]


def test_extra_delivery_penalty_can_favour_one_store():
    items = [item("rice"), item("dal")]
    offers = {
        "rice": [cand("megabazaar", 500, item="rice"), cand("kiranaconnect", 800, item="rice")],
        "dal": [cand("megabazaar", 400, item="dal"), cand("kiranaconnect", 160, item="dal")],
    }
    best = run(items, offers, penalty=500).plans[0]
    assert [sp.store_id for sp in best.stores] == ["megabazaar"]


def test_voucher_changes_the_chosen_plan():
    items = [item("rice")]
    offers = {"rice": [cand("megabazaar", 520), cand("freshmart", 540)]}
    assert run(items, offers).plans[0].stores[0].store_id == "megabazaar"
    # FreshMart: 540 + ₹40 delivery - ₹80 voucher = 500, beating MegaBazaar's 520.
    with_voucher = run(items, offers, vouchers=[voucher(store_id="freshmart", code="FRESH80", value=80)])
    best = with_voucher.plans[0]
    assert best.stores[0].store_id == "freshmart"
    assert best.stores[0].voucher.code == "FRESH80"
    assert best.grand_total == 500


def test_out_of_stock_is_never_chosen():
    offers = {"rice": [cand("megabazaar", 100, in_stock=False), cand("freshmart", 250)]}
    best = run([item("rice")], offers).plans[0]
    assert best.stores[0].store_id == "freshmart"


def test_ranking_scores_and_order():
    offers = [
        cand("megabazaar", 100, rating=3.0),
        cand("quickbasket", 120, rating=5.0),
        cand("freshmart", 90, in_stock=False),
    ]
    ranked = rank_candidates(offers, STORE_MAP, Weights())
    assert [c.store_id for c in ranked][-1] == "freshmart"  # out of stock last
    mega = next(c for c in ranked if c.store_id == "megabazaar")
    quick = next(c for c in ranked if c.store_id == "quickbasket")
    assert mega.price_score == 1.0 and quick.price_score == pytest.approx(100 / 120, abs=1e-4)
    assert quick.rating_score == 1.0 and mega.rating_score == 0.0
    assert mega.delivery_score == 0.0 and quick.delivery_score > 0.99
    assert all(0 <= c.score <= 1.05 for c in ranked)


def test_few_reviews_discount_rating():
    few = cand("megabazaar", 100, rating=5.0).model_copy(update={"rating_count": 5})
    assert rank_candidates([few], STORE_MAP, Weights())[0].rating_score == 0.7


def test_weights_renormalise():
    w = Weights(price=2, rating=1, delivery=1, availability=0).normalised()
    assert (w.price, w.rating, w.delivery, w.availability) == (0.5, 0.25, 0.25, 0)


def test_twelve_item_seeded_list_yields_three_plans():
    from app.services.matching import match_list
    from seed.generate_seed import generate

    stores, products = generate()
    names = [
        "rice",
        "wheat flour",
        "toor dal",
        "sunflower oil",
        "milk",
        "curd",
        "onion",
        "tomato",
        "potato",
        "tea",
        "sugar",
        "detergent",
    ]
    items = [ShoppingItem(id=n, canonical_name=n, original_text=n) for n in names]
    matches = match_list(items, products)
    store_map = {s["store_id"]: s for s in stores}
    ranked = {i.id: rank_candidates(matches[i.id], store_map, Weights()) for i in items}
    result = optimise(items, ranked, stores, [], 30, today=TODAY)
    assert [p.label for p in result.plans] == ["best", "single_store", "fastest"]
    best = result.plans[0]
    assert best.effective_total <= result.plans[1].effective_total
    assert sum(len(sp.lines) for sp in best.stores) == 12
