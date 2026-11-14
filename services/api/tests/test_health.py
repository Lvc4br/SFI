from fastapi.testclient import TestClient

from sfi_api.main import app


def test_liveness_endpoint() -> None:
    response = TestClient(app).get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app"] == "Sistema Financeiro Inteligente"


def test_root_endpoint() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
