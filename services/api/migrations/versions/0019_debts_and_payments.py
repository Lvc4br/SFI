"""Add personal debts and payment ledger.

Revision ID: 0019_debts_and_payments
Revises: 0018_credit_cards_invoices
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_debts_and_payments"
down_revision = "0018_credit_cards_invoices"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "debts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("creditor", sa.String(120), nullable=False),
        sa.Column("debt_type", sa.String(30), nullable=False),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("original_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("outstanding_principal", sa.Numeric(18, 2), nullable=False),
        sa.Column("annual_interest_rate", sa.Numeric(9, 6), nullable=False),
        sa.Column("amortization_method", sa.String(10), nullable=False),
        sa.Column("contracted_at", sa.Date(), nullable=False),
        sa.Column("first_due_date", sa.Date(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=True),
        sa.Column("installment_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("original_amount > 0", name="ck_debts_original_amount"),
        sa.CheckConstraint("outstanding_principal >= 0", name="ck_debts_outstanding_principal"),
        sa.CheckConstraint("annual_interest_rate >= 0", name="ck_debts_interest_rate"),
        sa.CheckConstraint("status IN ('active', 'paid', 'archived')", name="ck_debts_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_debts_id_user"),
    )
    op.create_index("ix_debts_user_status_due", "debts", ["user_id", "status", "next_due_date"])
    op.create_table(
        "debt_payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("debt_id", sa.Uuid(), nullable=False),
        sa.Column("source_account_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("principal_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_debt_payments_amount"),
        sa.CheckConstraint("principal_amount > 0", name="ck_debt_payments_principal"),
        sa.CheckConstraint("interest_amount >= 0", name="ck_debt_payments_interest"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["debt_id", "user_id"], ["debts.id", "debts.user_id"], name="fk_debt_payments_debt_owner", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_account_id", "user_id"], ["accounts.id", "accounts.user_id"], name="fk_debt_payments_account_owner", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transaction_id", "user_id"], ["transactions.id", "transactions.user_id"], name="fk_debt_payments_transaction_owner", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_debt_payments_idempotency"),
    )
    op.create_index("ix_debt_payments_user_paid", "debt_payments", ["user_id", "paid_at"])


def downgrade():
    op.drop_index("ix_debt_payments_user_paid", table_name="debt_payments")
    op.drop_table("debt_payments")
    op.drop_index("ix_debts_user_status_due", table_name="debts")
    op.drop_table("debts")
