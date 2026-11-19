import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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


class ShoppingProduct(Base):
    __tablename__ = "shopping_products"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_shopping_products_user", ondelete="RESTRICT"
        ),
        CheckConstraint("length(trim(name)) > 0", name="ck_shopping_products_name_nonempty"),
        UniqueConstraint("id", "user_id", name="uq_shopping_products_id_user"),
        Index("ix_shopping_products_user_name", "user_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), default="un", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProductPriceObservation(Base):
    __tablename__ = "product_price_observations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["product_id", "user_id"],
            ["shopping_products.id", "shopping_products.user_id"],
            name="fk_price_observations_product_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("price >= 0", name="ck_price_observations_price_nonnegative"),
        CheckConstraint("length(trim(currency)) = 3", name="ck_price_observations_currency_length"),
        Index("ix_price_observations_product_date", "product_id", "observed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
