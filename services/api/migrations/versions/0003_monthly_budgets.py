"""Create monthly category budgets.

Revision ID: 0003_monthly_budgets
Revises: 0002_financial_core
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_monthly_budgets"
down_revision = "0002_financial_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period", sa.String(length=7), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("limit_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("limit_amount > 0", name="ck_budgets_limit_positive"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_budgets_user_id_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_budgets_category_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "category_id", "period", "currency",
            name="uq_budgets_user_category_period_currency",
        ),
    )
    op.create_index("ix_budgets_user_period", "budgets", ["user_id", "period"])


def downgrade() -> None:
    op.drop_index("ix_budgets_user_period", table_name="budgets")
    op.drop_table("budgets")
