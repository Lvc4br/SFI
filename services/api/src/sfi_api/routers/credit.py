import calendar
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.credit import (
    CreditCard,
    CreditInvoice,
    CreditInvoicePayment,
    CreditPurchaseInstallment,
)
from sfi_api.models.finance import Account, Transaction
from sfi_api.models.user import User
from sfi_api.schemas.credit import (
    CreditCardCreate,
    CreditCardResponse,
    CreditInvoicePaymentCreate,
    CreditInvoicePaymentResponse,
    CreditInvoiceResponse,
    CreditPurchaseCreate,
)

router = APIRouter(prefix="/credit", tags=["credit-cards"])
SESSION_DEPENDENCY = Depends(get_session)
USER_DEPENDENCY = Depends(get_current_user)


def _month_shift(value: date, months: int) -> date:
    index = value.year * 12 + value.month - 1 + months
    year, month = divmod(index, 12)
    return date(year, month + 1, 1)


def _cycle_dates(card: CreditCard, purchase_date: date) -> tuple[str, date, date]:
    period_start = date(purchase_date.year, purchase_date.month, 1)
    if purchase_date.day > card.closing_day:
        period_start = _month_shift(period_start, 1)

    year, month = period_start.year, period_start.month
    closing = date(
        year,
        month,
        min(card.closing_day, calendar.monthrange(year, month)[1]),
    )
    due_month = (
        period_start
        if card.due_day > card.closing_day
        else _month_shift(period_start, 1)
    )
    due = date(
        due_month.year,
        due_month.month,
        min(
            card.due_day,
            calendar.monthrange(due_month.year, due_month.month)[1],
        ),
    )
    return period_start.strftime("%Y-%m"), closing, due


async def _invoice_for_period(
    session: AsyncSession,
    user_id: uuid.UUID,
    card: CreditCard,
    period_start: date,
) -> CreditInvoice:
    year, month = period_start.year, period_start.month
    period = period_start.strftime("%Y-%m")
    closing = date(
        year,
        month,
        min(card.closing_day, calendar.monthrange(year, month)[1]),
    )
    due_month = (
        period_start
        if card.due_day > card.closing_day
        else _month_shift(period_start, 1)
    )
    due = date(
        due_month.year,
        due_month.month,
        min(
            card.due_day,
            calendar.monthrange(due_month.year, due_month.month)[1],
        ),
    )
    invoice = await session.scalar(
        select(CreditInvoice).where(
            CreditInvoice.user_id == user_id,
            CreditInvoice.card_id == card.id,
            CreditInvoice.period == period,
        )
    )
    if invoice is None:
        invoice = CreditInvoice(
            user_id=user_id,
            card_id=card.id,
            period=period,
            closing_date=closing,
            due_date=due,
            status="open",
            paid_amount=Decimal("0.00"),
        )
        session.add(invoice)
        await session.flush()
    return invoice


async def _invoice(
    session: AsyncSession,
    user_id: uuid.UUID,
    card: CreditCard,
    purchase_date: date,
) -> CreditInvoice:
    period, _, _ = _cycle_dates(card, purchase_date)
    year, month = (int(part) for part in period.split("-"))
    return await _invoice_for_period(
        session,
        user_id,
        card,
        date(year, month, 1),
    )


async def _invoice_response(
    session: AsyncSession,
    invoice: CreditInvoice,
) -> CreditInvoiceResponse:
    total = await session.scalar(
        select(func.coalesce(func.sum(CreditPurchaseInstallment.amount), 0)).where(
            CreditPurchaseInstallment.invoice_id == invoice.id
        )
    )
    total = Decimal(total or 0).quantize(Decimal("0.01"))
    return CreditInvoiceResponse(
        id=invoice.id,
        card_id=invoice.card_id,
        period=invoice.period,
        closing_date=invoice.closing_date,
        due_date=invoice.due_date,
        status=invoice.status,
        total_amount=total,
        paid_amount=invoice.paid_amount,
        remaining_amount=max(Decimal("0.00"), total - invoice.paid_amount),
    )


