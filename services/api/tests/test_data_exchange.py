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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'exchange.db'}")
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
        json={"name": "Conta principal", "account_type": "checking"},
    )
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Mercado", "category_type": "expense"},
    )
    assert account.status_code == category.status_code == 201
    return account.json(), category.json()


def test_csv_preview_import_and_idempotent_reimport(client):
    headers = register(client, "exchange-owner@example.com")
    account, category = setup_account(client, headers)
    content = (
        "date,type,amount,description,account_id,category_id,external_id\n"
        (
            f"2026-11-16T12:00:00Z,expense,35.50,Compra mercado,"
            f"{account['id']},{category['id']},bank-001\n"
        )
        f"2026-11-17T12:00:00Z,expense,12.00,Café,{account['id']},{category['id']},bank-002\n"
        f"2026-11-17T12:00:00Z,expense,12.00,Café,{account['id']},{category['id']},bank-002\n"
    )
    payload = {
        "format": "csv",
        "content": content,
    }
    preview = client.post("/api/v1/exchange/transactions/preview", headers=headers, json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["total"] == 3
    assert preview.json()["valid"] == 2
    assert preview.json()["duplicates"] == 1
    assert preview.json()["invalid"] == 0

    imported = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": True},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["created"] == 2
    assert imported.json()["duplicates_skipped"] == 1

    repeated = client.post("/api/v1/exchange/transactions/preview", headers=headers, json=payload)
    assert repeated.json()["valid"] == 0
    assert repeated.json()["duplicates"] == 3

    replay = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": True},
    )
    assert replay.status_code == 201
    assert replay.json()["created"] == 0
    assert replay.json()["duplicates_skipped"] == 3
    assert len(client.get("/api/v1/finance/transactions", headers=headers).json()) == 2


def test_import_requires_confirmation_and_invalid_rows_abort_atomically(client):
    headers = register(client, "exchange-invalid@example.com")
    account, category = setup_account(client, headers)
    content = (
        "date,type,amount,description,account_id,category_id\n"
        f"2026-11-16T12:00:00Z,expense,25.00,Compra válida,{account['id']},{category['id']}\n"
        f"not-a-date,expense,5.00,Data errada,{account['id']},{category['id']}\n"
    )
    payload = {"format": "csv", "content": content}
    no_confirm = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": False},
    )
    assert no_confirm.status_code == 409
    invalid = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": True},
    )
    assert invalid.status_code == 422
    assert client.get("/api/v1/finance/transactions", headers=headers).json() == []


def test_ofx_import_export_and_user_isolation(client):
    owner = register(client, "exchange-ofx@example.com")
    other = register(client, "exchange-other@example.com")
    account, category = setup_account(client, owner)
    ofx = (
        "<OFX><BANKTRANLIST><STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20261116120000"
        "<TRNAMT>-18.90<FITID>ofx-001<NAME>Farmácia<MEMO>Compra mensal"
        "</STMTTRN></BANKTRANLIST></OFX>"
    )
    payload = {
        "format": "ofx",
        "content": ofx,
        "default_account_id": account["id"],
        "default_category_id": category["id"],
    }
    preview = client.post("/api/v1/exchange/transactions/preview", headers=owner, json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"] == 1
    imported = client.post(
        "/api/v1/exchange/transactions/import",
        headers=owner,
        json={**payload, "confirmed": True},
    )
    assert imported.status_code == 201, imported.text

    csv_export = client.get("/api/v1/exchange/transactions/export?format=csv", headers=owner)
    json_export = client.get("/api/v1/exchange/transactions/export?format=json", headers=owner)
    assert csv_export.status_code == 200
    assert "Farmácia" in csv_export.text
    assert json_export.status_code == 200
    assert len(json_export.json()) == 1
    assert client.get(
        "/api/v1/exchange/transactions/export?format=json", headers=other
    ).json() == []


def test_import_rejects_foreign_account_and_file_size_limit(client):
    owner = register(client, "exchange-owner2@example.com")
    other = register(client, "exchange-other2@example.com")
    account, _ = setup_account(client, other)
    content = (
        "date,type,amount,description,account_id\n"
        f"2026-11-16T12:00:00Z,expense,1.00,Conta alheia,{account['id']}\n"
    )
    preview = client.post(
        "/api/v1/exchange/transactions/preview",
        headers=owner,
        json={"format": "csv", "content": content},
    )
    assert preview.status_code == 200
    assert preview.json()["invalid"] == 1
    too_large = client.post(
        "/api/v1/exchange/transactions/preview",
        headers=owner,
        json={"format": "csv", "content": "x" * (5 * 1024 * 1024 + 1)},
    )
    assert too_large.status_code == 413
