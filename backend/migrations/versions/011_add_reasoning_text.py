"""add reasoning_text to price_predictions

Revision ID: 011
Revises: 010
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "price_predictions",
        sa.Column("reasoning_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("price_predictions", "reasoning_text")
