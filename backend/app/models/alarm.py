import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, func, ForeignKey, Numeric, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import enum


class AlarmStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    PAUSED = "paused"
    DELETED = "deleted"


class Alarm(Base):
    __tablename__ = "alarms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optionally target a specific store; if null, any store counts
    product_store_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_stores.id", ondelete="SET NULL"), nullable=True
    )

    target_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[AlarmStatus] = mapped_column(
        Enum(AlarmStatus, name="alarm_status_enum"), default=AlarmStatus.ACTIVE, index=True
    )

    # Price when alarm was triggered
    triggered_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="alarms")
    product: Mapped["Product"] = relationship("Product", back_populates="alarms")
    product_store: Mapped["ProductStore | None"] = relationship(
        "ProductStore", back_populates="alarms"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="alarm", lazy="noload"
    )
