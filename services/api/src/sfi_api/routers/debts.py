import calendar
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.debt import Debt, DebtPayment
from sfi_api.models.finance import Account, Transaction
from sfi_api.models.user import User
from sfi_api.schemas.debt import (
    DebtCreate,
    DebtPaymentCreate,
    DebtPaymentResponse,
    DebtResponse,
)

router = APIRouter(prefix="/debts", tags=["debts"])
SESSION_DEPENDENCY = Depends(get_session)
USER_DEPENDENCY = Depends(get_current_user)


@router.post("", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
async def create_debt(
    payload: DebtCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    data = payload.model_dump()
    principal = data.pop("outstanding_principal")
    debt = Debt(
        user_id=user.id,
        **data,
        outstanding_principal=(
            principal if principal is not None else payload.original_amount
        ),
        next_due_date=payload.first_due_date,
        status="active",
    )
    session.add(debt)
    await session.commit()
    await session.refresh(debt)
    return debt


@router.get("", response_model=list[DebtResponse])
async def list_debts(
    include_archived: bool = False,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    query = select(Debt).where(Debt.user_id == user.id)
    if not include_archived:
        query = query.where(Debt.status != "archived")
    result = await session.scalars(
        query.order_by(
            Debt.next_due_date.asc().nulls_last(),
            Debt.created_at.desc(),
        )
    )
    return list(result.all())


@router.get("/{debt_id}/payments", response_model=list[DebtPaymentResponse])
async def list_debt_payments(
    debt_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    debt = await session.scalar(
        select(Debt.id).where(Debt.id == debt_id, Debt.user_id == user.id)
    )
    if debt is None:
        raise HTTPException(404, "Dívida não encontrada.")
    result = await session.scalars(
        select(DebtPayment)
        .where(
            DebtPayment.debt_id == debt_id,
            DebtPayment.user_id == user.id,
        )
        .order_by(DebtPayment.paid_at.desc())
    )
    return list(result.all())



def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_amortization_schedule(debt: Debt) -> dict:
    if debt.amortization_method not in {"price", "sac"}:
        raise HTTPException(409, "Defina o método Price ou SAC para projetar parcelas.")
    if not debt.installment_count:
        raise HTTPException(409, "Informe a quantidade de parcelas para gerar a projeção.")
    principal = _money(debt.outstanding_principal)
    if principal <= 0:
        return {"debt_id": str(debt.id), "method": debt.amortization_method,
                "currency": debt.currency, "installments": [], "principal_total": "0.00",
                "interest_total": "0.00", "payment_total": "0.00", "is_estimate": True}
    monthly_rate = debt.annual_interest_rate / Decimal("100") / Decimal("12")
    count = debt.installment_count
    start_date = debt.next_due_date or debt.first_due_date
    with localcontext() as context:
        context.prec = 32
        if debt.amortization_method == "price":
            if monthly_rate == 0:
                fixed_payment = _money(principal / Decimal(count))
            else:
                factor = (Decimal("1") + monthly_rate) ** count
                fixed_payment = _money(principal * monthly_rate * factor / (factor - 1))
        else:
            fixed_payment = None
        balance = principal
        installments = []
        for index in range(1, count + 1):
            opening_balance = balance
            interest = _money(balance * monthly_rate)
            if debt.amortization_method == "sac":
                principal_part = balance if index == count else _money(principal / Decimal(count))
            else:
                principal_part = balance if index == count else min(
                    balance, max(Decimal("0.00"), _money(fixed_payment - interest))
                )
            payment = _money(principal_part + interest)
            balance = _money(max(Decimal("0"), balance - principal_part))
            installments.append({
                "number": index, "due_date": _add_months(start_date, index - 1).isoformat(),
                "opening_balance": str(opening_balance), "principal": str(principal_part),
                "interest": str(interest), "payment": str(payment),
                "closing_balance": str(balance),
            })
        principal_total = sum((Decimal(item["principal"]) for item in installments), Decimal("0"))
        interest_total = sum((Decimal(item["interest"]) for item in installments), Decimal("0"))
        payment_total = sum((Decimal(item["payment"]) for item in installments), Decimal("0"))
    return {
        "debt_id": str(debt.id), "method": debt.amortization_method, "currency": debt.currency,
        "annual_rate_percent": str(debt.annual_interest_rate),
        "monthly_rate_percent": str(monthly_rate * Decimal("100")),
        "installments": installments, "principal_total": str(_money(principal_total)),
        "interest_total": str(_money(interest_total)), "payment_total": str(_money(payment_total)),
        "is_estimate": True,
        "assumptions": [
            "Taxa anual nominal dividida por 12; não representa CET.",
            "Sem seguros, tarifas, impostos, multas, mora ou indexadores.",
            "Projeção calculada sobre o principal em aberto e a quantidade cadastrada de parcelas.",
            "Datas mensais preservam o dia de vencimento e ajustam para o último dia do mês quando necessário.",
        ],
    }


@router.get("/{debt_id}/schedule")
async def debt_amortization_schedule(
    debt_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    debt = await session.scalar(
        select(Debt).where(Debt.id == debt_id, Debt.user_id == user.id)
    )
    if debt is None:
        raise HTTPException(404, "Dívida não encontrada.")
    return _build_amortization_schedule(debt)


@router.post(
    "/{debt_id}/payments",
    response_model=DebtPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def pay_debt(
    debt_id: uuid.UUID,
    payload: DebtPaymentCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    existing = await session.scalar(
        select(DebtPayment).where(
            DebtPayment.user_id == user.id,
            DebtPayment.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        raise HTTPException(409, "Esta chave de idempotência já foi utilizada.")

    debt = await session.scalar(
        select(Debt)
        .where(
            Debt.id == debt_id,
            Debt.user_id == user.id,
            Debt.status == "active",
        )
        .with_for_update()
    )
    if debt is None:
        raise HTTPException(404, "Dívida ativa não encontrada.")

    account = await session.scalar(
        select(Account).where(
            Account.id == payload.source_account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
    )
    if account is None:
        raise HTTPException(404, "Conta de origem não encontrada.")
    if account.account_type == "credit" or account.currency != debt.currency:
        raise HTTPException(
            422,
            "A conta de origem precisa ser não crédito e usar a mesma moeda.",
        )

    if payload.principal_amount > debt.outstanding_principal:
        raise HTTPException(422, "A amortização não pode superar o saldo devedor.")
    amount = (
        payload.principal_amount + payload.interest_amount
    ).quantize(Decimal("0.01"))
    transaction_id = uuid.uuid4()
    transaction = Transaction(
        id=transaction_id,
        user_id=user.id,
        account_id=account.id,
        category_id=None,
        transaction_type="expense",
        amount=amount,
        currency=debt.currency,
        description=f"Pagamento de dívida: {debt.description}"[:160],
        idempotency_key=f"debt-payment:{payload.idempotency_key}"[:100],
        occurred_at=payload.paid_at,
    )
    payment = DebtPayment(
        user_id=user.id,
        debt_id=debt.id,
        source_account_id=account.id,
        transaction_id=transaction_id,
        amount=amount,
        principal_amount=payload.principal_amount,
        interest_amount=payload.interest_amount,
        idempotency_key=payload.idempotency_key,
        paid_at=payload.paid_at,
    )
    debt.outstanding_principal = (
        debt.outstanding_principal - payload.principal_amount
    ).quantize(Decimal("0.01"))
    if debt.outstanding_principal == Decimal("0.00"):
        debt.status = "paid"
        debt.next_due_date = None
    else:
        debt.next_due_date = payload.next_due_date
    session.add_all([transaction, payment])
    try:
        await session.commit()
        await session.refresh(payment)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            409,
            "O pagamento já foi registrado ou conflitou com outro lançamento.",
        ) from None
    return payment


@router.post("/{debt_id}/archive", response_model=DebtResponse)
async def archive_debt(
    debt_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    debt = await session.scalar(
        select(Debt).where(Debt.id == debt_id, Debt.user_id == user.id)
    )
    if debt is None:
        raise HTTPException(404, "Dívida não encontrada.")
    if debt.status == "active":
        raise HTTPException(409, "Quite a dívida antes de arquivá-la.")
    debt.status = "archived"
    await session.commit()
    await session.refresh(debt)
    return debt
