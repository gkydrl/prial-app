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
    # --- price_history: source column ---
    price_source_enum = sa.Enum(
        "own_scrape", "akakce_import", "cimri_import",
        name="price_source_enum",
    )
    price_source_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "price_history",
        sa.Column("source", price_source_enum, nullable=True, server_default="own_scrape"),
    )
    # Backfill existing rows
    op.execute("UPDATE price_history SET source = 'own_scrape' WHERE source IS NULL")
    op.alter_column("price_history", "source", nullable=False)

    # --- products: akakce columns ---
    op.add_column("products", sa.Column("l1y_lowest_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("l1y_highest_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("akakce_url", sa.String(1000), nullable=True))

    # --- price_predictions table ---
    recommendation_enum = sa.Enum("AL", "BEKLE", "GUCLU_BEKLE", name="recommendation_enum")
    recommendation_enum.create(op.get_bind(), checkfirst=True)

    direction_enum = sa.Enum("UP", "DOWN", "STABLE", name="predicted_direction_enum")
    direction_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "price_predictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("prediction_date", sa.Date(), nullable=False),
        sa.Column("recommendation", recommendation_enum, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("reasoning", JSONB, nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("current_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("predicted_direction", direction_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Unique constraint: one prediction per product per day
    op.create_index(
        "ix_price_predictions_product_date",
        "price_predictions",
        ["product_id", "prediction_date"],
        unique=True,
    )

    # --- prediction_outcomes table ---
    op.create_table(
        "prediction_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("prediction_id", UUID(as_uuid=True), sa.ForeignKey("price_predictions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("actual_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("outcome_date", sa.Date(), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("error_magnitude", sa.Numeric(8, 4), nullable=True),
        sa.Column("lesson_learned", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- model_parameters table ---
    op.create_table(
        "model_parameters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version", sa.String(50), nullable=False, unique=True),
        sa.Column("parameters", JSONB, nullable=False),
        sa.Column("accuracy_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("total_predictions", sa.Integer(), default=0),
        sa.Column("correct_predictions", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("model_parameters")
    op.drop_table("prediction_outcomes")
    op.drop_index("ix_price_predictions_product_date", table_name="price_predictions")
    op.drop_table("price_predictions")

    op.drop_column("products", "akakce_url")
    op.drop_column("products", "l1y_highest_price")
    op.drop_column("products", "l1y_lowest_price")

    op.drop_column("price_history", "source")

    # Drop enums
    sa.Enum(name="predicted_direction_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="recommendation_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="price_source_enum").drop(op.get_bind(), checkfirst=True)
