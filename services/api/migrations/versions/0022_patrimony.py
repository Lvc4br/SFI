"""Personal patrimony items and valuation history."""
from alembic import op
import sqlalchemy as sa

revision = "0022_patrimony"
down_revision = "0021_investments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "patrimony_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("item_kind", sa.String(10), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("item_kind IN ('asset', 'liability')", name="ck_patrimony_items_kind"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "user_id", name="uq_patrimony_items_id_user"),
    )
    op.create_index("ix_patrimony_items_user_kind", "patrimony_items", ["user_id", "item_kind"])
    op.create_table(
        "patrimony_valuations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("notes", sa.String(500)),
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("valued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_patrimony_valuations_amount"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["item_id", "user_id"],
            ["patrimony_items.id", "patrimony_items.user_id"],
            name="fk_patrimony_valuations_item_owner",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_patrimony_valuations_idempotency"),
    )
    op.create_index("ix_patrimony_valuations_item_date", "patrimony_valuations", ["item_id", "valued_at"])
    op.create_index("ix_patrimony_valuations_user_date", "patrimony_valuations", ["user_id", "valued_at"])


def downgrade():
    op.drop_index("ix_patrimony_valuations_user_date", table_name="patrimony_valuations")
    op.drop_index("ix_patrimony_valuations_item_date", table_name="patrimony_valuations")
    op.drop_table("patrimony_valuations")
    op.drop_index("ix_patrimony_items_user_kind", table_name="patrimony_items")
    op.drop_table("patrimony_items")
