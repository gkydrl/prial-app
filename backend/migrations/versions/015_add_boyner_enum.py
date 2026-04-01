"""add BOYNER to store_name_enum

Revision ID: 015
Revises: 014
Create Date: 2026-04-01
"""
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE store_name_enum ADD VALUE IF NOT EXISTS 'boyner';
        END $$;
    """)


def downgrade() -> None:
    pass
