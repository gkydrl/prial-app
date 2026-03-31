"""
reasoning_text null/eski format olan mevcut tahminler için açıklama üretir.
Paralel Claude çağrıları ile hızlı çalışır (~2-3 dk / 500 ürün).
"""
from __future__ import annotations

import asyncio
import traceback
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.prediction import PricePrediction
from app.services.prediction.reasoning_generator import generate_reasoning_text

CONCURRENCY = 10  # Paralel Claude çağrısı sayısı


async def _process_single(pred: PricePrediction, semaphore: asyncio.Semaphore) -> tuple[bool, str]:
    """Tek bir prediction için reasoning üret. Kendi DB session'ı açar."""
    async with semaphore:
        try:
            async with AsyncSessionLocal() as db:
                product = await db.get(Product, pred.product_id)
                if not product:
                    return False, f"Ürün bulunamadı: {pred.product_id}"

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

                # Doğrudan update — kendi session'ımız
                pred_obj = await db.get(PricePrediction, pred.id)
                if pred_obj:
                    pred_obj.reasoning_text = reasoning_text
                    await db.commit()

                return True, product.title[:50]
        except Exception as e:
            traceback.print_exc()
            return False, str(e)


async def backfill_reasoning_texts() -> dict:
    """Tüm reasoning_text=null/eski format tahminler için paralel açıklama üret."""
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
        print(f"[reasoning_backfill] {len(predictions)} tahmin için reasoning üretilecek (concurrency={CONCURRENCY})", flush=True)

        if not predictions:
            print("[reasoning_backfill] Güncellenecek tahmin yok.", flush=True)
            return stats

        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [_process_single(pred, semaphore) for pred in predictions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, r in enumerate(results):
            if isinstance(r, Exception):
                stats["errors"] += 1
                print(f"[reasoning_backfill] ✗ Exception: {r}", flush=True)
            elif r[0]:
                stats["updated"] += 1
                if (stats["updated"]) % 20 == 0:
                    print(f"[reasoning_backfill] İlerleme: {stats['updated']}/{stats['total']}", flush=True)
            else:
                stats["errors"] += 1
                print(f"[reasoning_backfill] ✗ {r[1]}", flush=True)

    except Exception as e:
        print(f"[reasoning_backfill] FATAL: {e}", flush=True)
        traceback.print_exc()

    print(f"[reasoning_backfill] Tamamlandı: {stats}", flush=True)
    return stats
