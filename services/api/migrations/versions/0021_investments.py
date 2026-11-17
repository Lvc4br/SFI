"""Investment assets and operation ledger."""
from alembic import op
import sqlalchemy as sa
revision="0021_investments"
down_revision="0020_financial_goals"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("investment_assets",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("user_id",sa.Uuid(),nullable=False),
        sa.Column("name",sa.String(120),nullable=False),sa.Column("ticker",sa.String(24)),
        sa.Column("asset_type",sa.String(20),nullable=False),sa.Column("currency",sa.String(3),nullable=False),
        sa.Column("notes",sa.String(500)),sa.Column("archived",sa.Boolean(),server_default=sa.false(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id","user_id",name="uq_investment_assets_id_user"))
    op.create_index("ix_investment_assets_user_type","investment_assets",["user_id","asset_type"])
    op.create_table("investment_operations",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("user_id",sa.Uuid(),nullable=False),sa.Column("asset_id",sa.Uuid(),nullable=False),
        sa.Column("operation_type",sa.String(10),nullable=False),sa.Column("amount",sa.Numeric(18,2),nullable=False),
        sa.Column("quantity",sa.Numeric(24,8),nullable=False),sa.Column("unit_price",sa.Numeric(18,8),nullable=False),
        sa.Column("fees",sa.Numeric(18,2),nullable=False),sa.Column("taxes",sa.Numeric(18,2),nullable=False),
        sa.Column("notes",sa.String(500)),sa.Column("idempotency_key",sa.String(100),nullable=False),
        sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint("operation_type IN ('buy','sell','dividend','fee','tax')",name="ck_investment_operations_type"),
        sa.CheckConstraint("amount>=0 AND quantity>=0 AND unit_price>=0 AND fees>=0 AND taxes>=0",name="ck_investment_operations_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["asset_id","user_id"],["investment_assets.id","investment_assets.user_id"],name="fk_investment_operations_asset_owner",ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("user_id","idempotency_key",name="uq_investment_operations_idempotency"))
    op.create_index("ix_investment_operations_user_date","investment_operations",["user_id","occurred_at"])
    op.create_index("ix_investment_operations_asset_date","investment_operations",["asset_id","occurred_at"])

def downgrade():
    op.drop_index("ix_investment_operations_asset_date",table_name="investment_operations")
    op.drop_index("ix_investment_operations_user_date",table_name="investment_operations")
    op.drop_table("investment_operations")
    op.drop_index("ix_investment_assets_user_type",table_name="investment_assets")
    op.drop_table("investment_assets")
