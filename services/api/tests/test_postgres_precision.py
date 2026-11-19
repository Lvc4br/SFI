import asyncio
import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.models import Account, Base, Transaction, User


@pytest.mark.skipif(
    not os.environ.get("SFI_TEST_POSTGRES_URL"),
    reason="SFI_TEST_POSTGRES_URL não configurada; teste exclusivo do job PostgreSQL.",
)
def test_postgresql_numeric_18_2_round_trip_and_overflow():
    url = os.environ["SFI_TEST_POSTGRES_URL"]
    engine = create_async_engine(url)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def run():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        try:
            async with factory() as session:
                user = User(
                    email=f"precision-{uuid.uuid4()}@example.test",
                    password_hash="test-only-not-a-real-password-hash",
                )
                session.add(user)
                await session.flush()
                account = Account(
                    user_id=user.id,
                    name="Precision test",
                    account_type="checking",
                    currency="BRL",
                    opening_balance=Decimal("0.00"),
                )
                session.add(account)
                await session.flush()
                exact = Decimal("9999999999999999.99")
                transaction = Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    transaction_type="income",
                    amount=exact,
                    currency="BRL",
                    description="Numeric(18,2) maximum",
                    idempotency_key=f"precision-{uuid.uuid4()}",
                    occurred_at=datetime.now(UTC),
                )
                session.add(transaction)
                await session.commit()
                await session.refresh(transaction)
                assert transaction.amount == exact

                overflow = Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    transaction_type="income",
                    amount=Decimal("10000000000000000.00"),
                    currency="BRL",
                    description="Numeric(18,2) overflow",
                    idempotency_key=f"overflow-{uuid.uuid4()}",
                    occurred_at=datetime.now(UTC),
                )
                session.add(overflow)
                with pytest.raises(DBAPIError):
                    await session.commit()
                await session.rollback()
        finally:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)

    try:
        asyncio.run(run())
    finally:
        asyncio.run(engine.dispose())
