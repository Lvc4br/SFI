import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.product import ShoppingProduct
from sfi_api.models.stock import StockMovement
from sfi_api.models.user import User

router = APIRouter(prefix="/shopping/stock", tags=["shopping-stock"])

INBOUND = {"purchase", "adjustment_in"}
OUTBOUND = {"adjustment_out", "consumption", "waste"}


class StockMovementCreate(BaseModel):
    movement_type: str
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("movement_type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in INBOUND | OUTBOUND:
            raise ValueError("Tipo de movimentação inválido.")
        return value

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data precisa conter fuso horário.")
        return value


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    movement_type: str
    quantity: Decimal
    unit: str
    reference: str | None
    notes: str | None
    occurred_at: datetime
    created_at: datetime


class StockBalanceResponse(BaseModel):
    product_id: uuid.UUID
    product_name: str
    unit: str
    balance: Decimal


async def _balance(session: AsyncSession, user_id: uuid.UUID, product_id: uuid.UUID) -> Decimal:
    signed_quantity = case(
        (StockMovement.movement_type.in_(INBOUND), StockMovement.quantity),
        else_=-StockMovement.quantity,
    )
    value = await session.scalar(
        select(func.coalesce(func.sum(signed_quantity), 0)).where(
            StockMovement.user_id == user_id,
            StockMovement.product_id == product_id,
        )
    )
    return Decimal(value or 0).quantize(Decimal("0.001"))


@router.get("", response_model=list[StockBalanceResponse])
async def list_stock(
    include_zero: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    signed_quantity = case(
        (StockMovement.movement_type.in_(INBOUND), StockMovement.quantity),
        else_=-StockMovement.quantity,
    )
    rows = await session.execute(
        select(
            ShoppingProduct.id,
            ShoppingProduct.name,
            ShoppingProduct.unit,
            func.coalesce(func.sum(signed_quantity), 0).label("balance"),
        )
        .outerjoin(
            StockMovement,
            (StockMovement.product_id == ShoppingProduct.id)
            & (StockMovement.user_id == ShoppingProduct.user_id),
        )
        .where(
            ShoppingProduct.user_id == user.id,
            ShoppingProduct.archived_at.is_(None),
        )
        .group_by(ShoppingProduct.id, ShoppingProduct.name, ShoppingProduct.unit)
        .order_by(ShoppingProduct.name)
    )
    result = [
        StockBalanceResponse(
            product_id=row.id,
            product_name=row.name,
            unit=row.unit,
            balance=Decimal(row.balance or 0).quantize(Decimal("0.001")),
        )
        for row in rows
    ]
    return result if include_zero else [item for item in result if item.balance != 0]


@router.get("/{product_id}/movements", response_model=list[StockMovementResponse])
async def list_movements(
    product_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    product = await session.scalar(
        select(ShoppingProduct).where(
            ShoppingProduct.id == product_id,
            ShoppingProduct.user_id == user.id,
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    rows = await session.scalars(
        select(StockMovement)
        .where(StockMovement.product_id == product_id, StockMovement.user_id == user.id)
        .order_by(StockMovement.occurred_at.desc(), StockMovement.created_at.desc())
        .limit(limit)
    )
    return [StockMovementResponse.model_validate(row) for row in rows.all()]


@router.post(
    "/{product_id}/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_movement(
    product_id: uuid.UUID,
    payload: StockMovementCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    product = await session.scalar(
        select(ShoppingProduct)
        .where(
            ShoppingProduct.id == product_id,
            ShoppingProduct.user_id == user.id,
            ShoppingProduct.archived_at.is_(None),
        )
        .with_for_update()
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Produto ativo não encontrado.")

    current = await _balance(session, user.id, product_id)
    if payload.movement_type in OUTBOUND and payload.quantity > current:
        raise HTTPException(
            status_code=409,
            detail=f"Estoque insuficiente. Saldo atual: {current} {product.unit}.",
        )

    movement = StockMovement(
        user_id=user.id,
        product_id=product.id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        unit=product.unit,
        reference=payload.reference,
        notes=payload.notes,
        occurred_at=payload.occurred_at,
    )
    session.add(movement)
    await session.commit()
    await session.refresh(movement)
    return StockMovementResponse.model_validate(movement)
