"""Add persistent access-token revocation.

Revision ID: 0007_access_token_revocation
Revises: 0006_transfer_reversals
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_access_token_revocation"
down_revision = "0006_transfer_reversals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "revoked_access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_revoked_access_tokens_user_id_users", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_revoked_access_tokens_jti"),
    )
    op.create_index(
        "ix_revoked_access_tokens_expires",
        "revoked_access_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_revoked_access_tokens_expires", table_name="revoked_access_tokens")
    op.drop_table("revoked_access_tokens")
