"""Add promo_codes and promo_code_products tables.

Revision ID: 006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # discount_type_enum
    discount_type_enum = sa.Enum("percentage", "fixed", name="discount_type_enum")
    discount_type_enum.create(op.get_bind(), checkfirst=True)

    # store_name_enum already exists from product model

    op.create_table(
        "promo_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("discount_type", discount_type_enum, nullable=False),
        sa.Column("discount_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("store", sa.Enum("trendyol", "hepsiburada", "amazon", "n11", "ciceksepeti", "mediamarkt", "teknosa", "vatan", "other", name="store_name_enum", create_type=False), nullable=True),
        sa.Column("min_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_promo_codes_expires_at", "promo_codes", ["expires_at"])
    op.create_index("ix_promo_codes_store", "promo_codes", ["store"])

    op.create_table(
        "promo_code_products",
        sa.Column("promo_code_id", UUID(as_uuid=True), sa.ForeignKey("promo_codes.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("promo_code_products")
    op.drop_index("ix_promo_codes_store", table_name="promo_codes")
    op.drop_index("ix_promo_codes_expires_at", table_name="promo_codes")
    op.drop_table("promo_codes")
    sa.Enum(name="discount_type_enum").drop(op.get_bind(), checkfirst=True)
