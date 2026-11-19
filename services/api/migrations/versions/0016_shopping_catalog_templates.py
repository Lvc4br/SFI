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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "is_template" not in {column["name"] for column in inspector.get_columns("shopping_lists")}:
        op.add_column(
            "shopping_lists",
            sa.Column("is_template", sa.Boolean(), server_default=sa.false(), nullable=False),
        )

    inspector = sa.inspect(bind)
    item_columns = {column["name"] for column in inspector.get_columns("shopping_list_items")}
    foreign_keys = inspector.get_foreign_keys("shopping_list_items")
    has_product_fk = any(
        fk.get("name") == "fk_shopping_items_product_owner" for fk in foreign_keys
    )
    if "product_id" not in item_columns or not has_product_fk:
        with op.batch_alter_table("shopping_list_items") as batch_op:
            if "product_id" not in item_columns:
                batch_op.add_column(sa.Column("product_id", sa.Uuid(), nullable=True))
            if not has_product_fk:
                batch_op.create_foreign_key(
                    "fk_shopping_items_product_owner",
                    "shopping_products",
                    ["product_id", "user_id"],
                    ["id", "user_id"],
                    ondelete="RESTRICT",
                )

    inspector = sa.inspect(bind)
    if not any(
        index["name"] == "ix_shopping_items_product"
        for index in inspector.get_indexes("shopping_list_items")
    ):
        op.create_index("ix_shopping_items_product", "shopping_list_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_shopping_items_product", table_name="shopping_list_items")
    with op.batch_alter_table("shopping_list_items") as batch_op:
        batch_op.drop_constraint("fk_shopping_items_product_owner", type_="foreignkey")
        batch_op.drop_column("product_id")
    op.drop_column("shopping_lists", "is_template")
