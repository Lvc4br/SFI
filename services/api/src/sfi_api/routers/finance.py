from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Budget, Category, Transaction, Transfer
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
    TransferCreate,
    TransferResponse,
    TransactionReversalResponse,
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
            Transaction.currency == budget.currency,
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
        currency=budget.currency,
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
        raise HTTPException(
            status_code=422,
            detail="Orçamentos só podem usar categorias de despesa.",
        )
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


@router.post("/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    payload: TransferCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> TransferResponse:
    existing = await session.scalar(
        select(Transfer).where(
            Transfer.user_id == user.id,
            Transfer.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta chave de idempotência já foi utilizada.",
        )

    if payload.source_account_id == payload.destination_account_id:
        raise HTTPException(status_code=422, detail="As contas de origem e destino devem ser diferentes.")

    accounts = await session.scalars(
        select(Account).where(
            Account.user_id == user.id,
            Account.id.in_([payload.source_account_id, payload.destination_account_id]),
        )
    )
    account_map = {account.id: account for account in accounts.all()}
    source = account_map.get(payload.source_account_id)
    destination = account_map.get(payload.destination_account_id)
    if source is None or destination is None:
        raise HTTPException(status_code=404, detail="Conta de origem ou destino não encontrada.")
    if source.currency != destination.currency:
        raise HTTPException(status_code=422, detail="Transferências entre moedas diferentes não são permitidas.")
    if source.account_type == "credit" or destination.account_type == "credit":
        raise HTTPException(
            status_code=422,
            detail="Transferências envolvendo cartão de crédito ainda não são suportadas.",
        )

    transfer = Transfer(
        user_id=user.id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=payload.amount,
        currency=source.currency,
        description=payload.description.strip(),
        idempotency_key=payload.idempotency_key,
        occurred_at=payload.occurred_at,
    )
    session.add(transfer)
    await session.flush()
    session.add_all([
        Transaction(
            user_id=user.id,
            account_id=source.id,
            category_id=None,
            transfer_id=transfer.id,
            transaction_type="expense",
            amount=payload.amount,
            currency=source.currency,
            description=f"Transferência enviada: {payload.description.strip()}",
            idempotency_key=f"transfer:{transfer.id}:out",
            occurred_at=payload.occurred_at,
        ),
        Transaction(
            user_id=user.id,
            account_id=destination.id,
            category_id=None,
            transfer_id=transfer.id,
            transaction_type="income",
            amount=payload.amount,
            currency=destination.currency,
            description=f"Transferência recebida: {payload.description.strip()}",
            idempotency_key=f"transfer:{transfer.id}:in",
            occurred_at=payload.occurred_at,
        ),
    ])
    try:
        await session.commit()
        await session.refresh(transfer)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflito ao registrar transferência; confira a chave de idempotência.",
        ) from None
    return TransferResponse.model_validate(transfer)


@router.post(
    "/transactions/{transaction_id}/reverse",
    response_model=TransactionReversalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reverse_transaction(
    transaction_id: uuid.UUID,
    idempotency_key: str = Query(min_length=16, max_length=100),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> TransactionReversalResponse:
    original = await session.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
    )
    if original is None:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada.")
    if original.reversal_of_transaction_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Um estorno não pode ser estornado novamente.",
        )
    if original.transfer_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Movimentações de transferência devem ser estornadas pelo fluxo de transferência.",
        )
    existing = await session.scalar(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.reversal_of_transaction_id == original.id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Esta movimentação já foi estornada.")
    duplicate_key = await session.scalar(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.idempotency_key == idempotency_key,
        )
    )
    if duplicate_key:
        raise HTTPException(status_code=409, detail="Esta chave de idempotência já foi utilizada.")

    reversal = Transaction(
        user_id=user.id,
        account_id=original.account_id,
        category_id=None,
        transaction_type="expense" if original.transaction_type == "income" else "income",
        amount=original.amount,
        currency=original.currency,
        description=f"Estorno da movimentação {original.id}",
        idempotency_key=idempotency_key,
        occurred_at=datetime.now(UTC),
        reversal_of_transaction_id=original.id,
    )
    session.add(reversal)
    try:
        await session.commit()
        await session.refresh(reversal)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="A movimentação já foi estornada.") from None
    return TransactionReversalResponse(
        original_transaction_id=original.id,
        reversal_transaction=TransactionResponse.model_validate(reversal),
    )
