import pytest

@pytest.fixture
def client(test_client):
    return test_client


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
