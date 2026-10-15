import pytest
from fastapi.testclient import TestClient

from app.agents.list_parser import get_list_parser
from app.config import get_settings
from app.db import get_repository
from app.main import create_app
from app.models.schemas import ParsedItem, ParsedList


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


@pytest.fixture
def fake_parser():
    return FakeParser()


@pytest.fixture
def client(monkeypatch, fake_parser):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setenv("DATASTORE", "memory")
    monkeypatch.delenv("AUTH_DISABLED", raising=False)
    get_settings.cache_clear()
    get_repository.cache_clear()
    app = create_app()
    app.dependency_overrides[get_list_parser] = lambda: fake_parser
    yield TestClient(app)
    get_settings.cache_clear()
    get_repository.cache_clear()


@pytest.fixture
def dev_client(client, monkeypatch):
    """Client with auth checks off, acting as "dev-user"."""
    monkeypatch.setenv("AUTH_DISABLED", "true")
    get_settings.cache_clear()
    return client
