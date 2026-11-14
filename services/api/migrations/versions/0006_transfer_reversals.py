"""Add paired, auditable transfer reversals.

Revision ID: 0006_transfer_reversals
Revises: 0005_recurrences
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_transfer_reversals"
down_revision = "0005_recurrences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transfer_reversals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transfer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_transfer_reversals_user_id_users", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transfer_id", "user_id"], ["transfers.id", "transfers.user_id"],
            name="fk_transfer_reversals_transfer_owner", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_transfer_reversals_id_user"),
        sa.UniqueConstraint(
            "user_id", "transfer_id", name="uq_transfer_reversals_one_per_transfer"
        ),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_transfer_reversals_user_idempotency"
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("transfer_reversal_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_transfer_reversal_owner",
        "transactions",
        "transfer_reversals",
        ["transfer_reversal_id", "user_id"],
        ["id", "user_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_transactions_transfer_reversal_owner", "transactions", type_="foreignkey"
    )
    op.drop_column("transactions", "transfer_reversal_id")
    op.drop_table("transfer_reversals")
