import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Transfer
from sfi_api.models.user import User

router = APIRouter(prefix="/finance", tags=["finance"])


class TransferHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_account_id: uuid.UUID
    destination_account_id: uuid.UUID
    amount: Decimal
    currency: str
    description: str
    occurred_at: datetime
    created_at: datetime


@router.get("/transfers", response_model=list[TransferHistoryItem])
async def list_transfers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[TransferHistoryItem]:
    result = await session.scalars(
        select(Transfer)
        .where(Transfer.user_id == user.id)
        .order_by(Transfer.occurred_at.desc(), Transfer.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [TransferHistoryItem.model_validate(item) for item in result.all()]
