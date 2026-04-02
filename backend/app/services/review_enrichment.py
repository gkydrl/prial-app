"""
Günlük review enrichment pipeline.
Ürünlerin Trendyol/Hepsiburada review'lerini çeker,
keyword filtreden geçirir ve product.review_summary JSONB'ye yazar.

Günde 500 ürün → ~15 günde full cycle (yorumlar yavaş değişir).
Concurrency: 5, delay: 1s
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore, StoreName
from app.services.review_fetcher import (
    fetch_trendyol_reviews,
    fetch_hepsiburada_reviews,
)
from app.services.review_analyzer import analyze_reviews


async def enrich_reviews_daily(batch_size: int = 500) -> dict:
    """
    review_summary NULL veya eski (>7 gün) olan ürünleri seç,
    her ürünün store'larından yorum çek, filtrele ve JSONB'ye kaydet.
    """
    stats = {"total": 0, "ok": 0, "skipped": 0, "error": 0}
    semaphore = asyncio.Semaphore(5)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    # Ürünleri seç: review_summary NULL veya eski
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product.id)
            .where(
                Product.id.in_(
                    select(ProductStore.product_id).distinct()
                ),
                or_(
                    Product.review_summary.is_(None),
                    Product.review_summary["updated_at"].astext < seven_days_ago.isoformat(),
                ),
            )
            .limit(batch_size)
        )
        product_ids = [row[0] for row in result.all()]

    total = len(product_ids)
    print(f"[review_enrichment] {total} ürün için review çekilecek", flush=True)

    processed = 0

    async def _process_one(product_id):
        nonlocal processed
        async with semaphore:
            try:
                async with AsyncSessionLocal() as db:
                    product = await db.get(Product, product_id)
                    if not product:
                        stats["skipped"] += 1
                        return

                    # Ürünün store'larını çek
                    store_result = await db.execute(
                        select(ProductStore).where(
                            ProductStore.product_id == product_id,
                            ProductStore.is_active == True,  # noqa: E712
                        )
                    )
                    stores = store_result.scalars().all()

                    review_data = {}

                    for store in stores:
                        if store.store == StoreName.TRENDYOL:
                            review = await fetch_trendyol_reviews(
                                store_product_id=store.store_product_id,
                                product_title=product.title,
                                product_url=store.url,
                                max_reviews=25,
                            )
                        elif store.store == StoreName.HEPSIBURADA:
                            review = await fetch_hepsiburada_reviews(
                                store_product_id=store.store_product_id,
                                product_title=product.title,
                                product_url=store.url,
                                max_reviews=25,
                            )
                        else:
                            continue

                        if review.status != "ok":
                            continue

                        # Keyword filter + sentiment
                        analysis = analyze_reviews(
                            reviews=review.sample_reviews or [],
                            product_title=product.title,
                            store=store.store.value,
                            highlight_limit=5,
                            lowlight_limit=3,
                        )

                        store_key = store.store.value.lower()
                        review_data[store_key] = {
                            "rating": review.rating,
                            "count": review.review_count,
                            "samples": analysis.sample_relevant[:3],
                            "highlights": analysis.highlights,
                            "lowlights": analysis.lowlights,
                            "sentiment": {
                                "positive": analysis.positive_count,
                                "negative": analysis.negative_count,
                                "neutral": analysis.neutral_count,
                            },
                        }

                    if review_data:
                        review_data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        product.review_summary = review_data
                        stats["ok"] += 1
                    else:
                        stats["skipped"] += 1

                    stats["total"] += 1
                    await db.commit()

            except Exception as e:
                print(f"[review_enrichment] Hata (product_id={product_id}): {e}", flush=True)
                stats["error"] += 1

            finally:
                processed += 1
                if processed % 50 == 0:
                    print(f"[review_enrichment] İlerleme: {processed}/{total} — {stats}", flush=True)

            # Rate limiting
            await asyncio.sleep(1.0)

    tasks = [_process_one(pid) for pid in product_ids]
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"[review_enrichment] Tamamlandı: {stats}", flush=True)
    return stats
