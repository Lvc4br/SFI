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


class FinancialGoal(Base):
    __tablename__ = "financial_goals"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_financial_goals_id_user"),
        CheckConstraint("target_amount > 0", name="ck_financial_goals_target"),
        CheckConstraint("current_amount >= 0", name="ck_financial_goals_current"),
        CheckConstraint(
            "status IN ('active', 'completed', 'paused', 'archived')",
            name="ck_financial_goals_status",
        ),
        Index("ix_financial_goals_user_status_due", "user_id", "status", "target_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    target_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class GoalEntry(Base):
    __tablename__ = "goal_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["goal_id", "user_id"],
            ["financial_goals.id", "financial_goals.user_id"],
            name="fk_goal_entries_goal_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_goal_entries_idempotency"
        ),
        CheckConstraint("amount > 0", name="ck_goal_entries_amount"),
        CheckConstraint(
            "entry_type IN ('contribution', 'withdrawal')",
            name="ck_goal_entries_type",
        ),
        Index("ix_goal_entries_user_date", "user_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    goal_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(12), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
