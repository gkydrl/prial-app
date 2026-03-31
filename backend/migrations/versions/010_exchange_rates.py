"""add exchange_rates table

Revision ID: 010
Revises: 009
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS exchange_rates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            currency_pair VARCHAR(7) NOT NULL,
            rate NUMERIC(12,6) NOT NULL,
            change_pct NUMERIC(8,4),
            source VARCHAR(50) NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # Index for fast lookups by currency_pair + recorded_at
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_exchange_rates_recorded_at
        ON exchange_rates (recorded_at);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_exchange_rates_pair_recorded
        ON exchange_rates (currency_pair, recorded_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS exchange_rates;")
