import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Transaction
from sfi_api.models.user import User
from sfi_api.schemas.finance import TransactionResponse

router = APIRouter(prefix="/finance/transactions", tags=["finance"])


def _filters(
    user_id: uuid.UUID,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    transaction_type: str | None,
    start_at: datetime | None,
    end_at: datetime | None,
    min_amount: Decimal | None,
    max_amount: Decimal | None,
):
    query = select(Transaction).where(Transaction.user_id == user_id)
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if transaction_type is not None:
        query = query.where(Transaction.transaction_type == transaction_type)
    if start_at is not None:
        query = query.where(Transaction.occurred_at >= start_at)
    if end_at is not None:
        query = query.where(Transaction.occurred_at <= end_at)
    if min_amount is not None:
        query = query.where(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.where(Transaction.amount <= max_amount)
    return query


@router.get("/page")
async def list_transaction_page(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    transaction_type: str | None = Query(default=None, pattern="^(income|expense)$"),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    min_amount: Decimal | None = Query(default=None, gt=0),
    max_amount: Decimal | None = Query(default=None, gt=0),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if start_at is not None and (start_at.tzinfo is None or start_at.utcoffset() is None):
        raise HTTPException(status_code=422, detail="start_at precisa conter fuso horário.")
    if end_at is not None and (end_at.tzinfo is None or end_at.utcoffset() is None):
        raise HTTPException(status_code=422, detail="end_at precisa conter fuso horário.")
    if start_at is not None and end_at is not None and end_at < start_at:
        raise HTTPException(status_code=422, detail="end_at não pode ser anterior a start_at.")
    if min_amount is not None and max_amount is not None and max_amount < min_amount:
        raise HTTPException(status_code=422, detail="max_amount não pode ser menor que min_amount.")

    filtered = _filters(
        user.id, account_id, category_id, transaction_type,
        start_at, end_at, min_amount, max_amount,
    )
    total = await session.scalar(select(func.count()).select_from(filtered.subquery()))
    result = await session.scalars(
        filtered.order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [TransactionResponse.model_validate(item) for item in result.all()]
    return {
        "items": items,
        "total": total or 0,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < (total or 0),
    }
