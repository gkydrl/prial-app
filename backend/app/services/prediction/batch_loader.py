"""
Batch prediction loader — N+1 sorgusu olmadan ürün listelerine
bugünkü tahminleri ekler.
"""
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.prediction import PricePrediction
from app.models.category import Category


def _parse_reasoning(reasoning_text: str | None) -> tuple[str | None, list[str] | None, list[str] | None]:
    """
    reasoning_text parse et → (summary, pros, cons)
    Desteklenen formatlar:
    - V2: düz paragraf string → (paragraf, None, None)
    - V1: JSON string {"summary": ..., "pros": [...], "cons": [...]} → (summary, pros, cons)
    """
    if not reasoning_text:
        return None, None, None
    try:
        data = json.loads(reasoning_text)
        if isinstance(data, dict) and ("pros" in data or "cons" in data):
            return (
                data.get("summary"),
                data.get("pros"),
                data.get("cons"),
            )
        # JSON but not our format — treat as plain text
        return reasoning_text, None, None
    except (json.JSONDecodeError, TypeError):
        # V2 format: plain text paragraph
        return reasoning_text, None, None


async def attach_predictions(products: list[Product], db: AsyncSession) -> None:
    """
    Tek IN sorgusu ile bugünkü prediction'ları ve kategori slug'larını ürünlere ekle.
    """
    if not products:
        return

    ids = [p.id for p in products]
    today = date.today()

    # Predictions — bugünkü yoksa son 7 günün en güncelini al
    result = await db.execute(
        select(PricePrediction)
        .where(
            PricePrediction.product_id.in_(ids),
            PricePrediction.prediction_date == today,
        )
    )
    predictions = result.scalars().all()
    pred_map = {pred.product_id: pred for pred in predictions}

    # Bugün prediction'ı olmayan ürünler için son 7 güne bak
    missing_ids = [pid for pid in ids if pid not in pred_map]
    if missing_ids:
        from datetime import timedelta
        seven_days_ago = today - timedelta(days=7)
        fallback_result = await db.execute(
            select(PricePrediction)
            .where(
                PricePrediction.product_id.in_(missing_ids),
                PricePrediction.prediction_date >= seven_days_ago,
                PricePrediction.prediction_date < today,
            )
            .order_by(PricePrediction.prediction_date.desc())
        )
        for pred in fallback_result.scalars().all():
            if pred.product_id not in pred_map:
                pred_map[pred.product_id] = pred

    # Category slugs — tek sorgu ile tüm gerekli kategorileri çek
    cat_ids = list({p.category_id for p in products if p.category_id})
    cat_slug_map: dict = {}
    if cat_ids:
        cat_result = await db.execute(
            select(Category.id, Category.slug).where(Category.id.in_(cat_ids))
        )
        cat_slug_map = {row[0]: row[1] for row in cat_result.all()}

    for product in products:
        # Category slug
        product.category_slug = cat_slug_map.get(product.category_id) if product.category_id else None  # type: ignore[attr-defined]

        # Prediction
        pred = pred_map.get(product.id)
        if pred:
            summary, pros, cons = _parse_reasoning(pred.reasoning_text)
            product.recommendation = pred.recommendation.value if pred.recommendation else None  # type: ignore[attr-defined]
            product.reasoning_text = summary  # type: ignore[attr-defined]
            product.reasoning_pros = pros  # type: ignore[attr-defined]
            product.reasoning_cons = cons  # type: ignore[attr-defined]
            product.predicted_direction = pred.predicted_direction.value if pred.predicted_direction else None  # type: ignore[attr-defined]
            product.prediction_confidence = float(pred.confidence) if pred.confidence is not None else None  # type: ignore[attr-defined]
        else:
            product.recommendation = None  # type: ignore[attr-defined]
            product.reasoning_text = None  # type: ignore[attr-defined]
            product.reasoning_pros = None  # type: ignore[attr-defined]
            product.reasoning_cons = None  # type: ignore[attr-defined]
            product.predicted_direction = None  # type: ignore[attr-defined]
            product.prediction_confidence = None  # type: ignore[attr-defined]
