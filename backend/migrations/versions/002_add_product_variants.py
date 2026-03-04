"""add product_variants table and variant_id columns

Revision ID: 002_add_product_variants
Revises: 001_add_priority_queue
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '002_add_product_variants'
down_revision = '001_add_priority_queue'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. product_variants tablosu oluştur
    op.create_table(
        'product_variants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('attributes', JSONB, nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('alarm_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('lowest_price_ever', sa.Numeric(12, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_product_variants_product_id', 'product_variants', ['product_id'])

    # 2. product_stores'a variant_id ekle (nullable)
    op.add_column('product_stores', sa.Column('variant_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_product_stores_variant_id',
        'product_stores', 'product_variants',
        ['variant_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_product_stores_variant_id', 'product_stores', ['variant_id'])

    # 3. alarms'a variant_id ekle (nullable)
    op.add_column('alarms', sa.Column('variant_id', UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_alarms_variant_id',
        'alarms', 'product_variants',
        ['variant_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_alarms_variant_id', 'alarms', ['variant_id'])

    # 4. Veri migrasyonu: her Product için 1 default variant oluştur
    #    ve mevcut product_stores / alarms kayıtlarını o variant'a bağla
    op.execute("""
        INSERT INTO product_variants (id, product_id, title, attributes, alarm_count, lowest_price_ever, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            p.id,
            NULL,
            '{}'::jsonb,
            p.alarm_count,
            p.lowest_price_ever,
            p.created_at,
            p.updated_at
        FROM products p
    """)

    # 5. product_stores.variant_id = o ürünün default variant id
    op.execute("""
        UPDATE product_stores ps
        SET variant_id = pv.id
        FROM product_variants pv
        WHERE pv.product_id = ps.product_id
    """)

    # 6. alarms.variant_id = ilgili product_store'un variant_id
    op.execute("""
        UPDATE alarms a
        SET variant_id = ps.variant_id
        FROM product_stores ps
        WHERE a.product_store_id = ps.id
          AND ps.variant_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_alarms_variant_id', 'alarms')
    op.drop_constraint('fk_alarms_variant_id', 'alarms', type_='foreignkey')
    op.drop_column('alarms', 'variant_id')

    op.drop_index('ix_product_stores_variant_id', 'product_stores')
    op.drop_constraint('fk_product_stores_variant_id', 'product_stores', type_='foreignkey')
    op.drop_column('product_stores', 'variant_id')

    op.drop_index('ix_product_variants_product_id', 'product_variants')
    op.drop_table('product_variants')
