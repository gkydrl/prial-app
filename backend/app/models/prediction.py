import uuid
import enum
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    String, Text, DateTime, Date, func, ForeignKey, Numeric, Boolean, Integer, Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Recommendation(str, enum.Enum):
    AL = "AL"
    BEKLE = "BEKLE"
    GUCLU_BEKLE = "GUCLU_BEKLE"


class PredictedDirection(str, enum.Enum):
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class PricePrediction(Base):
    __tablename__ = "price_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prediction_date: Mapped[date] = mapped_column(Date(), nullable=False)
    recommendation: Mapped[Recommendation] = mapped_column(
        Enum(
            Recommendation,
            name="recommendation_enum",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    reasoning: Mapped[dict | None] = mapped_column(JSONB)
    reasoning_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    predicted_direction: Mapped[PredictedDirection] = mapped_column(
        Enum(
            PredictedDirection,
            name="predicted_direction_enum",
            create_type=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="noload")
    outcome: Mapped["PredictionOutcome | None"] = relationship(
        "PredictionOutcome", back_populates="prediction", uselist=False, lazy="noload"
    )


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("price_predictions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    actual_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    outcome_date: Mapped[date] = mapped_column(Date(), nullable=False)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_magnitude: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    lesson_learned: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    prediction: Mapped["PricePrediction"] = relationship(
        "PricePrediction", back_populates="outcome"
    )


class ModelParameters(Base):
    __tablename__ = "model_parameters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    accuracy_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    correct_predictions: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
