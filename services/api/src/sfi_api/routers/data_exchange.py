import csv
import hashlib
import io
import json
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Category, Transaction
from sfi_api.models.user import User

router = APIRouter(prefix="/exchange", tags=["data exchange"])
MAX_IMPORT_BYTES = 5 * 1024 * 1024
MAX_IMPORT_ROWS = 10000


class ImportRequest(BaseModel):
    format: Literal["csv", "json", "ofx"]
    content: str = Field(min_length=1)
    default_account_id: uuid.UUID | None = None
    default_category_id: uuid.UUID | None = None


class ConfirmedImportRequest(ImportRequest):
    confirmed: bool


def _date_value(value: str) -> datetime:
    raw = value.strip()
    if not raw:
        raise ValueError("Data não informada.")
    if re.fullmatch(r"\d{8}(?:\d{6})?.*", raw):
        parsed = datetime.strptime(raw[:8], "%Y%m%d").replace(tzinfo=UTC)
        return parsed
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%d/%m/%Y").replace(
                hour=12, tzinfo=UTC
            )
        except ValueError as exc:
            raise ValueError("Data inválida; use ISO 8601 ou DD/MM/AAAA.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("A data precisa conter fuso horário.")
    return parsed.astimezone(UTC)


def _normalize_row(row: dict, line: int, source_format: str) -> dict:
    lowered = {
        str(key).strip().lstrip("\ufeff").lower(): value
        for key, value in row.items()
        if key
    }
    raw_amount = str(lowered.get("amount", lowered.get("trnamt", ""))).strip()
    normalized_amount = raw_amount.replace("R$", "").replace(" ", "")
    if "," in normalized_amount and "." in normalized_amount:
        normalized_amount = normalized_amount.replace(".", "").replace(",", ".")
    else:
        normalized_amount = normalized_amount.replace(",", ".")
    try:
        amount = Decimal(normalized_amount)
    except InvalidOperation as exc:
        raise ValueError("Valor monetário inválido.") from exc
    transaction_type = str(
        lowered.get("transaction_type", lowered.get("type", lowered.get("trntype", "")))
    ).strip().lower()
    if transaction_type in {"credit", "dep", "directdep", "int", "div"}:
        transaction_type = "income"
    elif transaction_type in {
        "debit", "check", "payment", "fee", "srvchg", "pos", "atm", "directdebit"
    }:
        transaction_type = "expense"
    if amount < 0:
        amount = abs(amount)
        transaction_type = "expense"
    if transaction_type not in {"income", "expense"}:
        raise ValueError("Tipo deve ser income/expense ou equivalente OFX.")
    if amount <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("A movimentação não pode ter mais de duas casas decimais.")
    if amount > Decimal("9999999999999999.99"):
        raise ValueError("O valor excede o limite de precisão financeira.")
    date_text = str(
        lowered.get("occurred_at", lowered.get("date", lowered.get("dtposted", "")))
    )
    description = str(
        lowered.get("description", lowered.get("name", lowered.get("memo", "")))
    ).strip()
    if not description:
        raise ValueError("Descrição não informada.")
    return {
        "line": line,
        "amount": amount,
        "transaction_type": transaction_type,
        "occurred_at": _date_value(date_text),
        "description": description[:160],
        "account_id": str(lowered.get("account_id", "")).strip() or None,
        "account_name": (
            str(lowered.get("account_name", lowered.get("account", ""))).strip() or None
        ),
        "category_id": str(lowered.get("category_id", "")).strip() or None,
        "category_name": (
            str(lowered.get("category_name", lowered.get("category", ""))).strip() or None
        ),
        "external_id": str(lowered.get("external_id", lowered.get("fitid", ""))).strip(),
    }


def _parse_content(payload: ImportRequest) -> list[dict]:
    if len(payload.content.encode("utf-8")) > MAX_IMPORT_BYTES:
        raise HTTPException(413, "O arquivo excede o limite de 5 MB.")
    if payload.format == "csv":
        try:
            sample = payload.content[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\\t")
            except csv.Error:
                dialect = csv.excel
            rows = list(csv.DictReader(io.StringIO(payload.content), dialect=dialect))
        except csv.Error as exc:
            raise HTTPException(422, f"CSV inválido: {exc}") from exc
        if not rows:
            raise HTTPException(422, "O CSV não contém linhas de dados.")
    elif payload.format == "json":
        try:
            decoded = json.loads(payload.content)
        except json.JSONDecodeError as exc:
            raise HTTPException(422, "JSON inválido.") from exc
        rows = decoded.get("transactions", []) if isinstance(decoded, dict) else decoded
        if not isinstance(rows, list) or not rows:
            raise HTTPException(422, "O JSON deve conter uma lista de transações.")
    else:
        rows = []
        pattern = r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>|</BANKTRANLIST>))"
        for match in re.finditer(pattern, payload.content, re.I | re.S):
            block = match.group(1)
            values = {
                key.lower(): value.strip()
                for key, value in re.findall(r"<([A-Z0-9]+)>([^<\r\n]+)", block, re.I)
            }
            rows.append(values)
        if not rows:
            raise HTTPException(422, "OFX sem registros STMTTRN.")
    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(413, "O arquivo excede 10.000 movimentações.")
    normalized = []
    for index, row in enumerate(rows, start=2 if payload.format == "csv" else 1):
        if not isinstance(row, dict):
            normalized.append({"line": index, "error": "Registro precisa ser um objeto."})
            continue
        try:
            normalized.append(_normalize_row(row, index, payload.format))
        except (ValueError, TypeError) as exc:
            normalized.append({"line": index, "error": str(exc)})
    return normalized


