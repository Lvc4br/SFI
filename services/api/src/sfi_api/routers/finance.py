from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Budget, Category, Transaction
from sfi_api.models.user import User
from sfi_api.schemas.finance import (
    AccountCreate,
    AccountResponse,
    BudgetCreate,
    BudgetResponse,
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


async def _budget_response(
    session: AsyncSession, user_id, budget: Budget, category: Category
) -> BudgetResponse:
    year, month = (int(part) for part in budget.period.split("-"))
    start = datetime(year, month, 1, tzinfo=UTC)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=UTC)
    spent = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_type == "expense",
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
    )
    spent_amount = Decimal(spent or 0)
    remaining = budget.limit_amount - spent_amount
    usage = (spent_amount / budget.limit_amount * Decimal("100")).quantize(Decimal("0.01"))
    if spent_amount > budget.limit_amount:
        budget_status = "over_limit"
    elif spent_amount == budget.limit_amount:
        budget_status = "reached_limit"
    else:
        budget_status = "within_limit"
    return BudgetResponse(
        id=budget.id,
        category_id=budget.category_id,
        category_name=category.name,
        period=budget.period,
        currency="BRL",
        limit_amount=budget.limit_amount,
        spent_amount=spent_amount,
        remaining_amount=remaining,
        usage_percent=usage,
        status=budget_status,
        created_at=budget.created_at,
    )


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> BudgetResponse:
    category = await session.scalar(
        select(Category).where(
            Category.id == payload.category_id,
            Category.user_id == user.id,
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    if category.category_type != "expense":
        raise HTTPException(status_code=422, detail="Orçamentos só podem usar categorias de despesa.")
    budget = Budget(user_id=user.id, **payload.model_dump())
    session.add(budget)
    try:
        await session.commit()
        await session.refresh(budget)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um orçamento para esta categoria neste mês.",
        ) from None
    return await _budget_response(session, user.id, budget, category)


@router.get("/budgets", response_model=list[BudgetResponse])
async def list_budgets(
    period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[BudgetResponse]:
    result = await session.execute(
        select(Budget, Category)
        .join(Category, Budget.category_id == Category.id)
        .where(Budget.user_id == user.id, Budget.period == period)
        .order_by(Category.name.asc())
    )
    return [
        await _budget_response(session, user.id, budget, category)
        for budget, category in result.all()
    ]
