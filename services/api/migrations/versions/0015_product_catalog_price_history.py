"""Add reusable shopping products and price observations.

Revision ID: 0015_product_catalog
Revises: 0014_shopping_lists
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_product_catalog"
down_revision = "0014_shopping_lists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("barcode", sa.String(length=32), nullable=True),
        sa.Column("unit", sa.String(length=20), server_default="un", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_shopping_products_name_nonempty"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_shopping_products_user", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopping_products_user_name", "shopping_products", ["user_id", "name"])
    op.create_table(
        "product_price_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("merchant", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("notes", sa.String(length=300), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_price_observations_price_nonnegative"),
        sa.CheckConstraint("length(trim(currency)) = 3", name="ck_price_observations_currency_length"),
        sa.ForeignKeyConstraint(
            ["product_id", "user_id"],
            ["shopping_products.id", "shopping_products.user_id"],
            name="fk_price_observations_product_owner",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_unique_constraint(
        "uq_shopping_products_id_user", "shopping_products", ["id", "user_id"]
    )
    op.create_index(
        "ix_price_observations_product_date",
        "product_price_observations",
        ["product_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_price_observations_product_date", table_name="product_price_observations")
    op.drop_table("product_price_observations")
    op.drop_constraint("uq_shopping_products_id_user", "shopping_products", type_="unique")
    op.drop_index("ix_shopping_products_user_name", table_name="shopping_products")
    op.drop_table("shopping_products")
