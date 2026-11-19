import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.patrimony import PatrimonyItem, PatrimonyValuation
from sfi_api.models.user import User

router = APIRouter(prefix="/patrimony", tags=["patrimony"])
SESSION_DEPENDENCY = Depends(get_session)
USER_DEPENDENCY = Depends(get_current_user)

ItemKind = Literal["asset", "liability"]
Category = Literal[
    "property", "vehicle", "cash", "receivable", "investment", "other_asset",
    "loan", "financing", "credit_card", "tax", "other_liability",
]


class PatrimonyItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    item_kind: ItemKind
    category: Category
    currency: str = Field(default="BRL", pattern=r"^[A-Z]{3}$")
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Informe o nome do bem ou passivo.")
        return value

    @model_validator(mode="after")
    def category_matches_kind(self):
        asset_categories = {
            "property", "vehicle", "cash", "receivable", "investment", "other_asset"
        }
        if self.item_kind == "asset" and self.category not in asset_categories:
            raise ValueError("A categoria selecionada não corresponde a um bem.")
        if self.item_kind == "liability" and self.category in asset_categories:
            raise ValueError("A categoria selecionada não corresponde a um passivo.")
        return self


class PatrimonyItemUpdate(BaseModel):
    archived: bool


class PatrimonyItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    item_kind: ItemKind
    category: Category
    currency: str
    description: str | None
    archived: bool
    created_at: datetime


class ValuationCreate(BaseModel):
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)
    idempotency_key: str = Field(min_length=16, max_length=100)
    valued_at: datetime

    @field_validator("valued_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data da avaliação precisa conter fuso horário.")
        return value.astimezone(UTC)


class ValuationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    amount: Decimal
    notes: str | None
    valued_at: datetime
    created_at: datetime


class CurrencyPosition(BaseModel):
    currency: str
    assets_total: Decimal
    liabilities_total: Decimal
    net_worth: Decimal
    items_count: int


class PatrimonySnapshot(BaseModel):
    as_of: date
    currencies: list[CurrencyPosition]


async def _snapshot(
    session: AsyncSession, user_id: uuid.UUID, cutoff: datetime, as_of: date
) -> PatrimonySnapshot:
    items = await session.scalars(
        select(PatrimonyItem).where(
            PatrimonyItem.user_id == user_id, PatrimonyItem.archived.is_(False)
        )
    )
    item_rows = list(items.all())
    if not item_rows:
        return PatrimonySnapshot(as_of=as_of, currencies=[])
    item_ids = [item.id for item in item_rows]
    valuations = await session.scalars(
        select(PatrimonyValuation)
        .where(
            PatrimonyValuation.user_id == user_id,
            PatrimonyValuation.item_id.in_(item_ids),
            PatrimonyValuation.valued_at <= cutoff,
        )
        .order_by(PatrimonyValuation.valued_at, PatrimonyValuation.created_at)
    )
    latest: dict[uuid.UUID, PatrimonyValuation] = {}
    for valuation in valuations.all():
        latest[valuation.item_id] = valuation
    totals: dict[str, dict[str, Decimal | int]] = defaultdict(
        lambda: {
            "assets": Decimal("0.00"),
            "liabilities": Decimal("0.00"),
            "count": 0,
        }
    )
    for item in item_rows:
        valuation = latest.get(item.id)
        if valuation is None:
            continue
        bucket = totals[item.currency]
        if item.item_kind == "asset":
            bucket["assets"] = Decimal(bucket["assets"]) + valuation.amount
        else:
            bucket["liabilities"] = Decimal(bucket["liabilities"]) + valuation.amount
        bucket["count"] = int(bucket["count"]) + 1
    currencies = [
        CurrencyPosition(
            currency=currency,
            assets_total=Decimal(values["assets"]),
            liabilities_total=Decimal(values["liabilities"]),
            net_worth=Decimal(values["assets"]) - Decimal(values["liabilities"]),
            items_count=int(values["count"]),
        )
        for currency, values in sorted(totals.items())
    ]
    return PatrimonySnapshot(as_of=as_of, currencies=currencies)


