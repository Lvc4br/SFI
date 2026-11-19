"""Add personal shopping lists and items.

Revision ID: 0014_shopping_lists
Revises: 0013_security_events
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_shopping_lists"
down_revision = "0013_security_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("shopping_lists"):
        op.create_table(
            "shopping_lists",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("is_favorite", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("id", "user_id", name="uq_shopping_lists_id_user"),
        )

    inspector = sa.inspect(bind)
    if not any(index["name"] == "ix_shopping_lists_user_updated" for index in inspector.get_indexes("shopping_lists")):
        op.create_index("ix_shopping_lists_user_updated", "shopping_lists", ["user_id", "updated_at"])

    if not inspector.has_table("shopping_list_items"):
        op.create_table(
            "shopping_list_items",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("list_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("quantity", sa.Numeric(12, 3), server_default="1.000", nullable=False),
            sa.Column("unit", sa.String(length=20), server_default="un", nullable=False),
            sa.Column("unit_price", sa.Numeric(18, 2), nullable=True),
            sa.Column("is_checked", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("position", sa.Integer(), server_default="0", nullable=False),
            sa.Column("notes", sa.String(length=300), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("quantity > 0", name="ck_shopping_items_quantity_positive"),
            sa.CheckConstraint("unit_price IS NULL OR unit_price >= 0", name="ck_shopping_items_price_nonnegative"),
            sa.ForeignKeyConstraint(["list_id", "user_id"], ["shopping_lists.id", "shopping_lists.user_id"], name="fk_shopping_items_list_owner", ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    if not any(index["name"] == "ix_shopping_items_list_position" for index in inspector.get_indexes("shopping_list_items")):
        op.create_index("ix_shopping_items_list_position", "shopping_list_items", ["list_id", "position"])

def downgrade() -> None:
    op.drop_index("ix_shopping_items_list_position", table_name="shopping_list_items")
    op.drop_table("shopping_list_items")
    op.drop_index("ix_shopping_lists_user_updated", table_name="shopping_lists")
    op.drop_table("shopping_lists")
