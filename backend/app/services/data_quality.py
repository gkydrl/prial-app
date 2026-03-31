"""
Günlük veri kalitesi kontrolü.
Gece pipeline'ı bittikten sonra (08:00) çalışır.
Sorunları tespit eder, kırık URL'leri deaktive eder, rapor üretir.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore, StoreName
from app.models.price_history import PriceHistory
from app.models.prediction import PricePrediction


async def run_data_quality_check() -> dict:
    """
    Kapsamlı veri kalitesi kontrolü.
    Sonuç pipeline_runs tablosuna stats olarak kaydedilir.
    """
    report = {}

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # ── 1. Genel sayılar ──
        total_products = await _count(db, select(func.count(Product.id)))
        total_stores = await _count(db, select(func.count(ProductStore.id)).where(ProductStore.is_active == True))
        akakce_matched = await _count(db, select(func.count(Product.id)).where(Product.akakce_url.isnot(None)))

        report["totals"] = {
            "products": total_products,
            "active_stores": total_stores,
            "akakce_matched": akakce_matched,
            "akakce_coverage_pct": round(akakce_matched / total_products * 100, 1) if total_products else 0,
        }

        # ── 2. Fiyatsız ürünler ──
        no_price = await _count(db, select(func.count(Product.id)).where(
            Product.daily_lowest_price.is_(None),
            Product.akakce_url.isnot(None),
        ))
        report["no_price"] = {"count": no_price}

        # ── 3. Eski review'ler ──
        stale_reviews = await _count(db, select(func.count(Product.id)).where(
            or_(
                Product.review_summary.is_(None),
                Product.review_summary["updated_at"].astext < thirty_days_ago.strftime("%Y-%m-%d"),
            ),
            Product.id.in_(select(ProductStore.product_id).distinct()),
        ))
        report["stale_reviews"] = {"count": stale_reviews}

        # ── 4. Kırık URL'ler (3+ gündür kontrol edilememiş) ──
        three_days_ago = now - timedelta(days=3)
        broken_stores_result = await db.execute(
            select(ProductStore).where(
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.last_checked_at < three_days_ago,
                ProductStore.current_price.is_(None),
            )
        )
        broken_stores = broken_stores_result.scalars().all()
        broken_count = len(broken_stores)

        # Oto-deaktive: 7+ gündür fiyatsız store'ları deaktive et
        deactivated = 0
        for store in broken_stores:
            if store.last_checked_at and store.last_checked_at < seven_days_ago:
                store.is_active = False
                deactivated += 1

        if deactivated > 0:
            await db.commit()
            print(f"[data_quality] {deactivated} kırık store deaktive edildi", flush=True)

        report["broken_stores"] = {
            "count": broken_count,
            "auto_deactivated": deactivated,
        }

        # ── 5. Prediction coverage ──
        today = datetime.now(timezone.utc).date()
        products_with_stores = await _count(db, select(func.count(func.distinct(ProductStore.product_id))))
        predictions_today = await _count(db, select(func.count(PricePrediction.id)).where(
            PricePrediction.prediction_date == today,
        ))

        report["prediction_coverage"] = {
            "products_with_stores": products_with_stores,
            "predictions_today": predictions_today,
            "coverage_pct": round(predictions_today / products_with_stores * 100, 1) if products_with_stores else 0,
        }

        # ── 6. Scrape başarı oranı (son 24 saat) ──
        yesterday = now - timedelta(hours=24)
        checked_stores = await _count(db, select(func.count(ProductStore.id)).where(
            ProductStore.last_checked_at >= yesterday,
        ))
        checked_with_price = await _count(db, select(func.count(ProductStore.id)).where(
            ProductStore.last_checked_at >= yesterday,
            ProductStore.current_price.isnot(None),
            ProductStore.current_price > 0,
        ))

        report["scrape_health"] = {
            "checked_last_24h": checked_stores,
            "with_valid_price": checked_with_price,
            "success_rate_pct": round(checked_with_price / checked_stores * 100, 1) if checked_stores else 0,
        }

        # ── 7. Store dağılımı ──
        store_dist_result = await db.execute(
            select(ProductStore.store, func.count())
            .where(ProductStore.is_active == True)  # noqa: E712
            .group_by(ProductStore.store)
        )
        report["store_distribution"] = {
            row[0].value: row[1] for row in store_dist_result.all()
        }

    # ── Genel sağlık skoru ──
    issues = []
    if report["no_price"]["count"] > total_products * 0.1:
        issues.append(f"Fiyatsız ürün oranı yüksek: {report['no_price']['count']}")
    if report["prediction_coverage"]["coverage_pct"] < 50:
        issues.append(f"Prediction coverage düşük: %{report['prediction_coverage']['coverage_pct']}")
    if report["scrape_health"]["success_rate_pct"] < 80:
        issues.append(f"Scrape başarı oranı düşük: %{report['scrape_health']['success_rate_pct']}")
    if report["broken_stores"]["count"] > 50:
        issues.append(f"Kırık store sayısı yüksek: {report['broken_stores']['count']}")

    report["health"] = {
        "status": "healthy" if not issues else "degraded",
        "issues": issues,
    }

    print(f"[data_quality] Kontrol tamamlandı: {report['health']['status']} | "
          f"Sorunlar: {len(issues)}", flush=True)

    return report


async def _count(db: AsyncSession, query) -> int:
    """Tek bir count sorgusunu çalıştırır."""
    result = await db.execute(query)
    return result.scalar() or 0
