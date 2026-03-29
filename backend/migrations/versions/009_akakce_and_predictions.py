"""add akakce integration and prediction tables

Revision ID: 009
Revises: 008
Create Date: 2026-03-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Enums (idempotent with DO $$ blocks) ---
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE price_source_enum AS ENUM ('own_scrape', 'akakce_import', 'cimri_import');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE recommendation_enum AS ENUM ('AL', 'BEKLE', 'GUCLU_BEKLE');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE predicted_direction_enum AS ENUM ('UP', 'DOWN', 'STABLE');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # --- price_history: source column ---
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE price_history ADD COLUMN source price_source_enum DEFAULT 'own_scrape';
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)
    op.execute("UPDATE price_history SET source = 'own_scrape' WHERE source IS NULL")
    op.execute("ALTER TABLE price_history ALTER COLUMN source SET NOT NULL")

    # --- products: akakce columns ---
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE products ADD COLUMN l1y_lowest_price NUMERIC(12,2);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE products ADD COLUMN l1y_highest_price NUMERIC(12,2);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE products ADD COLUMN akakce_url VARCHAR(1000);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)

    # --- price_predictions table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS price_predictions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            prediction_date DATE NOT NULL,
            recommendation recommendation_enum NOT NULL,
            confidence NUMERIC(5,4) NOT NULL,
            reasoning JSONB,
            model_version VARCHAR(50) NOT NULL,
            current_price NUMERIC(12,2) NOT NULL,
            predicted_direction predicted_direction_enum NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_price_predictions_product_id
        ON price_predictions (product_id)
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_price_predictions_product_date
        ON price_predictions (product_id, prediction_date)
    """)

    # --- prediction_outcomes table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS prediction_outcomes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            prediction_id UUID NOT NULL UNIQUE REFERENCES price_predictions(id) ON DELETE CASCADE,
            actual_price NUMERIC(12,2) NOT NULL,
            outcome_date DATE NOT NULL,
            was_correct BOOLEAN NOT NULL,
            error_magnitude NUMERIC(8,4),
            lesson_learned JSONB,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # --- model_parameters table ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_parameters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            version VARCHAR(50) NOT NULL UNIQUE,
            parameters JSONB NOT NULL,
            accuracy_score NUMERIC(5,4),
            total_predictions INTEGER DEFAULT 0,
            correct_predictions INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS model_parameters")
    op.execute("DROP TABLE IF EXISTS prediction_outcomes")
    op.execute("DROP TABLE IF EXISTS price_predictions")

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE products DROP COLUMN IF EXISTS akakce_url;
            ALTER TABLE products DROP COLUMN IF EXISTS l1y_highest_price;
            ALTER TABLE products DROP COLUMN IF EXISTS l1y_lowest_price;
        END $$;
    """)

    op.execute("ALTER TABLE price_history DROP COLUMN IF EXISTS source")

    op.execute("DROP TYPE IF EXISTS predicted_direction_enum")
    op.execute("DROP TYPE IF EXISTS recommendation_enum")
    op.execute("DROP TYPE IF EXISTS price_source_enum")
