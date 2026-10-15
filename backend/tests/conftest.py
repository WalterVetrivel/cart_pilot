import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()
