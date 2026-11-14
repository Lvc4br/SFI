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
    assert body["refresh_token"]
    assert "password_hash" not in body["user"]

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "LUCA@example.com", "password": "uma-senha-forte-123"},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]
    assert logged_in.json()["refresh_token"]

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


def test_refresh_token_rotates_and_reuse_revokes_family(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "uma-senha-forte-123"},
    )
    assert registered.status_code == 201
    original = registered.json()["refresh_token"]

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert rotated.status_code == 200
    replacement = rotated.json()["refresh_token"]
    assert replacement != original
    assert client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {rotated.json()['access_token']}"},
    ).status_code == 200

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert reused.status_code == 401
    family_revoked = client.post("/api/v1/auth/refresh", json={"refresh_token": replacement})
    assert family_revoked.status_code == 401


def test_unknown_refresh_token_is_rejected(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "x" * 64},
    )
    assert response.status_code == 401


def test_logout_revokes_refresh_token_family(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "logout-refresh@example.com", "password": "uma-senha-forte-123"},
    )
    assert registered.status_code == 201
    body = registered.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}

    logged_out = client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": body["refresh_token"]},
    )
    assert logged_out.status_code == 204

    refresh_attempt = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert refresh_attempt.status_code == 401


def test_logout_does_not_revoke_another_users_refresh_family(client):
    first = client.post(
        "/api/v1/auth/register",
        json={"email": "logout-owner@example.com", "password": "uma-senha-forte-123"},
    ).json()
    second = client.post(
        "/api/v1/auth/register",
        json={"email": "logout-other@example.com", "password": "uma-senha-forte-123"},
    ).json()

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {first['access_token']}"},
        json={"refresh_token": second["refresh_token"]},
    )
    assert response.status_code == 204

    second_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second["refresh_token"]},
    )
    assert second_refresh.status_code == 200




def test_change_password_invalidates_all_access_and_refresh_tokens(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "change-password@example.com", "password": "senha-original-123"},
    ).json()
    second_session = client.post(
        "/api/v1/auth/login",
        json={"email": "change-password@example.com", "password": "senha-original-123"},
    ).json()

    changed = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
        json={
            "current_password": "senha-original-123",
            "new_password": "senha-nova-e-segura-456",
        },
    )
    assert changed.status_code == 204

    for token in (registered["access_token"], second_session["access_token"]):
        assert client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code == 401

    for token in (registered["refresh_token"], second_session["refresh_token"]):
        assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 401

    assert client.post(
        "/api/v1/auth/login",
        json={"email": "change-password@example.com", "password": "senha-original-123"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "change-password@example.com", "password": "senha-nova-e-segura-456"},
    ).status_code == 200


def test_change_password_rejects_wrong_current_password(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "wrong-current@example.com", "password": "senha-original-123"},
    ).json()
    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
        json={
            "current_password": "senha-incorreta",
            "new_password": "senha-nova-e-segura-456",
        },
    )
    assert response.status_code == 401


def test_logout_all_revokes_every_session_for_the_user(client):
    first = client.post(
        "/api/v1/auth/register",
        json={"email": "logout-all@example.com", "password": "senha-original-123"},
    ).json()
    second = client.post(
        "/api/v1/auth/login",
        json={"email": "logout-all@example.com", "password": "senha-original-123"},
    ).json()

    response = client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {first['access_token']}"},
    )
    assert response.status_code == 204

    for token in (first["access_token"], second["access_token"]):
        assert client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code == 401

    for token in (first["refresh_token"], second["refresh_token"]):
        assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 401

    assert client.post(
        "/api/v1/auth/login",
        json={"email": "logout-all@example.com", "password": "senha-original-123"},
    ).status_code == 200


def test_web_refresh_cookie_is_httponly_and_refresh_requires_csrf(client):
    headers = {"X-SFI-Client": "web"}
    registered = client.post(
        "/api/v1/auth/register",
        headers=headers,
        json={"email": "web-cookie@example.com", "password": "uma-senha-forte-123"},
    )
    assert registered.status_code == 201
    assert registered.json()["refresh_token"] is None
    set_cookies = registered.headers.get_list("set-cookie")
    assert any("sfi_refresh=" in value and "httponly" in value.lower() for value in set_cookies)
    assert any("sfi_csrf=" in value and "httponly" not in value.lower() for value in set_cookies)

    original_refresh = client.cookies.get("sfi_refresh")
    csrf_token = client.cookies.get("sfi_csrf")
    assert original_refresh
    assert csrf_token

    missing_csrf = client.post("/api/v1/auth/refresh", headers=headers)
    assert missing_csrf.status_code == 403

    rotated = client.post(
        "/api/v1/auth/refresh",
        headers={**headers, "X-CSRF-Token": csrf_token},
    )
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] is None
    assert client.cookies.get("sfi_refresh") != original_refresh

    current_csrf = client.cookies.get("sfi_csrf")
    access_headers = {
        **headers,
        "Authorization": f"Bearer {rotated.json()['access_token']}",
        "X-CSRF-Token": current_csrf,
    }
    logged_out = client.post("/api/v1/auth/logout", headers=access_headers)
    assert logged_out.status_code == 204
    assert client.get("/api/v1/auth/me", headers=access_headers).status_code == 401


def test_login_rate_limit_blocks_repeated_invalid_passwords(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "rate-limit@example.com", "password": "uma-senha-forte-123"},
    )
    for _ in range(4):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "rate-limit@example.com", "password": "senha-errada"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "rate-limit@example.com", "password": "senha-errada"},
    )
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "900"

    correct_password = client.post(
        "/api/v1/auth/login",
        json={"email": "rate-limit@example.com", "password": "uma-senha-forte-123"},
    )
    assert correct_password.status_code == 429


def test_successful_login_clears_prior_failed_attempts(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "rate-reset@example.com", "password": "uma-senha-forte-123"},
    )
    failed = client.post(
        "/api/v1/auth/login",
        json={"email": "rate-reset@example.com", "password": "senha-errada"},
    )
    assert failed.status_code == 401

    successful = client.post(
        "/api/v1/auth/login",
        json={"email": "rate-reset@example.com", "password": "uma-senha-forte-123"},
    )
    assert successful.status_code == 200


def test_user_timezone_update(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "timezone-user@example.com",
            "password": "uma-senha-forte-123",
            "timezone": "America/Manaus",
        },
    )
    assert registered.status_code == 201
    assert registered.json()["user"]["timezone"] == "America/Manaus"
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    updated = client.patch(
        "/api/v1/auth/me/timezone",
        headers=headers,
        json={"timezone": "Europe/Lisbon"},
    )
    assert updated.status_code == 200
    assert updated.json()["timezone"] == "Europe/Lisbon"


def test_security_event_history_records_authentication_activity(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "security-events@example.com", "password": "uma-senha-forte-123"},
    )
    assert registered.status_code == 201
    failed = client.post(
        "/api/v1/auth/login",
        json={"email": "security-events@example.com", "password": "senha-errada"},
    )
    assert failed.status_code == 401
    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "security-events@example.com", "password": "uma-senha-forte-123"},
    )
    assert logged_in.status_code == 200
    current_headers = {
        "Authorization": f"Bearer {logged_in.json()['access_token']}"
    }

    events = client.get("/api/v1/auth/security-events", headers=current_headers)
    assert events.status_code == 200
    event_types = [event["event_type"] for event in events.json()]
    assert "account_registered" in event_types
    assert "login_failed" in event_types
    assert "login_succeeded" in event_types
