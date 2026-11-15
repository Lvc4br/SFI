"""Connect shopping list items to the personal catalog and add reusable templates.

Revision ID: 0016_shopping_catalog_templates
Revises: 0015_product_catalog
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_shopping_catalog_templates"
down_revision = "0015_product_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopping_lists",
        sa.Column("is_template", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    with op.batch_alter_table("shopping_list_items") as batch_op:
        batch_op.add_column(sa.Column("product_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_shopping_items_product_owner",
            "shopping_products",
            ["product_id", "user_id"],
            ["id", "user_id"],
            ondelete="RESTRICT",
        )
    op.create_index("ix_shopping_items_product", "shopping_list_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_shopping_items_product", table_name="shopping_list_items")
    with op.batch_alter_table("shopping_list_items") as batch_op:
        batch_op.drop_constraint("fk_shopping_items_product_owner", type_="foreignkey")
        batch_op.drop_column("product_id")
    op.drop_column("shopping_lists", "is_template")
