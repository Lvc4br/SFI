import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, Index, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from sfi_api.models.base import Base


class StockMovement(Base):
    """Immutable stock ledger; balance is derived from signed movement quantities."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "user_id"],
            ["shopping_products.id", "shopping_products.user_id"],
            name="fk_stock_movements_product_owner",
            ondelete="RESTRICT",
        ),
        CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
        CheckConstraint(
            "movement_type IN ('purchase', 'adjustment_in', 'adjustment_out', 'consumption', 'waste')",
            name="ck_stock_movements_type",
        ),
        Index("ix_stock_movements_user_product_date", "user_id", "product_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
