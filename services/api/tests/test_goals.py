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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'goals.db'}")
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


def create_goal(client, headers):
    response = client.post(
        "/api/v1/goals",
        headers=headers,
        json={
            "name": "Reserva de emergência",
            "description": "Reserva pessoal",
            "currency": "BRL",
            "target_amount": "5000.00",
            "target_date": "2027-12-31",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_goal_contribution_completion_withdrawal_and_history(client):
    headers = register(client, "goal-ledger@example.com")
    goal = create_goal(client, headers)
    url = f"/api/v1/goals/{goal['id']}/entries"
    contribution_payload = {
        "entry_type": "contribution",
        "amount": "5000.00",
        "description": "Aporte inicial",
        "occurred_at": "2026-11-16T12:00:00-03:00",
        "idempotency_key": "goal-contribution-000001",
    }
    contribution = client.post(url, headers=headers, json=contribution_payload)
    assert contribution.status_code == 201, contribution.text
    replay = client.post(url, headers=headers, json=contribution_payload)
    assert replay.status_code == 409

    completed = client.get(f"/api/v1/goals/{goal['id']}", headers=headers).json()
    assert completed["current_amount"] == "5000.00"
    assert completed["status"] == "completed"

    withdrawal = client.post(
        url,
        headers=headers,
        json={
            "entry_type": "withdrawal",
            "amount": "1250.00",
            "description": "Uso parcial da reserva",
            "occurred_at": "2026-11-17T12:00:00-03:00",
            "idempotency_key": "goal-withdrawal-000001",
        },
    )
    assert withdrawal.status_code == 201, withdrawal.text
    active = client.get(f"/api/v1/goals/{goal['id']}", headers=headers).json()
    assert active["current_amount"] == "3750.00"
    assert active["status"] == "active"

    history = client.get(url, headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_goal_withdrawal_cannot_exceed_balance_and_user_isolation(client):
    owner = register(client, "goal-owner@example.com")
    other = register(client, "goal-other@example.com")
    goal = create_goal(client, owner)
    url = f"/api/v1/goals/{goal['id']}"
    assert client.get(url, headers=other).status_code == 404
    assert client.get("/api/v1/goals", headers=other).json() == []

    rejected = client.post(
        f"{url}/entries",
        headers=owner,
        json={
            "entry_type": "withdrawal",
            "amount": "0.01",
            "occurred_at": "2026-11-16T12:00:00Z",
            "idempotency_key": "goal-withdrawal-too-much-0001",
        },
    )
    assert rejected.status_code == 422
    assert client.get(f"{url}/entries", headers=other).status_code == 404


def test_goal_validation_updates_and_archiving(client):
    headers = register(client, "goal-update@example.com")
    goal = create_goal(client, headers)
    updated = client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=headers,
        json={"target_amount": "7500.00", "name": "Reserva principal"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["target_amount"] == "7500.00"
    paused = client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=headers,
        json={"status": "paused"},
    )
    assert paused.json()["status"] == "paused"
    archived = client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=headers,
        json={"status": "archived"},
    )
    assert archived.json()["status"] == "archived"
    assert client.get("/api/v1/goals", headers=headers).json() == []
    assert client.get(
        "/api/v1/goals?include_archived=true", headers=headers
    ).json()[0]["status"] == "archived"
    assert client.patch(
        f"/api/v1/goals/{goal['id']}",
        headers=headers,
        json={"name": "Não permitido"},
    ).status_code == 409
