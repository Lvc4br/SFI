"""Add financial goals and their allocation ledger.

Revision ID: 0020_financial_goals
Revises: 0019_debts_and_payments
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_financial_goals"
down_revision = "0019_debts_and_payments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "financial_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_amount > 0", name="ck_financial_goals_target"),
        sa.CheckConstraint("current_amount >= 0", name="ck_financial_goals_current"),
        sa.CheckConstraint("status IN ('active', 'completed', 'paused', 'archived')", name="ck_financial_goals_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_financial_goals_id_user"),
    )
    op.create_index(
        "ix_financial_goals_user_status_due",
        "financial_goals",
        ["user_id", "status", "target_date"],
    )
    op.create_table(
        "goal_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.String(12), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_goal_entries_amount"),
        sa.CheckConstraint("entry_type IN ('contribution', 'withdrawal')", name="ck_goal_entries_type"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["goal_id", "user_id"],
            ["financial_goals.id", "financial_goals.user_id"],
            name="fk_goal_entries_goal_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_goal_entries_idempotency"),
    )
    op.create_index("ix_goal_entries_user_date", "goal_entries", ["user_id", "occurred_at"])


def downgrade():
    op.drop_index("ix_goal_entries_user_date", table_name="goal_entries")
    op.drop_table("goal_entries")
    op.drop_index("ix_financial_goals_user_status_due", table_name="financial_goals")
    op.drop_table("financial_goals")
