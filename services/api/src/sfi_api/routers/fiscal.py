import hashlib
import json
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.fiscal import FiscalDocument
from sfi_api.models.finance import Account, Category, Transaction
from sfi_api.models.user import User

router = APIRouter(prefix="/fiscal", tags=["fiscal documents"])
MAX_XML_BYTES = 2 * 1024 * 1024


class FiscalPreviewRequest(BaseModel):
    content: str = Field(min_length=1)


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
        raise HTTPException(422, "A NF-e está incompleta: emitente, identificação ou total ausente.")
    issuer_name = _text(issuer, "xNome")
    issuer_tax_id = re.sub(r"\D", "", _text(issuer, "CNPJ") or _text(issuer, "CPF"))
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
    if amount <= 0 or amount > Decimal("9999999999999999.99"):
        raise HTTPException(422, "O valor total da nota deve ser positivo e válido.")

    items = []
    for detail in (node for node in info if _local(node.tag) == "det"):
        product = next((node for node in detail if _local(node.tag) == "prod"), None)
        if product is None:
            continue
        def child(name: str) -> str:
            node = next((item for item in product if _local(item.tag) == name), None)
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


@router.post("/documents/preview")
async def preview_document(
    payload: FiscalPreviewRequest,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    parsed = parse_nfe_xml(payload.content)
    existing = await session.scalar(select(FiscalDocument.id).where(
        FiscalDocument.user_id == user.id,
        FiscalDocument.access_key == parsed["access_key"],
    ))
    return {**parsed, "already_imported": existing is not None}


@router.post("/documents/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_document(
    payload: FiscalConfirmRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    parsed = parse_nfe_xml(payload.content)
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
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
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
