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
    database_path = tmp_path / "sfi-test.db"
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


def test_register_login_and_authenticated_profile(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "  Luca@Example.com ", "password": "uma-senha-forte-123"},
    )
    assert registered.status_code == 201
    body = registered.json()
    assert body["user"]["email"] == "luca@example.com"
    assert body["token_type"] == "bearer"
    assert "password_hash" not in body["user"]

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "LUCA@example.com", "password": "uma-senha-forte-123"},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]

    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "luca@example.com"


def test_duplicate_email_is_rejected(client):
    payload = {"email": "luca@example.com", "password": "uma-senha-forte-123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "LUCA@example.com", "password": "outra-senha-forte-456"},
    )
    assert duplicate.status_code == 409


def test_invalid_credentials_and_protected_route(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "senha-incorreta"},
    )
    assert response.status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


def test_registration_requires_strong_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_logout_revokes_only_the_current_access_token(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "logout@example.com", "password": "uma-senha-forte-123"},
    )
    assert registered.status_code == 201
    original_token = registered.json()["access_token"]
    original_headers = {"Authorization": f"Bearer {original_token}"}

    assert client.get("/api/v1/auth/me", headers=original_headers).status_code == 200

    logged_out = client.post("/api/v1/auth/logout", headers=original_headers)
    assert logged_out.status_code == 204
    assert client.get("/api/v1/auth/me", headers=original_headers).status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "logout@example.com", "password": "uma-senha-forte-123"},
    )
    assert new_login.status_code == 200
    new_headers = {"Authorization": f"Bearer {new_login.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200
