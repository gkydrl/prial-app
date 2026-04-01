"""
Self-learning feedback loop.
V2: prediction_targets.target_date bazlı değerlendirme.
Çok seviyeli katsayı ayarlama: category → product → global.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.prediction import (
    PricePrediction, PredictionOutcome, PredictionTarget,
    ModelParameters, CategoryCoefficients, ProductCoefficients,
    Recommendation,
)
from app.services.prediction.predictor import DEFAULT_WEIGHTS


async def evaluate_predictions() -> dict:
    """
    target_date = today olan tahminleri + 7 gün önceki AL tahminlerini değerlendir.
    Her tahmin için outcome kaydet, çok seviyeli katsayı ayarla.
    """
    stats = {"evaluated": 0, "correct": 0, "errors": []}

    async with AsyncSessionLocal() as db:
        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        # 1. target_date = today olan BEKLE/GUCLU_BEKLE tahminleri
        target_result = await db.execute(
            select(PricePrediction)
            .join(PredictionTarget)
            .outerjoin(PredictionOutcome)
            .where(
                PredictionTarget.target_date == today,
                PredictionOutcome.id.is_(None),
            )
        )
        target_predictions = list(target_result.scalars().all())

        # 2. 7 gün önceki AL tahminleri (target_date = null)
        al_result = await db.execute(
            select(PricePrediction)
            .outerjoin(PredictionTarget)
            .outerjoin(PredictionOutcome)
            .where(
                PricePrediction.prediction_date == seven_days_ago,
                PricePrediction.recommendation == Recommendation.AL,
                PredictionOutcome.id.is_(None),
            )
        )
        al_predictions = list(al_result.scalars().all())

        predictions = target_predictions + al_predictions
        if not predictions:
            print("[prediction/evaluator] Değerlendirilecek tahmin yok", flush=True)
            return stats

        print(f"[prediction/evaluator] {len(predictions)} tahmin değerlendirilecek "
              f"({len(target_predictions)} hedefli, {len(al_predictions)} AL)", flush=True)

        error_types = {"missed_buy": 0, "premature_buy": 0, "correct_buy": 0, "correct_wait": 0}
        # Track per-category and per-product errors for multi-level adjustment
        category_errors: dict[str, dict] = defaultdict(lambda: {"missed_buy": 0, "premature_buy": 0, "correct": 0, "total": 0})
        product_errors: dict[str, dict] = defaultdict(lambda: {"missed_buy": 0, "premature_buy": 0, "correct": 0, "total": 0})

        for pred in predictions:
            # Mevcut fiyatı bul
            actual_price = await _get_current_price(pred.product_id, db)
            if actual_price is None:
                continue

            # Hedef fiyatı bul (PredictionTarget varsa)
            target = await _get_prediction_target(pred.id, db)
            expected_price = float(target.expected_price) if target else None

            # Değerlendirme
            was_correct, error_type, lesson = _evaluate_single(
                pred, float(actual_price), expected_price
            )

            # Outcome kaydet
            error_mag = abs(float(actual_price) - float(pred.current_price)) / float(pred.current_price)

            outcome = PredictionOutcome(
                prediction_id=pred.id,
                actual_price=actual_price,
                outcome_date=today,
                was_correct=was_correct,
                error_magnitude=Decimal(str(round(error_mag, 4))),
                lesson_learned=lesson,
            )
            db.add(outcome)

            # PredictionTarget güncelle
            if target:
                target.actual_price_at_target = actual_price
                target.price_hit = was_correct

            stats["evaluated"] += 1
            if was_correct:
                stats["correct"] += 1
            error_types[error_type] = error_types.get(error_type, 0) + 1

            # Per-category / per-product tracking
            product = await db.get(Product, pred.product_id)
            if product:
                cat_key = str(product.category_id) if product.category_id else None
                prod_key = str(pred.product_id)

                if cat_key:
                    category_errors[cat_key]["total"] += 1
                    if was_correct:
                        category_errors[cat_key]["correct"] += 1
                    elif error_type == "missed_buy":
                        category_errors[cat_key]["missed_buy"] += 1
                    elif error_type == "premature_buy":
                        category_errors[cat_key]["premature_buy"] += 1

                product_errors[prod_key]["total"] += 1
                if was_correct:
                    product_errors[prod_key]["correct"] += 1
                elif error_type == "missed_buy":
                    product_errors[prod_key]["missed_buy"] += 1
                elif error_type == "premature_buy":
                    product_errors[prod_key]["premature_buy"] += 1

        # Çok seviyeli katsayı ayarlama
        if stats["evaluated"] > 0:
            await _adjust_multilevel_weights(error_types, category_errors, product_errors, db)

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


async def _get_prediction_target(prediction_id, db: AsyncSession) -> PredictionTarget | None:
    result = await db.execute(
        select(PredictionTarget).where(PredictionTarget.prediction_id == prediction_id)
    )
    return result.scalar_one_or_none()


def _evaluate_single(
    pred: PricePrediction,
    actual_price: float,
    expected_price: float | None = None,
) -> tuple[bool, str, dict]:
    """
    Tek bir tahmini degerlendir.
    AL → doğru eğer fiyat ≥%97 (>3% düşmedi)
    BEKLE/GUCLU_BEKLE → doğru eğer actual ≤ expected × 1.05
    """
    pred_price = float(pred.current_price)
    price_change_pct = ((actual_price - pred_price) / pred_price) * 100 if pred_price > 0 else 0

    lesson = {
        "predicted_price": pred_price,
        "actual_price": actual_price,
        "expected_price": expected_price,
        "price_change_pct": round(price_change_pct, 2),
        "recommendation": pred.recommendation.value,
        "direction": pred.predicted_direction.value,
    }

    # AL dedik — fiyat düştü mü?
    if pred.recommendation == Recommendation.AL:
        if price_change_pct >= 0:
            lesson["verdict"] = "AL doğru — fiyat yükselmeden alındı"
            return True, "correct_buy", lesson
        elif price_change_pct < -3:
            lesson["verdict"] = f"Erken AL — fiyat %{abs(price_change_pct):.1f} düştü"
            return False, "premature_buy", lesson
        else:
            lesson["verdict"] = "AL kabul edilebilir — küçük düşüş"
            return True, "correct_buy", lesson

    # BEKLE/GUCLU_BEKLE — expected_price'a ulaştı mı?
    else:
        if expected_price and actual_price <= expected_price * 1.05:
            lesson["verdict"] = f"BEKLE doğru — fiyat {actual_price:,.0f} TL'ye düştü (beklenen: {expected_price:,.0f} TL)"
            return True, "correct_wait", lesson
        elif price_change_pct <= 0:
            lesson["verdict"] = "BEKLE doğru — fiyat düştü veya sabit"
            return True, "correct_wait", lesson
        elif price_change_pct > 5:
            lesson["verdict"] = f"Kaçırılan AL — fiyat %{price_change_pct:.1f} arttı"
            return False, "missed_buy", lesson
        else:
            lesson["verdict"] = "BEKLE kabul edilebilir — küçük artış"
            return True, "correct_wait", lesson


def _compute_weight_adjustments(error_counts: dict) -> dict | None:
    """
    Hata tiplerine göre ağırlık ayarlama vektörü hesapla.
    Returns None if no adjustments needed.
    """
    total = error_counts.get("total", 0)
    if total < 3:
        return None

    correct = error_counts.get("correct", 0)
    accuracy = correct / total
    if accuracy >= 0.70:
        return None  # %70+ doğru → ayarlama gerekmiyor

    adjustment = 0.02
    adjustments = {}

    if error_counts.get("missed_buy", 0) > 0:
        adjustments["trend"] = adjustment
        adjustments["seasonal"] = -adjustment / 2
        adjustments["volatility"] = -adjustment / 2

    if error_counts.get("premature_buy", 0) > 0:
        adjustments["percentile"] = adjustments.get("percentile", 0) + adjustment
        adjustments["drop_frequency"] = adjustments.get("drop_frequency", 0) + adjustment / 2
        adjustments["upcoming_event"] = adjustments.get("upcoming_event", 0) + adjustment / 2
        adjustments["trend"] = adjustments.get("trend", 0) - adjustment

    return adjustments if adjustments else None


def _apply_adjustments(base_weights: dict, adjustments: dict) -> dict:
    """Ağırlıklara ayarlamaları uygula, normalize et."""
    weights = dict(base_weights)
    for k, delta in adjustments.items():
        weights[k] = weights.get(k, 0.1) + delta

    # Normalize: clamp to [0.05, 1.0], then sum to 1.0
    total = sum(max(0.05, v) for v in weights.values())
    if total > 0:
        weights = {k: max(0.05, v) / total for k, v in weights.items()}
        total = sum(weights.values())
        weights = {k: round(v / total, 4) for k, v in weights.items()}

    return weights


async def _adjust_multilevel_weights(
    global_errors: dict,
    category_errors: dict[str, dict],
    product_errors: dict[str, dict],
    db: AsyncSession,
) -> None:
    """
    Çok seviyeli katsayı ayarlama:
    1. Kategori bazlı: >%30 yanlış → category_coefficients ayarla
    2. Ürün bazlı: >%30 yanlış VE kategori henüz ayarlanmadı → product_coefficients ayarla
    3. Global: genel accuracy <%60 → model_parameters ayarla
    """
    adjusted_categories = set()

    # 1. Kategori bazlı ayarlama
    for cat_id_str, errors in category_errors.items():
        total = errors["total"]
        if total < 3:
            continue
        correct = errors["correct"]
        accuracy = correct / total
        if accuracy < 0.70:
            adjustments = _compute_weight_adjustments(errors)
            if adjustments:
                await _upsert_category_coefficients(cat_id_str, adjustments, errors, db)
                adjusted_categories.add(cat_id_str)

    # 2. Ürün bazlı ayarlama (sadece kategorisi ayarlanmamışsa)
    for prod_id_str, errors in product_errors.items():
        total = errors["total"]
        if total < 3:
            continue
        correct = errors["correct"]
        accuracy = correct / total
        if accuracy < 0.70:
            # Ürünün kategorisi zaten ayarlandıysa skip
            product = await db.get(Product, prod_id_str)
            if product and product.category_id and str(product.category_id) in adjusted_categories:
                continue
            adjustments = _compute_weight_adjustments(errors)
            if adjustments:
                await _upsert_product_coefficients(prod_id_str, adjustments, errors, db)

    # 3. Global ayarlama
    total_eval = sum(global_errors.values())
    correct_total = global_errors.get("correct_buy", 0) + global_errors.get("correct_wait", 0)
    global_accuracy = correct_total / total_eval if total_eval > 0 else 1.0

    if global_accuracy < 0.60:
        await _update_model_weights(global_errors, db)


async def _upsert_category_coefficients(
    category_id_str: str, adjustments: dict, errors: dict, db: AsyncSession
) -> None:
    """Kategori katsayılarını güncelle veya oluştur."""
    cat_id = _uuid.UUID(category_id_str)

    result = await db.execute(
        select(CategoryCoefficients).where(CategoryCoefficients.category_id == cat_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        new_weights = _apply_adjustments(existing.weights, adjustments)
        existing.weights = new_weights
        existing.total_predictions = (existing.total_predictions or 0) + errors["total"]
        existing.correct_predictions = (existing.correct_predictions or 0) + errors["correct"]
        existing.accuracy_score = Decimal(str(round(
            existing.correct_predictions / existing.total_predictions, 4
        ))) if existing.total_predictions > 0 else None
        from datetime import datetime, timezone
        existing.updated_at = datetime.now(timezone.utc)
        print(f"[evaluator] Kategori katsayı güncellendi: {category_id_str[:8]}", flush=True)
    else:
        # Global'den başla
        global_weights, _ = await _get_global_weights(db)
        new_weights = _apply_adjustments(global_weights, adjustments)

        accuracy = errors["correct"] / errors["total"] if errors["total"] > 0 else None
        coeff = CategoryCoefficients(
            category_id=cat_id,
            weights=new_weights,
            accuracy_score=Decimal(str(round(accuracy, 4))) if accuracy else None,
            total_predictions=errors["total"],
            correct_predictions=errors["correct"],
        )
        db.add(coeff)
        print(f"[evaluator] Kategori katsayı oluşturuldu: {category_id_str[:8]}", flush=True)


async def _upsert_product_coefficients(
    product_id_str: str, adjustments: dict, errors: dict, db: AsyncSession
) -> None:
    """Ürün katsayılarını güncelle veya oluştur."""
    prod_id = _uuid.UUID(product_id_str)

    result = await db.execute(
        select(ProductCoefficients).where(ProductCoefficients.product_id == prod_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        new_weights = _apply_adjustments(existing.weights, adjustments)
        existing.weights = new_weights
        existing.total_predictions = (existing.total_predictions or 0) + errors["total"]
        existing.correct_predictions = (existing.correct_predictions or 0) + errors["correct"]
        existing.accuracy_score = Decimal(str(round(
            existing.correct_predictions / existing.total_predictions, 4
        ))) if existing.total_predictions > 0 else None
        from datetime import datetime, timezone
        existing.updated_at = datetime.now(timezone.utc)
        print(f"[evaluator] Ürün katsayı güncellendi: {product_id_str[:8]}", flush=True)
    else:
        global_weights, _ = await _get_global_weights(db)
        new_weights = _apply_adjustments(global_weights, adjustments)

        accuracy = errors["correct"] / errors["total"] if errors["total"] > 0 else None
        coeff = ProductCoefficients(
            product_id=prod_id,
            weights=new_weights,
            accuracy_score=Decimal(str(round(accuracy, 4))) if accuracy else None,
            total_predictions=errors["total"],
            correct_predictions=errors["correct"],
        )
        db.add(coeff)
        print(f"[evaluator] Ürün katsayı oluşturuldu: {product_id_str[:8]}", flush=True)


async def _get_global_weights(db: AsyncSession) -> tuple[dict, str]:
    """Aktif global model parametrelerini getir."""
    result = await db.execute(
        select(ModelParameters)
        .where(ModelParameters.is_active == True)  # noqa: E712
        .order_by(ModelParameters.created_at.desc())
        .limit(1)
    )
    model = result.scalar_one_or_none()
    if model:
        return model.parameters, model.version
    return DEFAULT_WEIGHTS.copy(), "v1.0"


async def _update_model_weights(error_types: dict, db: AsyncSession) -> None:
    """
    Global model ağırlıklarını ayarla. Sadece genel accuracy <%60 olduğunda çağrılır.
    """
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
        active_model.is_active = False
    else:
        weights = DEFAULT_WEIGHTS.copy()
        old_version = "v1.0"

    adjustment = 0.02

    if error_types.get("missed_buy", 0) > 0:
        weights["trend"] = weights.get("trend", 0.20) + adjustment
        weights["seasonal"] = weights.get("seasonal", 0.10) - adjustment / 2
        weights["volatility"] = weights.get("volatility", 0.15) - adjustment / 2

    if error_types.get("premature_buy", 0) > 0:
        weights["percentile"] = weights.get("percentile", 0.25) + adjustment
        weights["drop_frequency"] = weights.get("drop_frequency", 0.12) + adjustment / 2
        weights["upcoming_event"] = weights.get("upcoming_event", 0.15) + adjustment / 2
        weights["trend"] = weights.get("trend", 0.18) - adjustment
        weights["near_historical_low"] = weights.get("near_historical_low", 0.10) - adjustment / 2

    # Normalize
    total = sum(weights.values())
    if total > 0:
        weights = {k: max(0.05, v / total) for k, v in weights.items()}
        total = sum(weights.values())
        weights = {k: round(v / total, 4) for k, v in weights.items()}

    try:
        version_num = int(old_version.replace("v", "").split(".")[1]) + 1
    except (ValueError, IndexError):
        version_num = 2
    new_version = f"v1.{version_num}"

    total_eval = sum(error_types.values())
    correct = error_types.get("correct_buy", 0) + error_types.get("correct_wait", 0)
    accuracy = correct / total_eval if total_eval > 0 else None

    new_model = ModelParameters(
        version=new_version,
        parameters=weights,
        accuracy_score=Decimal(str(round(accuracy, 4))) if accuracy is not None else None,
        total_predictions=total_eval,
        correct_predictions=correct,
        is_active=True,
    )
    db.add(new_model)

    print(f"[prediction/evaluator] Global model güncellendi: {old_version} → {new_version}", flush=True)
    print(f"  Ağırlıklar: {weights}", flush=True)
    if accuracy is not None:
        print(f"  Doğruluk: %{accuracy*100:.1f}", flush=True)


async def get_accuracy_stats(db: AsyncSession) -> dict:
    """Model dogruluk istatistiklerini getir."""
    result = await db.execute(
        select(ModelParameters)
        .where(ModelParameters.is_active == True)  # noqa: E712
        .limit(1)
    )
    active_model = result.scalar_one_or_none()

    total_outcomes = (await db.execute(
        select(func.count(PredictionOutcome.id))
    )).scalar() or 0

    correct_outcomes = (await db.execute(
        select(func.count(PredictionOutcome.id))
        .where(PredictionOutcome.was_correct == True)  # noqa: E712
    )).scalar() or 0

    thirty_days_ago = date.today() - timedelta(days=30)
    recent_predictions = (await db.execute(
        select(func.count(PricePrediction.id))
        .where(PricePrediction.prediction_date >= thirty_days_ago)
    )).scalar() or 0

    # Category coefficients count
    cat_coeff_count = (await db.execute(
        select(func.count(CategoryCoefficients.id))
        .where(CategoryCoefficients.is_active == True)  # noqa: E712
    )).scalar() or 0

    # Product coefficients count
    prod_coeff_count = (await db.execute(
        select(func.count(ProductCoefficients.id))
        .where(ProductCoefficients.is_active == True)  # noqa: E712
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
        "category_coefficients_active": cat_coeff_count,
        "product_coefficients_active": prod_coeff_count,
    }
