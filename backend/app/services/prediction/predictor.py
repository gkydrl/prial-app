"""
Weighted scoring modeli — IYI_FIYAT/FIYAT_DUSEBILIR/FIYAT_YUKSELISTE tahmini.
6 faktor agirlikli skor: percentile, trend, volatility, drop_frequency, seasonal, near_historical_low.
Hierarchical weights: product → category → global (model_parameters).
"""
from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import (
    PricePrediction, ModelParameters, Recommendation, PredictedDirection,
    PredictionTarget, CategoryCoefficients, ProductCoefficients,
)
from app.services.prediction.analyzer import PriceFeatures


# Default weights (self-learning ile guncellenir)
DEFAULT_WEIGHTS = {
    "percentile": 0.25,
    "trend": 0.18,
    "volatility": 0.12,
    "drop_frequency": 0.12,
    "seasonal": 0.08,
    "near_historical_low": 0.10,
    "upcoming_event": 0.15,
}

DEFAULT_VERSION = "v1.0"


@dataclass
class PredictionResult:
    recommendation: Recommendation
    confidence: float  # 0.0 - 1.0
    score: float       # raw score 0.0 - 1.0
    direction: PredictedDirection
    reasoning: dict


async def get_active_weights(db: AsyncSession) -> tuple[dict, str]:
    """Aktif model parametrelerini getir. Yoksa default kullan."""
    result = await db.execute(
        select(ModelParameters)
        .where(ModelParameters.is_active == True)  # noqa: E712
        .order_by(ModelParameters.created_at.desc())
        .limit(1)
    )
    model = result.scalar_one_or_none()

    if model:
        return model.parameters, model.version

    return DEFAULT_WEIGHTS.copy(), DEFAULT_VERSION


async def get_resolved_weights(
    db: AsyncSession,
    product_id: _uuid.UUID | None = None,
    category_id: _uuid.UUID | None = None,
) -> tuple[dict, str]:
    """
    Hiyerarşik katsayı çözümleme: product → category → global.
    En spesifik aktif katsayıyı döner.
    """
    # 1. Product-level
    if product_id:
        result = await db.execute(
            select(ProductCoefficients).where(
                ProductCoefficients.product_id == product_id,
                ProductCoefficients.is_active == True,  # noqa: E712
            )
        )
        pc = result.scalar_one_or_none()
        if pc:
            return pc.weights, f"product:{product_id}"

    # 2. Category-level
    if category_id:
        result = await db.execute(
            select(CategoryCoefficients).where(
                CategoryCoefficients.category_id == category_id,
                CategoryCoefficients.is_active == True,  # noqa: E712
            )
        )
        cc = result.scalar_one_or_none()
        if cc:
            return cc.weights, f"category:{category_id}"

    # 3. Global (model_parameters)
    return await get_active_weights(db)


def compute_wait_days(recommendation: Recommendation, features: PriceFeatures) -> int | None:
    """
    Bekleme süresi hesapla.
    IYI_FIYAT → None (hemen al)
    FIYAT_YUKSELISTE → 30 gün
    FIYAT_DUSEBILIR → event/trend bazlı 1-14 gün
    """
    if recommendation == Recommendation.IYI_FIYAT:
        return None

    if recommendation == Recommendation.FIYAT_YUKSELISTE:
        return 30

    # FIYAT_DUSEBILIR — event ve trend'e göre
    if features.event_details:
        closest_event = features.event_details[0]
        days_to_event = closest_event.get("days_to_start", 999)
        if days_to_event <= 1:
            return 1
        if days_to_event <= 7:
            return 7
        if days_to_event <= 21:
            return 14

    # Güçlü düşüş trendi
    if features.trend_30d is not None and features.trend_30d < -10:
        return 7

    # Normal düşüş trendi
    if features.trend_30d is not None and features.trend_30d < 0:
        return 14

    # Default FIYAT_DUSEBILIR
    return 14


def compute_expected_price(
    current_price: float,
    wait_days: int | None,
    features: PriceFeatures,
) -> float:
    """
    Beklenen fiyat hesapla.
    IYI_FIYAT → current_price (hemen al)
    FIYAT_DUSEBILIR → event/trend/seasonal bazlı indirim tahmini
    Taban: asla l1y_lowest altına düşmez.
    """
    if wait_days is None:
        return current_price

    expected = current_price

    # Event bazlı indirim
    if features.event_details:
        closest_event = features.event_details[0]
        discount_pct = closest_event.get("expected_discount_pct", 0)
        if discount_pct:
            expected = current_price * (1 - discount_pct / 100)
    # Trend bazlı
    elif features.trend_30d is not None and features.trend_30d < 0:
        daily_trend = features.trend_30d / 30 / 100  # %/gün → oran/gün
        expected = current_price * (1 + daily_trend * wait_days)
    # Seasonal
    elif features.seasonal_score is not None and features.seasonal_score > 0:
        expected = current_price * (1 - features.seasonal_score * 0.05)

    # Taban: l1y_lowest altına düşmez
    if features.l1y_min and expected < features.l1y_min:
        expected = features.l1y_min

    return round(expected, 2)


