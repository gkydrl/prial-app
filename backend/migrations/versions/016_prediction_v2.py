"""prediction v2: category/product coefficients + prediction targets

Revision ID: 016
Revises: 015
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "category_coefficients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("weights", JSONB, nullable=False),
        sa.Column("accuracy_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("total_predictions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("correct_predictions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "product_coefficients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("weights", JSONB, nullable=False),
        sa.Column("accuracy_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("total_predictions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("correct_predictions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "prediction_targets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("prediction_id", UUID(as_uuid=True), sa.ForeignKey("price_predictions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("wait_days", sa.Integer, nullable=True),
        sa.Column("expected_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("actual_price_at_target", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_hit", sa.Boolean, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_prediction_targets_target_date", "prediction_targets", ["target_date"])


def downgrade() -> None:
    op.drop_index("ix_prediction_targets_target_date", table_name="prediction_targets")
    op.drop_table("prediction_targets")
    op.drop_table("product_coefficients")
    op.drop_table("category_coefficients")
