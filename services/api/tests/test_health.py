from fastapi.testclient import TestClient

from sfi_api.main import app


def test_liveness_endpoint() -> None:
    response = TestClient(app).get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "Sistema Financeiro Integrado"


def test_root_endpoint() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_api_responses_include_baseline_security_headers() -> None:
    response = TestClient(app).get("/api/v1/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_hsts_is_enabled_only_in_production(monkeypatch) -> None:
    monkeypatch.setattr("sfi_api.main.settings.environment", "production")
    response = TestClient(app).get("/api/v1/health/live")
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_hsts_is_not_enabled_in_development(monkeypatch) -> None:
    monkeypatch.setattr("sfi_api.main.settings.environment", "development")
    response = TestClient(app).get("/api/v1/health/live")
    assert "strict-transport-security" not in response.headers
