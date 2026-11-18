import asyncio
import base64
import hashlib
import io
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'exchange.db'}")
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
        f"2026-11-16T12:00:00Z,expense,35.50,Compra mercado,{account['id']},"
        f"{category['id']},bank-001\n"
        f"2026-11-17T12:00:00Z,expense,12.00,Café,{account['id']},"
        f"{category['id']},bank-002\n"
        f"2026-11-17T12:00:00Z,expense,12.00,Café,{account['id']},"
        f"{category['id']},bank-002\n"
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


def test_xlsx_preview_import_and_export_round_trip(client):
    headers = register(client, "exchange-xlsx@example.com")
    account, category = setup_account(client, headers)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["date", "type", "amount", "description", "account_id", "category_id"])
    sheet.append([
        "2026-11-16T12:00:00Z", "expense", "48.90", "Compra em planilha",
        account["id"], category["id"],
    ])
    stream = io.BytesIO()
    workbook.save(stream)
    workbook.close()
    payload = {
        "format": "xlsx",
        "content": base64.b64encode(stream.getvalue()).decode("ascii"),
    }

    preview = client.post(
        "/api/v1/exchange/transactions/preview", headers=headers, json=payload
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"] == 1
    assert preview.json()["rows"][0]["description"] == "Compra em planilha"

    imported = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": True},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["created"] == 1

    exported = client.get(
        "/api/v1/exchange/transactions/export?format=xlsx", headers=headers
    )
    assert exported.status_code == 200
    restored = load_workbook(io.BytesIO(exported.content), read_only=True, data_only=True)
    rows = list(restored.active.iter_rows(values_only=True))
    restored.close()
    assert rows[0][0] == "id"
    assert rows[1][6] == "Compra em planilha"
    assert rows[1][4] == "48.90"


def test_xlsx_import_rejects_invalid_base64_and_empty_workbook(client):
    headers = register(client, "exchange-xlsx-invalid@example.com")
    invalid = client.post(
        "/api/v1/exchange/transactions/preview",
        headers=headers,
        json={"format": "xlsx", "content": "not-base64!?"},
    )
    assert invalid.status_code == 422

    workbook = Workbook()
    stream = io.BytesIO()
    workbook.save(stream)
    workbook.close()
    empty = client.post(
        "/api/v1/exchange/transactions/preview",
        headers=headers,
        json={
            "format": "xlsx",
            "content": base64.b64encode(stream.getvalue()).decode("ascii"),
        },
    )
    assert empty.status_code == 422


def test_full_backup_preview_restore_and_user_isolation(client):
    owner = register(client, "backup-owner@example.com")
    other = register(client, "backup-other@example.com")
    account, category = setup_account(client, owner)
    transaction_payload = {
        "format": "csv",
        "content": (
            "date,type,amount,description,account_id,category_id\n"
            f"2026-11-16T12:00:00Z,expense,73.25,Registro preservado,"
            f"{account['id']},{category['id']}\n"
        ),
    }
    imported = client.post(
        "/api/v1/exchange/transactions/import",
        headers=owner,
        json={**transaction_payload, "confirmed": True},
    )
    assert imported.status_code == 201, imported.text

    exported = client.get("/api/v1/backup/export", headers=owner)
    assert exported.status_code == 200, exported.text
    backup = exported.json()
    assert backup["format"] == "sfi-personal-data"
    assert backup["version"] == 1
    assert "transactions" in backup["tables"]
    assert len(backup["tables"]["transactions"]) == 1
    assert "refresh_tokens" not in backup["tables"]
    assert "security_events" not in backup["tables"]

    later_payload = {
        "format": "csv",
        "content": (
            "date,type,amount,description,account_id,category_id\n"
            f"2026-11-17T12:00:00Z,expense,12.00,Registro posterior ao backup,"
            f"{account['id']},{category['id']}\n"
        ),
    }
    extra = client.post(
        "/api/v1/exchange/transactions/import",
        headers=owner,
        json={**later_payload, "confirmed": True},
    )
    assert extra.status_code == 201, extra.text

    preview = client.post(
        "/api/v1/backup/preview", headers=owner, json={"backup": backup}
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["records_in_backup"] < preview.json()["records_current"]
    assert preview.json()["restore_mode"] == "replace"
    assert preview.json()["requires_confirmation"] is True

    no_confirmation = client.post(
        "/api/v1/backup/restore",
        headers=owner,
        json={"backup": backup, "confirmed": False},
    )
    assert no_confirmation.status_code == 409
    assert len(client.get("/api/v1/finance/transactions", headers=owner).json()) == 2

    restored = client.post(
        "/api/v1/backup/restore",
        headers=owner,
        json={"backup": backup, "confirmed": True},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["records_restored"] >= 3
    owner_transactions = client.get("/api/v1/finance/transactions", headers=owner)
    assert owner_transactions.status_code == 200
    assert len(owner_transactions.json()) == 1
    assert owner_transactions.json()[0]["description"] == "Registro preservado"
    assert client.get("/api/v1/finance/transactions", headers=other).json() == []


def test_backup_restore_rejects_incomplete_or_unsupported_backup(client):
    headers = register(client, "backup-invalid@example.com")
    exported = client.get("/api/v1/backup/export", headers=headers)
    assert exported.status_code == 200
    backup = exported.json()

    incomplete = dict(backup)
    incomplete["tables"] = dict(backup["tables"])
    incomplete["tables"].pop("transactions")
    response = client.post(
        "/api/v1/backup/preview", headers=headers, json={"backup": incomplete}
    )
    assert response.status_code == 422

    unsupported = {**backup, "version": 999}
    response = client.post(
        "/api/v1/backup/preview", headers=headers, json={"backup": unsupported}
    )
    assert response.status_code == 422


def test_backup_restore_rolls_back_when_referential_integrity_fails(client):
    headers = register(client, "backup-atomic@example.com")
    account, category = setup_account(client, headers)
    payload = {
        "format": "csv",
        "content": (
            "date,type,amount,description,account_id,category_id\n"
            f"2026-11-16T12:00:00Z,expense,8.50,Registro válido,"
            f"{account['id']},{category['id']}\n"
        ),
    }
    imported = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": True},
    )
    assert imported.status_code == 201
    backup = client.get("/api/v1/backup/export", headers=headers).json()
    backup["tables"]["accounts"][0]["id"] = "00000000-0000-0000-0000-000000000001"
    unsigned = {key: value for key, value in backup.items() if key != "integrity"}
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    backup["integrity"]["digest"] = hashlib.sha256(canonical).hexdigest()

    response = client.post(
        "/api/v1/backup/restore",
        headers=headers,
        json={"backup": backup, "confirmed": True},
    )
    assert response.status_code == 422
    transactions = client.get("/api/v1/finance/transactions", headers=headers)
    assert transactions.status_code == 200
    assert len(transactions.json()) == 1
    assert transactions.json()[0]["description"] == "Registro válido"


def test_qif_preview_import_and_idempotent_reimport(client):
    headers = register(client, "exchange-qif@example.com")
    account, category = setup_account(client, headers)
    qif = (
        "!Type:Bank\n"
        "D11/18'26\n"
        "T-35.90\n"
        "PMercado Central\n"
        "MCompra semanal\n"
        "^\n"
    )
    payload = {
        "format": "qif",
        "content": qif,
        "default_account_id": account["id"],
        "default_category_id": category["id"],
    }
    preview = client.post(
        "/api/v1/exchange/transactions/preview", headers=headers, json=payload
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"] == 1
    assert preview.json()["rows"][0]["description"] == "Mercado Central"

    imported = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": True},
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["created"] == 1

    repeated = client.post(
        "/api/v1/exchange/transactions/preview", headers=headers, json=payload
    )
    assert repeated.status_code == 200
    assert repeated.json()["duplicates"] == 1


def test_qif_incomplete_record_is_reported_without_importing(client):
    headers = register(client, "exchange-qif-invalid@example.com")
    account, category = setup_account(client, headers)
    qif = "!Type:Bank\nD11/18'26\nT-20.00\nPRegistro sem terminador"
    payload = {
        "format": "qif",
        "content": qif,
        "default_account_id": account["id"],
        "default_category_id": category["id"],
    }
    preview = client.post(
        "/api/v1/exchange/transactions/preview", headers=headers, json=payload
    )
    assert preview.status_code == 200
    assert preview.json()["invalid"] == 1
    imported = client.post(
        "/api/v1/exchange/transactions/import",
        headers=headers,
        json={**payload, "confirmed": True},
    )
    assert imported.status_code == 422
    assert client.get("/api/v1/finance/transactions", headers=headers).json() == []


def test_pdf_text_preview_requires_unambiguous_signed_or_marked_amount(client, monkeypatch):
    from types import SimpleNamespace

    headers = register(client, "exchange-pdf@example.com")
    account, _ = setup_account(client, headers)

    class FakePdfReader:
        def __init__(self, _stream, strict=True):
            self.is_encrypted = False
            self.pages = [
                SimpleNamespace(
                    extract_text=lambda: (
                        "Extrato da conta\n"
                        "18/11/2026 Mercado Central -25,90\n"
                        "18/11/2026 Salário 1500,00 C\n"
                    )
                )
            ]

    monkeypatch.setattr("sfi_api.routers.data_exchange.PdfReader", FakePdfReader)
    payload = {
        "format": "pdf",
        "content": base64.b64encode(b"fake-pdf-bytes").decode("ascii"),
        "default_account_id": account["id"],
    }
    preview = client.post(
        "/api/v1/exchange/transactions/preview", headers=headers, json=payload
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["total"] == 2
    assert preview.json()["valid"] == 2
    assert preview.json()["rows"][0]["description"] == "Mercado Central"
    assert preview.json()["rows"][1]["amount"] == "1500.00"


def test_pdf_text_preview_rejects_unsigned_amount_as_ambiguous(client, monkeypatch):
    from types import SimpleNamespace

    headers = register(client, "exchange-pdf-ambiguous@example.com")
    account, _ = setup_account(client, headers)

    class FakePdfReader:
        def __init__(self, _stream, strict=True):
            self.is_encrypted = False
            self.pages = [
                SimpleNamespace(extract_text=lambda: "18/11/2026 Compra 25,90")
            ]

    monkeypatch.setattr("sfi_api.routers.data_exchange.PdfReader", FakePdfReader)
    payload = {
        "format": "pdf",
        "content": base64.b64encode(b"fake-pdf-bytes").decode("ascii"),
        "default_account_id": account["id"],
    }
    preview = client.post(
        "/api/v1/exchange/transactions/preview", headers=headers, json=payload
    )
    assert preview.status_code == 200
    assert preview.json()["invalid"] == 1
    assert "não é seguro inferir" in preview.json()["rows"][0]["error"]


def test_qif_export_is_account_scoped_and_round_trips_signs(client):
    owner = register(client, "exchange-qif-export@example.com")
    other = register(client, "exchange-qif-export-other@example.com")
    account, category = setup_account(client, owner)
    other_account, _ = setup_account(client, other)
    content = (
        "date,type,amount,description,account_id,category_id\n"
        f"2026-11-16T12:00:00Z,expense,35.90,Mercado,{account['id']},{category['id']}\n"
        f"2026-11-17T12:00:00Z,income,1500.00,Salário,{account['id']},\n"
    )
    imported = client.post(
        "/api/v1/exchange/transactions/import", headers=owner,
        json={"format": "csv", "content": content, "confirmed": True},
    )
    assert imported.status_code == 201, imported.text
    missing_account = client.get(
        "/api/v1/exchange/transactions/export?format=qif", headers=owner
    )
    assert missing_account.status_code == 422
    exported = client.get(
        f"/api/v1/exchange/transactions/export?format=qif&account_id={account['id']}",
        headers=owner,
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/x-qif")
    assert exported.text.startswith("!Type:Bank\n")
    assert "T-35.90\n" in exported.text
    assert "T1500.00\n" in exported.text
    assert "PMercado\n" in exported.text
    round_trip = client.post(
        "/api/v1/exchange/transactions/preview", headers=owner,
        json={"format": "qif", "content": exported.text, "default_account_id": account["id"]},
    )
    assert round_trip.status_code == 200, round_trip.text
    assert round_trip.json()["total"] == 2
    foreign = client.get(
        f"/api/v1/exchange/transactions/export?format=qif&account_id={other_account['id']}",
        headers=owner,
    )
    assert foreign.status_code == 404


def test_qif_export_uses_credit_card_account_type(client):
    headers = register(client, "exchange-qif-credit@example.com")
    account = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Cartão", "account_type": "credit"},
    ).json()
    exported = client.get(
        f"/api/v1/exchange/transactions/export?format=qif&account_id={account['id']}",
        headers=headers,
    )
    assert exported.status_code == 200
    assert exported.text.startswith("!Type:CCard\n")


def test_pdf_export_is_valid_and_isolated_by_user(client):
    from pypdf import PdfReader

    owner = register(client, "exchange-pdf-export@example.com")
    other = register(client, "exchange-pdf-export-other@example.com")
    account, category = setup_account(client, owner)
    content = (
        "date,type,amount,description,account_id,category_id\n"
        f"2026-11-16T12:00:00Z,expense,19.90,Farmácia,{account['id']},{category['id']}\n"
    )
    imported = client.post(
        "/api/v1/exchange/transactions/import", headers=owner,
        json={"format": "csv", "content": content, "confirmed": True},
    )
    assert imported.status_code == 201, imported.text
    exported = client.get("/api/v1/exchange/transactions/export?format=pdf", headers=owner)
    assert exported.status_code == 200
    assert exported.content.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(exported.content))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Farm" in extracted
    other_pdf = client.get("/api/v1/exchange/transactions/export?format=pdf", headers=other)
    assert other_pdf.status_code == 200
    other_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(other_pdf.content)).pages
    )
    assert "Farm" not in other_text
