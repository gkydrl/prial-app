"""add enrichment columns: delivery, installment, review_summary, daily_lowest

Revision ID: 012
Revises: 011
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ProductStore: delivery & installment fields
    op.add_column("product_stores", sa.Column("estimated_delivery_days", sa.Integer(), nullable=True))
    op.add_column("product_stores", sa.Column("delivery_text", sa.String(200), nullable=True))
    op.add_column("product_stores", sa.Column("installment_text", sa.String(200), nullable=True))

    # Product: review summary & daily lowest price
    op.add_column("products", sa.Column("review_summary", JSONB(), nullable=True))
    op.add_column("products", sa.Column("daily_lowest_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("daily_lowest_store", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "daily_lowest_store")
    op.drop_column("products", "daily_lowest_price")
    op.drop_column("products", "review_summary")
    op.drop_column("product_stores", "installment_text")
    op.drop_column("product_stores", "delivery_text")
    op.drop_column("product_stores", "estimated_delivery_days")
