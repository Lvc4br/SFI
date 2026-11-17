import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sfi_api.models.base import Base

class InvestmentAsset(Base):
    __tablename__ = "investment_assets"
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_investment_assets_id_user"), Index("ix_investment_assets_user_type", "user_id", "asset_type"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(24))
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    notes: Mapped[str | None] = mapped_column(String(500))
    archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class InvestmentOperation(Base):
    __tablename__ = "investment_operations"
    __table_args__ = (ForeignKeyConstraint(["asset_id", "user_id"], ["investment_assets.id", "investment_assets.user_id"], name="fk_investment_operations_asset_owner", ondelete="RESTRICT"), UniqueConstraint("user_id", "idempotency_key", name="uq_investment_operations_idempotency"), CheckConstraint("operation_type IN ('buy','sell','dividend','fee','tax')", name="ck_investment_operations_type"), CheckConstraint("amount >= 0 AND quantity >= 0 AND unit_price >= 0 AND fees >= 0 AND taxes >= 0", name="ck_investment_operations_nonnegative"), Index("ix_investment_operations_user_date", "user_id", "occurred_at"), Index("ix_investment_operations_asset_date", "asset_id", "occurred_at"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=Decimal("0"))
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    taxes: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
