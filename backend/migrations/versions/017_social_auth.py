"""social auth: add auth_provider, provider_id, has_completed_consent; make password_hash nullable

Revision ID: 017
Revises: 016
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("auth_provider", sa.String(20), nullable=True))
    op.add_column("users", sa.Column("provider_id", sa.String(255), nullable=True))
    op.add_column(
        "users",
        sa.Column("has_completed_consent", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index(
        "ix_users_auth_provider_provider_id",
        "users",
        ["auth_provider", "provider_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_auth_provider_provider_id", table_name="users")
    op.drop_column("users", "has_completed_consent")
    op.drop_column("users", "provider_id")
    op.drop_column("users", "auth_provider")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