def predict(features: PriceFeatures, weights: dict) -> PredictionResult:
    """
    Feature'lardan IYI_FIYAT/FIYAT_DUSEBILIR/FIYAT_YUKSELISTE tahmini uret.
    Yuksek skor = IYI_FIYAT, dusuk skor = FIYAT_DUSEBILIR (daha da dusebilir).
    """
    scores = {}
    reasoning = {}

    # 1. Percentile (dusukse iyi → skor yuksek)
    if features.percentile is not None:
        s = 1.0 - features.percentile  # Invert: low percentile = high score
        scores["percentile"] = s
        reasoning["percentile"] = {
            "value": round(features.percentile, 3),
            "score": round(s, 3),
            "note": f"Fiyat 1y aralığının %{features.percentile*100:.0f}'inde",
        }
    else:
        scores["percentile"] = 0.5  # Neutral when no data
        reasoning["percentile"] = {"note": "Yeterli veri yok"}

    # 2. Trend (negatif trend = fiyat dusuyor = bekle, pozitif trend = fiyat artiyor = al)
    if features.trend_30d is not None:
        # Positive trend (rising prices) → buy signal
        # Map -20% to +20% range to 0-1
        t = (features.trend_30d + 20) / 40
        t = max(0.0, min(1.0, t))
        scores["trend"] = t
        reasoning["trend"] = {
            "trend_7d": round(features.trend_7d, 2) if features.trend_7d else None,
            "trend_30d": round(features.trend_30d, 2),
            "score": round(t, 3),
            "note": f"30g trend: %{features.trend_30d:+.1f}",
        }
    else:
        scores["trend"] = 0.5
        reasoning["trend"] = {"note": "Yeterli veri yok"}

    # 3. Volatility (yuksek volatilite = daha cok dalgalanma = bekle)
    if features.volatility_30d is not None:
        # High volatility → might drop more → lower buy score
        v = 1.0 - min(1.0, features.volatility_30d * 5)  # CV of 0.20 → score 0.0
        scores["volatility"] = max(0.0, v)
        reasoning["volatility"] = {
            "value": round(features.volatility_30d, 4),
            "score": round(max(0.0, v), 3),
            "note": f"30g volatilite: {features.volatility_30d:.3f}",
        }
    else:
        scores["volatility"] = 0.5
        reasoning["volatility"] = {"note": "Yeterli veri yok"}

    # 4. Drop frequency (sik dusuyorsa = bekle)
    if features.drop_frequency is not None:
        # Many drops → price tends to drop → wait
        d = 1.0 - min(1.0, features.drop_frequency / 12)  # 12+ drops/year → 0
        scores["drop_frequency"] = max(0.0, d)
        reasoning["drop_frequency"] = {
            "value": features.drop_frequency,
            "score": round(max(0.0, d), 3),
            "note": f"Yılda {features.drop_frequency} kez >%5 düşüş",
        }
    else:
        scores["drop_frequency"] = 0.5
        reasoning["drop_frequency"] = {"note": "Yeterli veri yok"}

    # 5. Seasonal (bu ay normalde ucuzsa = al, pahaliysa = bekle)
    if features.seasonal_score is not None:
        # Negative seasonal = this month is cheaper than avg → buy
        s = (1.0 - features.seasonal_score) / 2  # Map -1..1 to 1..0
        scores["seasonal"] = max(0.0, min(1.0, s))
        reasoning["seasonal"] = {
            "value": round(features.seasonal_score, 3),
            "score": round(max(0.0, min(1.0, s)), 3),
            "note": f"Mevsimsel skor: {features.seasonal_score:+.2f}",
        }
    else:
        scores["seasonal"] = 0.5
        reasoning["seasonal"] = {"note": "Yeterli veri yok"}

    # 6. Near historical low (tarihsel dusuge yakinsa = guclu AL sinyali)
    if features.near_historical_low:
        scores["near_historical_low"] = 1.0
        reasoning["near_historical_low"] = {
            "score": 1.0,
            "note": "1y en düşüğe %5 yakın — güçlü İyi Fiyat sinyali",
        }
    else:
        scores["near_historical_low"] = 0.0
        reasoning["near_historical_low"] = {
            "score": 0.0,
            "note": "Tarihi düşükten uzak",
        }

    # 7. Upcoming event (yaklasan ozel gun/indirim donemi)
    if features.event_score < 0:
        # Negatif event_score = yaklasan indirim = BEKLE sinyali → dusuk buy score
        ev_score = 1.0 + features.event_score  # -1.0 → 0.0, 0.0 → 1.0
        scores["upcoming_event"] = max(0.0, ev_score)
        event_names = [e["name"] for e in features.event_details[:3]]
        reasoning["upcoming_event"] = {
            "event_score": features.event_score,
            "score": round(max(0.0, ev_score), 3),
            "events": event_names,
            "note": f"Yaklaşan etkinlik: {', '.join(event_names)}" if event_names else "Yaklaşan etkinlik var",
        }
    else:
        scores["upcoming_event"] = 0.5  # Neutral — no upcoming events
        reasoning["upcoming_event"] = {
            "event_score": 0.0,
            "score": 0.5,
            "note": "3 hafta içinde özel gün yok",
        }

    # Weighted total score
    total_score = sum(scores[k] * weights.get(k, 0) for k in scores)
    total_weight = sum(weights.get(k, 0) for k in scores)
    if total_weight > 0:
        total_score /= total_weight
    total_score = max(0.0, min(1.0, total_score))

    # Recommendation
    if total_score >= 0.65:
        rec = Recommendation.IYI_FIYAT
    elif total_score <= 0.30:
        rec = Recommendation.FIYAT_YUKSELISTE
    else:
        rec = Recommendation.FIYAT_DUSEBILIR

    # Predicted direction based on trend
    if features.trend_7d is not None:
        if features.trend_7d > 2:
            direction = PredictedDirection.UP
        elif features.trend_7d < -2:
            direction = PredictedDirection.DOWN
        else:
            direction = PredictedDirection.STABLE
    else:
        direction = PredictedDirection.STABLE

    # Confidence: higher when score is far from thresholds
    confidence = abs(total_score - 0.475) * 2  # 0-1 scale, max at extremes
    confidence = min(1.0, max(0.1, confidence))

    reasoning["_summary"] = {
        "total_score": round(total_score, 4),
        "recommendation": rec.value,
        "confidence": round(confidence, 4),
        "weights_version": "from_model",
    }

    return PredictionResult(
        recommendation=rec,
        confidence=confidence,
        score=total_score,
        direction=direction,
        reasoning=reasoning,
    )


