"""Deterministic mock marketplace (SPEC §7).

    python -m seed.generate_seed      # writes seed/data/{stores,products}.json

The same generator also feeds the in-memory datastore and `seed.load`, so the
catalogue is identical everywhere. Random seed is fixed at 42.
"""

import json
import random
import re
from pathlib import Path

SEED = 42
DATA_DIR = Path(__file__).parent / "data"

# Fees and rules from the SPEC §7 table. Prices are multipliers on a baseline.
STORES: list[dict] = [
    {
        "store_id": "freshmart",
        "name": "FreshMart",
        "type": "Supermarket",
        "delivery_fee": 40,
        "free_delivery_at": 600,
        "min_order": 200,
        "small_cart_fee": 0,
        "small_cart_below": 0,
        "eta_label": "Next day slots",
        "eta_minutes": 1440,
        "price_range": (1.0, 1.0),
        "rating_range": (3.7, 4.4),
    },
    {
        "store_id": "quickbasket",
        "name": "QuickBasket",
        "type": "10-minute delivery",
        "delivery_fee": 25,
        "free_delivery_at": 399,
        "min_order": 99,
        "small_cart_fee": 15,
        "small_cart_below": 199,
        "eta_label": "12 min",
        "eta_minutes": 12,
        "price_range": (1.08, 1.15),
        "rating_range": (4.2, 4.8),
    },
    {
        "store_id": "megabazaar",
        "name": "MegaBazaar",
        "type": "Online marketplace",
        "delivery_fee": 49,
        "free_delivery_at": 499,
        "min_order": 0,
        "small_cart_fee": 0,
        "small_cart_below": 0,
        "eta_label": "2 days",
        "eta_minutes": 2880,
        "price_range": (0.88, 0.95),
        "rating_range": (2.6, 4.7),
    },
    {
        "store_id": "kiranaconnect",
        "name": "Kirana Connect",
        "type": "Local stores network",
        "delivery_fee": 20,
        "free_delivery_at": 300,
        "min_order": 150,
        "small_cart_fee": 0,
        "small_cart_below": 0,
        "eta_label": "45 min",
        "eta_minutes": 45,
        "price_range": (0.95, 0.98),
        "rating_range": (3.6, 4.3),
    },
]

