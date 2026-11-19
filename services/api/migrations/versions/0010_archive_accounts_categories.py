"""Add soft archive timestamps to accounts and categories.

Revision ID: 0010_archive_accounts_categories
Revises: 0009_user_token_version
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_archive_accounts_categories"
down_revision = "0009_user_token_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("categories", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_accounts_user_archived",
        "accounts",
        ["user_id", "archived_at"],
        unique=False,
    )
    op.create_index(
        "ix_categories_user_archived",
        "categories",
        ["user_id", "archived_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_categories_user_archived", table_name="categories")
    op.drop_index("ix_accounts_user_archived", table_name="accounts")
    op.drop_column("categories", "archived_at")
    op.drop_column("accounts", "archived_at")
