from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Category, Transaction
from sfi_api.models.user import User
from sfi_api.schemas.finance import (
    AccountBalanceResponse,
    CategorySpending,
    CurrencyTotals,
    FinanceSummaryResponse,
)

router = APIRouter(prefix="/finance", tags=["finance"])


def _period_bounds(
    start_date: date, end_date: date, timezone_name: str
) -> tuple[datetime, datetime]:
    timezone = ZoneInfo(timezone_name)
    start = datetime.combine(start_date, time.min, tzinfo=timezone).astimezone(UTC)
    end = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=timezone
    ).astimezone(UTC)
    return start, end


async def _account_balance(
    session: AsyncSession, user_id: UUID, account: Account
) -> AccountBalanceResponse:
    income = func.coalesce(
        func.sum(
            case(
                (Transaction.transaction_type == "income", Transaction.amount),
                else_=Decimal("0.00"),
            )
        ),
        Decimal("0.00"),
    )
    expenses = func.coalesce(
        func.sum(
            case(
                (Transaction.transaction_type == "expense", Transaction.amount),
                else_=Decimal("0.00"),
            )
        ),
        Decimal("0.00"),
    )
    totals = (
        await session.execute(
            select(income.label("income"), expenses.label("expenses")).where(
                Transaction.user_id == user_id,
                Transaction.account_id == account.id,
            )
        )
    ).one()
    income_total = Decimal(totals.income)
    expense_total = Decimal(totals.expenses)
    is_credit = account.account_type == "credit"
    balance = (
        account.opening_balance + expense_total - income_total
        if is_credit
        else account.opening_balance + income_total - expense_total
    )
    return AccountBalanceResponse(
        account_id=account.id,
        name=account.name,
        account_type=account.account_type,
        currency=account.currency,
        opening_balance=account.opening_balance,
        income_total=income_total,
        expense_total=expense_total,
        balance=balance,
        balance_kind="credit_used" if is_credit else "available_balance",
    )


@router.get("/accounts/{account_id}/balance", response_model=AccountBalanceResponse)
async def get_account_balance(
    account_id: UUID,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> AccountBalanceResponse:
    account = await session.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user.id)
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    return await _account_balance(session, user.id, account)


@router.get("/summary", response_model=FinanceSummaryResponse)
async def get_finance_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> FinanceSummaryResponse:
    local_today = datetime.now(ZoneInfo(user.timezone)).date()
    end_date = end_date or local_today
    start_date = start_date or end_date.replace(day=1)
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="A data final não pode ser anterior à inicial.")
    if (end_date - start_date).days > 366:
        raise HTTPException(status_code=422, detail="O período máximo permitido é de 367 dias.")

    start, end = _period_bounds(start_date, end_date, user.timezone)
    reversal = aliased(Transaction)
    has_reversal = (
        select(reversal.id)
        .where(
            reversal.user_id == user.id,
            reversal.reversal_of_transaction_id == Transaction.id,
        )
        .exists()
    )
    # Exclude both the original entry once reversed and its compensating entry
    # from period income/expense totals. Both entries still affect account balance.
    not_reversed = (
        Transaction.reversal_of_transaction_id.is_(None)
        & ~has_reversal
    )
    income = func.coalesce(
        func.sum(
            case(
                (
                    (Transaction.transaction_type == "income")
                    & Transaction.transfer_id.is_(None)
                    & Transaction.transfer_reversal_id.is_(None)
                    & not_reversed
                    & ~Transaction.idempotency_key.like("invoice-payment:%"),
                    Transaction.amount,
                ),
                else_=Decimal("0.00"),
            )
        ),
        Decimal("0.00"),
    )
    expenses = func.coalesce(
        func.sum(
            case(
                (
                    (Transaction.transaction_type == "expense")
                    & Transaction.transfer_id.is_(None)
                    & Transaction.transfer_reversal_id.is_(None)
                    & not_reversed
                    & ~Transaction.idempotency_key.like("invoice-payment:%"),
                    Transaction.amount,
                ),
                else_=Decimal("0.00"),
            )
        ),
        Decimal("0.00"),
    )
    totals_result = await session.execute(
        select(Transaction.currency, income.label("income"), expenses.label("expenses"))
        .where(
            Transaction.user_id == user.id,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
        .group_by(Transaction.currency)
        .order_by(Transaction.currency)
    )
    totals_by_currency = [
        CurrencyTotals(
            currency=row.currency,
            income_total=Decimal(row.income),
            expense_total=Decimal(row.expenses),
            net_flow=Decimal(row.income) - Decimal(row.expenses),
        )
        for row in totals_result
    ]

    accounts_result = await session.scalars(
        select(Account).where(Account.user_id == user.id).order_by(Account.created_at, Account.id)
    )
    account_balances = [
        await _account_balance(session, user.id, account)
        for account in accounts_result.all()
    ]

    category_result = await session.execute(
        select(
            Category.id,
            Category.name,
            Transaction.currency,
            func.sum(Transaction.amount).label("amount"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user.id,
            Transaction.transaction_type == "expense",
            Transaction.reversal_of_transaction_id.is_(None),
            ~has_reversal,
            Transaction.occurred_at >= start,
            Transaction.occurred_at < end,
        )
        .group_by(Category.id, Category.name, Transaction.currency)
        .order_by(Transaction.currency, func.sum(Transaction.amount).desc(), Category.name)
    )
    spending_by_category = [
        CategorySpending(
            category_id=row.id,
            category_name=row.name,
            currency=row.currency,
            amount=Decimal(row.amount),
        )
        for row in category_result
    ]

    return FinanceSummaryResponse(
        start_date=start_date,
        end_date=end_date,
        totals_by_currency=totals_by_currency,
        account_balances=account_balances,
        spending_by_category=spending_by_category,
    )
