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
    database_path = tmp_path / "sfi-transaction-filters-test.db"
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
    monkeypatch.setattr(
        "sfi_api.security.get_settings",
        lambda: Settings(jwt_secret_key="test-only-secret-key-with-at-least-32-bytes"),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def test_transaction_filters_combine_and_keep_user_scope(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"email": "filters-owner@example.com", "password": "senha-forte-teste-123"},
    )
    other = client.post(
        "/api/v1/auth/register",
        json={"email": "filters-other@example.com", "password": "senha-forte-teste-123"},
    )
    headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    account_a = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta A", "account_type": "checking"},
    )
    account_b = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta B", "account_type": "cash"},
    )
    food = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Alimentação", "category_type": "expense"},
    )
    transport = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Transporte", "category_type": "expense"},
    )
    base_time = datetime(2027, 2, 1, 12, 0, tzinfo=UTC)

    payloads = [
        (account_a.json()["id"], food.json()["id"], "expense", "80.00", base_time),
        (account_a.json()["id"], food.json()["id"], "expense", "120.00", base_time + timedelta(days=1)),
        (account_b.json()["id"], transport.json()["id"], "expense", "35.00", base_time + timedelta(days=2)),
    ]
    for index, (account_id, category_id, transaction_type, amount, occurred_at) in enumerate(payloads):
        response = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "category_id": category_id,
                "transaction_type": transaction_type,
                "amount": amount,
                "description": f"Despesa {index}",
                "occurred_at": occurred_at.isoformat(),
                "idempotency_key": f"transaction-filter-key-{index:04d}",
            },
        )
        assert response.status_code == 201

    filtered = client.get(
        "/api/v1/finance/transactions",
        headers=headers,
        params={
            "account_id": account_a.json()["id"],
            "category_id": food.json()["id"],
            "transaction_type": "expense",
            "start_at": base_time.isoformat(),
            "end_at": (base_time + timedelta(days=1)).isoformat(),
            "min_amount": "80.00",
            "max_amount": "100.00",
        },
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["amount"] == "80.00"

    hidden = client.get(
        "/api/v1/finance/transactions",
        headers=other_headers,
        params={"account_id": account_a.json()["id"]},
    )
    assert hidden.status_code == 200
    assert hidden.json() == []


def test_transaction_filters_reject_invalid_ranges_and_naive_datetimes(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "filters-validation@example.com", "password": "senha-forte-teste-123"},
    )
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

    inverted_dates = client.get(
        "/api/v1/finance/transactions",
        headers=headers,
        params={
            "start_at": "2027-02-02T12:00:00+00:00",
            "end_at": "2027-02-01T12:00:00+00:00",
        },
    )
    inverted_amounts = client.get(
        "/api/v1/finance/transactions",
        headers=headers,
        params={"min_amount": "100.00", "max_amount": "50.00"},
    )
    naive_datetime = client.get(
        "/api/v1/finance/transactions",
        headers=headers,
        params={"start_at": "2027-02-01T12:00:00"},
    )
    assert inverted_dates.status_code == 422
    assert inverted_amounts.status_code == 422
    assert naive_datetime.status_code == 422