async def predict_and_save(
    product_id,
    current_price: float,
    features: PriceFeatures,
    db: AsyncSession,
    category_id: _uuid.UUID | None = None,
) -> PricePrediction:
    """Tahmin uret, PredictionTarget ile birlikte DB'ye kaydet."""
    weights, version = await get_resolved_weights(db, product_id, category_id)
    result = predict(features, weights)

    prediction = PricePrediction(
        product_id=product_id,
        prediction_date=date.today(),
        recommendation=result.recommendation,
        confidence=Decimal(str(round(result.confidence, 4))),
        reasoning=result.reasoning,
        model_version=version,
        current_price=Decimal(str(round(current_price, 2))),
        predicted_direction=result.direction,
    )
    db.add(prediction)
    await db.flush()  # prediction.id'yi set et — autoflush'tan önce

    # wait_days: önce önceki prediction'ın target_date'inden countdown hesapla
    wait_days = await _countdown_or_compute(product_id, result.recommendation, features, db)
    expected_price = compute_expected_price(current_price, wait_days, features)

    target = PredictionTarget(
        prediction_id=prediction.id,
        wait_days=wait_days,
        expected_price=Decimal(str(expected_price)),
        target_date=date.today() + timedelta(days=wait_days) if wait_days else None,
    )
    db.add(target)

    # Attach to prediction for downstream use
    prediction._wait_days = wait_days
    prediction._expected_price = expected_price

    return prediction


async def _countdown_or_compute(
    product_id,
    recommendation: Recommendation,
    features: PriceFeatures,
    db: AsyncSession,
) -> int | None:
    """
    Önceki prediction'ın target_date'i varsa kalan günü countdown yap.
    Yoksa veya target geçmişse yeni wait_days hesapla.
    """
    if recommendation == Recommendation.IYI_FIYAT:
        return None

    today = date.today()

    # Dünkü (veya son 7 gündeki) prediction'ın target'ını bul
    result = await db.execute(
        select(PredictionTarget.target_date)
        .join(PricePrediction)
        .where(
            PricePrediction.product_id == product_id,
            PricePrediction.prediction_date >= today - timedelta(days=7),
            PricePrediction.prediction_date < today,
            PredictionTarget.target_date.isnot(None),
        )
        .order_by(PricePrediction.prediction_date.desc())
        .limit(1)
    )
    prev_target_date = result.scalar_one_or_none()

    if prev_target_date and prev_target_date > today:
        remaining = (prev_target_date - today).days
        if remaining > 0:
            return remaining

    # Önceki target yok veya geçmiş → yeni hesapla
    return compute_wait_days(recommendation, features)
