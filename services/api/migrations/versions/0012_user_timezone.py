"""Persist user IANA timezone.

Revision ID: 0012_user_timezone
Revises: 0011_login_attempts
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_user_timezone"
down_revision = "0011_login_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="America/Sao_Paulo",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "timezone")
