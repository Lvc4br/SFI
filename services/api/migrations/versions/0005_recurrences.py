"""Create recurrence rules for cash-flow forecasting.

Revision ID: 0005_recurrences
Revises: 0004_transfers_reversals
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_recurrences"
down_revision = "0004_transfers_reversals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurrences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("frequency", sa.String(length=10), nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_recurrences_amount_positive"),
        sa.CheckConstraint(
            "frequency IN ('weekly', 'monthly', 'yearly')",
            name="ck_recurrences_frequency",
        ),
        sa.CheckConstraint("interval_count BETWEEN 1 AND 52", name="ck_recurrences_interval"),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_recurrences_date_range",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_recurrences_user_id_users", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            name="fk_recurrences_account_owner", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"], ["categories.id", "categories.user_id"],
            name="fk_recurrences_category_owner", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_recurrences_user_idempotency"
        ),
    )
    op.create_index(
        "ix_recurrences_user_active", "recurrences", ["user_id", "is_active"]
    )


def downgrade() -> None:
    op.drop_index("ix_recurrences_user_active", table_name="recurrences")
    op.drop_table("recurrences")
