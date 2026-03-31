"""add pipeline_runs table and scraper_budget tracking

Revision ID: 013
Revises: 012
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pipeline monitoring tablosu
    op.create_table(
        "pipeline_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_name", sa.String(100), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("stats", JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("credits_used", sa.Integer(), nullable=True),
    )

    # Index: son çalışmaları hızlı çekmek için
    op.create_index("ix_pipeline_runs_started_at", "pipeline_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_started_at")
    op.drop_table("pipeline_runs")
