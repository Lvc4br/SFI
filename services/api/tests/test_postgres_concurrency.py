import asyncio
import os
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.models import (
    Account,
    Base,
    CreditCard,
    CreditInvoice,
    CreditInvoicePayment,
    CreditPurchaseInstallment,
    User,
)
from sfi_api.routers.credit import pay_invoice
from sfi_api.schemas.credit import CreditInvoicePaymentCreate


@pytest.mark.skipif(
    not os.environ.get("SFI_TEST_POSTGRES_URL"),
    reason="SFI_TEST_POSTGRES_URL não configurada; teste exclusivo do job PostgreSQL.",
)
def test_concurrent_invoice_payments_cannot_overpay():
    engine = create_async_engine(os.environ["SFI_TEST_POSTGRES_URL"], pool_size=5)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def run():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        user = User(
            email=f"concurrency-{uuid.uuid4()}@example.test",
            password_hash="test-only-not-a-real-password-hash",
        )
        async with factory() as session:
            session.add(user)
            await session.flush()
            credit_account = Account(
                user_id=user.id,
                name="Concurrency card",
                account_type="credit",
                currency="BRL",
                opening_balance=Decimal("0.00"),
            )
            source_account = Account(
                user_id=user.id,
                name="Concurrency source",
                account_type="checking",
                currency="BRL",
                opening_balance=Decimal("0.00"),
            )
            session.add_all([credit_account, source_account])
            await session.flush()
            card = CreditCard(
                user_id=user.id,
                account_id=credit_account.id,
                name="Concurrency card",
                closing_day=10,
                due_day=20,
                credit_limit=Decimal("1000.00"),
            )
            session.add(card)
            await session.flush()
            invoice = CreditInvoice(
                user_id=user.id,
                card_id=card.id,
                period="2026-12",
                closing_date=date(2026, 12, 10),
                due_date=date(2026, 12, 20),
                status="open",
                paid_amount=Decimal("0.00"),
            )
            session.add(invoice)
            await session.flush()
            session.add(
                CreditPurchaseInstallment(
                    user_id=user.id,
                    invoice_id=invoice.id,
                    purchase_id=uuid.uuid4(),
                    installment_number=1,
                    installment_count=1,
                    description="Concurrent fixture",
                    amount=Decimal("100.00"),
                    occurred_at=datetime(2026, 12, 1, 12, tzinfo=UTC),
                )
            )
            await session.commit()
            invoice_id = invoice.id
            user_id = user.id
            source_id = source_account.id

        async def attempt(key: str):
            async with factory() as session:
                payload = CreditInvoicePaymentCreate(
                    source_account_id=source_id,
                    amount=Decimal("60.00"),
                    paid_at=datetime(2026, 12, 15, 12, tzinfo=UTC),
                    idempotency_key=key,
                )
                try:
                    await pay_invoice(invoice_id, payload, session=session, user=user)
                    return "created"
                except HTTPException as exc:
                    return exc.status_code

        outcomes = await asyncio.gather(
            attempt("concurrent-payment-0001"),
            attempt("concurrent-payment-0002"),
        )
        assert sorted(outcomes, key=str) == [422, "created"]

        async with factory() as session:
            persisted = await session.scalar(
                select(CreditInvoice).where(
                    CreditInvoice.id == invoice_id,
                    CreditInvoice.user_id == user_id,
                )
            )
            payment_count = await session.scalar(
                select(func.count(CreditInvoicePayment.id)).where(
                    CreditInvoicePayment.invoice_id == invoice_id,
                    CreditInvoicePayment.user_id == user_id,
                )
            )
            assert persisted is not None
            assert persisted.paid_amount == Decimal("60.00")
            assert persisted.status == "closed"
            assert payment_count == 1

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

    try:
        asyncio.run(run())
    finally:
        asyncio.run(engine.dispose())
