"""Store reviewed NF-e/NFC-e metadata without retaining raw XML."""
from alembic import op
import sqlalchemy as sa

revision = "0023_fiscal_documents"
down_revision = "0022_patrimony"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fiscal_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("access_key", sa.String(44), nullable=False),
        sa.Column("document_number", sa.String(20), nullable=False),
        sa.Column("series", sa.String(10), nullable=False),
        sa.Column("issuer_name", sa.String(160), nullable=False),
        sa.Column("issuer_tax_id", sa.String(14), nullable=False),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_amount", sa.String(24), nullable=False),
        sa.Column("currency", sa.String(3), server_default="BRL", nullable=False),
        sa.Column("items_json", sa.Text(), nullable=False),
        sa.Column("xml_sha256", sa.String(64), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            name="fk_fiscal_documents_account_owner", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id", "user_id"], ["categories.id", "categories.user_id"],
            name="fk_fiscal_documents_category_owner", ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "access_key", name="uq_fiscal_documents_user_access_key"),
    )
    op.create_index(
        "ix_fiscal_documents_user_issue_date", "fiscal_documents", ["user_id", "issue_date"]
    )


def downgrade():
    op.drop_index("ix_fiscal_documents_user_issue_date", table_name="fiscal_documents")
    op.drop_table("fiscal_documents")
