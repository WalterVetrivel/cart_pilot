"""Datastore access (SPEC §10).

MemoryRepository serves the seeded catalogue and keeps user data in process, so
the API runs with no Google services at all. FirestoreRepository talks to real
Firestore, or to the local emulator when FIRESTORE_EMULATOR_HOST is set.
"""

from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class Repository(Protocol):
    def stores(self) -> list[dict]: ...
    def products(self) -> list[dict]: ...
    def save_list(self, uid: str, list_id: str, data: dict) -> None: ...
    def get_list(self, uid: str, list_id: str) -> dict | None: ...
    def vouchers(self, uid: str) -> list[dict]: ...
    def save_plan(self, uid: str, plan_id: str, data: dict) -> None: ...
    def get_plan(self, uid: str, plan_id: str) -> dict | None: ...
    def update_plan(self, uid: str, plan_id: str, fields: dict) -> None: ...
    def replace_vouchers(self, uid: str, source: str, vouchers: list[dict]) -> None: ...
    def mark_vouchers_used(self, uid: str, voucher_ids: list[str]) -> None: ...
    def take_stock(self, wanted: dict[str, int]) -> list[str]: ...
    def save_order(self, uid: str, order_id: str, data: dict) -> None: ...
    def orders(self, uid: str) -> list[dict]: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _merge_vouchers(existing: list[dict], source: str, incoming: list[dict]) -> list[dict]:
    """Replace one source's vouchers, keeping a voucher 'used' if it was already used."""
    used = {v["id"] for v in existing if v.get("status") == "used"}
    kept = [v for v in existing if v.get("source") != source]
    fresh = [{**v, "status": "used" if v["id"] in used else v.get("status", "active")} for v in incoming]
    return kept + fresh


class MemoryRepository:
    def __init__(self) -> None:
        from seed.generate_seed import generate

        self._stores, self._products = generate()
        self._lists: dict[tuple[str, str], dict] = {}
        self._vouchers: dict[str, list[dict]] = {}
        self._plans: dict[tuple[str, str], dict] = {}
        self._orders: dict[str, list[dict]] = {}
        self._by_id = {p["product_id"]: p for p in self._products}

    def stores(self) -> list[dict]:
        return self._stores

    def products(self) -> list[dict]:
        return self._products

    def save_list(self, uid: str, list_id: str, data: dict) -> None:
        existing = self._lists.get((uid, list_id), {})
        self._lists[(uid, list_id)] = {"created_at": existing.get("created_at", _now()), **data}

    def get_list(self, uid: str, list_id: str) -> dict | None:
        return self._lists.get((uid, list_id))

    def vouchers(self, uid: str) -> list[dict]:
        return list(self._vouchers.get(uid, []))

    def save_plan(self, uid: str, plan_id: str, data: dict) -> None:
        self._plans[(uid, plan_id)] = {"created_at": _now(), **data}

    def get_plan(self, uid: str, plan_id: str) -> dict | None:
        return self._plans.get((uid, plan_id))

    def update_plan(self, uid: str, plan_id: str, fields: dict) -> None:
        self._plans[(uid, plan_id)].update(fields)

    def replace_vouchers(self, uid: str, source: str, vouchers: list[dict]) -> None:
        self._vouchers[uid] = _merge_vouchers(self._vouchers.get(uid, []), source, vouchers)

    def mark_vouchers_used(self, uid: str, voucher_ids: list[str]) -> None:
        for v in self._vouchers.get(uid, []):
            if v["id"] in voucher_ids:
                v["status"] = "used"

    def take_stock(self, wanted: dict[str, int]) -> list[str]:
        short = [pid for pid, qty in wanted.items() if self._by_id.get(pid, {}).get("stock_qty", 0) < qty]
        if short:
            return short
        for pid, qty in wanted.items():
            product = self._by_id[pid]
            product["stock_qty"] -= qty
            product["in_stock"] = product["stock_qty"] > 0
        return []

    def save_order(self, uid: str, order_id: str, data: dict) -> None:
        self._orders.setdefault(uid, []).append(data)

    def orders(self, uid: str) -> list[dict]:
        return sorted(self._orders.get(uid, []), key=lambda o: o["created_at"], reverse=True)


