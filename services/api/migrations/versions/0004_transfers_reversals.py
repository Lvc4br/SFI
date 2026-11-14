"""Add transfers and auditable transaction reversals.

Revision ID: 0004_transfers_reversals
Revises: 0003_monthly_budgets
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_transfers_reversals"
down_revision = "0003_monthly_budgets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_transfers_amount_positive"),
        sa.CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transfers_distinct_accounts",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_transfers_user_id_users", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            name="fk_transfers_source_account_owner", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["destination_account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            name="fk_transfers_destination_account_owner", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_transfers_id_user"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_transfers_user_idempotency"),
    )
    op.create_index("ix_transfers_user_date", "transfers", ["user_id", "occurred_at"])
    op.add_column(
        "transactions", sa.Column("transfer_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "transactions",
        sa.Column("reversal_of_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint("uq_transactions_id_user", "transactions", ["id", "user_id"])
    op.create_unique_constraint(
        "uq_transactions_one_reversal",
        "transactions",
        ["user_id", "reversal_of_transaction_id"],
    )
    op.create_foreign_key(
        "fk_transactions_transfer_owner", "transactions", "transfers",
        ["transfer_id", "user_id"], ["id", "user_id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_transactions_reversal_owner", "transactions", "transactions",
        ["reversal_of_transaction_id", "user_id"], ["id", "user_id"], ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_transactions_reversal_owner", "transactions", type_="foreignkey")
    op.drop_constraint("fk_transactions_transfer_owner", "transactions", type_="foreignkey")
    op.drop_constraint("uq_transactions_one_reversal", "transactions", type_="unique")
    op.drop_constraint("uq_transactions_id_user", "transactions", type_="unique")
    op.drop_column("transactions", "reversal_of_transaction_id")
    op.drop_column("transactions", "transfer_id")
    op.drop_index("ix_transfers_user_date", table_name="transfers")
    op.drop_table("transfers")
