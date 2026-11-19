import base64
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal
from urllib.parse import unquote_plus

import pypdfium2 as pdfium
from fastapi import APIRouter, Depends, HTTPException, status
from PIL import Image
from pydantic import BaseModel, Field
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Category, Transaction
from sfi_api.models.fiscal import FiscalDocument
from sfi_api.models.user import User

router = APIRouter(prefix="/fiscal", tags=["fiscal documents"])
SESSION_DEPENDENCY = Depends(get_session)
USER_DEPENDENCY = Depends(get_current_user)
MAX_XML_BYTES = 2 * 1024 * 1024


class FiscalPreviewRequest(BaseModel):
    content: str = Field(min_length=1, max_length=14_000_000)
    format: Literal["xml", "pdf", "image"] = "xml"
    qr_code_payload: str | None = Field(default=None, max_length=4096)


class FiscalConfirmRequest(FiscalPreviewRequest):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    create_expense: bool = False


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first(root: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in root.iter() if _local(node.tag) == name), None)


def _text(root: ET.Element, name: str, default: str = "") -> str:
    node = _first(root, name)
    return (node.text or "").strip() if node is not None else default


def parse_nfe_xml(content: str) -> dict:
    raw = content.encode("utf-8")
    if len(raw) > MAX_XML_BYTES:
        raise HTTPException(413, "O XML excede o limite de 2 MB.")
    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise HTTPException(422, "XML com DTD ou entidades não é permitido.")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise HTTPException(422, "XML inválido ou malformado.") from exc

    info = _first(root, "infNFe")
    if info is None:
        raise HTTPException(422, "O arquivo não contém uma NF-e/NFC-e (infNFe).")
    identifier = info.attrib.get("Id", "")
    access_key = identifier.removeprefix("NFe")
    if not re.fullmatch(r"\d{44}", access_key):
        raise HTTPException(422, "Chave de acesso da NF-e inválida ou ausente.")

    issuer = _first(info, "emit")
    ide = _first(info, "ide")
    total = _first(info, "ICMSTot")
    if issuer is None or ide is None or total is None:
        raise HTTPException(
            422, "A NF-e está incompleta: emitente, identificação ou total ausente."
        )
    issuer_name = _text(issuer, "xNome")
    issuer_tax_id = re.sub(
        r"\D", "", _text(issuer, "CNPJ") or _text(issuer, "CPF")
    )
    if not issuer_name or len(issuer_tax_id) not in {11, 14}:
        raise HTTPException(422, "Dados de identificação do emitente inválidos.")
    try:
        amount = Decimal(_text(total, "vNF"))
        issued = datetime.fromisoformat(
            _text(ide, "dhEmi") or _text(ide, "dEmi")
        )
        if issued.tzinfo is None:
            issued = issued.replace(tzinfo=UTC)
        issued = issued.astimezone(UTC)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(422, "Data de emissão ou valor total inválido.") from exc
    if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999999999.99"):
        raise HTTPException(422, "O valor total da nota deve ser positivo e válido.")

    items = []
    for detail in (node for node in info if _local(node.tag) == "det"):
        product = next((node for node in detail if _local(node.tag) == "prod"), None)
        if product is None:
            continue
        def child(name: str, product_node: ET.Element = product) -> str:
            node = next((item for item in product_node if _local(item.tag) == name), None)
            return (node.text or "").strip() if node is not None else ""
        items.append({
            "code": child("cProd"),
            "description": child("xProd")[:160],
            "ncm": child("NCM"),
            "cfop": child("CFOP"),
            "quantity": child("qCom"),
            "unit": child("uCom"),
            "unit_price": child("vUnCom"),
            "total": child("vProd"),
        })
    return {
        "access_key": access_key,
        "document_number": _text(ide, "nNF"),
        "series": _text(ide, "serie"),
        "issuer_name": issuer_name[:160],
        "issuer_tax_id": issuer_tax_id,
        "issue_date": issued.isoformat(),
        "total_amount": str(amount.quantize(Decimal("0.01"))),
        "currency": "BRL",
        "items": items,
        "xml_sha256": hashlib.sha256(raw).hexdigest(),
    }


MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 10
MAX_PDF_TEXT_CHARS = 200_000
MAX_OCR_TOTAL_PIXELS = 40_000_000


def _valid_access_key(key: str) -> bool:
    if not re.fullmatch(r"\d{44}", key):
        return False
    weights = (2, 3, 4, 5, 6, 7, 8, 9)
    total = sum(
        int(digit) * weights[index % len(weights)]
        for index, digit in enumerate(reversed(key[:-1]))
    )
    remainder = total % 11
    expected = 0 if remainder in (0, 1) else 11 - remainder
    return expected == int(key[-1])


