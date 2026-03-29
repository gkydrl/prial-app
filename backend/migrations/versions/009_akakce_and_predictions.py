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


def _enum_exists(conn, name: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = :name"
    ), {"name": name})
    return result.fetchone() is not None


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table, "column": column})
    return result.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table AND table_schema = 'public'"
    ), {"table": table})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # --- price_history: source column ---
    if not _enum_exists(conn, "price_source_enum"):
        op.execute("CREATE TYPE price_source_enum AS ENUM ('own_scrape', 'akakce_import', 'cimri_import')")

    if not _column_exists(conn, "price_history", "source"):
        op.add_column(
            "price_history",
            sa.Column("source", sa.Enum("own_scrape", "akakce_import", "cimri_import", name="price_source_enum"),
                       nullable=True, server_default="own_scrape"),
        )
        op.execute("UPDATE price_history SET source = 'own_scrape' WHERE source IS NULL")
        op.alter_column("price_history", "source", nullable=False)

    # --- products: akakce columns ---
    if not _column_exists(conn, "products", "l1y_lowest_price"):
        op.add_column("products", sa.Column("l1y_lowest_price", sa.Numeric(12, 2), nullable=True))
    if not _column_exists(conn, "products", "l1y_highest_price"):
        op.add_column("products", sa.Column("l1y_highest_price", sa.Numeric(12, 2), nullable=True))
    if not _column_exists(conn, "products", "akakce_url"):
        op.add_column("products", sa.Column("akakce_url", sa.String(1000), nullable=True))

    # --- Enums for prediction tables ---
    if not _enum_exists(conn, "recommendation_enum"):
        op.execute("CREATE TYPE recommendation_enum AS ENUM ('AL', 'BEKLE', 'GUCLU_BEKLE')")
    if not _enum_exists(conn, "predicted_direction_enum"):
        op.execute("CREATE TYPE predicted_direction_enum AS ENUM ('UP', 'DOWN', 'STABLE')")

    # --- price_predictions table ---
    if not _table_exists(conn, "price_predictions"):
        op.create_table(
            "price_predictions",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("prediction_date", sa.Date(), nullable=False),
            sa.Column("recommendation", sa.Enum("AL", "BEKLE", "GUCLU_BEKLE", name="recommendation_enum", create_type=False), nullable=False),
            sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
            sa.Column("reasoning", JSONB, nullable=True),
            sa.Column("model_version", sa.String(50), nullable=False),
            sa.Column("current_price", sa.Numeric(12, 2), nullable=False),
            sa.Column("predicted_direction", sa.Enum("UP", "DOWN", "STABLE", name="predicted_direction_enum", create_type=False), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_price_predictions_product_date",
            "price_predictions",
            ["product_id", "prediction_date"],
            unique=True,
        )

    # --- prediction_outcomes table ---
    if not _table_exists(conn, "prediction_outcomes"):
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
    if not _table_exists(conn, "model_parameters"):
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

    op.execute("DROP TYPE IF EXISTS predicted_direction_enum")
    op.execute("DROP TYPE IF EXISTS recommendation_enum")
    op.execute("DROP TYPE IF EXISTS price_source_enum")
