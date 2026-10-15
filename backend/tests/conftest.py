from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.agents.explainer import get_explainer
from app.agents.list_parser import get_list_parser
from app.agents.voucher_extractor import get_voucher_extractor
from app.config import get_settings
from app.db import get_repository
from app.main import create_app
from app.models.schemas import Explanation, ParsedItem, ParsedList, VoucherList
from app.services.gmail import get_email_fetcher

TODAY = date(2026, 10, 15)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """Demo vouchers expire on real dates, so pin "today" for the API."""
    monkeypatch.setattr("app.routers.vouchers.today", lambda: TODAY)
    monkeypatch.setattr("app.routers.optimise.today", lambda: TODAY)


class FakeParser:
    """Stands in for Gemini: records what it was sent, returns a fixed list."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.result = ParsedList(
            items=[
                ParsedItem(
                    canonical_name="tomato", original_text="thakkali 1 kg", quantity=1, unit="kg", category="vegetables"
                ),
                ParsedItem(
                    canonical_name="wheat flour", original_text="atta 5kg", quantity=5, unit="kg", category="staples"
                ),
                ParsedItem(canonical_name="dragon fruit", original_text="dragon fruit", category="fruits"),
            ],
            detected_language="mixed",
        )

    async def parse(self, text, blob, mime_type):
        self.calls.append({"text": text, "blob": blob, "mime_type": mime_type})
        return self.result


class FakeExplainer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def explain(self, plans, stores, language):
        self.calls.append({"plans": plans, "language": language})
        return Explanation(headline="Fake headline", bullets=["fake"])


class FakeExtractor:
    """Returns `result`, or raises like an unreachable Gemini when result is None."""

    def __init__(self) -> None:
        self.calls: list[list] = []
        self.result: VoucherList | None = None

    async def extract(self, emails):
        self.calls.append(emails)
        if self.result is None:
            raise RuntimeError("Gemini unavailable")
        return self.result


class FakeFetcher:
    def __init__(self) -> None:
        self.tokens: list[str] = []
        self.emails: list = []
        self.error: Exception | None = None

    def __call__(self, token):
        self.tokens.append(token)
        if self.error:
            raise self.error
        return self.emails


@pytest.fixture
def fake_extractor():
    return FakeExtractor()


@pytest.fixture
def fake_fetcher():
    return FakeFetcher()


@pytest.fixture
def fake_explainer():
    return FakeExplainer()


@pytest.fixture
def fake_parser():
    return FakeParser()


@pytest.fixture
def client(monkeypatch, fake_parser, fake_explainer, fake_extractor, fake_fetcher):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("DATASTORE", "memory")
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    get_settings.cache_clear()
    get_repository.cache_clear()
    app = create_app()
    app.dependency_overrides[get_list_parser] = lambda: fake_parser
    app.dependency_overrides[get_explainer] = lambda: fake_explainer
    app.dependency_overrides[get_voucher_extractor] = lambda: fake_extractor
    app.dependency_overrides[get_email_fetcher] = lambda: fake_fetcher
    yield TestClient(app)
    get_settings.cache_clear()
    get_repository.cache_clear()


@pytest.fixture
def dev_client(client, monkeypatch):
    """Client with auth checks off, acting as "dev-user"."""
    monkeypatch.setenv("AUTH_DISABLED", "true")
    get_settings.cache_clear()
    return client
