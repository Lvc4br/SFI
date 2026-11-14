import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Budget, Category, Transaction, Transfer
from sfi_api.models.recurrence import Recurrence
from sfi_api.models.transfer_reversal import TransferReversal
from sfi_api.models.user import User
from sfi_api.schemas.finance import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    BudgetCreate,
    BudgetResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    TransactionCreate,
    TransactionResponse,
    TransactionReversalResponse,
    TransferCreate,
    TransferResponse,
)
from sfi_api.schemas.transfer_reversal import TransferReversalResponse

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
    include_archived: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[AccountResponse]:
    query = select(Account).where(Account.user_id == user.id)
    if not include_archived:
        query = query.where(Account.archived_at.is_(None))
    result = await session.scalars(query.order_by(Account.created_at.desc()))
    return [AccountResponse.model_validate(item) for item in result.all()]


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> AccountResponse:
    account = await session.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Conta ativa não encontrada.")
    account.name = payload.name
    await session.commit()
    await session.refresh(account)
    return AccountResponse.model_validate(account)


@router.post("/accounts/{account_id}/archive", response_model=AccountResponse)
async def archive_account(
    account_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> AccountResponse:
    account = await session.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Conta ativa não encontrada.")
    active_recurrence = await session.scalar(
        select(Recurrence.id).where(
            Recurrence.user_id == user.id,
            Recurrence.account_id == account.id,
            Recurrence.is_active.is_(True),
        ).limit(1)
    )
    if active_recurrence is not None:
        raise HTTPException(
            status_code=409,
            detail="Desative as recorrências desta conta antes de arquivá-la.",
        )
    income = func.coalesce(
        func.sum(case((Transaction.transaction_type == "income", Transaction.amount), else_=0)),
        Decimal("0.00"),
    )
    expenses = func.coalesce(
        func.sum(case((Transaction.transaction_type == "expense", Transaction.amount), else_=0)),
        Decimal("0.00"),
    )
    totals = (
        await session.execute(
            select(income.label("income"), expenses.label("expenses")).where(
                Transaction.user_id == user.id,
                Transaction.account_id == account.id,
            )
        )
    ).one()
    balance = (
        account.opening_balance + Decimal(totals.expenses) - Decimal(totals.income)
        if account.account_type == "credit"
        else account.opening_balance + Decimal(totals.income) - Decimal(totals.expenses)
    )
    if balance != Decimal("0.00"):
        raise HTTPException(
            status_code=409,
            detail="Zere o saldo da conta antes de arquivá-la.",
        )
    account.archived_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(account)
    return AccountResponse.model_validate(account)


@router.post("/categories/{category_id}/archive", response_model=CategoryResponse)
async def archive_category(
    category_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> CategoryResponse:
    category = await session.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user.id,
            Category.archived_at.is_(None),
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria ativa não encontrada.")
    active_recurrence = await session.scalar(
        select(Recurrence.id).where(
            Recurrence.user_id == user.id,
            Recurrence.category_id == category.id,
            Recurrence.is_active.is_(True),
        ).limit(1)
    )
    if active_recurrence is not None:
        raise HTTPException(
            status_code=409,
            detail="Desative as recorrências desta categoria antes de arquivá-la.",
        )
    category.archived_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(category)
    return CategoryResponse.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> CategoryResponse:
    category = await session.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user.id,
            Category.archived_at.is_(None),
        )
    )
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria ativa não encontrada.")
    category.name = payload.name
    try:
        await session.commit()
        await session.refresh(category)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma categoria ativa com este nome e tipo.",
        ) from None
    return CategoryResponse.model_validate(category)


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
    include_archived: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[CategoryResponse]:
    query = select(Category).where(Category.user_id == user.id)
    if not include_archived:
        query = query.where(Category.archived_at.is_(None))
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
        select(Account).where(
            Account.id == payload.account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
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
                Category.archived_at.is_(None),
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
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    transaction_type: str | None = Query(default=None, pattern="^(income|expense)$"),
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    min_amount: Decimal | None = Query(default=None, gt=0),  # noqa: B008
    max_amount: Decimal | None = Query(default=None, gt=0),  # noqa: B008
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[TransactionResponse]:
    if start_at is not None and (start_at.tzinfo is None or start_at.utcoffset() is None):
        raise HTTPException(status_code=422, detail="start_at precisa conter fuso horário.")
    if end_at is not None and (end_at.tzinfo is None or end_at.utcoffset() is None):
        raise HTTPException(status_code=422, detail="end_at precisa conter fuso horário.")
    if start_at is not None and end_at is not None and end_at < start_at:
        raise HTTPException(status_code=422, detail="end_at não pode ser anterior a start_at.")
    if min_amount is not None and max_amount is not None and max_amount < min_amount:
        raise HTTPException(
            status_code=422, detail="max_amount não pode ser menor que min_amount."
        )

    query = select(Transaction).where(Transaction.user_id == user.id)
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

    result = await session.scalars(
        query.order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc())
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
    reversal = aliased(Transaction)
    has_reversal = (
        select(reversal.id)
        .where(
            reversal.user_id == user_id,
            reversal.reversal_of_transaction_id == Transaction.id,
        )
        .exists()
    )
    spent = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_type == "expense",
            Transaction.reversal_of_transaction_id.is_(None),
            Transaction.currency == budget.currency,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
            ~has_reversal,
        )
    )
    spent_amount = Decimal(spent or Decimal("0.00")).quantize(Decimal("0.01"))
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
            Category.archived_at.is_(None),
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
        raise HTTPException(
            status_code=422,
            detail="As contas de origem e destino devem ser diferentes.",
        )

    accounts = await session.scalars(
        select(Account).where(
            Account.user_id == user.id,
            Account.archived_at.is_(None),
            Account.id.in_([payload.source_account_id, payload.destination_account_id]),
        )
    )
    account_map = {account.id: account for account in accounts.all()}
    source = account_map.get(payload.source_account_id)
    destination = account_map.get(payload.destination_account_id)
    if source is None or destination is None:
        raise HTTPException(status_code=404, detail="Conta de origem ou destino não encontrada.")
    if source.currency != destination.currency:
        raise HTTPException(
            status_code=422,
            detail="Transferências entre moedas diferentes não são permitidas.",
        )
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
    "/transfers/{transfer_id}/reverse",
    response_model=TransferReversalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reverse_transfer(
    transfer_id: uuid.UUID,
    idempotency_key: str = Query(min_length=16, max_length=100),
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> TransferReversalResponse:
    transfer = await session.scalar(
        select(Transfer).where(Transfer.id == transfer_id, Transfer.user_id == user.id)
    )
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transferência não encontrada.")

    existing_reversal = await session.scalar(
        select(TransferReversal).where(
            TransferReversal.user_id == user.id,
            TransferReversal.transfer_id == transfer.id,
        )
    )
    if existing_reversal is not None:
        raise HTTPException(status_code=409, detail="Esta transferência já foi estornada.")

    duplicate_key = await session.scalar(
        select(TransferReversal).where(
            TransferReversal.user_id == user.id,
            TransferReversal.idempotency_key == idempotency_key,
        )
    )
    if duplicate_key is not None:
        raise HTTPException(status_code=409, detail="Esta chave de idempotência já foi utilizada.")

    original_entries = await session.scalars(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.transfer_id == transfer.id,
        )
    )
    entries = original_entries.all()
    source_entry = next(
        (item for item in entries if item.account_id == transfer.source_account_id),
        None,
    )
    destination_entry = next(
        (item for item in entries if item.account_id == transfer.destination_account_id),
        None,
    )
    if (
        len(entries) != 2
        or source_entry is None
        or destination_entry is None
        or source_entry.transaction_type != "expense"
        or destination_entry.transaction_type != "income"
        or source_entry.amount != transfer.amount
        or destination_entry.amount != transfer.amount
        or source_entry.currency != transfer.currency
        or destination_entry.currency != transfer.currency
    ):
        raise HTTPException(
            status_code=409,
            detail="O histórico da transferência está inconsistente; estorno não realizado.",
        )

    occurred_at = datetime.now(UTC)
    reversal = TransferReversal(
        user_id=user.id,
        transfer_id=transfer.id,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at,
    )
    session.add(reversal)
    await session.flush()

    source_compensation = Transaction(
        user_id=user.id,
        account_id=transfer.source_account_id,
        category_id=None,
        transfer_reversal_id=reversal.id,
        transaction_type="income",
        amount=transfer.amount,
        currency=transfer.currency,
        description=f"Estorno de transferência recebida: {transfer.description}",
        idempotency_key=f"transfer-reversal:{reversal.id}:source",
        occurred_at=occurred_at,
    )
    destination_compensation = Transaction(
        user_id=user.id,
        account_id=transfer.destination_account_id,
        category_id=None,
        transfer_reversal_id=reversal.id,
        transaction_type="expense",
        amount=transfer.amount,
        currency=transfer.currency,
        description=f"Estorno de transferência enviada: {transfer.description}",
        idempotency_key=f"transfer-reversal:{reversal.id}:destination",
        occurred_at=occurred_at,
    )
    session.add_all([source_compensation, destination_compensation])
    try:
        await session.commit()
        await session.refresh(reversal)
        await session.refresh(source_compensation)
        await session.refresh(destination_compensation)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A transferência já foi estornada ou houve conflito de idempotência.",
        ) from None

    return TransferReversalResponse(
        transfer_id=transfer.id,
        reversal_id=reversal.id,
        occurred_at=reversal.occurred_at,
        reversal_transactions=[
            TransactionResponse.model_validate(source_compensation),
            TransactionResponse.model_validate(destination_compensation),
        ],
    )


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
    if original.transfer_id is not None or original.transfer_reversal_id is not None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Movimentações de transferência devem ser estornadas pelo fluxo de transferência."
            ),
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
