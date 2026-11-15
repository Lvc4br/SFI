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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'shopping.db'}")
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
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_shopping_lists_items_favorites_and_user_isolation(client):
    owner = register(client, "shopping-owner@example.com")
    other = register(client, "shopping-other@example.com")

    created = client.post(
        "/api/v1/shopping/lists",
        headers=owner,
        json={"name": "Mercado da semana", "is_favorite": True},
    )
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]

    favorite_lists = client.get("/api/v1/shopping/lists?favorites_only=true", headers=owner)
    assert favorite_lists.status_code == 200
    assert len(favorite_lists.json()) == 1

    item = client.post(
        f"/api/v1/shopping/lists/{list_id}/items",
        headers=owner,
        json={"name": "Arroz", "quantity": "2.000", "unit": "kg", "unit_price": "7.50"},
    )
    assert item.status_code == 201, item.text
    assert item.json()["quantity"] == "2.000"

    checked = client.patch(
        f"/api/v1/shopping/lists/{list_id}/items/{item.json()['id']}",
        headers=owner,
        json={"is_checked": True},
    )
    assert checked.status_code == 200
    assert checked.json()["is_checked"] is True

    detail = client.get(f"/api/v1/shopping/lists/{list_id}", headers=owner)
    assert detail.status_code == 200
    assert len(detail.json()["items"]) == 1

    assert client.get("/api/v1/shopping/lists", headers=other).json() == []
    assert client.get(f"/api/v1/shopping/lists/{list_id}", headers=other).status_code == 404
    assert client.patch(
        f"/api/v1/shopping/lists/{list_id}/items/{item.json()['id']}",
        headers=other,
        json={"is_checked": False},
    ).status_code == 404


def test_shopping_rejects_invalid_item_values(client):
    headers = register(client, "shopping-invalid@example.com")
    shopping_list = client.post(
        "/api/v1/shopping/lists", headers=headers, json={"name": "Farmácia"}
    ).json()
    response = client.post(
        f"/api/v1/shopping/lists/{shopping_list['id']}/items",
        headers=headers,
        json={"name": "Vitamina", "quantity": "0", "unit_price": "-1"},
    )
    assert response.status_code == 422
