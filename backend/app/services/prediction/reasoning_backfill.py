"""
reasoning_text null olan mevcut tahminler için açıklama üretir.
"""
from __future__ import annotations

import traceback
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.prediction import PricePrediction
from app.services.prediction.reasoning_generator import generate_reasoning_text


async def backfill_reasoning_texts() -> dict:
    """reasoning_text=null veya eski format tahminler için açıklama üret."""
    stats = {"total": 0, "updated": 0, "errors": 0}

    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import func as sa_func
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
                    (PricePrediction.reasoning_text.is_(None))
                    | (~PricePrediction.reasoning_text.startswith("{"))
                )
            )
            predictions = result.scalars().all()
            stats["total"] = len(predictions)
            print(f"[reasoning_backfill] {len(predictions)} tahmin için reasoning üretilecek", flush=True)

            for i, pred in enumerate(predictions):
                try:
                    product = await db.get(Product, pred.product_id)
                    if not product:
                        print(f"[reasoning_backfill] ✗ Ürün bulunamadı: {pred.product_id}", flush=True)
                        continue

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
                    # Her 5 üründe bir commit — partial progress korunur
                    if (i + 1) % 5 == 0:
                        await db.commit()
                        print(f"[reasoning_backfill] Committed {i + 1}/{len(predictions)}", flush=True)
                    stats["updated"] += 1
                    print(f"[reasoning_backfill] ✓ [{i+1}/{len(predictions)}] {product.title[:50]}", flush=True)
                except Exception as e:
                    stats["errors"] += 1
                    print(f"[reasoning_backfill] ✗ Hata: {e}", flush=True)
                    traceback.print_exc()

            await db.commit()
    except Exception as e:
        print(f"[reasoning_backfill] FATAL HATA: {e}", flush=True)
        traceback.print_exc()

    print(f"[reasoning_backfill] Tamamlandı: {stats}", flush=True)
    return stats
