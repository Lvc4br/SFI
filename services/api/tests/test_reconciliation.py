# ruff: noqa: E501
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'reconciliation.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(prepare())

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


def register(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_account(client, headers):
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta corrente", "account_type": "checking"},
    )
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Mercado", "category_type": "expense"},
    )
    assert account.status_code == category.status_code == 201
    return account.json(), category.json()


def test_statement_import_suggestions_match_and_idempotency(client):
    owner = register(client, "reconciliation-owner@example.com")
    account, category = setup_account(client, owner)
    transaction = client.post(
        "/api/v1/finance/transactions",
        headers=owner,
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "transaction_type": "expense",
            "amount": "25.90",
            "description": "Mercado Central",
            "occurred_at": "2026-11-17T12:00:00Z",
            "idempotency_key": "reconciliation-transaction-001",
        },
    )
    assert transaction.status_code == 201, transaction.text
    content = (
        "date,type,amount,description,external_id\n"
        "2026-11-17T13:00:00Z,expense,25.90,Mercado Central,bank-001\n"
    )
    payload = {
        "format": "csv",
        "content": content,
        "account_id": account["id"],
    }
    imported = client.post(
        "/api/v1/reconciliation/statements/import", headers=owner, json=payload
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["created"] == 1
    repeated = client.post(
        "/api/v1/reconciliation/statements/import", headers=owner, json=payload
    )
    assert repeated.status_code == 201
    assert repeated.json()["duplicates_skipped"] == 1

    entries = client.get("/api/v1/reconciliation/entries?entry_status=pending", headers=owner)
    assert entries.status_code == 200
    entry = entries.json()[0]
    suggestions = client.get(
        f"/api/v1/reconciliation/entries/{entry['id']}/suggestions", headers=owner
    )
    assert suggestions.status_code == 200
    assert suggestions.json()[0]["transaction_id"] == transaction.json()["id"]
    matched = client.post(
        f"/api/v1/reconciliation/entries/{entry['id']}/match",
        headers=owner,
        json={"transaction_id": transaction.json()["id"]},
    )
    assert matched.status_code == 200, matched.text
    assert matched.json()["status"] == "matched"
    summary = client.get("/api/v1/reconciliation/summary", headers=owner)
    assert summary.json()["entries_by_currency"][0]["matched"] == 1


def test_reconciliation_rejects_foreign_users_and_wrong_amount(client):
    owner = register(client, "reconciliation-owner2@example.com")
    other = register(client, "reconciliation-other@example.com")
    account, _ = setup_account(client, owner)
    other_account, other_category = setup_account(client, other)
    content = (
        "date,type,amount,description,external_id\n"
        "2026-11-17T12:00:00Z,expense,12.00,Compra,bank-foreign\n"
    )
    imported = client.post(
        "/api/v1/reconciliation/statements/import",
        headers=owner,
        json={"format": "csv", "content": content, "account_id": account["id"]},
    )
    entry = client.get("/api/v1/reconciliation/entries", headers=owner).json()[0]
    foreign = client.post(
        "/api/v1/finance/transactions",
        headers=other,
        json={
            "account_id": other_account["id"],
            "category_id": other_category["id"],
            "transaction_type": "expense",
            "amount": "12.00",
            "description": "Compra",
            "occurred_at": "2026-11-17T12:00:00Z",
            "idempotency_key": "foreign-reconciliation-transaction",
        },
    )
    assert imported.status_code == 201
    assert foreign.status_code == 201
    attempt = client.post(
        f"/api/v1/reconciliation/entries/{entry['id']}/match",
        headers=owner,
        json={"transaction_id": foreign.json()["id"]},
    )
    assert attempt.status_code == 404


def test_reconciliation_rejects_invalid_statement_atomically(client):
    owner = register(client, "reconciliation-invalid@example.com")
    account, _ = setup_account(client, owner)
    content = (
        "date,type,amount,description\n"
        "2026-11-17T12:00:00Z,expense,10.00,Valid\n"
        "bad-date,expense,20.00,Invalid\n"
    )
    response = client.post(
        "/api/v1/reconciliation/statements/import",
        headers=owner,
        json={"format": "csv", "content": content, "account_id": account["id"]},
    )
    assert response.status_code == 422
    assert client.get("/api/v1/reconciliation/entries", headers=owner).json() == []
