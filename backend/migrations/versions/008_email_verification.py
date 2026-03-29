"""add email verification columns and mark existing users as verified

Revision ID: 008
Revises: 007
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Check if columns already exist (may have been added outside alembic)
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'verification_code'"
    ))
    if not result.fetchone():
        op.add_column("users", sa.Column("verification_code", sa.String(6), nullable=True))
        op.add_column("users", sa.Column("verification_code_expires", sa.DateTime(timezone=True), nullable=True))
    # Mark all existing users as verified so they're not locked out
    op.execute("UPDATE users SET is_verified = true WHERE is_verified = false")


def downgrade() -> None:
    op.drop_column("users", "verification_code_expires")
    op.drop_column("users", "verification_code")
