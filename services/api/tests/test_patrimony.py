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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'patrimony.db'}")
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


def test_patrimony_net_worth_history_and_currency_separation(client):
    headers = register(client, "patrimony@example.com")
    house = client.post(
        "/api/v1/patrimony",
        headers=headers,
        json={"name": "Apartamento", "item_kind": "asset", "category": "property"},
    )
    loan = client.post(
        "/api/v1/patrimony",
        headers=headers,
        json={"name": "Financiamento", "item_kind": "liability", "category": "financing"},
    )
    foreign = client.post(
        "/api/v1/patrimony",
        headers=headers,
        json={"name": "Conta em dólar", "item_kind": "asset", "category": "cash", "currency": "USD"},
    )
    assert house.status_code == loan.status_code == foreign.status_code == 201
    def valuation(item_id, amount, key, day):
        return client.post(
            f"/api/v1/patrimony/{item_id}/valuations",
            headers=headers,
            json={
                "amount": amount,
                "idempotency_key": key,
                "valued_at": f"{day}T12:00:00-03:00",
            },
        )
    assert valuation(house.json()["id"], "500000.00", "patrimony-house-0001", "2026-10-01").status_code == 201
    assert valuation(loan.json()["id"], "300000.00", "patrimony-loan-0001", "2026-10-01").status_code == 201
    assert valuation(foreign.json()["id"], "1000.00", "patrimony-usd-00001", "2026-10-01").status_code == 201
    assert valuation(house.json()["id"], "520000.00", "patrimony-house-0002", "2026-11-01").status_code == 201

    summary = client.get("/api/v1/patrimony/summary?as_of=2026-11-17", headers=headers)
    assert summary.status_code == 200, summary.text
    by_currency = {row["currency"]: row for row in summary.json()["currencies"]}
    assert by_currency["BRL"]["assets_total"] == "520000.00"
    assert by_currency["BRL"]["liabilities_total"] == "300000.00"
    assert by_currency["BRL"]["net_worth"] == "220000.00"
    assert by_currency["USD"]["net_worth"] == "1000.00"

    history = client.get("/api/v1/patrimony/history", headers=headers)
    assert history.status_code == 200, history.text
    assert [row["as_of"] for row in history.json()] == ["2026-10-01", "2026-11-01"]
    october = {row["currency"]: row for row in history.json()[0]["currencies"]}
    assert october["BRL"]["net_worth"] == "200000.00"


def test_patrimony_idempotency_and_user_isolation(client):
    owner = register(client, "patrimony-owner@example.com")
    other = register(client, "patrimony-other@example.com")
    item = client.post(
        "/api/v1/patrimony",
        headers=owner,
        json={"name": "Carro", "item_kind": "asset", "category": "vehicle"},
    )
    item_id = item.json()["id"]
    payload = {
        "amount": "80000.00",
        "idempotency_key": "patrimony-car-value-0001",
        "valued_at": "2026-11-17T12:00:00Z",
    }
    url = f"/api/v1/patrimony/{item_id}/valuations"
    assert client.post(url, headers=owner, json=payload).status_code == 201
    assert client.post(url, headers=owner, json=payload).status_code == 409
    assert client.get(f"/api/v1/patrimony/{item_id}/valuations", headers=other).status_code == 404
    assert client.get("/api/v1/patrimony", headers=other).json() == []
    assert client.get("/api/v1/patrimony/summary", headers=other).json()["currencies"] == []


def test_patrimony_rejects_naive_timestamp_and_invalid_date_range(client):
    headers = register(client, "patrimony-validation@example.com")
    item = client.post(
        "/api/v1/patrimony",
        headers=headers,
        json={"name": "Reserva", "item_kind": "asset", "category": "cash"},
    ).json()
    response = client.post(
        f"/api/v1/patrimony/{item['id']}/valuations",
        headers=headers,
        json={"amount": "0", "idempotency_key": "patrimony-naive-date-0001", "valued_at": "2026-11-17T12:00:00"},
    )
    assert response.status_code == 422
    assert client.get(
        "/api/v1/patrimony/history?start_date=2026-12-01&end_date=2026-11-01",
        headers=headers,
    ).status_code == 422
