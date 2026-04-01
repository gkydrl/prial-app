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
    # Idempotent: IF NOT EXISTS kullan (önceki kısmi çalışma durumunda tekrar çalışabilir)

    # ProductStore: delivery & installment fields
    op.execute("ALTER TABLE product_stores ADD COLUMN IF NOT EXISTS estimated_delivery_days INTEGER")
    op.execute("ALTER TABLE product_stores ADD COLUMN IF NOT EXISTS delivery_text VARCHAR(200)")
    op.execute("ALTER TABLE product_stores ADD COLUMN IF NOT EXISTS installment_text VARCHAR(200)")

    # Product: review summary & daily lowest price
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS review_summary JSONB")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS daily_lowest_price NUMERIC(12, 2)")
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS daily_lowest_store VARCHAR(50)")


def downgrade() -> None:
    op.drop_column("products", "daily_lowest_store")
    op.drop_column("products", "daily_lowest_price")
    op.drop_column("products", "review_summary")
    op.drop_column("product_stores", "installment_text")
    op.drop_column("product_stores", "delivery_text")
    op.drop_column("product_stores", "estimated_delivery_days")
