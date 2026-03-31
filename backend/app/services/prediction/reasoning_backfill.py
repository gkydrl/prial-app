"""
reasoning_text null olan mevcut tahminler için açıklama üretir.
"""
from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.prediction import PricePrediction
from app.services.prediction.reasoning_generator import generate_reasoning_text


async def backfill_reasoning_texts() -> dict:
    """Bugünkü reasoning_text=null tahminler için Claude ile açıklama üret."""
    stats = {"total": 0, "updated": 0, "errors": 0}

    async with AsyncSessionLocal() as db:
        # reasoning_text null olan en son tahminleri getir (her ürün için 1 tane)
        from sqlalchemy import func as sa_func
        # En son prediction_date her ürün için
        subq = (
            select(
                PricePrediction.product_id,
                sa_func.max(PricePrediction.prediction_date).label("max_date"),
            )
            .group_by(PricePrediction.product_id)
            .subquery()
        )
        result = await db.execute(
            select(PricePrediction)
            .join(
                subq,
                (PricePrediction.product_id == subq.c.product_id)
                & (PricePrediction.prediction_date == subq.c.max_date),
            )
            .where(
                # null veya eski format (JSON olmayan) olanları güncelle
                (PricePrediction.reasoning_text.is_(None))
                | (~PricePrediction.reasoning_text.startswith("{"))
            )
        )
        predictions = result.scalars().all()
        stats["total"] = len(predictions)
        print(f"[reasoning_backfill] {len(predictions)} tahmin için reasoning üretilecek", flush=True)

        for pred in predictions:
            try:
                # Ürün bilgilerini getir
                product = await db.get(Product, pred.product_id)
                if not product:
                    continue

                # Mevcut en düşük fiyatı bul
                price_result = await db.execute(
                    select(func.min(ProductStore.current_price))
                    .where(
                        ProductStore.product_id == product.id,
                        ProductStore.is_active == True,  # noqa: E712
                        ProductStore.in_stock == True,    # noqa: E712
                        ProductStore.current_price.isnot(None),
                    )
                )
                current_price = price_result.scalar_one_or_none()
                if not current_price:
                    current_price = pred.current_price

                reasoning_text = await generate_reasoning_text(
                    product_title=product.title,
                    recommendation=pred.recommendation.value,
                    confidence=float(pred.confidence),
                    current_price=float(current_price),
                    reasoning=pred.reasoning or {},
                    l1y_lowest=float(product.l1y_lowest_price) if product.l1y_lowest_price else None,
                    l1y_highest=float(product.l1y_highest_price) if product.l1y_highest_price else None,
                    predicted_direction=pred.predicted_direction.value,
                )
                pred.reasoning_text = reasoning_text
                stats["updated"] += 1
                print(f"[reasoning_backfill] ✓ {product.title[:40]}", flush=True)
            except Exception as e:
                stats["errors"] += 1
                print(f"[reasoning_backfill] ✗ Hata: {e}", flush=True)

        await db.commit()

    print(f"[reasoning_backfill] Tamamlandı: {stats}", flush=True)
    return stats
