import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from sfi_api.models.base import Base


class Debt(Base):
    __tablename__ = "debts"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_debts_id_user"),
        CheckConstraint("original_amount > 0", name="ck_debts_original_amount"),
        CheckConstraint("outstanding_principal >= 0", name="ck_debts_outstanding_principal"),
        CheckConstraint("annual_interest_rate >= 0", name="ck_debts_interest_rate"),
        CheckConstraint("status IN ('active', 'paid', 'archived')", name="ck_debts_status"),
        Index("ix_debts_user_status_due", "user_id", "status", "next_due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    creditor: Mapped[str] = mapped_column(String(120), nullable=False)
    debt_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(160), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    original_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    outstanding_principal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    annual_interest_rate: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False, default=Decimal("0"))
    amortization_method: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")
    contracted_at: Mapped[date] = mapped_column(Date(), nullable=False)
    first_due_date: Mapped[date] = mapped_column(Date(), nullable=False)
    next_due_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    installment_count: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DebtPayment(Base):
    __tablename__ = "debt_payments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["debt_id", "user_id"], ["debts.id", "debts.user_id"],
            name="fk_debt_payments_debt_owner", ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["source_account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            name="fk_debt_payments_account_owner", ondelete="RESTRICT"
        ),
        UniqueConstraint("user_id", "idempotency_key", name="uq_debt_payments_idempotency"),
        CheckConstraint("amount > 0", name="ck_debt_payments_amount"),
        CheckConstraint("principal_amount > 0", name="ck_debt_payments_principal"),
        CheckConstraint("interest_amount >= 0", name="ck_debt_payments_interest"),
        Index("ix_debt_payments_user_paid", "user_id", "paid_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    debt_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_account_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    interest_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
