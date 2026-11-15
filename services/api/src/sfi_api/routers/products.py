import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.product import ProductPriceObservation, ShoppingProduct
from sfi_api.models.user import User
from sfi_api.schemas.product import (
    PriceObservationCreate,
    PriceObservationResponse,
    ProductCreate,
    ProductResponse,
)

router = APIRouter(prefix="/shopping/products", tags=["shopping-products"])


async def _owned_product(
    session: AsyncSession, user_id: uuid.UUID, product_id: uuid.UUID
) -> ShoppingProduct:
    product = await session.scalar(
        select(ShoppingProduct).where(
            ShoppingProduct.id == product_id,
            ShoppingProduct.user_id == user_id,
            ShoppingProduct.archived_at.is_(None),
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    product = ShoppingProduct(user_id=user.id, **payload.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)


@router.get("", response_model=list[ProductResponse])
async def list_products(
    search: str | None = Query(default=None, max_length=160),
    include_archived: bool = False,
    limit: int = Query(default=100, ge=1, le=200),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    query = select(ShoppingProduct).where(ShoppingProduct.user_id == user.id)
    if not include_archived:
        query = query.where(ShoppingProduct.archived_at.is_(None))
    if search and search.strip():
        query = query.where(ShoppingProduct.name.ilike(f"%{search.strip()}%"))
    rows = await session.scalars(query.order_by(ShoppingProduct.name).limit(limit))
    return [ProductResponse.model_validate(row) for row in rows.all()]


@router.post("/{product_id}/archive", response_model=ProductResponse)
async def archive_product(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    product = await _owned_product(session, user.id, product_id)
    product.archived_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(product)
    return ProductResponse.model_validate(product)


@router.post(
    "/{product_id}/prices",
    response_model=PriceObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_price_observation(
    product_id: uuid.UUID,
    payload: PriceObservationCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    await _owned_product(session, user.id, product_id)
    observation = ProductPriceObservation(
        product_id=product_id,
        user_id=user.id,
        **payload.model_dump(),
    )
    session.add(observation)
    await session.commit()
    await session.refresh(observation)
    return PriceObservationResponse.model_validate(observation)


@router.get("/{product_id}/prices", response_model=list[PriceObservationResponse])
async def list_price_history(
    product_id: uuid.UUID,
    currency: str = Query(default="BRL", min_length=3, max_length=3),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
):
    await _owned_product(session, user.id, product_id)
    rows = await session.scalars(
        select(ProductPriceObservation)
        .where(
            ProductPriceObservation.product_id == product_id,
            ProductPriceObservation.user_id == user.id,
            ProductPriceObservation.currency == currency.upper(),
        )
        .order_by(ProductPriceObservation.observed_at.desc())
        .limit(limit)
    )
    return [PriceObservationResponse.model_validate(row) for row in rows.all()]
