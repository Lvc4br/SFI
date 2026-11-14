import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "sfi-finance-test.db"
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


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_account_category_and_transaction_flow(client):
    token = register(client, "owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta principal", "account_type": "checking", "opening_balance": "1000.00"},
    )
    assert account.status_code == 201
    account_id = account.json()["id"]

    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Moradia", "category_type": "expense"},
    )
    assert category.status_code == 201

    transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": category.json()["id"],
            "transaction_type": "expense",
            "amount": "125.90",
            "description": "Conta de energia",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": "finance-test-key-0001",
        },
    )
    assert transaction.status_code == 201
    assert transaction.json()["amount"] == "125.90"
    assert transaction.json()["currency"] == "BRL"

    listing = client.get("/api/v1/finance/transactions", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_financial_data_is_isolated_between_users(client):
    owner_token = register(client, "owner2@example.com")
    other_token = register(client, "other@example.com")

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    account = client.post(
        "/api/v1/finance/accounts",
        headers=owner_headers,
        json={"name": "Conta privada", "account_type": "checking"},
    )
    account_id = account.json()["id"]

    assert client.get("/api/v1/finance/accounts", headers=other_headers).json() == []
    foreign_transaction = client.post(
        "/api/v1/finance/transactions",
        headers=other_headers,
        json={
            "account_id": account_id,
            "transaction_type": "expense",
            "amount": "1.00",
            "description": "Tentativa de acesso",
            "idempotency_key": "foreign-user-key-001",
        },
    )
    assert foreign_transaction.status_code == 404


def test_transactions_reject_duplicate_idempotency_key(client):
    token = register(client, "idem@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Carteira", "account_type": "cash"},
    )
    payload = {
        "account_id": account.json()["id"],
        "transaction_type": "income",
        "amount": "250.00",
        "description": "Pagamento",
        "idempotency_key": "same-key-finance-0001",
    }
    assert client.post("/api/v1/finance/transactions", headers=headers, json=payload).status_code == 201
    assert client.post("/api/v1/finance/transactions", headers=headers, json=payload).status_code == 409


def test_transactions_are_append_only(client):
    token = register(client, "append@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    )
    created = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "income",
            "amount": "300.00",
            "description": "Salário",
            "idempotency_key": "append-only-key-0001",
        },
    )
    assert created.status_code == 201
    assert client.patch(
        f"/api/v1/finance/transactions/{created.json()['id']}",
        headers=headers,
        json={"amount": "999.99"},
    ).status_code == 405
