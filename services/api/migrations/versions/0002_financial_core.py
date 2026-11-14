"""Add user-owned accounts, categories and transactions.

Revision ID: 0002_financial_core
Revises: 0001_create_users
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_financial_core"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("account_type", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("opening_balance", sa.Numeric(18, 2), server_default="0.00", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_accounts_user_id_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_accounts_id_user"),
        sa.CheckConstraint("opening_balance >= 0", name="ck_accounts_opening_balance_nonnegative"),
    )
    op.create_index("ix_accounts_user_created", "accounts", ["user_id", "created_at"])

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("category_type", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_categories_user_id_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_categories_id_user"),
        sa.UniqueConstraint("user_id", "name", "category_type", name="uq_categories_user_name_type"),
    )
    op.create_index("ix_categories_user", "categories", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_transactions_user_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            name="fk_transactions_account_owner", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"], ["categories.id", "categories.user_id"],
            name="fk_transactions_category_owner", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_transactions_user_idempotency"),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_transactions_user_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("ix_categories_user", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_accounts_user_created", table_name="accounts")
    op.drop_table("accounts")
