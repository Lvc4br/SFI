import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from sfi_api.models.base import Base


class TransferReversal(Base):
    __tablename__ = "transfer_reversals"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_transfer_reversals_id_user"),
        UniqueConstraint(
            "user_id", "transfer_id", name="uq_transfer_reversals_one_per_transfer"
        ),
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_transfer_reversals_user_idempotency"
        ),
        ForeignKeyConstraint(
            ["transfer_id", "user_id"],
            ["transfers.id", "transfers.user_id"],
            name="fk_transfer_reversals_transfer_owner",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    transfer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
