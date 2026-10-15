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


def _now() -> str:
    return datetime.now(UTC).isoformat()


class MemoryRepository:
    def __init__(self) -> None:
        from seed.generate_seed import generate

        self._stores, self._products = generate()
        self._lists: dict[tuple[str, str], dict] = {}
        self._vouchers: dict[str, list[dict]] = {}
        self._plans: dict[tuple[str, str], dict] = {}

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


@lru_cache
def get_repository() -> Repository:
    settings = get_settings()
    if settings.use_firestore:
        return FirestoreRepository(settings.google_cloud_project)
    return MemoryRepository()
