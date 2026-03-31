import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ExchangeRate(Base):
    """Döviz kuru kaydı — USD/TRY, EUR/TRY vb."""

    __tablename__ = "exchange_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    currency_pair: Mapped[str] = mapped_column(String(7), nullable=False)  # "USD/TRY"
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))  # günlük değişim %
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # "tcmb", "exchangerate_api"
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