def _ocr_image_bytes(image_bytes: bytes) -> str:
    bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[4]))
    bundled_ocr = bundle_root / "ocr"
    executable = bundled_ocr / "tesseract.exe"
    if not executable.is_file():
        found = shutil.which("tesseract")
        if not found:
            raise HTTPException(
                503,
                (
                    "O mecanismo OCR não está disponível nesta instalação. "
                    "Atualize o SFI para uma versão com OCR."
                ),
            )
        executable = Path(found)
        tessdata = os.environ.get("TESSDATA_PREFIX")
    else:
        tessdata = str(bundled_ocr / "tessdata")

    environment = os.environ.copy()
    if tessdata:
        environment["TESSDATA_PREFIX"] = tessdata
    environment["OMP_THREAD_LIMIT"] = "1"
    try:
        result = subprocess.run(
            [str(executable), "stdin", "stdout", "-l", "por+eng", "--psm", "6"],
            input=image_bytes,
            capture_output=True,
            timeout=45,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(422, "O OCR excedeu o tempo máximo de processamento.") from exc
    except OSError as exc:
        raise HTTPException(503, "Não foi possível iniciar o mecanismo OCR.") from exc
    if result.returncode != 0:
        raise HTTPException(422, "O OCR não conseguiu processar a imagem enviada.")
    text = result.stdout.decode("utf-8", errors="replace")
    if len(text) > MAX_PDF_TEXT_CHARS:
        raise HTTPException(413, "O texto reconhecido excede o limite de 200 mil caracteres.")
    return text


def _ocr_pdf_text(raw: bytes) -> str:
    try:
        document = pdfium.PdfDocument(raw)
        if not 1 <= len(document) <= MAX_PDF_PAGES:
            raise HTTPException(422, "O PDF deve conter entre 1 e 10 páginas.")
        recognized = []
        total_pixels = 0
        for index in range(len(document)):
            page = document[index]
            width, height = page.get_size()
            if width <= 0 or height <= 0:
                raise HTTPException(422, "O PDF contém uma página com dimensões inválidas.")
            scale = min(2.0, math.sqrt(20_000_000 / (width * height)))
            if scale < 0.1:
                raise HTTPException(413, "Uma página do PDF excede o limite de renderização OCR.")
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().convert("RGB")
            image.thumbnail((4000, 4000))
            total_pixels += image.width * image.height
            if total_pixels > MAX_OCR_TOTAL_PIXELS:
                raise HTTPException(413, "O PDF excede o limite total de pixels para OCR.")
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            recognized.append(_ocr_image_bytes(buffer.getvalue()))
            page.close()
        document.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "Não foi possível converter as páginas do PDF para OCR.") from exc
    text = "\n".join(recognized)
    if len(text) > MAX_PDF_TEXT_CHARS:
        raise HTTPException(413, "O texto reconhecido excede o limite de 200 mil caracteres.")
    return text


