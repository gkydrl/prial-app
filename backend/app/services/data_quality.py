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

        # ── 8. Spike tespiti: Son 7 günde %200+ fiyat artışı ──
        spike_count = 0
        recent_history = await db.execute(
            select(
                PriceHistory.product_store_id,
                PriceHistory.price,
                PriceHistory.recorded_at,
            )
            .where(PriceHistory.recorded_at >= seven_days_ago)
            .order_by(PriceHistory.product_store_id, PriceHistory.recorded_at)
        )
        rows = recent_history.all()
        # Gruplama: ardışık kayıtlar arasında spike ara
        prev_row = None
        for row in rows:
            if prev_row and prev_row[0] == row[0]:  # Aynı store
                old_p, new_p = prev_row[1], row[1]
                if old_p and old_p > 0 and new_p and new_p > old_p * 3:
                    spike_count += 1
            prev_row = row

        report["price_spikes_7d"] = {"count": spike_count}

        # ── 9. Veri boşluğu: 7+ gündür yeni kayıt olmayan aktif store'lar ──
        active_store_ids = await db.execute(
            select(ProductStore.id).where(
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.current_price.isnot(None),
            )
        )
        active_ids = [r[0] for r in active_store_ids.all()]

        if active_ids:
            stores_with_recent = await db.execute(
                select(func.distinct(PriceHistory.product_store_id))
                .where(
                    PriceHistory.product_store_id.in_(active_ids),
                    PriceHistory.recorded_at >= seven_days_ago,
                )
            )
            recent_store_ids = {r[0] for r in stores_with_recent.all()}
            data_gap_count = len([sid for sid in active_ids if sid not in recent_store_ids])
        else:
            data_gap_count = 0

        report["data_gaps_7d"] = {"count": data_gap_count}

        # ── 10. Fiyat tutarsızlığı: Aynı ürünün store'ları arasında 5x+ fark ──
        from collections import defaultdict
        product_prices: dict[str, list[float]] = defaultdict(list)
        store_prices_result = await db.execute(
            select(ProductStore.product_id, ProductStore.current_price)
            .where(
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.current_price.isnot(None),
                ProductStore.current_price > 0,
            )
        )
        for pid, price in store_prices_result.all():
            product_prices[pid].append(float(price))

        inconsistency_count = 0
        for pid, prices_list in product_prices.items():
            if len(prices_list) < 2:
                continue
            if max(prices_list) / min(prices_list) >= 5:
                inconsistency_count += 1

        report["price_inconsistency"] = {"count": inconsistency_count}

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
    if report["price_spikes_7d"]["count"] > 10:
        issues.append(f"Son 7 günde {report['price_spikes_7d']['count']} fiyat spike'ı tespit edildi")
    if report["data_gaps_7d"]["count"] > 50:
        issues.append(f"7+ gün veri boşluğu olan store: {report['data_gaps_7d']['count']}")
    if report["price_inconsistency"]["count"] > 10:
        issues.append(f"Fiyat tutarsızlığı olan ürün: {report['price_inconsistency']['count']}")

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
