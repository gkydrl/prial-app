"""
Self-learning feedback loop.
7 gun onceki tahminleri gercek fiyatla karsilastirir, model agirliklarini ayarlar.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory
from app.models.prediction import (
    PricePrediction, PredictionOutcome, ModelParameters,
    Recommendation, PredictedDirection,
)
from app.services.prediction.predictor import DEFAULT_WEIGHTS


async def evaluate_predictions() -> dict:
    """
    7 gun onceki tahminleri gercek fiyatla karsilastir.
    Her tahmin icin outcome kaydet, model agirliklarini guncelle.
    Returns: {"evaluated": N, "correct": N, "accuracy": float}
    """
    stats = {"evaluated": 0, "correct": 0, "errors": []}

    async with AsyncSessionLocal() as db:
        target_date = date.today() - timedelta(days=7)

        # 7 gun onceki tahminleri al (henuz outcome'u olmayanlar)
        result = await db.execute(
            select(PricePrediction)
            .outerjoin(PredictionOutcome)
            .where(
                PricePrediction.prediction_date == target_date,
                PredictionOutcome.id.is_(None),  # No outcome yet
            )
        )
        predictions = result.scalars().all()

        if not predictions:
            print("[prediction/evaluator] Değerlendirilecek tahmin yok", flush=True)
            return stats

        print(f"[prediction/evaluator] {len(predictions)} tahmin değerlendirilecek", flush=True)

        error_types = {"missed_buy": 0, "premature_buy": 0, "correct_buy": 0, "correct_wait": 0}

        for pred in predictions:
            # Mevcut fiyati bul
            actual_price = await _get_current_price(pred.product_id, db)
            if actual_price is None:
                continue

            # Degerlendirme
            was_correct, error_type, lesson = _evaluate_single(
                pred, float(actual_price)
            )

            # Outcome kaydet
            error_mag = abs(float(actual_price) - float(pred.current_price)) / float(pred.current_price)

            outcome = PredictionOutcome(
                prediction_id=pred.id,
                actual_price=actual_price,
                outcome_date=date.today(),
                was_correct=was_correct,
                error_magnitude=Decimal(str(round(error_mag, 4))),
                lesson_learned=lesson,
            )
            db.add(outcome)

            stats["evaluated"] += 1
            if was_correct:
                stats["correct"] += 1
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # Model agirliklarini guncelle
        if stats["evaluated"] > 0:
            await _update_model_weights(error_types, db)

        await db.commit()

    stats["accuracy"] = stats["correct"] / stats["evaluated"] if stats["evaluated"] > 0 else 0
    stats["error_types"] = error_types
    print(f"[prediction/evaluator] Sonuç: {stats}", flush=True)
    return stats


async def _get_current_price(product_id, db: AsyncSession) -> Decimal | None:
    """Urunun mevcut en ucuz fiyatini getir."""
    result = await db.execute(
        select(func.min(ProductStore.current_price))
        .where(
            ProductStore.product_id == product_id,
            ProductStore.is_active == True,  # noqa: E712
            ProductStore.in_stock == True,   # noqa: E712
            ProductStore.current_price.isnot(None),
        )
    )
    return result.scalar_one_or_none()


def _evaluate_single(
    pred: PricePrediction,
    actual_price: float,
) -> tuple[bool, str, dict]:
    """
    Tek bir tahmini degerlendir.
    Returns: (was_correct, error_type, lesson_learned)
    """
    pred_price = float(pred.current_price)
    price_change_pct = ((actual_price - pred_price) / pred_price) * 100 if pred_price > 0 else 0

    lesson = {
        "predicted_price": pred_price,
        "actual_price": actual_price,
        "price_change_pct": round(price_change_pct, 2),
        "recommendation": pred.recommendation.value,
        "direction": pred.predicted_direction.value,
    }

    # AL dedik — fiyat dustu mu?
    if pred.recommendation == Recommendation.AL:
        if price_change_pct >= 0:
            # Fiyat yukseldi veya ayni kaldi → AL dogru
            lesson["verdict"] = "AL doğru — fiyat yükselmeden alındı"
            return True, "correct_buy", lesson
        elif price_change_pct < -3:
            # Fiyat %3'den fazla dustu → premature buy
            lesson["verdict"] = f"Erken AL — fiyat %{abs(price_change_pct):.1f} düştü"
            lesson["affected_factor"] = "percentile"
            return False, "premature_buy", lesson
        else:
            # Minor drop <3% → acceptable
            lesson["verdict"] = "AL kabul edilebilir — küçük düşüş"
            return True, "correct_buy", lesson

    # BEKLE/GUCLU_BEKLE dedik — fiyat yukseldi mi?
    else:
        if price_change_pct <= 0:
            # Fiyat dustu veya ayni kaldi → BEKLE dogru
            lesson["verdict"] = "BEKLE doğru — fiyat düştü veya sabit"
            return True, "correct_wait", lesson
        elif price_change_pct > 5:
            # Fiyat %5'den fazla artti → missed buy
            lesson["verdict"] = f"Kaçırılan AL — fiyat %{price_change_pct:.1f} arttı"
            lesson["affected_factor"] = "trend"
            return False, "missed_buy", lesson
        else:
            # Minor increase <5% → acceptable
            lesson["verdict"] = "BEKLE kabul edilebilir — küçük artış"
            return True, "correct_wait", lesson


async def _update_model_weights(error_types: dict, db: AsyncSession) -> None:
    """
    Hata tiplerine gore model agirliklarini ayarla.
    missed_buy → trend agirligini artir
    premature_buy → percentile agirligini artir
    """
    # Aktif modeli al
    result = await db.execute(
        select(ModelParameters)
        .where(ModelParameters.is_active == True)  # noqa: E712
        .order_by(ModelParameters.created_at.desc())
        .limit(1)
    )
    active_model = result.scalar_one_or_none()

    if active_model:
        weights = dict(active_model.parameters)
        old_version = active_model.version
        # Deactivate old model
        active_model.is_active = False
    else:
        weights = DEFAULT_WEIGHTS.copy()
        old_version = "v1.0"

    adjustment = 0.02  # %2 ayarlama

    # missed_buy: BEKLE dedik ama fiyat yukseldi → trend agirligini artir
    if error_types.get("missed_buy", 0) > 0:
        weights["trend"] = weights.get("trend", 0.20) + adjustment
        weights["seasonal"] = weights.get("seasonal", 0.10) - adjustment / 2
        weights["volatility"] = weights.get("volatility", 0.15) - adjustment / 2

    # premature_buy: AL dedik ama fiyat dustu → percentile/drop_freq/event agirligini artir
    if error_types.get("premature_buy", 0) > 0:
        weights["percentile"] = weights.get("percentile", 0.25) + adjustment
        weights["drop_frequency"] = weights.get("drop_frequency", 0.12) + adjustment / 2
        weights["upcoming_event"] = weights.get("upcoming_event", 0.15) + adjustment / 2
        weights["trend"] = weights.get("trend", 0.18) - adjustment
        weights["near_historical_low"] = weights.get("near_historical_low", 0.10) - adjustment / 2

    # Normalize weights to sum = 1.0
    total = sum(weights.values())
    if total > 0:
        weights = {k: max(0.05, v / total) for k, v in weights.items()}
        # Re-normalize after clamping
        total = sum(weights.values())
        weights = {k: round(v / total, 4) for k, v in weights.items()}

    # Yeni versiyon numarasi
    try:
        version_num = int(old_version.replace("v", "").split(".")[1]) + 1
    except (ValueError, IndexError):
        version_num = 2
    new_version = f"v1.{version_num}"

    # Accuracy hesapla
    total_eval = sum(error_types.values())
    correct = error_types.get("correct_buy", 0) + error_types.get("correct_wait", 0)
    accuracy = correct / total_eval if total_eval > 0 else None

    # Yeni model kaydet
    new_model = ModelParameters(
        version=new_version,
        parameters=weights,
        accuracy_score=Decimal(str(round(accuracy, 4))) if accuracy is not None else None,
        total_predictions=total_eval,
        correct_predictions=correct,
        is_active=True,
    )
    db.add(new_model)

    print(f"[prediction/evaluator] Model güncellendi: {old_version} → {new_version}", flush=True)
    print(f"  Ağırlıklar: {weights}", flush=True)
    if accuracy is not None:
        print(f"  Doğruluk: %{accuracy*100:.1f}", flush=True)


async def get_accuracy_stats(db: AsyncSession) -> dict:
    """Model dogruluk istatistiklerini getir."""
    # Aktif model
    result = await db.execute(
        select(ModelParameters)
        .where(ModelParameters.is_active == True)  # noqa: E712
        .limit(1)
    )
    active_model = result.scalar_one_or_none()

    # Toplam outcome sayilari
    total_outcomes = (await db.execute(
        select(func.count(PredictionOutcome.id))
    )).scalar() or 0

    correct_outcomes = (await db.execute(
        select(func.count(PredictionOutcome.id))
        .where(PredictionOutcome.was_correct == True)  # noqa: E712
    )).scalar() or 0

    # Son 30 gun tahmin sayisi
    thirty_days_ago = date.today() - timedelta(days=30)
    recent_predictions = (await db.execute(
        select(func.count(PricePrediction.id))
        .where(PricePrediction.prediction_date >= thirty_days_ago)
    )).scalar() or 0

    return {
        "active_model": {
            "version": active_model.version if active_model else DEFAULT_WEIGHTS,
            "weights": active_model.parameters if active_model else DEFAULT_WEIGHTS,
            "accuracy": float(active_model.accuracy_score) if active_model and active_model.accuracy_score else None,
        },
        "total_outcomes": total_outcomes,
        "correct_outcomes": correct_outcomes,
        "overall_accuracy": correct_outcomes / total_outcomes if total_outcomes > 0 else None,
        "recent_predictions_30d": recent_predictions,
    }