# canonical item -> (category, [(pack_size, pack_unit, baseline price ₹), ...])
ITEMS: dict[str, tuple[str, list[tuple[float, str, float]]]] = {
    # vegetables
    "onion": ("vegetables", [(1, "kg", 40), (2, "kg", 76)]),
    "tomato": ("vegetables", [(500, "g", 20), (1, "kg", 38)]),
    "potato": ("vegetables", [(1, "kg", 35), (2, "kg", 66)]),
    "carrot": ("vegetables", [(500, "g", 30), (1, "kg", 56)]),
    "green chilli": ("vegetables", [(100, "g", 10), (250, "g", 22)]),
    "ginger": ("vegetables", [(100, "g", 18), (250, "g", 40)]),
    "garlic": ("vegetables", [(100, "g", 25), (250, "g", 58)]),
    "coriander leaves": ("vegetables", [(100, "g", 15), (200, "g", 26)]),
    "curry leaves": ("vegetables", [(50, "g", 8), (100, "g", 14)]),
    "brinjal": ("vegetables", [(500, "g", 30), (1, "kg", 55)]),
    "okra": ("vegetables", [(250, "g", 18), (500, "g", 34)]),
    "cauliflower": ("vegetables", [(1, "pcs", 40), (2, "pcs", 75)]),
    "cabbage": ("vegetables", [(1, "pcs", 35), (2, "pcs", 66)]),
    "beans": ("vegetables", [(250, "g", 25), (500, "g", 46)]),
    # fruits
    "banana": ("fruits", [(6, "pcs", 40), (12, "pcs", 75)]),
    "apple": ("fruits", [(500, "g", 90), (1, "kg", 170)]),
    "orange": ("fruits", [(500, "g", 60), (1, "kg", 110)]),
    "pomegranate": ("fruits", [(500, "g", 95), (1, "kg", 180)]),
    "grapes": ("fruits", [(500, "g", 60), (1, "kg", 112)]),
    "lemon": ("fruits", [(4, "pcs", 20), (8, "pcs", 36)]),
    "papaya": ("fruits", [(1, "pcs", 55), (2, "pcs", 104)]),
    # dairy
    "milk": ("dairy", [(500, "ml", 30), (1, "l", 58)]),
    "curd": ("dairy", [(400, "g", 45), (1, "kg", 95)]),
    "paneer": ("dairy", [(200, "g", 90), (500, "g", 210)]),
    "butter": ("dairy", [(100, "g", 58), (500, "g", 275)]),
    "ghee": ("dairy", [(500, "ml", 320), (1, "l", 620)]),
    "cheese slices": ("dairy", [(200, "g", 140), (400, "g", 270)]),
    "eggs": ("dairy", [(6, "pcs", 48), (12, "pcs", 90), (30, "pcs", 210)]),
    "buttermilk": ("dairy", [(200, "ml", 15), (500, "ml", 30)]),
    # staples
    "rice": ("staples", [(1, "kg", 70), (5, "kg", 330), (10, "kg", 640)]),
    "basmati rice": ("staples", [(1, "kg", 140), (5, "kg", 650)]),
    "wheat flour": ("staples", [(1, "kg", 55), (5, "kg", 260), (10, "kg", 500)]),
    "toor dal": ("staples", [(500, "g", 85), (1, "kg", 165)]),
    "moong dal": ("staples", [(500, "g", 80), (1, "kg", 155)]),
    "urad dal": ("staples", [(500, "g", 82), (1, "kg", 158)]),
    "chana dal": ("staples", [(500, "g", 55), (1, "kg", 105)]),
    "semolina": ("staples", [(500, "g", 35), (1, "kg", 66)]),
    "poha": ("staples", [(500, "g", 40), (1, "kg", 76)]),
    "sugar": ("staples", [(1, "kg", 48), (5, "kg", 230)]),
    "salt": ("staples", [(1, "kg", 28), (2, "kg", 54)]),
    "jaggery": ("staples", [(500, "g", 55), (1, "kg", 105)]),
    "sunflower oil": ("staples", [(1, "l", 155), (5, "l", 740)]),
    "groundnut oil": ("staples", [(1, "l", 190), (5, "l", 920)]),
    "turmeric powder": ("staples", [(100, "g", 30), (200, "g", 56)]),
    "chilli powder": ("staples", [(100, "g", 38), (200, "g", 72)]),
    "coriander powder": ("staples", [(100, "g", 28), (200, "g", 52)]),
    "garam masala": ("staples", [(50, "g", 45), (100, "g", 85)]),
    "tamarind": ("staples", [(200, "g", 45), (500, "g", 105)]),
    # snacks
    "biscuits": ("snacks", [(1, "pack", 30), (3, "pack", 85)]),
    "namkeen": ("snacks", [(200, "g", 50), (400, "g", 95)]),
    "potato chips": ("snacks", [(52, "g", 20), (90, "g", 40)]),
    "instant noodles": ("snacks", [(1, "pack", 14), (4, "pack", 54)]),
    "bread": ("snacks", [(400, "g", 45), (800, "g", 85)]),
    "cornflakes": ("snacks", [(475, "g", 180), (875, "g", 320)]),
    "oats": ("snacks", [(500, "g", 99), (1, "kg", 185)]),
    "chocolate": ("snacks", [(50, "g", 50), (150, "g", 140)]),
    # beverages
    "tea": ("beverages", [(250, "g", 140), (500, "g", 270), (1, "kg", 520)]),
    "coffee": ("beverages", [(100, "g", 180), (200, "g", 340)]),
    "green tea": ("beverages", [(25, "pcs", 150), (100, "pcs", 520)]),
    "fruit juice": ("beverages", [(1, "l", 110), (2, "l", 210)]),
    "soft drink": ("beverages", [(750, "ml", 40), (2, "l", 95)]),
    "mineral water": ("beverages", [(1, "l", 20), (5, "l", 75)]),
    "health drink": ("beverages", [(500, "g", 250), (1, "kg", 480)]),
    # household
    "detergent": ("household", [(1, "kg", 120), (4, "kg", 450)]),
    "dishwash liquid": ("household", [(500, "ml", 105), (750, "ml", 150)]),
    "floor cleaner": ("household", [(500, "ml", 99), (1, "l", 185)]),
    "toilet cleaner": ("household", [(500, "ml", 95), (1, "l", 180)]),
    "garbage bags": ("household", [(1, "pack", 90), (3, "pack", 250)]),
    "tissue paper": ("household", [(1, "pack", 60), (4, "pack", 220)]),
    # personal care
    "soap": ("personal_care", [(1, "pcs", 40), (4, "pcs", 150)]),
    "toothpaste": ("personal_care", [(100, "g", 55), (200, "g", 105)]),
    "shampoo": ("personal_care", [(180, "ml", 150), (340, "ml", 270)]),
    "toothbrush": ("personal_care", [(1, "pcs", 30), (4, "pcs", 99)]),
    "hand wash": ("personal_care", [(200, "ml", 99), (750, "ml", 250)]),
    "coconut oil": ("personal_care", [(250, "ml", 110), (500, "ml", 210)]),
}

