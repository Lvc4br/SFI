import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
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


class BankStatementEntry(Base):
    __tablename__ = "bank_statement_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_statement_entries_account_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["matched_transaction_id", "user_id"],
            ["transactions.id", "transactions.user_id"],
            name="fk_statement_entries_transaction_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_statement_entries_user_idempotency"
        ),
        UniqueConstraint(
            "user_id", "account_id", "external_id",
            name="uq_statement_entries_external_id",
        ),
        UniqueConstraint(
            "user_id", "matched_transaction_id",
            name="uq_statement_entries_one_transaction",
        ),
        CheckConstraint("amount > 0", name="ck_statement_entries_amount_positive"),
        CheckConstraint(
            "status IN ('pending', 'matched', 'ignored')",
            name="ck_statement_entries_status",
        ),
        Index("ix_statement_entries_user_account_status", "user_id", "account_id", "status"),
        Index("ix_statement_entries_user_date", "user_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    matched_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str] = mapped_column(String(160), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(10), default="pending", nullable=False)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
