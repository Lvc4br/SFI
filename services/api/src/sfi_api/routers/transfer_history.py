import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Transfer
from sfi_api.models.transfer_reversal import TransferReversal
from sfi_api.models.user import User

router = APIRouter(prefix="/finance", tags=["finance"])


class TransferHistoryItem(BaseModel):
    id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal
    currency: str
    description: str
    occurred_at: datetime
    created_at: datetime
    is_reversed: bool
    reversal_id: uuid.UUID | None = None
    reversed_at: datetime | None = None


@router.get("/transfers", response_model=list[TransferHistoryItem])
async def list_transfers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[TransferHistoryItem]:
    result = await session.execute(
        select(Transfer, TransferReversal)
        .outerjoin(
            TransferReversal,
            and_(
                TransferReversal.transfer_id == Transfer.id,
                TransferReversal.user_id == Transfer.user_id,
            ),
        )
        .where(Transfer.user_id == user.id)
        .order_by(Transfer.occurred_at.desc(), Transfer.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        TransferHistoryItem(
            id=transfer.id,
            source_account_id=transfer.source_account_id,
            destination_account_id=transfer.destination_account_id,
            amount=transfer.amount,
            currency=transfer.currency,
            description=transfer.description,
            occurred_at=transfer.occurred_at,
            created_at=transfer.created_at,
            is_reversed=reversal is not None,
            reversal_id=reversal.id if reversal is not None else None,
            reversed_at=reversal.occurred_at if reversal is not None else None,
        )
        for transfer, reversal in result.all()
    ]
