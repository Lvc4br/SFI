from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Category, Transaction
from sfi_api.models.user import User
from sfi_api.schemas.finance import (
    AccountCreate,
    AccountResponse,
    CategoryCreate,
    CategoryResponse,
    TransactionCreate,
    TransactionResponse,
)

router = APIRouter(prefix="/finance", tags=["finance"])


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> AccountResponse:
    account = Account(user_id=user.id, **payload.model_dump())
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return AccountResponse.model_validate(account)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[AccountResponse]:
    result = await session.scalars(
        select(Account).where(Account.user_id == user.id).order_by(Account.created_at.desc())
    )
    return [AccountResponse.model_validate(item) for item in result.all()]


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> CategoryResponse:
    category = Category(user_id=user.id, **payload.model_dump())
    session.add(category)
    try:
        await session.commit()
        await session.refresh(category)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma categoria com este nome e tipo.",
        ) from None
    return CategoryResponse.model_validate(category)


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    category_type: str | None = Query(default=None, pattern="^(income|expense)$"),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[CategoryResponse]:
    query = select(Category).where(Category.user_id == user.id)
    if category_type:
        query = query.where(Category.category_type == category_type)
    result = await session.scalars(query.order_by(Category.name.asc()))
    return [CategoryResponse.model_validate(item) for item in result.all()]


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    payload: TransactionCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> TransactionResponse:
    existing = await session.scalar(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta chave de idempotência já foi utilizada.",
        )

    account = await session.scalar(
        select(Account).where(Account.id == payload.account_id, Account.user_id == user.id)
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    if account.account_type == "credit" and payload.transaction_type == "income":
        raise HTTPException(
            status_code=422,
            detail="Receitas não podem ser lançadas diretamente em uma conta de crédito.",
        )

    if payload.category_id:
        category = await session.scalar(
            select(Category).where(
                Category.id == payload.category_id,
                Category.user_id == user.id,
            )
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Categoria não encontrada.")
        if category.category_type != payload.transaction_type:
            raise HTTPException(
                status_code=422,
                detail="O tipo da categoria não corresponde ao tipo da movimentação.",
            )

    transaction = Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=payload.category_id,
        transaction_type=payload.transaction_type,
        amount=payload.amount,
        currency=account.currency,
        description=payload.description,
        occurred_at=payload.occurred_at,
        idempotency_key=payload.idempotency_key,
    )
    session.add(transaction)
    try:
        await session.commit()
        await session.refresh(transaction)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflito ao registrar movimentação; confira a chave de idempotência.",
        ) from None
    return TransactionResponse.model_validate(transaction)


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[TransactionResponse]:
    result = await session.scalars(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [TransactionResponse.model_validate(item) for item in result.all()]
