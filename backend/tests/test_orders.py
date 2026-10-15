import pytest

from app.config import get_settings
from app.db import get_repository
from tests.test_deals_api import ITEMS, _new_list


def _best_plan(client, *, vouchers=False):
    if vouchers:
        client.post("/api/vouchers/demo")
    list_id = _new_list(client, ITEMS)
    return client.post("/api/optimise", json={"list_id": list_id, "explain": False}).json()["plans"][0]


def _order(client, plan, **kw):
    body = {"plan_id": plan["plan_id"], "approved": True, "displayed_total": plan["grand_total"], **kw}
    return client.post("/api/orders", json=body)


def test_order_needs_approval(dev_client):
    plan = _best_plan(dev_client)
    res = _order(dev_client, plan, approved=False)
    assert res.status_code == 400 and res.json()["error"]["code"] == "approval_required"
    assert dev_client.get("/api/orders").json()["orders"] == []


def test_order_rejects_changed_total(dev_client):
    plan = _best_plan(dev_client)
    res = _order(dev_client, plan, displayed_total=plan["grand_total"] - 1)
    assert res.status_code == 409 and res.json()["error"]["code"] == "total_changed"


def test_order_over_spending_cap(dev_client, monkeypatch):
    plan = _best_plan(dev_client)
    monkeypatch.setenv("MAX_ORDER_INR", "100")
    get_settings.cache_clear()
    res = _order(dev_client, plan)
    assert res.status_code == 422 and res.json()["error"]["code"] == "over_spending_cap"
    assert "₹100" in res.json()["error"]["message"]


def test_order_unknown_plan(dev_client):
    res = dev_client.post("/api/orders", json={"plan_id": "nope", "approved": True, "displayed_total": 1})
    assert res.status_code == 404


def test_order_needs_auth(client):
    assert client.post("/api/orders", json={"plan_id": "x", "approved": True, "displayed_total": 1}).status_code == 401
    assert client.get("/api/orders").status_code == 401


def test_place_order_end_to_end(dev_client):
    plan = _best_plan(dev_client, vouchers=True)
    repo = get_repository()
    products = {p["product_id"]: p for p in repo.products()}
    lines = [line for sp in plan["stores"] for line in sp["lines"]]
    stock_before = {line["product_id"]: products[line["product_id"]]["stock_qty"] for line in lines}
    used = [sp["voucher"]["voucher_id"] for sp in plan["stores"] if sp["voucher"]]
    assert used, "demo vouchers should apply to this list"

    res = _order(dev_client, plan)
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["orders"]) == len(plan["stores"])
    assert body["grand_total"] == plan["grand_total"]
    for order in body["orders"]:
        assert order["status"] == "placed" and order["payment_id"].startswith("sandbox_pay_")
    for line in lines:
        assert products[line["product_id"]]["stock_qty"] == stock_before[line["product_id"]] - line["qty"]
    statuses = {v["id"]: v["status"] for v in dev_client.get("/api/vouchers").json()["vouchers"]}
    assert all(statuses[v] == "used" for v in used)

    history = dev_client.get("/api/orders").json()
    assert {o["order_id"] for o in history["orders"]} == {o["order_id"] for o in body["orders"]}

    again = _order(dev_client, plan)
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_ordered"


def test_used_voucher_cannot_apply_twice(dev_client):
    first = _best_plan(dev_client, vouchers=True)
    list_id = _new_list(dev_client, ITEMS)
    second = dev_client.post("/api/optimise", json={"list_id": list_id, "explain": False}).json()["plans"][0]
    assert _order(dev_client, first).status_code == 200
    res = _order(dev_client, second)
    if any(sp["voucher"] for sp in second["stores"]):
        assert res.status_code == 409 and res.json()["error"]["code"] == "voucher_unavailable"
    else:
        pytest.skip("second plan used no voucher")


def test_sold_out_since_plan_was_made(dev_client):
    plan = _best_plan(dev_client)
    products = {p["product_id"]: p for p in get_repository().products()}
    line = plan["stores"][0]["lines"][0]
    products[line["product_id"]]["stock_qty"] = 0
    other = plan["stores"][-1]["lines"][-1]
    before = products[other["product_id"]]["stock_qty"]

    res = _order(dev_client, plan)
    assert res.status_code == 409 and res.json()["error"]["code"] == "out_of_stock"
    assert line["name"] in res.json()["error"]["message"]
    assert products[other["product_id"]]["stock_qty"] == before  # nothing decremented
    assert dev_client.get("/api/orders").json()["orders"] == []