def _parse_danfe_text(text: str, raw: bytes) -> dict:
    if not text.strip():
        raise HTTPException(
            422,
            "Não foi possível reconhecer texto no DANFE. Confira a qualidade da imagem.",
        )
    normalized = re.sub(r"[ \t]+", " ", text)
    key_match = re.search(r"(?<!\d)((?:\d[\s.-]?){43}\d)(?!\d)", normalized)
    if not key_match:
        raise HTTPException(422, "Não foi possível localizar a chave de acesso de 44 dígitos.")
    access_key = re.sub(r"\D", "", key_match.group(1))
    if not _valid_access_key(access_key):
        raise HTTPException(422, "A chave de acesso encontrada possui dígito verificador inválido.")

    tax_match = re.search(
        r"(?<!\d)(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\d{3}\.?\d{3}\.?\d{3}-?\d{2})(?!\d)",
        normalized,
    )
    issuer_tax_id = re.sub(r"\D", "", tax_match.group(1)) if tax_match else ""
    if len(issuer_tax_id) not in {11, 14}:
        raise HTTPException(422, "Não foi possível identificar o CNPJ/CPF do emitente.")

    issuer_match = re.search(
        r"RECEBEMOS DE\s+(.+?)(?:\s+OS PRODUTOS|\s*$)",
        normalized,
        re.IGNORECASE,
    )
    issuer_name = issuer_match.group(1).strip(" :-") if issuer_match else ""
    if not issuer_name:
        tax_position = normalized.find(tax_match.group(1))
        issuer_name = next(
            (
                line.strip()
                for line in reversed(normalized[:tax_position].splitlines())
                if line.strip()
            ),
            "",
        )
    issuer_name = re.sub(r"\s+", " ", issuer_name)[:160]
    if not issuer_name:
        raise HTTPException(422, "Não foi possível identificar o emitente no DANFE.")

    date_match = re.search(
        r"DATA\s+DA\s+EMISS[AÃ]O\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        normalized,
        re.IGNORECASE,
    )
    number_match = re.search(
        r"(?:N[º°.]?\s*|N[ÚU]MERO\s*[: ]\s*)(\d{1,12})",
        normalized,
        re.IGNORECASE,
    )
    series_match = re.search(r"S[ÉE]RIE\s*[: ]?\s*(\d{1,3})", normalized, re.IGNORECASE)
    total_match = re.search(
        r"VALOR\s+TOTAL\s+DA\s+NOTA\s*[: ]*\s*(?:R\$\s*)?([\d.]+,\d{2}|\d+\.\d{2})",
        normalized,
        re.IGNORECASE,
    )
    if not date_match or not number_match or not series_match or not total_match:
        raise HTTPException(
            422,
            (
                "O layout do DANFE não foi reconhecido por completo. Confira o XML original "
                "ou revise os dados manualmente."
            ),
        )
    try:
        issued_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").replace(tzinfo=UTC)
        raw_amount = total_match.group(1)
        amount = (
            Decimal(raw_amount.replace(".", "").replace(",", "."))
            if "," in raw_amount
            else Decimal(raw_amount)
        )
    except (ValueError, InvalidOperation) as exc:
        raise HTTPException(422, "Data ou valor total inválido no DANFE.") from exc
    if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999999999.99"):
        raise HTTPException(422, "O valor total do DANFE deve ser positivo e válido.")
    return {
        "access_key": access_key,
        "document_number": number_match.group(1),
        "series": series_match.group(1),
        "issuer_name": issuer_name,
        "issuer_tax_id": issuer_tax_id,
        "issue_date": issued_date.isoformat(),
        "total_amount": str(amount.quantize(Decimal("0.01"))),
        "currency": "BRL",
        "items": [],
        "xml_sha256": hashlib.sha256(raw).hexdigest(),
    }


def parse_nfe_pdf(content_base64: str) -> dict:
    try:
        raw = base64.b64decode(content_base64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise HTTPException(422, "PDF em Base64 inválido.") from exc
    if not raw or len(raw) > MAX_PDF_BYTES:
        raise HTTPException(413, "O PDF deve ter até 10 MB.")
    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise HTTPException(422, "PDF protegido por senha não é aceito.")
        if not 1 <= len(reader.pages) <= MAX_PDF_PAGES:
            raise HTTPException(422, "O PDF deve conter entre 1 e 10 páginas.")
        extracted_pages = [page.extract_text() or "" for page in reader.pages]
        if sum(len(page_text) for page_text in extracted_pages) > MAX_PDF_TEXT_CHARS:
            raise HTTPException(
                413, "O texto extraído do PDF excede o limite de 200 mil caracteres."
            )
        text = "\n".join(extracted_pages)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "PDF inválido ou não suportado.") from exc
    if not text.strip():
        text = _ocr_pdf_text(raw)
    return _parse_danfe_text(text, raw)


def parse_nfe_image(content_base64: str) -> dict:
    try:
        raw = base64.b64decode(content_base64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise HTTPException(422, "Imagem em Base64 inválida.") from exc
    if not raw or len(raw) > MAX_PDF_BYTES:
        raise HTTPException(413, "A imagem deve ter até 10 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP", "TIFF"}:
                raise HTTPException(422, "Formato de imagem não suportado.")
            if image.width * image.height > 20_000_000:
                raise HTTPException(413, "A imagem excede o limite de 20 megapixels.")
            image = image.convert("RGB")
            image.thumbnail((4000, 4000))
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "Imagem inválida ou não suportada.") from exc
    text = _ocr_image_bytes(buffer.getvalue())
    return _parse_danfe_text(text, raw)