class FirestoreRepository:
    def __init__(self, project: str | None) -> None:
        from google.cloud import firestore

        self._db = firestore.Client(project=project)
        self._catalogue: tuple[list[dict], list[dict]] | None = None

    def _load_catalogue(self) -> tuple[list[dict], list[dict]]:
        # ~600 read-only docs: read once per instance.
        if self._catalogue is None:
            stores = [d.to_dict() for d in self._db.collection("stores").stream()]
            products = [d.to_dict() for d in self._db.collection("products").stream()]
            self._catalogue = (stores, products)
        return self._catalogue

    def stores(self) -> list[dict]:
        return self._load_catalogue()[0]

    def products(self) -> list[dict]:
        return self._load_catalogue()[1]

    def _list_ref(self, uid: str, list_id: str):
        return self._db.collection("users").document(uid).collection("lists").document(list_id)

    def save_list(self, uid: str, list_id: str, data: dict) -> None:
        ref = self._list_ref(uid, list_id)
        snap = ref.get()
        created = snap.get("created_at") if snap.exists else _now()
        ref.set({"created_at": created, **data})

    def get_list(self, uid: str, list_id: str) -> dict | None:
        snap = self._list_ref(uid, list_id).get()
        return snap.to_dict() if snap.exists else None

    def _user(self, uid: str):
        return self._db.collection("users").document(uid)

    def vouchers(self, uid: str) -> list[dict]:
        return [d.to_dict() for d in self._user(uid).collection("vouchers").stream()]

    def save_plan(self, uid: str, plan_id: str, data: dict) -> None:
        self._user(uid).collection("plans").document(plan_id).set({"created_at": _now(), **data})

    def get_plan(self, uid: str, plan_id: str) -> dict | None:
        snap = self._user(uid).collection("plans").document(plan_id).get()
        return snap.to_dict() if snap.exists else None

    def update_plan(self, uid: str, plan_id: str, fields: dict) -> None:
        self._user(uid).collection("plans").document(plan_id).update(fields)

    def replace_vouchers(self, uid: str, source: str, vouchers: list[dict]) -> None:
        col = self._user(uid).collection("vouchers")
        existing = [d.to_dict() for d in col.stream()]
        merged = _merge_vouchers(existing, source, vouchers)
        batch = self._db.batch()
        for v in existing:
            if v.get("source") == source:
                batch.delete(col.document(v["id"]))
        for v in merged:
            if v.get("source") == source:
                batch.set(col.document(v["id"]), v)
        batch.commit()

    def mark_vouchers_used(self, uid: str, voucher_ids: list[str]) -> None:
        col = self._user(uid).collection("vouchers")
        for vid in voucher_ids:
            col.document(vid).update({"status": "used"})

    def take_stock(self, wanted: dict[str, int]) -> list[str]:
        from google.cloud import firestore

        refs = {pid: self._db.collection("products").document(pid) for pid in wanted}

        @firestore.transactional
        def run(tx) -> list[str]:
            snaps = {pid: ref.get(transaction=tx) for pid, ref in refs.items()}
            short = [pid for pid, snap in snaps.items() if not snap.exists or snap.get("stock_qty") < wanted[pid]]
            if short:
                return short
            for pid, snap in snaps.items():
                left = snap.get("stock_qty") - wanted[pid]
                tx.update(refs[pid], {"stock_qty": left, "in_stock": left > 0})
            return []

        short = run(self._db.transaction())
        if not short and self._catalogue is not None:
            # Keep this instance's cached catalogue in step without re-reading every product.
            for product in self._catalogue[1]:
                if product["product_id"] in wanted:
                    product["stock_qty"] -= wanted[product["product_id"]]
                    product["in_stock"] = product["stock_qty"] > 0
        return short

    def save_order(self, uid: str, order_id: str, data: dict) -> None:
        self._user(uid).collection("orders").document(order_id).set(data)

    def orders(self, uid: str) -> list[dict]:
        docs = [d.to_dict() for d in self._user(uid).collection("orders").stream()]
        return sorted(docs, key=lambda o: o["created_at"], reverse=True)


@lru_cache
def get_repository() -> Repository:
    settings = get_settings()
    if settings.use_firestore:
        return FirestoreRepository(settings.google_cloud_project)
    return MemoryRepository()
