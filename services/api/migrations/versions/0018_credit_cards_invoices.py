"""Add personal credit cards, invoices, installment ledger and payments.
Revision ID: 0018_credit_cards_invoices
Revises: 0017_stock_movement_ledger
"""
from alembic import op
import sqlalchemy as sa
revision="0018_credit_cards_invoices"
down_revision="0017_stock_movement_ledger"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("credit_cards",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("user_id",sa.Uuid(),nullable=False),sa.Column("account_id",sa.Uuid(),nullable=False),
        sa.Column("name",sa.String(80),nullable=False),sa.Column("brand",sa.String(30)),sa.Column("last_four",sa.String(4)),
        sa.Column("closing_day",sa.Integer(),nullable=False),sa.Column("due_day",sa.Integer(),nullable=False),sa.Column("credit_limit",sa.Numeric(18,2),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint("closing_day BETWEEN 1 AND 31",name="ck_credit_cards_closing_day"),sa.CheckConstraint("due_day BETWEEN 1 AND 31",name="ck_credit_cards_due_day"),sa.CheckConstraint("credit_limit > 0",name="ck_credit_cards_limit_positive"),
        sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["account_id","user_id"],["accounts.id","accounts.user_id"],name="fk_credit_cards_account_owner",ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("id","user_id",name="uq_credit_cards_id_user"),sa.UniqueConstraint("account_id",name="uq_credit_cards_account"))
    op.create_index("ix_credit_cards_user","credit_cards",["user_id"])
    op.create_table("credit_invoices",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("user_id",sa.Uuid(),nullable=False),sa.Column("card_id",sa.Uuid(),nullable=False),sa.Column("period",sa.String(7),nullable=False),
        sa.Column("closing_date",sa.Date(),nullable=False),sa.Column("due_date",sa.Date(),nullable=False),sa.Column("status",sa.String(10),nullable=False),sa.Column("paid_amount",sa.Numeric(18,2),nullable=False,server_default="0"),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint("status IN ('open','closed','paid')",name="ck_credit_invoices_status"),sa.CheckConstraint("paid_amount >= 0",name="ck_credit_invoices_paid_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["card_id","user_id"],["credit_cards.id","credit_cards.user_id"],name="fk_credit_invoices_card_owner",ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("id","user_id",name="uq_credit_invoices_id_user"),sa.UniqueConstraint("card_id","period",name="uq_credit_invoices_card_period"))
    op.create_index("ix_credit_invoices_user_due","credit_invoices",["user_id","due_date"])
    op.create_table("credit_purchase_installments",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("user_id",sa.Uuid(),nullable=False),sa.Column("invoice_id",sa.Uuid(),nullable=False),sa.Column("purchase_id",sa.Uuid(),nullable=False),
        sa.Column("installment_number",sa.Integer(),nullable=False),sa.Column("installment_count",sa.Integer(),nullable=False),sa.Column("description",sa.String(160),nullable=False),sa.Column("amount",sa.Numeric(18,2),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("installment_number >= 1 AND installment_count >= installment_number",name="ck_credit_installment_sequence"),sa.CheckConstraint("amount > 0",name="ck_credit_installment_amount"),
        sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["invoice_id","user_id"],["credit_invoices.id","credit_invoices.user_id"],name="fk_credit_installments_invoice_owner",ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("purchase_id","installment_number",name="uq_credit_installment_number"))
    op.create_index("ix_credit_installments_user_invoice","credit_purchase_installments",["user_id","invoice_id"])
    op.create_table("credit_invoice_payments",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("user_id",sa.Uuid(),nullable=False),sa.Column("invoice_id",sa.Uuid(),nullable=False),sa.Column("source_account_id",sa.Uuid(),nullable=False),
        sa.Column("amount",sa.Numeric(18,2),nullable=False),sa.Column("idempotency_key",sa.String(100),nullable=False),sa.Column("paid_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint("amount > 0",name="ck_credit_payment_amount"),sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["invoice_id","user_id"],["credit_invoices.id","credit_invoices.user_id"],name="fk_credit_payments_invoice_owner",ondelete="RESTRICT"),sa.ForeignKeyConstraint(["source_account_id","user_id"],["accounts.id","accounts.user_id"],name="fk_credit_payments_source_owner",ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("user_id","idempotency_key",name="uq_credit_payment_idempotency"))
