import uuid
import enum
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


class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


# Many-to-many association table
promo_code_products = Table(
    "promo_code_products",
    Base.metadata,
    Column("promo_code_id", UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
)


class PromoCode(Base):
    __tablename__ = "promo_codes"
    __table_args__ = (
        Index("ix_promo_codes_expires_at", "expires_at"),
        Index("ix_promo_codes_store", "store"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="discount_type_enum", create_type=False,
             values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    store: Mapped[StoreName | None] = mapped_column(
        Enum(StoreName, name="store_name_enum", create_type=False), nullable=True
    )
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", secondary=promo_code_products, lazy="selectin"
    )
