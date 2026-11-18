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


class PatrimonyItem(Base):
    __tablename__ = "patrimony_items"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_patrimony_items_id_user"),
        CheckConstraint(
            "item_kind IN ('asset', 'liability')",
            name="ck_patrimony_items_kind",
        ),
        Index("ix_patrimony_items_user_kind", "user_id", "item_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    item_kind: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str] = mapped_column(String(24), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    description: Mapped[str | None] = mapped_column(String(500))
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PatrimonyValuation(Base):
    __tablename__ = "patrimony_valuations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["item_id", "user_id"],
            ["patrimony_items.id", "patrimony_items.user_id"],
            name="fk_patrimony_valuations_item_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint("amount >= 0", name="ck_patrimony_valuations_amount"),
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_patrimony_valuations_idempotency"
        ),
        Index("ix_patrimony_valuations_item_date", "item_id", "valued_at"),
        Index("ix_patrimony_valuations_user_date", "user_id", "valued_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    valued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
