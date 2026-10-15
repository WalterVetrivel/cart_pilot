def test_health_is_public(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "model": "test-model"}


def test_protected_route_requires_token(client):
    res = client.get("/api/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthenticated"


def test_auth_disabled_for_local_dev(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("AUTH_DISABLED", "true")
    get_settings.cache_clear()
    res = client.get("/api/me")
    assert res.status_code == 200
    assert res.json()["uid"] == "dev-user"
