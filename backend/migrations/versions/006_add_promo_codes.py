"""Add promo_codes and promo_code_products tables.

Revision ID: 006
"""
from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum values must match Python enum NAMES (uppercase) — same as store_name_enum pattern
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE discount_type_enum AS ENUM ('PERCENTAGE', 'FIXED');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # Drop if exists with wrong case values (from previous failed attempts)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'discount_type_enum') THEN
                -- Check if values are lowercase (wrong)
                IF EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'discount_type_enum' AND e.enumlabel = 'percentage'
                ) THEN
                    DROP TYPE discount_type_enum;
                    CREATE TYPE discount_type_enum AS ENUM ('PERCENTAGE', 'FIXED');
                END IF;
            END IF;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code VARCHAR(50) UNIQUE NOT NULL,
            title VARCHAR(200) NOT NULL,
            discount_type discount_type_enum NOT NULL,
            discount_value NUMERIC(12,2) NOT NULL,
            store store_name_enum,
            min_price NUMERIC(12,2),
            starts_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_promo_codes_expires_at ON promo_codes (expires_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_promo_codes_store ON promo_codes (store);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS promo_code_products (
            promo_code_id UUID REFERENCES promo_codes(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id) ON DELETE CASCADE,
            PRIMARY KEY (promo_code_id, product_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS promo_code_products")
    op.execute("DROP INDEX IF EXISTS ix_promo_codes_store")
    op.execute("DROP INDEX IF EXISTS ix_promo_codes_expires_at")
    op.execute("DROP TABLE IF EXISTS promo_codes")
    op.execute("DROP TYPE IF EXISTS discount_type_enum")
