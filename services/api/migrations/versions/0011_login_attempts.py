"""Add persistent login rate-limit state.

Revision ID: 0011_login_attempts
Revises: 0010_archive_accounts_categories
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_login_attempts"
down_revision = "0010_archive_accounts_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(
        "ix_login_attempts_locked_until",
        "login_attempts",
        ["locked_until"],
        unique=False,
    )
    op.create_index(
        "ix_login_attempts_updated_at",
        "login_attempts",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_login_attempts_updated_at", table_name="login_attempts")
    op.drop_index("ix_login_attempts_locked_until", table_name="login_attempts")
    op.drop_table("login_attempts")
