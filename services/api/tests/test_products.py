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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'products.db'}")
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


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_product_catalog_and_price_history_are_user_scoped(client):
    owner = _register(client, "product-owner@example.com")
    other = _register(client, "product-other@example.com")

    created = client.post(
        "/api/v1/shopping/products",
        headers=owner,
        json={"name": "Arroz integral", "brand": "Marca teste", "unit": "kg"},
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    price = client.post(
        f"/api/v1/shopping/products/{product_id}/prices",
        headers=owner,
        json={
            "price": "12.90",
            "currency": "BRL",
            "merchant": "Mercado fictício",
            "source": "manual",
            "observed_at": "2026-11-15T10:00:00Z",
        },
    )
    assert price.status_code == 201, price.text
    assert price.json()["price"] == "12.90"

    history = client.get(
        f"/api/v1/shopping/products/{product_id}/prices", headers=owner
    )
    assert history.status_code == 200
    assert len(history.json()) == 1

    assert client.get("/api/v1/shopping/products", headers=other).json() == []
    assert client.get(
        f"/api/v1/shopping/products/{product_id}/prices", headers=other
    ).status_code == 404


def test_product_search_and_archive(client):
    owner = _register(client, "product-archive@example.com")
    created = client.post(
        "/api/v1/shopping/products",
        headers=owner,
        json={"name": "Leite sem lactose"},
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    assert len(client.get(
        "/api/v1/shopping/products?search=sem%20lactose", headers=owner
    ).json()) == 1
    archived = client.post(
        f"/api/v1/shopping/products/{product_id}/archive", headers=owner
    )
    assert archived.status_code == 200
    assert client.get("/api/v1/shopping/products", headers=owner).json() == []


def test_price_history_rejects_invalid_values_and_naive_timestamps(client):
    owner = _register(client, "product-validation@example.com")
    product = client.post(
        "/api/v1/shopping/products",
        headers=owner,
        json={"name": "Café"},
    ).json()
    url = f"/api/v1/shopping/products/{product['id']}/prices"

    invalid_price = client.post(
        url,
        headers=owner,
        json={"price": "-0.01", "observed_at": "2026-11-15T10:00:00Z"},
    )
    assert invalid_price.status_code == 422

    naive_timestamp = client.post(
        url,
        headers=owner,
        json={"price": "5.50", "observed_at": "2026-11-15T10:00:00"},
    )
    assert naive_timestamp.status_code == 422
