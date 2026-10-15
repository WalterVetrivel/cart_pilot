import asyncio

from app.agents.explainer import GeminiExplainer, template_explanation
from app.models.schemas import AppliedVoucher, CartPlan, Explanation, PlanLine, StorePlan

STORES = {"megabazaar": {"name": "MegaBazaar"}, "kiranaconnect": {"name": "Kirana Connect"}}


def _new_list(client, items):
    list_id = client.post("/api/parse", data={"text": "x"}).json()["list_id"]
    res = client.put(f"/api/lists/{list_id}", json={"items": items, "detected_language": "en"})
    assert res.status_code == 200, res.text
    return list_id


ITEMS = [
    {"canonical_name": n, "original_text": n, "quantity": q, "unit": u}
    for n, q, u in [
        ("rice", 5, "kg"),
        ("toor dal", 1, "kg"),
        ("milk", 2, "l"),
        ("onion", 2, "kg"),
        ("sunflower oil", 1, "l"),
        ("sugar", 1, "kg"),
    ]
]


def test_rank_orders_candidates(dev_client):
    list_id = _new_list(dev_client, ITEMS)
    res = dev_client.post(
        "/api/rank", json={"list_id": list_id, "weights": {"price": 1, "rating": 0, "delivery": 0, "availability": 0}}
    )
    assert res.status_code == 200, res.text
    for item in res.json()["items"]:
        stocked = [c for c in item["candidates"] if c["in_stock"]]
        assert stocked[0]["line_price"] == min(c["line_price"] for c in stocked)


def test_optimise_returns_three_plans_with_explanation(dev_client, fake_explainer):
    list_id = _new_list(dev_client, ITEMS)
    res = dev_client.post("/api/optimise", json={"list_id": list_id})
    assert res.status_code == 200, res.text
    plans = res.json()["plans"]
    assert [p["label"] for p in plans] == ["best", "single_store", "fastest"]
    assert plans[0]["explanation"]["headline"] == "Fake headline"
    assert plans[1]["explanation"]["headline"]  # template for alternatives
    assert len(fake_explainer.calls) == 1
    for plan in plans:
        assert plan["grand_total"] == round(sum(s["total"] for s in plan["stores"]), 2)
        for store in plan["stores"]:
            assert store["subtotal"] == round(sum(line["line_price"] for line in store["lines"]), 2)


def test_optimise_without_explain_skips_gemini(dev_client, fake_explainer):
    list_id = _new_list(dev_client, ITEMS)
    res = dev_client.post("/api/optimise", json={"list_id": list_id, "explain": False})
    assert res.status_code == 200
    assert fake_explainer.calls == []


def test_optimise_no_valid_plan(dev_client):
    # Nothing on the list exists in any store, so there is nothing to plan.
    list_id = _new_list(dev_client, [{"canonical_name": "caviar", "original_text": "caviar"}])
    res = dev_client.post("/api/optimise", json={"list_id": list_id})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "no_valid_plan"


def test_optimise_unknown_list(dev_client):
    assert dev_client.post("/api/optimise", json={"list_id": "nope"}).status_code == 404


def _plan() -> CartPlan:
    return CartPlan(
        label="best",
        stores=[
            StorePlan(
                store_id="megabazaar",
                lines=[PlanLine(item_id="1", item_name="rice", product_id="p", name="Rice", qty=1, line_price=500)],
                subtotal=500,
                delivery_fee=0,
                voucher=AppliedVoucher(code="MEGA75", discount=75),
                total=425,
                eta="2 days",
            ),
            StorePlan(
                store_id="kiranaconnect",
                lines=[PlanLine(item_id="2", item_name="dal", product_id="q", name="Dal", qty=1, line_price=160)],
                subtotal=160,
                delivery_fee=20,
                total=180,
                eta="45 min",
            ),
        ],
        grand_total=605,
        savings_vs_single_store=212,
        unavailable_items=["caviar"],
    )


def test_template_explanation():
    exp = template_explanation(_plan(), STORES)
    assert exp.headline == "Split across 2 stores and save ₹212"
    assert exp.bullets[0] == "MegaBazaar: 1 item, ₹425 (free delivery, MEGA75 saves ₹75), 2 days"
    assert exp.bullets[-1] == "Not available: caviar"


def test_explainer_rejects_invented_numbers(monkeypatch):
    import app.agents.explainer as mod

    async def invented(*_):
        return Explanation(headline="Save ₹999 today", bullets=[])

    monkeypatch.setattr(mod, "run_structured", invented)
    result = asyncio.run(GeminiExplainer().explain([_plan()], STORES, "en"))
    assert result.headline == "Split across 2 stores and save ₹212"


def test_explainer_keeps_faithful_output(monkeypatch):
    import app.agents.explainer as mod

    async def faithful(*_):
        return Explanation(headline="Split across 2 stores and save ₹212", bullets=["MegaBazaar ₹425, Kirana ₹180"])

    monkeypatch.setattr(mod, "run_structured", faithful)
    result = asyncio.run(GeminiExplainer().explain([_plan()], STORES, "ta"))
    assert result.bullets == ["MegaBazaar ₹425, Kirana ₹180"]


def test_explainer_falls_back_on_error(monkeypatch):
    import app.agents.explainer as mod

    async def boom(*_):
        raise RuntimeError("quota")

    monkeypatch.setattr(mod, "run_structured", boom)
    assert asyncio.run(GeminiExplainer().explain([_plan()], STORES, "en")).headline.startswith("Split across 2")