async def _resolve_account(
    session: AsyncSession, user_id: uuid.UUID, row: dict, default_id: uuid.UUID | None
) -> Account:
    account_id = row.get("account_id") or (str(default_id) if default_id else None)
    if account_id:
        try:
            parsed_id = uuid.UUID(account_id)
        except ValueError as exc:
            raise ValueError("Identificador de conta inválido.") from exc
        account = await session.scalar(
            select(Account).where(
                Account.id == parsed_id,
                Account.user_id == user_id,
                Account.archived_at.is_(None),
            )
        )
    elif row.get("account_name"):
        account = await session.scalar(
            select(Account).where(
                Account.user_id == user_id,
                Account.name == row["account_name"],
                Account.archived_at.is_(None),
            )
        )
    else:
        raise ValueError("Informe account_id/account_name ou uma conta padrão.")
    if account is None:
        raise ValueError("Conta inexistente, arquivada ou de outro usuário.")
    return account


async def _resolve_category(
    session: AsyncSession, user_id: uuid.UUID, row: dict, default_id: uuid.UUID | None
) -> Category | None:
    category_id = row.get("category_id") or (str(default_id) if default_id else None)
    if category_id:
        try:
            parsed_id = uuid.UUID(category_id)
        except ValueError as exc:
            raise ValueError("Identificador de categoria inválido.") from exc
        category = await session.scalar(
            select(Category).where(
                Category.id == parsed_id,
                Category.user_id == user_id,
                Category.archived_at.is_(None),
            )
        )
    elif row.get("category_name"):
        category = await session.scalar(
            select(Category).where(
                Category.user_id == user_id,
                Category.name == row["category_name"],
                Category.archived_at.is_(None),
            )
        )
    else:
        return None
    if category is None:
        raise ValueError("Categoria inexistente, arquivada ou de outro usuário.")
    if category.category_type != row["transaction_type"]:
        raise ValueError("A categoria não corresponde ao tipo da movimentação.")
    return category


def _idempotency_key(
    user_id: uuid.UUID, account: Account, category: Category | None, row: dict
) -> str:
    material = "|".join(
        [
            str(user_id), str(account.id), str(category.id if category else ""),
            row["transaction_type"], str(row["amount"]),
            row["occurred_at"].isoformat(), row["description"], row.get("external_id", ""),
        ]
    )
    return "exchange:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


