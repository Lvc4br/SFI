from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_transaction_page_filters_orders_and_paginates_per_user(client):
    owner = _register(client, "page-owner@example.com")
    other = _register(client, "page-other@example.com")
    account = client.post(
        "/api/v1/finance/accounts",
        headers=owner,
        json={"name": "Conta paginada", "account_type": "checking"},
    ).json()
    category = client.post(
        "/api/v1/finance/categories",
        headers=owner,
        json={"name": "Mercado", "category_type": "expense"},
    ).json()

    for index, amount in enumerate(("10.00", "20.00", "30.00")):
        response = client.post(
            "/api/v1/finance/transactions",
            headers=owner,
            json={
                "account_id": account["id"],
                "category_id": category["id"],
                "transaction_type": "expense",
                "amount": amount,
                "description": f"Compra {index}",
                "occurred_at": datetime(2026, 11, 10 + index, 12, tzinfo=UTC).isoformat(),
                "idempotency_key": f"pagination-test-key-{index:04d}",
            },
        )
        assert response.status_code == 201

    first = client.get(
        "/api/v1/finance/transactions/page?limit=2&offset=0&transaction_type=expense",
        headers=owner,
    )
    assert first.status_code == 200
    assert first.json()["total"] == 3
    assert first.json()["has_more"] is True
    assert [item["amount"] for item in first.json()["items"]] == ["30.00", "20.00"]

    second = client.get(
        "/api/v1/finance/transactions/page?limit=2&offset=2&transaction_type=expense",
        headers=owner,
    )
    assert second.status_code == 200
    assert second.json()["has_more"] is False
    assert [item["amount"] for item in second.json()["items"]] == ["10.00"]

    filtered = client.get(
        f"/api/v1/finance/transactions/page?category_id={category['id']}&min_amount=20",
        headers=owner,
    )
    assert filtered.json()["total"] == 2

    isolated = client.get("/api/v1/finance/transactions/page", headers=other)
    assert isolated.status_code == 200
    assert isolated.json()["total"] == 0
    assert isolated.json()["items"] == []


def test_transaction_page_rejects_invalid_ranges(client):
    headers = _register(client, "page-validation@example.com")
    response = client.get(
        "/api/v1/finance/transactions/page?start_at=2026-11-20T00:00:00Z&end_at=2026-11-01T00:00:00Z",
        headers=headers,
    )
    assert response.status_code == 422
