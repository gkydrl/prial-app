import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, func, ForeignKey, Numeric, Boolean, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


class StoreName(str, enum.Enum):
    TRENDYOL = "trendyol"
    HEPSIBURADA = "hepsiburada"
    AMAZON = "amazon"
    N11 = "n11"
    CICEKSEPETI = "ciceksepeti"
    MEDIAMARKT = "mediamarkt"
    TEKNOSA = "teknosa"
    VATAN = "vatan"
    OTHER = "other"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(String(2000))
    image_url: Mapped[str | None] = mapped_column(String(500))

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    # Aggregate stats (denormalized for performance)
    lowest_price_ever: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    alarm_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    category: Mapped["Category | None"] = relationship("Category", back_populates="products")
    stores: Mapped[list["ProductStore"]] = relationship(
        "ProductStore", back_populates="product", lazy="selectin"
    )
    alarms: Mapped[list["Alarm"]] = relationship("Alarm", back_populates="product", lazy="noload")


class ProductStore(Base):
    """A product listed on a specific store with its own URL and price."""

    __tablename__ = "product_stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    store: Mapped[StoreName] = mapped_column(
        Enum(StoreName, name="store_name_enum"), nullable=False
    )
    store_product_id: Mapped[str | None] = mapped_column(String(255))  # store's own product ID
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)

    current_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    original_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))  # before discount
    currency: Mapped[str] = mapped_column(String(3), default="TRY")
    discount_percent: Mapped[int | None] = mapped_column(Integer)

    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # still being scraped

    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="stores")
    price_history: Mapped[list["PriceHistory"]] = relationship(
        "PriceHistory", back_populates="product_store", lazy="noload"
    )
    alarms: Mapped[list["Alarm"]] = relationship(
        "Alarm", back_populates="product_store", lazy="noload"
    )
