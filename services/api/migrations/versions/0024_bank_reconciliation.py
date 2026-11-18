"""Persist bank statement rows and explicit reconciliation links."""
from alembic import op
import sqlalchemy as sa

revision = "0024_bank_reconciliation"
down_revision = "0023_fiscal_documents"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bank_statement_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("matched_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("external_id", sa.String(160), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(10), server_default="pending", nullable=False),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_statement_entries_amount_positive"),
        sa.CheckConstraint("status IN ('pending', 'matched', 'ignored')", name="ck_statement_entries_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            name="fk_statement_entries_account_owner", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["matched_transaction_id", "user_id"], ["transactions.id", "transactions.user_id"],
            name="fk_statement_entries_transaction_owner", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_statement_entries_user_idempotency"),
        sa.UniqueConstraint("user_id", "account_id", "external_id", name="uq_statement_entries_external_id"),
        sa.UniqueConstraint("user_id", "matched_transaction_id", name="uq_statement_entries_one_transaction"),
    )
    op.create_index(
        "ix_statement_entries_user_account_status", "bank_statement_entries",
        ["user_id", "account_id", "status"],
    )
    op.create_index(
        "ix_statement_entries_user_date", "bank_statement_entries", ["user_id", "occurred_at"]
    )


def downgrade():
    op.drop_index("ix_statement_entries_user_date", table_name="bank_statement_entries")
    op.drop_index("ix_statement_entries_user_account_status", table_name="bank_statement_entries")
    op.drop_table("bank_statement_entries")
