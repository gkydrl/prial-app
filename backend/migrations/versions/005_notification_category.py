"""add category and product_id to notifications

Revision ID: 005
Revises: 004
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

notification_category_enum = sa.Enum(
    "target_reached", "price_drop", "milestone", "daily_summary", "weekly_summary",
    name="notification_category_enum",
)


def upgrade() -> None:
    notification_category_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "notifications",
        sa.Column("category", notification_category_enum, nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("product_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_notifications_category", "notifications", ["category"])
    op.create_index("ix_notifications_product_id", "notifications", ["product_id"])
    op.create_foreign_key(
        "fk_notifications_product_id",
        "notifications",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_notifications_product_id", "notifications", type_="foreignkey")
    op.drop_index("ix_notifications_product_id", table_name="notifications")
    op.drop_index("ix_notifications_category", table_name="notifications")
    op.drop_column("notifications", "product_id")
    op.drop_column("notifications", "category")
    notification_category_enum.drop(op.get_bind(), checkfirst=True)
