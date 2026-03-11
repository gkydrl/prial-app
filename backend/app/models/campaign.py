import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String, DateTime, func, ForeignKey, Numeric, Boolean, Enum, Table, Column,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.product import StoreName
from app.models.promo_code import DiscountType


class StoreAccount(Base):
    __tablename__ = "store_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store: Mapped[StoreName] = mapped_column(
        Enum(StoreName, name="store_name_enum", create_type=False), nullable=False
    )
    company_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="store_account", lazy="noload")


# Many-to-many: campaign <-> products
campaign_products = Table(
    "campaign_products",
    Base.metadata,
    Column("campaign_id", UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("ix_campaigns_store_account_id", "store_account_id"),
        Index("ix_campaigns_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("store_accounts.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="discount_type_enum", create_type=False), nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    target_price_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_price_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    is_unique_codes: Mapped[bool] = mapped_column(Boolean, default=True)
    fixed_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    store_account: Mapped["StoreAccount"] = relationship("StoreAccount", back_populates="campaigns")
    products: Mapped[list["Product"]] = relationship(
        "Product", secondary=campaign_products, lazy="selectin"
    )
    code_pool: Mapped[list["CodePool"]] = relationship("CodePool", back_populates="campaign", lazy="noload")


class CodePool(Base):
    __tablename__ = "code_pool"
    __table_args__ = (
        Index("ix_code_pool_campaign_id", "campaign_id"),
        Index("ix_code_pool_assigned_to", "assigned_to"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="code_pool")


class UserPromoAssignment(Base):
    __tablename__ = "user_promo_assignments"
    __table_args__ = (
        Index("ix_user_promo_user_product", "user_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
