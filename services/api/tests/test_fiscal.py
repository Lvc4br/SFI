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



def sample_danfe_pdf():
    import base64
    from io import BytesIO

    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page = canvas.Canvas(buffer)
    lines = [
        "DANFE",
        "RECEBEMOS DE MERCADO EXEMPLO LTDA OS PRODUTOS CONSTANTES DA NOTA FISCAL",
        "CNPJ: 12.345.678/0001-95",
        "DATA DA EMISSAO: 17/11/2026",
        "NUMERO: 123 SERIE: 1",
        "CHAVE DE ACESSO: 35261112345678000195550010000001231000001235",
        "VALOR TOTAL DA NOTA: R$ 25,90",
    ]
    for index, line in enumerate(lines):
        page.drawString(40, 800 - index * 24, line)
    page.save()
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_danfe_pdf_text_preview_and_confirmation(client):
    headers = register(client, "fiscal-pdf@example.com")
    content = sample_danfe_pdf()
    preview = client.post(
        "/api/v1/fiscal/documents/preview",
        headers=headers,
        json={"content": content, "format": "pdf"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["issuer_name"] == "MERCADO EXEMPLO LTDA"
    assert preview.json()["issuer_tax_id"] == "12345678000195"
    assert preview.json()["total_amount"] == "25.90"
    assert preview.json()["items"] == []

    saved = client.post(
        "/api/v1/fiscal/documents/confirm",
        headers=headers,
        json={"content": content, "format": "pdf", "create_expense": False},
    )
    assert saved.status_code == 201, saved.text
    assert client.get("/api/v1/fiscal/documents", headers=headers).json()[0]["access_key"] == (
        "35261112345678000195550010000001231000001235"
    )


def test_danfe_pdf_rejects_scanned_or_invalid_documents(client):
    import base64
    from io import BytesIO

    from reportlab.pdfgen import canvas

    headers = register(client, "fiscal-pdf-scanned@example.com")
    buffer = BytesIO()
    page = canvas.Canvas(buffer)
    page.drawString(40, 800, "Imagem de DANFE sem campos selecionáveis")
    page.save()
    response = client.post(
        "/api/v1/fiscal/documents/preview",
        headers=headers,
        json={"content": base64.b64encode(buffer.getvalue()).decode("ascii"), "format": "pdf"},
    )
    assert response.status_code == 422



def test_nfe_qr_payload_must_match_document_key(client):
    headers = register(client, "fiscal-qr@example.com")
    key = "35261112345678000195550010000001231000001235"
    matching = client.post(
        "/api/v1/fiscal/documents/preview",
        headers=headers,
        json={"content": sample_xml(), "qr_code_payload": f"https://example.test/qrcode?p={key}"},
    )
    assert matching.status_code == 200, matching.text
    assert matching.json()["qr_code_status"] == "matches"
    assert matching.json()["qr_code_access_key"] == key

    mismatch = client.post(
        "/api/v1/fiscal/documents/preview",
        headers=headers,
        json={
            "content": sample_xml(),
            "qr_code_payload": "https://example.test/qrcode?p=35261112345678000195550010000001231000001234",
        },
    )
    assert mismatch.status_code == 422



def ocr_danfe_text():
    return """RECEBEMOS DE MERCADO EXEMPLO LTDA OS PRODUTOS CONSTANTES DA NOTA FISCAL
CNPJ: 12.345.678/0001-95
DATA DA EMISSAO: 17/11/2026
NUMERO: 123 SERIE: 1
CHAVE DE ACESSO: 35261112345678000195550010000001231000001235
VALOR TOTAL DA NOTA: R$ 25,90"""


def blank_danfe_image():
    import base64
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (1200, 800), "white").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_scanned_danfe_image_uses_local_ocr_and_returns_reviewable_preview(client, monkeypatch):
    monkeypatch.setattr("sfi_api.routers.fiscal._ocr_image_bytes", lambda _image: ocr_danfe_text())
    headers = register(client, "fiscal-image-ocr@example.com")
    response = client.post(
        "/api/v1/fiscal/documents/preview",
        headers=headers,
        json={"content": blank_danfe_image(), "format": "image"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["issuer_name"] == "MERCADO EXEMPLO LTDA"
    assert response.json()["issuer_tax_id"] == "12345678000195"
    assert response.json()["total_amount"] == "25.90"


def test_scanned_danfe_pdf_falls_back_to_ocr(client, monkeypatch):
    import base64
    from io import BytesIO

    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    monkeypatch.setattr("sfi_api.routers.fiscal._ocr_image_bytes", lambda _image: ocr_danfe_text())
    image_buffer = BytesIO()
    Image.new("RGB", (1200, 800), "white").save(image_buffer, format="PNG")
    pdf_buffer = BytesIO()
    page = canvas.Canvas(pdf_buffer)
    page.drawImage(ImageReader(BytesIO(image_buffer.getvalue())), 20, 20, width=550, height=360)
    page.save()

    headers = register(client, "fiscal-scanned-pdf-ocr@example.com")
    response = client.post(
        "/api/v1/fiscal/documents/preview",
        headers=headers,
        json={"content": base64.b64encode(pdf_buffer.getvalue()).decode("ascii"), "format": "pdf"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_key"] == "35261112345678000195550010000001231000001235"
    assert response.json()["total_amount"] == "25.90"
