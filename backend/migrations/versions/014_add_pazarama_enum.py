"""add PAZARAMA to store_name_enum

Revision ID: 014
Revises: 013
Create Date: 2026-04-01
"""
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: zaten varsa hata vermez
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE store_name_enum ADD VALUE IF NOT EXISTS 'pazarama';
        END $$;
    """)


def downgrade() -> None:
    # PostgreSQL enum value silmeyi desteklemiyor — downgrade no-op
    pass
