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


class CreditCard(Base):
    __tablename__ = "credit_cards"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_credit_cards_id_user"),
        UniqueConstraint("account_id", name="uq_credit_cards_account"),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_credit_cards_account_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "closing_day BETWEEN 1 AND 31",
            name="ck_credit_cards_closing_day",
        ),
        CheckConstraint("due_day BETWEEN 1 AND 31", name="ck_credit_cards_due_day"),
        CheckConstraint("credit_limit > 0", name="ck_credit_cards_limit_positive"),
        Index("ix_credit_cards_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    closing_day: Mapped[int] = mapped_column(nullable=False)
    due_day: Mapped[int] = mapped_column(nullable=False)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CreditInvoice(Base):
    __tablename__ = "credit_invoices"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_credit_invoices_id_user"),
        UniqueConstraint("card_id", "period", name="uq_credit_invoices_card_period"),
        ForeignKeyConstraint(
            ["card_id", "user_id"],
            ["credit_cards.id", "credit_cards.user_id"],
            name="fk_credit_invoices_card_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('open', 'closed', 'paid')",
            name="ck_credit_invoices_status",
        ),
        CheckConstraint("paid_amount >= 0", name="ck_credit_invoices_paid_nonnegative"),
        Index("ix_credit_invoices_user_due", "user_id", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    card_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    closing_date: Mapped[date] = mapped_column(Date(), nullable=False)
    due_date: Mapped[date] = mapped_column(Date(), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="open", nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CreditPurchaseInstallment(Base):
    __tablename__ = "credit_purchase_installments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["invoice_id", "user_id"],
            ["credit_invoices.id", "credit_invoices.user_id"],
            name="fk_credit_installments_invoice_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "installment_number >= 1 AND installment_count >= installment_number",
            name="ck_credit_installment_sequence",
        ),
        CheckConstraint("amount > 0", name="ck_credit_installment_amount"),
        UniqueConstraint(
            "purchase_id",
            "installment_number",
            name="uq_credit_installment_number",
        ),
        Index("ix_credit_installments_user_invoice", "user_id", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    purchase_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    installment_number: Mapped[int] = mapped_column(nullable=False)
    installment_count: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CreditInvoicePayment(Base):
    __tablename__ = "credit_invoice_payments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["invoice_id", "user_id"],
            ["credit_invoices.id", "credit_invoices.user_id"],
            name="fk_credit_payments_invoice_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["source_account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_credit_payments_source_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("user_id", "idempotency_key", name="uq_credit_payment_idempotency"),
        CheckConstraint("amount > 0", name="ck_credit_payment_amount"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
