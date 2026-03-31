"""
Batch prediction loader — N+1 sorgusu olmadan ürün listelerine
bugünkü tahminleri ekler.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.prediction import PricePrediction


async def attach_predictions(products: list[Product], db: AsyncSession) -> None:
    """
    Tek IN sorgusu ile bugünkü prediction'ları ürünlere ekle.
    Ürün ORM nesnelerine recommendation, reasoning_text, predicted_direction,
    prediction_confidence attribute'ları eklenir.
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
            product.recommendation = pred.recommendation.value  # type: ignore[attr-defined]
            product.reasoning_text = pred.reasoning_text  # type: ignore[attr-defined]
            product.predicted_direction = pred.predicted_direction.value  # type: ignore[attr-defined]
            product.prediction_confidence = float(pred.confidence)  # type: ignore[attr-defined]
        else:
            product.recommendation = None  # type: ignore[attr-defined]
            product.reasoning_text = None  # type: ignore[attr-defined]
            product.predicted_direction = None  # type: ignore[attr-defined]
            product.prediction_confidence = None  # type: ignore[attr-defined]
