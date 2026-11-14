import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "sfi-pages-test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare_database():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(prepare_database())

    async def override_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    def test_settings() -> Settings:
        return Settings(jwt_secret_key="test-only-secret-key-with-at-least-32-bytes")

    monkeypatch.setattr("sfi_api.security.get_settings", test_settings)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


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


def test_transaction_page_handles_large_dataset_without_duplicates_or_gaps(client):
    owner = _register(client, "page-volume@example.com")
    account = client.post(
        "/api/v1/finance/accounts",
        headers=owner,
        json={"name": "Conta volume", "account_type": "checking"},
    ).json()

    for index in range(65):
        response = client.post(
            "/api/v1/finance/transactions",
            headers=owner,
            json={
                "account_id": account["id"],
                "transaction_type": "expense",
                "amount": "1.00",
                "description": f"Movimentação volume {index:03d}",
                "occurred_at": (
                    datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)
                    + timedelta(seconds=index)
                ).isoformat(),
                "idempotency_key": f"page-volume-key-{index:04d}",
            },
        )
        assert response.status_code == 201

    collected = []
    for offset in (0, 25, 50):
        response = client.get(
            f"/api/v1/finance/transactions/page?limit=25&offset={offset}",
            headers=owner,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 65
        collected.extend(item["id"] for item in payload["items"])
        assert payload["has_more"] is (offset < 50)

    assert len(collected) == 65
    assert len(set(collected)) == 65


def test_calendar_date_filters_use_the_users_timezone(client):
    headers = _register(client, "date-filter-timezone@example.com")
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    ).json()
    created = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "transaction_type": "expense",
            "amount": "5.00",
            "description": "Instante próximo à meia-noite",
            "occurred_at": "2026-11-01T02:00:00+00:00",
            "idempotency_key": "date-filter-timezone-0001",
        },
    )
    assert created.status_code == 201

    local_october = client.get(
        "/api/v1/finance/transactions/page?start_date=2026-10-31&end_date=2026-10-31",
        headers=headers,
    )
    local_november = client.get(
        "/api/v1/finance/transactions/page?start_date=2026-11-01&end_date=2026-11-01",
        headers=headers,
    )
    assert local_october.json()["total"] == 1
    assert local_november.json()["total"] == 0

    token = headers["Authorization"].removeprefix("Bearer ")
    changed = client.patch(
        "/api/v1/auth/me/timezone",
        headers={"Authorization": f"Bearer {token}"},
        json={"timezone": "UTC"},
    )
    assert changed.status_code == 200
    utc_november = client.get(
        "/api/v1/finance/transactions/page?start_date=2026-11-01&end_date=2026-11-01",
        headers=headers,
    )
    assert utc_november.json()["total"] == 1
