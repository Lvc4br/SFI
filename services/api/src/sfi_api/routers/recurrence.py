import calendar
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.finance import Account, Category
from sfi_api.models.recurrence import Recurrence
from sfi_api.models.user import User
from sfi_api.schemas.recurrence import (
    CashFlowForecastResponse,
    ForecastCurrencyTotal,
    ForecastOccurrence,
    RecurrenceCreate,
    RecurrenceResponse,
    RecurrenceStatusUpdate,
)

router = APIRouter(prefix="/finance", tags=["finance"])


def _monthly_date(anchor: date, month_offset: int) -> date:
    month_index = anchor.year * 12 + anchor.month - 1 + month_offset
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _yearly_date(anchor: date, year_offset: int) -> date:
    year = anchor.year + year_offset
    day = min(anchor.day, calendar.monthrange(year, anchor.month)[1])
    return date(year, anchor.month, day)


def _occurrence_dates(
    recurrence: Recurrence, start: date, end: date, max_occurrences: int = 5000
) -> list[date]:
    anchor = recurrence.start_date
    until = min(end, recurrence.end_date) if recurrence.end_date else end
    if until < start or anchor > until:
        return []

    dates: list[date] = []
    interval = recurrence.interval_count
    if recurrence.frequency == "weekly":
        step = timedelta(weeks=interval)
        current = anchor
        if current < start:
            jumps = (start - current).days // step.days
            current += step * jumps
            while current < start:
                current += step
        while current <= until:
            dates.append(current)
            if len(dates) > max_occurrences:
                raise HTTPException(
                    status_code=422, detail="A projeção excede o limite de ocorrências."
                )
            current += step
        return dates

    if recurrence.frequency == "monthly":
        month_step = interval
        month_index = anchor.year * 12 + anchor.month - 1
        target_index = start.year * 12 + start.month - 1
        jumps = max(0, (target_index - month_index) // month_step)
        current = _monthly_date(anchor, jumps * month_step)
        while current < start:
            jumps += 1
            current = _monthly_date(anchor, jumps * month_step)
        while current <= until:
            dates.append(current)
            if len(dates) > max_occurrences:
                raise HTTPException(
                    status_code=422, detail="A projeção excede o limite de ocorrências."
                )
            jumps += 1
            current = _monthly_date(anchor, jumps * month_step)
        return dates

    year_step = interval
    jumps = max(0, (start.year - anchor.year) // year_step)
    current = _yearly_date(anchor, jumps * year_step)
    while current < start:
        jumps += 1
        current = _yearly_date(anchor, jumps * year_step)
    while current <= until:
        dates.append(current)
        if len(dates) > max_occurrences:
            raise HTTPException(
                status_code=422, detail="A projeção excede o limite de ocorrências."
            )
        jumps += 1
        current = _yearly_date(anchor, jumps * year_step)
    return dates


@router.post(
    "/recurrences",
    response_model=RecurrenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_recurrence(
    payload: RecurrenceCreate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> RecurrenceResponse:
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
            detail="Receitas não podem ser previstas diretamente em uma conta de crédito.",
        )

    if payload.category_id is not None:
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
                detail="O tipo da categoria não corresponde ao tipo da recorrência.",
            )

    existing = await session.scalar(
        select(Recurrence).where(
            Recurrence.user_id == user.id,
            Recurrence.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Esta chave de idempotência já foi utilizada.")

    recurrence = Recurrence(
        user_id=user.id,
        account_id=account.id,
        category_id=payload.category_id,
        transaction_type=payload.transaction_type,
        amount=payload.amount,
        currency=account.currency,
        description=payload.description,
        idempotency_key=payload.idempotency_key,
        frequency=payload.frequency,
        interval_count=payload.interval_count,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    session.add(recurrence)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="Esta chave de idempotência já foi utilizada."
        ) from exc
    await session.refresh(recurrence)
    return RecurrenceResponse.model_validate(recurrence)


@router.get("/recurrences", response_model=list[RecurrenceResponse])
async def list_recurrences(
    active_only: bool = True,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[RecurrenceResponse]:
    query = select(Recurrence).where(Recurrence.user_id == user.id)
    if active_only:
        query = query.where(Recurrence.is_active.is_(True))
    result = await session.scalars(query.order_by(Recurrence.created_at.desc()))
    return [RecurrenceResponse.model_validate(item) for item in result.all()]


@router.patch(
    "/recurrences/{recurrence_id}",
    response_model=RecurrenceResponse,
)
async def update_recurrence_status(
    recurrence_id: uuid.UUID,
    payload: RecurrenceStatusUpdate,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> RecurrenceResponse:
    recurrence = await session.scalar(
        select(Recurrence).where(
            Recurrence.id == recurrence_id,
            Recurrence.user_id == user.id,
        )
    )
    if recurrence is None:
        raise HTTPException(status_code=404, detail="Recorrência não encontrada.")
    recurrence.is_active = payload.is_active
    await session.commit()
    await session.refresh(recurrence)
    return RecurrenceResponse.model_validate(recurrence)


@router.get("/cash-flow/forecast", response_model=CashFlowForecastResponse)
async def get_cash_flow_forecast(
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_session),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> CashFlowForecastResponse:
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="A data final não pode ser anterior à inicial.")
    if (end_date - start_date).days > 366:
        raise HTTPException(status_code=422, detail="O período máximo da projeção é de 367 dias.")

    result = await session.execute(
        select(Recurrence, Account.name)
        .join(Account, Recurrence.account_id == Account.id)
        .where(Recurrence.user_id == user.id, Recurrence.is_active.is_(True))
        .order_by(Recurrence.start_date, Recurrence.id)
    )
    occurrences: list[ForecastOccurrence] = []
    totals: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"income": Decimal("0.00"), "expense": Decimal("0.00")}
    )
    for recurrence, account_name in result.all():
        for due_date in _occurrence_dates(recurrence, start_date, end_date):
            occurrences.append(
                ForecastOccurrence(
                    recurrence_id=recurrence.id,
                    account_id=recurrence.account_id,
                    account_name=account_name,
                    category_id=recurrence.category_id,
                    transaction_type=recurrence.transaction_type,
                    amount=recurrence.amount,
                    currency=recurrence.currency,
                    description=recurrence.description,
                    due_date=due_date,
                )
            )
            totals[recurrence.currency][recurrence.transaction_type] += recurrence.amount

    occurrences.sort(key=lambda item: (item.due_date, item.currency, str(item.recurrence_id)))
    totals_by_currency = [
        ForecastCurrencyTotal(
            currency=currency,
            income_total=values["income"],
            expense_total=values["expense"],
            net_flow=values["income"] - values["expense"],
        )
        for currency, values in sorted(totals.items())
    ]
    return CashFlowForecastResponse(
        start_date=start_date,
        end_date=end_date,
        occurrences=occurrences,
        totals_by_currency=totals_by_currency,
    )
