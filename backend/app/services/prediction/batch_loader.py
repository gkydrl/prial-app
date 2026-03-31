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


def _parse_reasoning(reasoning_text: str | None) -> tuple[str | None, list[str] | None, list[str] | None]:
    """reasoning_text JSON string'ini parse et → (summary, pros, cons)"""
    if not reasoning_text:
        return None, None, None
    try:
        data = json.loads(reasoning_text)
        return (
            data.get("summary"),
            data.get("pros"),
            data.get("cons"),
        )
    except (json.JSONDecodeError, TypeError):
        # Eski format: plain text string
        return reasoning_text, None, None


async def attach_predictions(products: list[Product], db: AsyncSession) -> None:
    """
    Tek IN sorgusu ile bugünkü prediction'ları ürünlere ekle.
    Ürün ORM nesnelerine recommendation, reasoning_text, reasoning_pros,
    reasoning_cons, predicted_direction, prediction_confidence attribute'ları eklenir.
    """
    if not products:
        return

    ids = [p.id for p in products]
    today = date.today()

    result = await db.execute(
        select(PricePrediction)
        .where(
            PricePrediction.product_id.in_(ids),
            PricePrediction.prediction_date == today,
        )
    )
    predictions = result.scalars().all()

    # product_id → prediction map
    pred_map = {}
    for pred in predictions:
        pred_map[pred.product_id] = pred

    for product in products:
        pred = pred_map.get(product.id)
        if pred:
            summary, pros, cons = _parse_reasoning(pred.reasoning_text)
            product.recommendation = pred.recommendation.value  # type: ignore[attr-defined]
            product.reasoning_text = summary  # type: ignore[attr-defined]
            product.reasoning_pros = pros  # type: ignore[attr-defined]
            product.reasoning_cons = cons  # type: ignore[attr-defined]
            product.predicted_direction = pred.predicted_direction.value  # type: ignore[attr-defined]
            product.prediction_confidence = float(pred.confidence)  # type: ignore[attr-defined]
        else:
            product.recommendation = None  # type: ignore[attr-defined]
            product.reasoning_text = None  # type: ignore[attr-defined]
            product.reasoning_pros = None  # type: ignore[attr-defined]
            product.reasoning_cons = None  # type: ignore[attr-defined]
            product.predicted_direction = None  # type: ignore[attr-defined]
            product.prediction_confidence = None  # type: ignore[attr-defined]
