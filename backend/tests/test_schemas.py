from app.models.schemas import CartPlan, ShoppingList


def test_shopping_list_defaults():
    parsed = ShoppingList.model_validate(
        {"items": [{"canonical_name": "tomato", "original_text": "thakkali 1 kg", "quantity": 1, "unit": "kg"}]}
    )
    item = parsed.items[0]
    assert item.id and item.category == "other" and item.optional is False


def test_cart_plan_roundtrip():
    plan = CartPlan(label="best", stores=[], grand_total=0)
    assert CartPlan.model_validate_json(plan.model_dump_json()) == plan
