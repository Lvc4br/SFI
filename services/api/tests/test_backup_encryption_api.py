import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'encrypted-backup.db'}")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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


def register(client, email="encrypted-backup@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_encrypted_backup_export_preview_restore_and_wrong_password(client):
    headers = register(client)
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta original", "account_type": "checking"},
    )
    assert account.status_code == 201, account.text

    passphrase = "senha-mestra-backup-segura-2026"
    exported = client.post(
        "/api/v1/backup/encrypted/export",
        headers=headers,
        json={"passphrase": passphrase},
    )
    assert exported.status_code == 200, exported.text
    envelope = exported.json()
    assert envelope["format"] == "sfi-encrypted-backup"
    assert "tables" not in envelope
    assert "ciphertext" in envelope

    wrong_password = client.post(
        "/api/v1/backup/encrypted/preview",
        headers=headers,
        json={"passphrase": "senha-incorreta-comprida", "envelope": envelope},
    )
    assert wrong_password.status_code == 422

    added = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta posterior", "account_type": "checking"},
    )
    assert added.status_code == 201, added.text

    preview = client.post(
        "/api/v1/backup/encrypted/preview",
        headers=headers,
        json={"passphrase": passphrase, "envelope": envelope},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["encrypted"] is True
    assert preview.json()["records_in_backup"] < preview.json()["records_current"]

    not_confirmed = client.post(
        "/api/v1/backup/encrypted/restore",
        headers=headers,
        json={"passphrase": passphrase, "envelope": envelope, "confirmed": False},
    )
    assert not_confirmed.status_code == 409

    restored = client.post(
        "/api/v1/backup/encrypted/restore",
        headers=headers,
        json={"passphrase": passphrase, "envelope": envelope, "confirmed": True},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["encrypted"] is True
    accounts = client.get("/api/v1/finance/accounts", headers=headers)
    assert accounts.status_code == 200
    assert len(accounts.json()) == 1
    assert accounts.json()[0]["name"] == "Conta original"


def test_encrypted_backup_rejects_tampered_envelope(client):
    headers = register(client)
    passphrase = "senha-mestra-backup-segura-2026"
    envelope = client.post(
        "/api/v1/backup/encrypted/export",
        headers=headers,
        json={"passphrase": passphrase},
    ).json()
    envelope["ciphertext"] = envelope["ciphertext"][:-4] + "AAAA"
    response = client.post(
        "/api/v1/backup/encrypted/preview",
        headers=headers,
        json={"passphrase": passphrase, "envelope": envelope},
    )
    assert response.status_code == 422



def test_encrypted_restore_does_not_modify_another_users_data(client):
    owner_headers = register(client, "backup-owner@example.com")
    other_headers = register(client, "backup-other@example.com")

    owner_account = client.post(
        "/api/v1/finance/accounts",
        headers=owner_headers,
        json={"name": "Conta do proprietário", "account_type": "checking"},
    )
    other_account = client.post(
        "/api/v1/finance/accounts",
        headers=other_headers,
        json={"name": "Conta de outro usuário", "account_type": "checking"},
    )
    assert owner_account.status_code == 201, owner_account.text
    assert other_account.status_code == 201, other_account.text

    passphrase = "senha-mestra-backup-segura-2026"
    envelope_response = client.post(
        "/api/v1/backup/encrypted/export",
        headers=owner_headers,
        json={"passphrase": passphrase},
    )
    assert envelope_response.status_code == 200, envelope_response.text

    later_account = client.post(
        "/api/v1/finance/accounts",
        headers=owner_headers,
        json={"name": "Conta posterior", "account_type": "checking"},
    )
    assert later_account.status_code == 201, later_account.text

    restored = client.post(
        "/api/v1/backup/encrypted/restore",
        headers=owner_headers,
        json={
            "passphrase": passphrase,
            "envelope": envelope_response.json(),
            "confirmed": True,
        },
    )
    assert restored.status_code == 200, restored.text

    owner_accounts = client.get("/api/v1/finance/accounts", headers=owner_headers)
    other_accounts = client.get("/api/v1/finance/accounts", headers=other_headers)
    assert owner_accounts.status_code == 200
    assert [item["name"] for item in owner_accounts.json()] == ["Conta do proprietário"]
    assert other_accounts.status_code == 200
    assert [item["name"] for item in other_accounts.json()] == ["Conta de outro usuário"]


def test_automatic_backup_controls_are_desktop_windows_only(client):
    headers = register(client)
    status = client.get("/api/v1/backup/automatic", headers=headers)
    assert status.status_code == 409
    configured = client.put(
        "/api/v1/backup/automatic",
        headers=headers,
        json={
            "cadence": "daily",
            "local_time": "08:00",
            "passphrase": "senha-mestra-backup-segura-2026",
        },
    )
    assert configured.status_code == 409