def parse_document(payload: FiscalPreviewRequest) -> dict:
    parsed = (
        parse_nfe_pdf(payload.content)
        if payload.format == "pdf"
        else parse_nfe_image(payload.content)
        if payload.format == "image"
        else parse_nfe_xml(payload.content)
    )
    if not payload.qr_code_payload:
        parsed["qr_code_status"] = "not_provided"
        parsed["qr_code_access_key"] = None
        return parsed
    qr_text = unquote_plus(payload.qr_code_payload)
    match = re.search(r"(?<!\d)(\d{44})(?!\d)", qr_text)
    if not match:
        raise HTTPException(
            422, "O conteúdo informado não contém uma chave de acesso válida no QR Code."
        )
    qr_key = match.group(1)
    if not _valid_access_key(qr_key):
        raise HTTPException(422, "O QR Code contém uma chave com dígito verificador inválido.")
    if qr_key != parsed["access_key"]:
        raise HTTPException(
            422, "A chave do QR Code não corresponde à chave do documento importado."
        )
    parsed["qr_code_status"] = "matches"
    parsed["qr_code_access_key"] = qr_key
    return parsed


@router.post("/documents/preview")
async def preview_document(
    payload: FiscalPreviewRequest,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    parsed = parse_document(payload)
    existing = await session.scalar(select(FiscalDocument.id).where(
        FiscalDocument.user_id == user.id,
        FiscalDocument.access_key == parsed["access_key"],
    ))
    return {**parsed, "already_imported": existing is not None}


@router.post("/documents/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_document(
    payload: FiscalConfirmRequest,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    parsed = parse_document(payload)
    existing = await session.scalar(select(FiscalDocument.id).where(
        FiscalDocument.user_id == user.id,
        FiscalDocument.access_key == parsed["access_key"],
    ))
    if existing:
        raise HTTPException(409, "Esta chave de acesso já foi importada.")
    account = None
    category = None
    if payload.create_expense:
        if payload.account_id is None:
            raise HTTPException(422, "Selecione uma conta para criar a despesa.")
        account = await session.scalar(select(Account).where(
            Account.id == payload.account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        ))
        if account is None or account.account_type == "credit" or account.currency != "BRL":
            raise HTTPException(422, "Selecione uma conta ativa, não creditícia e em BRL.")
        if payload.category_id:
            category = await session.scalar(select(Category).where(
                Category.id == payload.category_id,
                Category.user_id == user.id,
                Category.archived_at.is_(None),
                Category.category_type == "expense",
            ))
            if category is None:
                raise HTTPException(422, "Categoria de despesa inválida.")
    transaction = None
    if payload.create_expense:
        transaction = Transaction(
            user_id=user.id,
            account_id=account.id,
            category_id=category.id if category else None,
            transaction_type="expense",
            amount=Decimal(parsed["total_amount"]),
            currency=account.currency,
            description=f"NF-e {parsed['document_number']} · {parsed['issuer_name']}"[:160],
            occurred_at=datetime.fromisoformat(parsed["issue_date"]),
            idempotency_key=f"nfe:{parsed['access_key']}",
        )
        session.add(transaction)
        await session.flush()
    document = FiscalDocument(
        user_id=user.id,
        access_key=parsed["access_key"],
        document_number=parsed["document_number"][:20],
        series=parsed["series"][:10],
        issuer_name=parsed["issuer_name"],
        issuer_tax_id=parsed["issuer_tax_id"],
        issue_date=datetime.fromisoformat(parsed["issue_date"]),
        total_amount=parsed["total_amount"],
        currency=parsed["currency"],
        items_json=json.dumps(parsed["items"], ensure_ascii=False),
        xml_sha256=parsed["xml_sha256"],
        account_id=account.id if account else None,
        category_id=category.id if category else None,
        transaction_id=transaction.id if transaction else None,
    )
    session.add(document)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Documento ou despesa já importado; atualize a prévia.") from None
    return {
        "id": str(document.id),
        "access_key": document.access_key,
        "issuer_name": document.issuer_name,
        "document_number": document.document_number,
        "total_amount": document.total_amount,
        "transaction_id": str(transaction.id) if transaction else None,
    }


@router.get("/documents")
async def list_documents(
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    rows = await session.scalars(
        select(FiscalDocument).where(FiscalDocument.user_id == user.id)
        .order_by(FiscalDocument.issue_date.desc())
    )
    return [{
        "id": str(row.id),
        "access_key": row.access_key,
        "document_number": row.document_number,
        "series": row.series,
        "issuer_name": row.issuer_name,
        "issuer_tax_id": row.issuer_tax_id,
        "issue_date": row.issue_date.isoformat(),
        "total_amount": row.total_amount,
        "currency": row.currency,
        "items": json.loads(row.items_json),
        "transaction_id": str(row.transaction_id) if row.transaction_id else None,
    } for row in rows.all()]
