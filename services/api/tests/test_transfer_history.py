import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base


def test_transfer_history_is_paginated_and_user_scoped(tmp_path, monkeypatch):
    database_path = tmp_path / "transfer-history.db"
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

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/auth/register",
            json={
                "email": "transfer-history-owner@example.com",
                "password": "senha-forte-teste-123",
            },
        )
        second = client.post(
            "/api/v1/auth/register",
            json={
                "email": "transfer-history-other@example.com",
                "password": "senha-forte-teste-123",
            },
        )
        owner_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
        other_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

        source = client.post(
            "/api/v1/finance/accounts", headers=owner_headers,
            json={"name": "Origem", "account_type": "checking"},
        )
        destination = client.post(
            "/api/v1/finance/accounts", headers=owner_headers,
            json={"name": "Destino", "account_type": "savings"},
        )
        for index in range(2):
            response = client.post(
                "/api/v1/finance/transfers",
                headers=owner_headers,
                json={
                    "source_account_id": source.json()["id"],
                    "destination_account_id": destination.json()["id"],
                    "amount": "10.25",
                    "description": f"Transferência {index}",
                    "idempotency_key": f"history-transfer-key-{index:04d}",
                },
            )
            assert response.status_code == 201

        page = client.get("/api/v1/finance/transfers?limit=1&offset=0", headers=owner_headers)
        assert page.status_code == 200
        assert len(page.json()) == 1
        assert page.json()[0]["amount"] == "10.25"

        all_transfers = client.get("/api/v1/finance/transfers", headers=owner_headers)
        assert all_transfers.status_code == 200
        assert len(all_transfers.json()) == 2
        assert client.get("/api/v1/finance/transfers", headers=other_headers).json() == []

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
