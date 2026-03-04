"""add priority queue fields to product_stores

Revision ID: 001_add_priority_queue
Revises:
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

revision = '001_add_priority_queue'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('product_stores', sa.Column('check_priority', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('product_stores', sa.Column('next_check_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_product_stores_check_priority', 'product_stores', ['check_priority'])
    op.create_index('ix_product_stores_next_check_at', 'product_stores', ['next_check_at'])


def downgrade() -> None:
    op.drop_index('ix_product_stores_next_check_at', 'product_stores')
    op.drop_index('ix_product_stores_check_priority', 'product_stores')
    op.drop_column('product_stores', 'next_check_at')
    op.drop_column('product_stores', 'check_priority')