@router.post("", response_model=PatrimonyItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: PatrimonyItemCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    item = PatrimonyItem(user_id=user.id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("", response_model=list[PatrimonyItemResponse])
async def list_items(
    include_archived: bool = False,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    query = select(PatrimonyItem).where(PatrimonyItem.user_id == user.id)
    if not include_archived:
        query = query.where(PatrimonyItem.archived.is_(False))
    result = await session.scalars(query.order_by(PatrimonyItem.item_kind, PatrimonyItem.name))
    return list(result.all())


@router.patch("/{item_id}", response_model=PatrimonyItemResponse)
async def update_item(
    item_id: uuid.UUID,
    payload: PatrimonyItemUpdate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    item = await session.scalar(
        select(PatrimonyItem)
        .where(PatrimonyItem.id == item_id, PatrimonyItem.user_id == user.id)
        .with_for_update()
    )
    if item is None:
        raise HTTPException(404, "Item patrimonial não encontrado.")
    item.archived = payload.archived
    await session.commit()
    await session.refresh(item)
    return item


@router.post(
    "/{item_id}/valuations",
    response_model=ValuationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_valuation(
    item_id: uuid.UUID,
    payload: ValuationCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    item = await session.scalar(
        select(PatrimonyItem)
        .where(
            PatrimonyItem.id == item_id,
            PatrimonyItem.user_id == user.id,
            PatrimonyItem.archived.is_(False),
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(404, "Item patrimonial não encontrado ou arquivado.")
    duplicate = await session.scalar(
        select(PatrimonyValuation.id).where(
            PatrimonyValuation.user_id == user.id,
            PatrimonyValuation.idempotency_key == payload.idempotency_key,
        )
    )
    if duplicate:
        raise HTTPException(409, "Chave de idempotência já utilizada.")
    valuation = PatrimonyValuation(
        user_id=user.id, item_id=item.id, **payload.model_dump()
    )
    session.add(valuation)
    try:
        await session.commit()
        await session.refresh(valuation)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Avaliação duplicada ou conflitante.") from None
    return valuation


@router.get("/{item_id}/valuations", response_model=list[ValuationResponse])
async def list_valuations(
    item_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    item = await session.scalar(
        select(PatrimonyItem.id).where(
            PatrimonyItem.id == item_id, PatrimonyItem.user_id == user.id
        )
    )
    if item is None:
        raise HTTPException(404, "Item patrimonial não encontrado.")
    result = await session.scalars(
        select(PatrimonyValuation)
        .where(
            PatrimonyValuation.item_id == item_id,
            PatrimonyValuation.user_id == user.id,
        )
        .order_by(PatrimonyValuation.valued_at.desc())
    )
    return list(result.all())


@router.get("/summary", response_model=PatrimonySnapshot)
async def summary(
    as_of: date | None = None,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    selected_date = as_of or datetime.now(UTC).date()
    cutoff = datetime.combine(selected_date, time.max, tzinfo=UTC)
    return await _snapshot(session, user.id, cutoff, selected_date)


@router.get("/history", response_model=list[PatrimonySnapshot])
async def history(
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, "A data inicial não pode ser posterior à final.")
    result = await session.scalars(
        select(PatrimonyValuation.valued_at)
        .where(PatrimonyValuation.user_id == user.id)
        .order_by(PatrimonyValuation.valued_at)
    )
    dates = sorted({value.date() for value in result.all()})
    if start_date:
        dates = [value for value in dates if value >= start_date]
    if end_date:
        dates = [value for value in dates if value <= end_date]
    snapshots = []
    for day in dates:
        cutoff = datetime.combine(day, time.max, tzinfo=UTC)
        snapshots.append(await _snapshot(session, user.id, cutoff, day))
    return snapshots