@router.post(
    "/cards",
    response_model=CreditCardResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_card(
    payload: CreditCardCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    account = await session.scalar(
        select(Account).where(
            Account.id == payload.account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
    )
    if account is None:
        raise HTTPException(404, "Conta não encontrada.")
    if account.account_type != "credit":
        raise HTTPException(
            422,
            "O cartão precisa estar vinculado a uma conta do tipo crédito.",
        )
    if account.currency != "BRL":
        raise HTTPException(422, "Cartões só aceitam conta em BRL nesta versão.")

    card = CreditCard(user_id=user.id, **payload.model_dump())
    session.add(card)
    try:
        await session.commit()
        await session.refresh(card)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            409,
            "Esta conta já está vinculada a outro cartão.",
        ) from None
    return card


@router.get("/cards", response_model=list[CreditCardResponse])
async def list_cards(
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    result = await session.scalars(
        select(CreditCard)
        .where(CreditCard.user_id == user.id)
        .order_by(CreditCard.created_at.desc())
    )
    return list(result.all())


@router.post("/purchases", status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: CreditPurchaseCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    card = await session.scalar(
        select(CreditCard).where(
            CreditCard.id == payload.card_id,
            CreditCard.user_id == user.id,
        ).with_for_update()
    )
    if card is None:
        raise HTTPException(404, "Cartão não encontrado.")

    account = await session.scalar(
        select(Account).where(
            Account.id == card.account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
    )
    if account is None:
        raise HTTPException(409, "A conta vinculada ao cartão não está disponível.")

    purchase_id = uuid.uuid5(user.id, payload.idempotency_key)
    existing = await session.scalar(
        select(CreditPurchaseInstallment.id).where(
            CreditPurchaseInstallment.user_id == user.id,
            CreditPurchaseInstallment.purchase_id == purchase_id,
        )
    )
    if existing:
        raise HTTPException(409, "Esta compra já foi registrada.")

    used = await session.scalar(
        select(func.coalesce(func.sum(CreditPurchaseInstallment.amount), 0)).where(
            CreditPurchaseInstallment.user_id == user.id,
            CreditPurchaseInstallment.invoice_id.in_(
                select(CreditInvoice.id).where(
                    CreditInvoice.card_id == card.id,
                    CreditInvoice.user_id == user.id,
                )
            ),
        )
    )
    paid = await session.scalar(
        select(func.coalesce(func.sum(CreditInvoice.paid_amount), 0)).where(
            CreditInvoice.card_id == card.id,
            CreditInvoice.user_id == user.id,
        )
    )
    if Decimal(used or 0) - Decimal(paid or 0) + payload.amount > card.credit_limit:
        raise HTTPException(
            422,
            "A compra excede o limite disponível do cartão.",
        )

    cents = int((payload.amount * 100).to_integral_exact())
    base = Decimal(cents // payload.installments) / 100
    remainder = cents - (cents // payload.installments) * payload.installments
    first_period, _, _ = _cycle_dates(card, payload.purchase_date)
    first_year, first_month = (int(part) for part in first_period.split("-"))
    first_cycle = date(first_year, first_month, 1)

    for number in range(1, payload.installments + 1):
        cycle_date = _month_shift(first_cycle, number - 1)
        existing_invoice = await session.scalar(
            select(CreditInvoice)
            .where(
                CreditInvoice.user_id == user.id,
                CreditInvoice.card_id == card.id,
                CreditInvoice.period == cycle_date.strftime("%Y-%m"),
            )
            .with_for_update()
        )
        if existing_invoice is not None and existing_invoice.status != "open":
            await session.rollback()
            raise HTTPException(
                409,
                "A compra não pode ser adicionada a uma fatura fechada ou paga.",
            )

        installment_amount = base + (
            Decimal("0.01") if number <= remainder else Decimal("0.00")
        )
        invoice = await _invoice_for_period(
            session,
            user.id,
            card,
            cycle_date,
        )
        if invoice.status != "open":
            await session.rollback()
            raise HTTPException(
                409,
                "A compra não pode ser adicionada a uma fatura fechada ou paga.",
            )
        description = (
            payload.description
            if payload.installments == 1
            else f"{payload.description} ({number}/{payload.installments})"
        )
        occurred_at = datetime.combine(
            cycle_date,
            datetime.min.time(),
            tzinfo=ZoneInfo(user.timezone),
        ).astimezone(UTC)
        installment = CreditPurchaseInstallment(
            user_id=user.id,
            invoice_id=invoice.id,
            purchase_id=purchase_id,
            installment_number=number,
            installment_count=payload.installments,
            description=description,
            amount=installment_amount,
            occurred_at=occurred_at,
        )
        transaction = Transaction(
            user_id=user.id,
            account_id=account.id,
            category_id=None,
            transaction_type="expense",
            amount=installment_amount,
            currency="BRL",
            description=description,
            occurred_at=occurred_at,
            idempotency_key=f"card:{purchase_id}:{number}",
        )
        session.add_all([installment, transaction])

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Conflito ao registrar compra ou parcelas.") from None

    return {
        "purchase_id": str(purchase_id),
        "installments_created": payload.installments,
        "total_amount": payload.amount,
    }


@router.get("/invoices", response_model=list[CreditInvoiceResponse])
async def list_invoices(
    card_id: uuid.UUID | None = None,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    query = select(CreditInvoice).where(CreditInvoice.user_id == user.id)
    if card_id is not None:
        query = query.where(CreditInvoice.card_id == card_id)
    invoices = await session.scalars(query.order_by(CreditInvoice.due_date.desc()))
    return [
        await _invoice_response(session, invoice)
        for invoice in invoices.all()
    ]


@router.post(
    "/invoices/{invoice_id}/close",
    response_model=CreditInvoiceResponse,
)
async def close_invoice(
    invoice_id: uuid.UUID,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    invoice = await session.scalar(
        select(CreditInvoice).where(
            CreditInvoice.id == invoice_id,
            CreditInvoice.user_id == user.id,
        ).with_for_update()
    )
    if invoice is None:
        raise HTTPException(404, "Fatura não encontrada.")
    if invoice.status == "paid":
        raise HTTPException(409, "Fatura já está paga.")
    invoice.status = "closed"
    await session.commit()
    return await _invoice_response(session, invoice)


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=CreditInvoicePaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def pay_invoice(
    invoice_id: uuid.UUID,
    payload: CreditInvoicePaymentCreate,
    session: AsyncSession = SESSION_DEPENDENCY,
    user: User = USER_DEPENDENCY,
):
    existing = await session.scalar(
        select(CreditInvoicePayment).where(
            CreditInvoicePayment.user_id == user.id,
            CreditInvoicePayment.idempotency_key == payload.idempotency_key,
        )
    )
    if existing:
        raise HTTPException(409, "Esta chave de pagamento já foi utilizada.")

    invoice = await session.scalar(
        select(CreditInvoice).where(
            CreditInvoice.id == invoice_id,
            CreditInvoice.user_id == user.id,
        ).with_for_update()
    )
    if invoice is None:
        raise HTTPException(404, "Fatura não encontrada.")

    card = await session.scalar(
        select(CreditCard).where(
            CreditCard.id == invoice.card_id,
            CreditCard.user_id == user.id,
        )
    )
    source = await session.scalar(
        select(Account).where(
            Account.id == payload.source_account_id,
            Account.user_id == user.id,
            Account.archived_at.is_(None),
        )
    )
    if source is None:
        raise HTTPException(404, "Conta de pagamento não encontrada.")

    credit = await session.scalar(
        select(Account).where(
            Account.id == card.account_id,
            Account.user_id == user.id,
        )
    )
    if source.account_type == "credit" or source.currency != "BRL":
        raise HTTPException(
            422,
            "O pagamento deve sair de uma conta não crédito em BRL.",
        )
    if credit.currency != "BRL":
        raise HTTPException(422, "A conta do cartão precisa estar em BRL.")

    total = await session.scalar(
        select(func.coalesce(func.sum(CreditPurchaseInstallment.amount), 0)).where(
            CreditPurchaseInstallment.invoice_id == invoice.id
        )
    )
    remaining = Decimal(total or 0) - invoice.paid_amount
    if payload.amount > remaining:
        raise HTTPException(422, "O pagamento excede o saldo da fatura.")

    payment = CreditInvoicePayment(
        user_id=user.id,
        invoice_id=invoice.id,
        source_account_id=source.id,
        amount=payload.amount,
        idempotency_key=payload.idempotency_key,
        paid_at=payload.paid_at,
    )
    debit = Transaction(
        user_id=user.id,
        account_id=source.id,
        category_id=None,
        transaction_type="expense",
        amount=payload.amount,
        currency="BRL",
        description=f"Pagamento de fatura {invoice.period}",
        occurred_at=payload.paid_at,
        idempotency_key=f"invoice-payment:{payment.id}:debit",
    )
    credit_entry = Transaction(
        user_id=user.id,
        account_id=credit.id,
        category_id=None,
        transaction_type="income",
        amount=payload.amount,
        currency="BRL",
        description=f"Pagamento recebido da fatura {invoice.period}",
        occurred_at=payload.paid_at,
        idempotency_key=f"invoice-payment:{payment.id}:credit",
    )
    session.add_all([payment, debit, credit_entry])
    invoice.paid_amount += payload.amount
    invoice.status = (
        "paid" if invoice.paid_amount == Decimal(total or 0) else "closed"
    )

    try:
        await session.commit()
        await session.refresh(payment)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Conflito ao registrar pagamento.") from None
    return payment
