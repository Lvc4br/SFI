"""Add immutable household stock movement ledger.

Revision ID: 0017_stock_movement_ledger
Revises: 0016_shopping_catalog_templates
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_stock_movement_ledger"
down_revision = "0016_shopping_catalog_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.String(length=300), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
        sa.CheckConstraint(
            "movement_type IN ('purchase', 'adjustment_in', 'adjustment_out', 'consumption', 'waste')",
            name="ck_stock_movements_type",
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "user_id"],
            ["shopping_products.id", "shopping_products.user_id"],
            name="fk_stock_movements_product_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stock_movements_user_product_date",
        "stock_movements",
        ["user_id", "product_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_stock_movements_user_product_date", table_name="stock_movements")
    op.drop_table("stock_movements")
