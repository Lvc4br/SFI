import uuid
from datetime import datetime

from sqlalchemy import (\n    DateTime,\n    ForeignKey,\n    ForeignKeyConstraint,\n    Index,\n    String,\n    Text,\n    UniqueConstraint,\n    Uuid,\n    func,\n)
from sqlalchemy.orm import Mapped, mapped_column

from sfi_api.models.base import Base


class FiscalDocument(Base):
    __tablename__ = "fiscal_documents"
    __table_args__ = (
        UniqueConstraint("user_id", "access_key", name="uq_fiscal_documents_user_access_key"),
        ForeignKeyConstraint(
            ["account_id", "user_id"],
            ["accounts.id", "accounts.user_id"],
            name="fk_fiscal_documents_account_owner",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_fiscal_documents_category_owner",
            ondelete="RESTRICT",
        ),
        Index("ix_fiscal_documents_user_issue_date", "user_id", "issue_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    access_key: Mapped[str] = mapped_column(String(44), nullable=False)
    document_number: Mapped[str] = mapped_column(String(20), nullable=False)
    series: Mapped[str] = mapped_column(String(10), nullable=False)
    issuer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    issuer_tax_id: Mapped[str] = mapped_column(String(14), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[str] = mapped_column(String(24), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    items_json: Mapped[str] = mapped_column(Text, nullable=False)
    xml_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    account_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
