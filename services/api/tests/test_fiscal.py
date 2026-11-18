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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'fiscal.db'}")
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


def sample_xml():
    key = "35261112345678000195550010000001231000001235"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe Id="NFe{key}">
<ide><nNF>123</nNF><serie>1</serie><dhEmi>2026-11-17T10:00:00-03:00</dhEmi></ide>
<emit><CNPJ>12345678000195</CNPJ><xNome>Mercado Exemplo LTDA</xNome></emit>
<det nItem="1"><prod><cProd>001</cProd><xProd>Arroz 5kg</xProd><NCM>10063021</NCM><CFOP>5102</CFOP><uCom>UN</uCom><qCom>1.0000</qCom><vUnCom>25.90</vUnCom><vProd>25.90</vProd></prod></det>
<total><ICMSTot><vNF>25.90</vNF></ICMSTot></total>
</infNFe></NFe></nfeProc>"""


def test_nfe_preview_and_confirm_without_raw_xml_storage(client):
    headers = register(client, "fiscal-preview@example.com")
    xml = sample_xml()
    preview = client.post("/api/v1/fiscal/documents/preview", headers=headers, json={"content": xml})
    assert preview.status_code == 200, preview.text
    assert preview.json()["issuer_name"] == "Mercado Exemplo LTDA"
    assert preview.json()["total_amount"] == "25.90"
    assert preview.json()["items"][0]["description"] == "Arroz 5kg"

    saved = client.post("/api/v1/fiscal/documents/confirm", headers=headers, json={"content": xml})
    assert saved.status_code == 201, saved.text
    assert saved.json()["transaction_id"] is None
    repeated = client.post("/api/v1/fiscal/documents/confirm", headers=headers, json={"content": xml})
    assert repeated.status_code == 409
    listed = client.get("/api/v1/fiscal/documents", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert "xml" not in listed.text.lower()


def test_nfe_can_create_expense_atomically(client):
    headers = register(client, "fiscal-expense@example.com")
    account = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    ).json()
    category = client.post(
        "/api/v1/finance/categories", headers=headers,
        json={"name": "Mercado", "category_type": "expense"},
    ).json()
    response = client.post(
        "/api/v1/fiscal/documents/confirm", headers=headers,
        json={"content": sample_xml(), "create_expense": True,
              "account_id": account["id"], "category_id": category["id"]},
    )
    assert response.status_code == 201, response.text
    transactions = client.get("/api/v1/finance/transactions", headers=headers).json()
    assert len(transactions) == 1
    assert transactions[0]["amount"] == "25.90"
    assert transactions[0]["transaction_type"] == "expense"


@pytest.mark.parametrize("xml", [
    "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><foo>&xxe;</foo>",
    "<broken>",
    "<root/>",
])
def test_nfe_rejects_unsafe_or_invalid_xml(client, xml):
    headers = register(client, f"fiscal-invalid-{len(xml)}@example.com")
    response = client.post("/api/v1/fiscal/documents/preview", headers=headers, json={"content": xml})
    assert response.status_code == 422


def test_nfe_documents_are_isolated_by_user(client):
    owner = register(client, "fiscal-owner@example.com")
    other = register(client, "fiscal-other@example.com")
    assert client.post(
        "/api/v1/fiscal/documents/confirm", headers=owner, json={"content": sample_xml()}
    ).status_code == 201
    assert client.get("/api/v1/fiscal/documents", headers=other).json() == []
