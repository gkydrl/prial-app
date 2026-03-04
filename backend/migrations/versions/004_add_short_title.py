"""add short_title to products

Revision ID: 004
Revises: 003
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("products", sa.Column("short_title", sa.String(60), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "short_title")