async def _prepare(
    payload: ImportRequest, session: AsyncSession, user: User
) -> tuple[list[dict], int, int]:
    rows = _parse_content(payload)
    prepared = []
    seen_keys: set[str] = set()
    valid_count = 0
    duplicate_count = 0
    for row in rows:
        if "error" in row:
            prepared.append(row)
            continue
        try:
            account = await _resolve_account(session, user.id, row, payload.default_account_id)
            category = await _resolve_category(session, user.id, row, payload.default_category_id)
            key = _idempotency_key(user.id, account, category, row)
            duplicate = key in seen_keys or bool(
                await session.scalar(
                    select(Transaction.id).where(
                        Transaction.user_id == user.id,
                        Transaction.idempotency_key == key,
                    )
                )
            )
            seen_keys.add(key)
            entry = {
                **row,
                "account_id": account.id,
                "category_id": category.id if category else None,
                "currency": account.currency,
                "idempotency_key": key,
                "status": "duplicate" if duplicate else "valid",
            }
            duplicate_count += int(bool(duplicate))
            valid_count += int(not duplicate)
            prepared.append(entry)
        except ValueError as exc:
            prepared.append({"line": row["line"], "error": str(exc), "status": "invalid"})
    return prepared, valid_count, duplicate_count


@router.post("/transactions/preview")
async def preview_transactions(
    payload: ImportRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    rows, valid_count, duplicate_count = await _prepare(payload, session, user)
    invalid = [row for row in rows if row.get("error")]
    return {
        "total": len(rows),
        "valid": valid_count,
        "duplicates": duplicate_count,
        "invalid": len(invalid),
        "rows": [
            {
                "line": row["line"],
                "status": row.get("status", "invalid"),
                "description": row.get("description", ""),
                "amount": str(row.get("amount", "")),
                "currency": row.get("currency", ""),
                "error": row.get("error"),
            }
            for row in rows
        ],
    }


@router.post("/transactions/import", status_code=status.HTTP_201_CREATED)
async def import_transactions(
    payload: ConfirmedImportRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    if not payload.confirmed:
        raise HTTPException(409, "A importação exige confirmação explícita.")
    rows, valid_count, duplicate_count = await _prepare(payload, session, user)
    invalid = [row for row in rows if row.get("error")]
    if invalid:
        raise HTTPException(
            422,
            detail={
                "message": "Importação cancelada: corrija todas as linhas inválidas.",
                "invalid_rows": [
                    {"line": row["line"], "error": row["error"]} for row in invalid
                ],
            },
        )
    for row in rows:
        if row["status"] != "valid":
            continue
        session.add(
            Transaction(
                user_id=user.id,
                account_id=row["account_id"],
                category_id=row["category_id"],
                transaction_type=row["transaction_type"],
                amount=row["amount"],
                currency=row["currency"],
                description=row["description"],
                occurred_at=row["occurred_at"],
                idempotency_key=row["idempotency_key"],
            )
        )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            409, "Conflito de idempotência; atualize a prévia e tente novamente."
        ) from None
    return {
        "created": valid_count,
        "duplicates_skipped": duplicate_count,
        "total": len(rows),
    }


@router.get("/transactions/export")
async def export_transactions(
    format: Literal["csv", "json"] = "csv",
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    rows = await session.scalars(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.occurred_at, Transaction.created_at)
    )
    records = [
        {
            "id": str(row.id),
            "account_id": str(row.account_id),
            "category_id": str(row.category_id) if row.category_id else "",
            "transaction_type": row.transaction_type,
            "amount": str(row.amount),
            "currency": row.currency,
            "description": row.description,
            "occurred_at": row.occurred_at.isoformat(),
        }
        for row in rows.all()
    ]
    if format == "json":
        return Response(
            content=json.dumps(records, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="sfi-transactions.json"'},
        )
    buffer = io.StringIO(newline="")
    fields = [
        "id", "account_id", "category_id", "transaction_type", "amount",
        "currency", "description", "occurred_at",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(records)
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="sfi-transactions.csv"'},
    )
