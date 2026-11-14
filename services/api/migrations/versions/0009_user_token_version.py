"""Add user token version for global session invalidation.

Revision ID: 0009_user_token_version
Revises: 0008_refresh_token_rotation
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_user_token_version"
down_revision = "0008_refresh_token_rotation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
