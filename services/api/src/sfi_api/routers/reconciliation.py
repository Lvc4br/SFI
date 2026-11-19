import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Transaction
from sfi_api.models.reconciliation import BankStatementEntry
from sfi_api.models.user import User
from sfi_api.routers.data_exchange import ImportRequest, _parse_content, _resolve_account

router = APIRouter(prefix="/reconciliation", tags=["bank reconciliation"])
SESSION_DEPENDENCY = Depends(get_session)
USER_DEPENDENCY = Depends(get_current_user)


class StatementImportRequest(BaseModel):
    format: Literal["csv", "json", "ofx"]
    content: str = Field(min_length=1)
    account_id: uuid.UUID

    @field_validator("content")
    @classmethod
    def limit_content(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 5 * 1024 * 1024:
            raise ValueError("O extrato excede o limite de 5 MB.")
        return value


class MatchRequest(BaseModel):
    transaction_id: uuid.UUID


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _entry_key(user_id: uuid.UUID, account: Account, row: dict) -> str:
    material = "|".join(
        [
            str(user_id),
            str(account.id),
            row["transaction_type"],
            str(row["amount"]),
            _utc(row["occurred_at"]).isoformat(),
            row["description"].strip().casefold(),
            row.get("external_id", ""),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _entry_response(entry: BankStatementEntry) -> dict:
    return {
        "id": str(entry.id),
        "account_id": str(entry.account_id),
        "matched_transaction_id": (
            str(entry.matched_transaction_id) if entry.matched_transaction_id else None
        ),
        "external_id": entry.external_id,
        "transaction_type": entry.transaction_type,
        "amount": str(entry.amount),
        "currency": entry.currency,
        "description": entry.description,
        "occurred_at": entry.occurred_at.isoformat(),
        "status": entry.status,
        "matched_at": entry.matched_at.isoformat() if entry.matched_at else None,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.post("/statements/import", status_code=status.HTTP_201_CREATED)
async def import_statement(
    payload: StatementImportRequest,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    account = await session.scalar(
        select(Account).where(
            Account.id == payload.account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
            Account.account_type != "credit",
        )
    )
    if account is None:
        raise HTTPException(422, "Selecione uma conta ativa e não creditícia.")
    parsed_rows = _parse_content(
        ImportRequest(
            format=payload.format,
            content=payload.content,
            default_account_id=payload.account_id,
        )
    )
    invalid = [row for row in parsed_rows if row.get("error")]
    if invalid:
        raise HTTPException(
            422,
            detail={
                "message": "Extrato não importado: corrija as linhas inválidas.",
                "invalid_rows": [
                    {"line": row["line"], "error": row["error"]} for row in invalid
                ],
            },
        )
    created = 0
    duplicates = 0
    seen: set[str] = set()
    for row in parsed_rows:
        row_account = await _resolve_account(session, user.id, row, payload.account_id)
        if row_account.id != account.id:
            raise HTTPException(422, "Todas as linhas precisam pertencer à conta selecionada.")
        if row_account.currency != account.currency:
            raise HTTPException(422, "A moeda do lançamento diverge da conta.")
        key = _entry_key(user.id, account, row)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        exists = await session.scalar(
            select(BankStatementEntry.id).where(
                BankStatementEntry.user_id == user.id,
                BankStatementEntry.idempotency_key == key,
            )
        )
        external_id = row.get("external_id") or None
        if not exists and external_id:
            exists = await session.scalar(
                select(BankStatementEntry.id).where(
                    BankStatementEntry.user_id == user.id,
                    BankStatementEntry.account_id == account.id,
                    BankStatementEntry.external_id == external_id,
                )
            )
        if exists:
            duplicates += 1
            continue
        session.add(
            BankStatementEntry(
                user_id=user.id,
                account_id=account.id,
                external_id=external_id[:160] if external_id else None,
                idempotency_key=key,
                transaction_type=row["transaction_type"],
                amount=row["amount"],
                currency=account.currency,
                description=row["description"],
                occurred_at=_utc(row["occurred_at"]),
                status="pending",
            )
        )
        created += 1
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            409, "O extrato contém registros já importados; atualize e tente novamente."
        ) from None
    return {"created": created, "duplicates_skipped": duplicates, "total": len(parsed_rows)}


@router.get("/entries")
async def list_entries(
    account_id: uuid.UUID | None = None,
    entry_status: Literal["pending", "matched", "ignored"] | None = None,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    query = select(BankStatementEntry).where(BankStatementEntry.user_id == user.id)
    if account_id:
        query = query.where(BankStatementEntry.account_id == account_id)
    if entry_status:
        query = query.where(BankStatementEntry.status == entry_status)
    rows = await session.scalars(
        query.order_by(BankStatementEntry.occurred_at.desc()).limit(500)
    )
    return [_entry_response(row) for row in rows.all()]


@router.get("/summary")
async def reconciliation_summary(
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    rows = await session.execute(
        select(BankStatementEntry.status, BankStatementEntry.currency).where(
            BankStatementEntry.user_id == user.id
        )
    )
    totals: dict[str, dict[str, int]] = {}
    for entry_status, currency in rows.all():
        totals.setdefault(currency, {"pending": 0, "matched": 0, "ignored": 0})
        totals[currency][entry_status] += 1
    return {
        "entries_by_currency": [
            {"currency": currency, **counts} for currency, counts in sorted(totals.items())
        ]
    }


@router.get("/entries/{entry_id}/suggestions")
async def match_suggestions(
    entry_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    entry = await session.scalar(
        select(BankStatementEntry).where(
            BankStatementEntry.id == entry_id,
            BankStatementEntry.user_id == user.id,
        )
    )
    if entry is None:
        raise HTTPException(404, "Registro de extrato não encontrado.")
    if entry.status != "pending":
        raise HTTPException(409, "Somente registros pendentes podem ser conciliados.")
    lower = _utc(entry.occurred_at) - timedelta(days=7)
    upper = _utc(entry.occurred_at) + timedelta(days=7)
    candidates = await session.scalars(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.account_id == entry.account_id,
            Transaction.currency == entry.currency,
            Transaction.transaction_type == entry.transaction_type,
            Transaction.amount == entry.amount,
            Transaction.occurred_at >= lower,
            Transaction.occurred_at <= upper,
            Transaction.transfer_id.is_(None),
            Transaction.reversal_of_transaction_id.is_(None),
        ).order_by(Transaction.occurred_at.desc()).limit(100)
    )
    matched_ids = set(
        (await session.scalars(
            select(BankStatementEntry.matched_transaction_id).where(
                BankStatementEntry.user_id == user.id,
                BankStatementEntry.matched_transaction_id.is_not(None),
            )
        )).all()
    )
    results = []
    for transaction in candidates.all():
        if transaction.id in matched_ids:
            continue
        day_delta = (
            abs((_utc(transaction.occurred_at) - _utc(entry.occurred_at)).total_seconds())
            / 86400
        )
        similarity = SequenceMatcher(
            None, entry.description.casefold(), transaction.description.casefold()
        ).ratio()
        score = max(0, 100 - int(day_delta * 10)) * 0.75 + similarity * 25
        results.append(
            {
                "transaction_id": str(transaction.id),
                "description": transaction.description,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "occurred_at": transaction.occurred_at.isoformat(),
                "date_difference_days": round(day_delta, 2),
                "description_similarity": round(similarity, 3),
                "score": round(score, 1),
            }
        )
    return sorted(results, key=lambda row: row["score"], reverse=True)


@router.post("/entries/{entry_id}/match")
async def match_entry(
    entry_id: uuid.UUID,
    payload: MatchRequest,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    entry = await session.scalar(
        select(BankStatementEntry).where(
            BankStatementEntry.id == entry_id,
            BankStatementEntry.user_id == user.id,
        )
    )
    if entry is None:
        raise HTTPException(404, "Registro de extrato não encontrado.")
    if entry.status != "pending":
        raise HTTPException(409, "O registro não está pendente.")
    transaction = await session.scalar(
        select(Transaction).where(
            Transaction.id == payload.transaction_id,
            Transaction.user_id == user.id,
        )
    )
    if transaction is None:
        raise HTTPException(404, "Movimentação não encontrada.")
    if (
        transaction.account_id != entry.account_id
        or transaction.currency != entry.currency
        or transaction.transaction_type != entry.transaction_type
        or transaction.amount != entry.amount
        or transaction.transfer_id is not None
        or transaction.reversal_of_transaction_id is not None
    ):
        raise HTTPException(
            422,
            "Conciliação manual exige mesma conta, moeda, tipo e valor; "
            "transferências e estornos não entram nesta etapa.",
        )
    try:
        entry.matched_transaction_id = transaction.id
        entry.status = "matched"
        entry.matched_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(entry)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            409, "Esta movimentação já foi conciliada com outro registro."
        ) from None
    return _entry_response(entry)


@router.post("/entries/{entry_id}/ignore")
async def ignore_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    entry = await session.scalar(
        select(BankStatementEntry).where(
            BankStatementEntry.id == entry_id,
            BankStatementEntry.user_id == user.id,
        )
    )
    if entry is None:
        raise HTTPException(404, "Registro de extrato não encontrado.")
    if entry.status != "pending":
        raise HTTPException(409, "Somente registros pendentes podem ser ignorados.")
    entry.status = "ignored"
    await session.commit()
    await session.refresh(entry)
    return _entry_response(entry)


@router.post("/entries/{entry_id}/unmatch")
async def unmatch_entry(
    entry_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    entry = await session.scalar(
        select(BankStatementEntry).where(
            BankStatementEntry.id == entry_id,
            BankStatementEntry.user_id == user.id,
        )
    )
    if entry is None:
        raise HTTPException(404, "Registro de extrato não encontrado.")
    if entry.status != "matched":
        raise HTTPException(409, "O registro não está conciliado.")
    entry.matched_transaction_id = None
    entry.matched_at = None
    entry.status = "pending"
    await session.commit()
    await session.refresh(entry)
    return _entry_response(entry)