# Invented brand names only (SPEC §7: no real brands).
BRANDS: dict[str, list[str]] = {
    "vegetables": ["Farm Fresh", "Green Basket", "Village Harvest"],
    "fruits": ["Orchard Gold", "Farm Fresh", "Sunny Grove"],
    "dairy": ["Pasture Pure", "Morning Dew", "Green Meadow"],
    "staples": ["Golden Harvest", "Kaveri Fields", "Nandi Select"],
    "snacks": ["Crunchy Co", "Tiffin Time", "Masala Magic"],
    "beverages": ["Hill Estate", "Chai Point Gold", "Brewmaster"],
    "household": ["SparkleHome", "CleanEdge", "Pristine"],
    "personal_care": ["Herbal Glow", "PureSmile", "Neem Naturals"],
}

OUT_OF_STOCK_RATE = 0.08
MISSING_ITEM_RATE = 0.06  # chance a store does not carry an item at all


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _size_label(size: float, unit: str) -> str:
    size_txt = f"{size:g}"
    return f"{size_txt} {unit}" if unit in ("pcs", "pack") else f"{size_txt}{unit}"


def public_store(store: dict) -> dict:
    """Store document without generator-only fields."""
    return {k: v for k, v in store.items() if k not in ("price_range", "rating_range")}


def generate() -> tuple[list[dict], list[dict]]:
    """Returns (stores, products). Deterministic for a given SEED."""
    rng = random.Random(SEED)
    products: list[dict] = []

    for item, (category, variants) in ITEMS.items():
        brands = BRANDS[category]
        # Make sure every item is carried by at least two stores.
        carriers = [s for s in STORES if rng.random() >= MISSING_ITEM_RATE]
        while len(carriers) < 2:
            extra = rng.choice([s for s in STORES if s not in carriers])
            carriers.append(extra)
            carriers.sort(key=STORES.index)

        for store in carriers:
            lo, hi = store["price_range"]
            r_lo, r_hi = store["rating_range"]
            for idx, (size, unit, base_price) in enumerate(variants):
                brand = brands[(idx + STORES.index(store)) % len(brands)]
                mrp = round(base_price * 1.1)
                price = round(base_price * rng.uniform(lo, hi))
                rating_count = int(rng.choice([rng.randint(3, 19), rng.randint(20, 5000)]))
                in_stock = rng.random() >= OUT_OF_STOCK_RATE
                products.append(
                    {
                        "product_id": f"{store['store_id']}-{_slug(item)}-{idx + 1}",
                        "store_id": store["store_id"],
                        "canonical_item": item,
                        "name": f"{brand} {item.title()} {_size_label(size, unit)}",
                        "brand": brand,
                        "category": category,
                        "pack_size": size,
                        "pack_unit": unit,
                        "price": float(min(price, mrp)),
                        "mrp": float(mrp),
                        "rating": round(rng.uniform(r_lo, r_hi), 1),
                        "rating_count": rating_count,
                        "in_stock": in_stock,
                        "stock_qty": rng.randint(5, 80) if in_stock else 0,
                    }
                )

    return [public_store(s) for s in STORES], products


def main() -> None:
    stores, products = generate()
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "stores.json").write_text(json.dumps(stores, indent=2) + "\n")
    (DATA_DIR / "products.json").write_text(json.dumps(products, indent=1) + "\n")
    print(f"{len(stores)} stores, {len(ITEMS)} canonical items, {len(products)} products -> {DATA_DIR}")


if __name__ == "__main__":
    main()
