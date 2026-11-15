import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Category, Transaction
from sfi_api.models.product import ProductPriceObservation, ShoppingProduct
from sfi_api.models.shopping import ShoppingList, ShoppingListItem
from sfi_api.models.stock import StockMovement
from sfi_api.models.user import User

router = APIRouter(prefix="/shopping/purchases", tags=["shopping-purchases"])


class PurchaseConfirm(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    merchant: str | None = Field(default=None, max_length=120)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("merchant")
    @classmethod
    def clean_merchant(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data da compra precisa conter fuso horário.")
        return value


class PurchaseConfirmResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    transaction_id: uuid.UUID
    list_id: uuid.UUID
    amount: Decimal
    currency: str
    description: str
    occurred_at: datetime
    items_count: int


@router.post("/{list_id}/confirm", response_model=PurchaseConfirmResponse,
             status_code=status.HTTP_201_CREATED)
async def confirm_purchase(
    list_id: uuid.UUID,
    payload: PurchaseConfirm,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> PurchaseConfirmResponse:
    shopping_list = await session.scalar(
        select(ShoppingList).where(
            ShoppingList.id == list_id,
            ShoppingList.user_id == user.id,
            ShoppingList.is_template.is_(False),
        )
    )
    if shopping_list is None:
        raise HTTPException(status_code=404, detail="Lista de compras não encontrada.")

    idempotency_key = f"shopping-purchase:{shopping_list.id}"
    existing = await session.scalar(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.idempotency_key == idempotency_key,
        )
    )
    if existing is not None or shopping_list.archived_at is not None:
        raise HTTPException(status_code=409, detail="Esta lista já foi convertida em uma compra.")

    items_result = await session.scalars(
        select(ShoppingListItem).where(
            ShoppingListItem.list_id == list_id,
            ShoppingListItem.user_id == user.id,
        ).order_by(ShoppingListItem.position, ShoppingListItem.created_at)
    )
    items = list(items_result.all())
    if not items:
        raise HTTPException(status_code=422, detail="Adicione itens antes de confirmar a compra.")
    if any(item.unit_price is None for item in items):
        raise HTTPException(
            status_code=422,
            detail="Informe o preço unitário de todos os itens antes de confirmar a compra.",
        )
    if any(not item.is_checked for item in items):
        raise HTTPException(
            status_code=422,
            detail="Marque todos os itens como comprados antes de confirmar a compra.",
        )

    linked_products: dict[uuid.UUID, ShoppingProduct] = {}
    for item in items:
        if item.product_id is None:
            continue
        product = await session.scalar(
            select(ShoppingProduct).where(
                ShoppingProduct.id == item.product_id,
                ShoppingProduct.user_id == user.id,
            )
        )
        if product is None:
            raise HTTPException(status_code=404, detail="Produto vinculado não encontrado.")
        if product.unit != item.unit:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"A unidade do item {item.name} ({item.unit}) difere da unidade "
                    f"do catálogo ({product.unit})."
                ),
            )
        linked_products[item.id] = product

    account = await session.scalar(
        select(Account).where(
            Account.id == payload.account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Conta ativa não encontrada.")
    if account.currency != "BRL":
        raise HTTPException(
            status_code=422,
            detail=(
                "A confirmação de compras exige uma conta em BRL; "
                "conversão cambial não é automática."
            ),
        )

    category = None
    if payload.category_id is not None:
        category = await session.scalar(
            select(Category).where(
                Category.id == payload.category_id,
                Category.user_id == user.id,
                Category.archived_at.is_(None),
                Category.category_type == "expense",
            )
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Categoria de despesa não encontrada.")

    total = sum(
        (item.quantity * item.unit_price for item in items if item.unit_price is not None),
        Decimal("0.00"),
    ).quantize(Decimal("0.01"))
    if total <= 0:
        raise HTTPException(status_code=422, detail="O total da compra precisa ser maior que zero.")

    # A deterministic key makes a retry safe even if the client loses the response.
    merchant = payload.merchant
    description = f"Compra: {shopping_list.name}"
    if merchant:
        description = f"{description} — {merchant}"
    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id if category else None,
        transaction_type="expense",
        amount=total,
        currency=account.currency,
        description=description[:160],
        idempotency_key=idempotency_key,
        occurred_at=payload.occurred_at,
    )
    try:
        session.add(transaction)
        await session.flush()
        for item in items:
            item.is_checked = True
            if item.product_id is not None:
                session.add(StockMovement(
                    user_id=user.id,
                    product_id=item.product_id,
                    movement_type="purchase",
                    quantity=item.quantity,
                    unit=linked_products[item.id].unit,
                    reference=f"shopping-list:{shopping_list.id}",
                    notes=f"Entrada automática da compra {shopping_list.name}"[:300],
                    occurred_at=payload.occurred_at,
                ))
                if item.unit_price is not None:
                    session.add(ProductPriceObservation(
                        product_id=item.product_id,
                        user_id=user.id,
                        price=item.unit_price,
                        currency=account.currency,
                        merchant=merchant,
                        source="manual",
                        notes=f"Compra confirmada pela lista {shopping_list.name}"[:300],
                        observed_at=payload.occurred_at,
                    ))
        shopping_list.archived_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(transaction)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A compra já foi registrada ou houve conflito de integridade.",
        ) from None

    return PurchaseConfirmResponse(
        transaction_id=transaction.id,
        list_id=shopping_list.id,
        amount=transaction.amount,
        currency=transaction.currency,
        description=transaction.description,
        occurred_at=transaction.occurred_at,
        items_count=len(items),
    )
