"""
Akakce eşleşme doğrulama servisi.
Her ürünün akakce_url'inden taze chart verisi çeker, DB'deki fiyatlarla karşılaştırır.
Yanlış eşleşmeleri tespit eder, düzeltir ve raporlar.

Günlük pipeline'da 07:30'da çalışır.

Doğrulama mantığı:
1. Akakce'den taze fiyat çek (chart_extractor)
2. DB'deki own_scrape fiyatlarıyla karşılaştır
3. Akakce median vs own_scrape/current_price karşılaştır
4. 5x+ fark → yanlış eşleşme → akakce_url'yi sıfırla, hatalı kayıtları sil
5. Rapor üret
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory


# Eşik değerler
MISMATCH_THRESHOLD = 5.0   # Akakce median vs gerçek fiyat 5x+ fark → yanlış eşleşme
BATCH_SIZE = 50             # Aynı anda kaç ürün kontrol edilsin
CONCURRENCY = 5             # Eşzamanlı Akakce istek sayısı
DAILY_LIMIT = 200           # Günlük kontrol edilecek max ürün


async def verify_akakce_matches(
    limit: int = DAILY_LIMIT,
    fix: bool = True,
) -> dict:
    """
    Akakce eşleşmelerini doğrula.

    Args:
        limit: Kontrol edilecek ürün sayısı
        fix: True ise yanlış eşleşmeleri otomatik düzelt

    Returns:
        İstatistik raporu
    """
    from app.services.akakce.chart_extractor import extract_price_history

    stats = {
        "checked": 0,
        "ok": 0,
        "mismatch": 0,
        "no_chart_data": 0,
        "no_reference_price": 0,
        "error": 0,
        "fixed": 0,
        "records_deleted": 0,
        "mismatched_products": [],
    }

    semaphore = asyncio.Semaphore(CONCURRENCY)

    # Ürünleri seç: akakce_url'si olan, son 30 günde kontrol edilmemiş
    async with AsyncSessionLocal() as db:
        # Öncelik: alarm_count yüksek + son kontrol tarihi eski
        query = (
            select(Product.id, Product.title, Product.brand, Product.akakce_url)
            .where(
                Product.akakce_url.isnot(None),
                Product.akakce_url != "",
            )
            .order_by(
                # Henüz hiç doğrulanmamışlar önce, sonra alarm_count'a göre
                Product.alarm_count.desc(),
            )
            .limit(limit)
        )
        result = await db.execute(query)
        products = result.all()

    total = len(products)
    print(f"[akakce/verify] {total} ürün doğrulanacak", flush=True)

    async def _verify_one(product_row):
        product_id, title, brand, akakce_url = product_row

        async with semaphore:
            try:
                stats["checked"] += 1

                # 1. Akakce'den taze chart verisi çek
                chart_data = await extract_price_history(akakce_url)

                if not chart_data:
                    stats["no_chart_data"] += 1
                    return

                # 2. Akakce fiyat aralığını hesapla
                akakce_prices = sorted([dp.price for dp in chart_data if dp.price > 0])
                if not akakce_prices:
                    stats["no_chart_data"] += 1
                    return

                akakce_median = akakce_prices[len(akakce_prices) // 2]

                # 3. Referans fiyat: own_scrape veya current_price
                async with AsyncSessionLocal() as db:
                    # own_scrape median
                    store_ids_result = await db.execute(
                        select(ProductStore.id).where(
                            ProductStore.product_id == product_id,
                            ProductStore.is_active == True,  # noqa: E712
                        )
                    )
                    store_ids = [r[0] for r in store_ids_result.all()]

                    reference_price = None

                    if store_ids:
                        # own_scrape fiyatları
                        scrape_result = await db.execute(
                            select(PriceHistory.price)
                            .where(
                                PriceHistory.product_store_id.in_(store_ids),
                                PriceHistory.source == "own_scrape",
                                PriceHistory.price > 0,
                            )
                        )
                        scrape_prices = [float(r[0]) for r in scrape_result.all()]
                        if scrape_prices:
                            scrape_prices.sort()
                            reference_price = scrape_prices[len(scrape_prices) // 2]

                        # Fallback: current_price
                        if reference_price is None:
                            cp_result = await db.execute(
                                select(ProductStore.current_price)
                                .where(
                                    ProductStore.product_id == product_id,
                                    ProductStore.is_active == True,  # noqa: E712
                                    ProductStore.current_price.isnot(None),
                                    ProductStore.current_price > 0,
                                )
                                .order_by(ProductStore.current_price)
                                .limit(1)
                            )
                            cp_row = cp_result.first()
                            if cp_row:
                                reference_price = float(cp_row[0])

                if reference_price is None:
                    stats["no_reference_price"] += 1
                    return

                # 4. Karşılaştır
                ratio = max(akakce_median, reference_price) / max(min(akakce_median, reference_price), 0.01)

                if ratio >= MISMATCH_THRESHOLD:
                    # YANLIŞ EŞLEŞME
                    stats["mismatch"] += 1
                    mismatch_info = {
                        "product_id": str(product_id)[:8],
                        "title": title[:50],
                        "akakce_url": akakce_url,
                        "akakce_median": round(akakce_median, 2),
                        "reference_price": round(reference_price, 2),
                        "ratio": round(ratio, 1),
                    }
                    stats["mismatched_products"].append(mismatch_info)

                    print(
                        f"[akakce/verify] YANLIŞ EŞLEŞME: {title[:40]} | "
                        f"akakce: {akakce_median:,.0f} vs gerçek: {reference_price:,.0f} ({ratio:.1f}x)",
                        flush=True,
                    )

                    if fix:
                        await _fix_mismatch(product_id, store_ids, stats)
                else:
                    stats["ok"] += 1

            except Exception as e:
                stats["error"] += 1
                print(f"[akakce/verify] Hata ({title[:30]}): {e}", flush=True)

            # Rate limiting
            await asyncio.sleep(random.uniform(0.5, 1.5))

    # Concurrent doğrulama
    tasks = [_verify_one(p) for p in products]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Rapor özeti (mismatched_products listesini kısalt)
    if len(stats["mismatched_products"]) > 20:
        stats["mismatched_products"] = stats["mismatched_products"][:20]
        stats["mismatched_products_truncated"] = True

    print(
        f"[akakce/verify] Tamamlandı: {stats['checked']} kontrol, "
        f"{stats['ok']} OK, {stats['mismatch']} yanlış eşleşme, "
        f"{stats['fixed']} düzeltildi, {stats['records_deleted']} kayıt silindi",
        flush=True,
    )

    return stats


async def _fix_mismatch(
    product_id,
    store_ids: list,
    stats: dict,
) -> None:
    """
    Yanlış Akakce eşleşmesini düzelt:
    1. O ürünün akakce_import kaynaklı price_history kayıtlarını sil
    2. akakce_url'yi sıfırla (bir sonraki enrichment'ta yeniden aranacak)
    3. l1y istatistiklerini yeniden hesapla
    """
    async with AsyncSessionLocal() as db:
        # 1. Hatalı akakce_import kayıtlarını sil
        if store_ids:
            del_result = await db.execute(
                delete(PriceHistory).where(
                    PriceHistory.product_store_id.in_(store_ids),
                    PriceHistory.source == "akakce_import",
                )
            )
            deleted = del_result.rowcount
            stats["records_deleted"] += deleted

        # 2. akakce_url'yi sıfırla
        product = await db.get(Product, product_id)
        if product:
            product.akakce_url = None

            # 3. l1y'yi yeniden hesapla (kalan own_scrape verilerinden)
            if store_ids:
                one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
                remaining = await db.execute(
                    select(PriceHistory.price)
                    .where(
                        PriceHistory.product_store_id.in_(store_ids),
                        PriceHistory.recorded_at >= one_year_ago,
                        PriceHistory.price > 0,
                    )
                )
                prices = sorted([float(r[0]) for r in remaining.all()])
                if prices:
                    product.l1y_lowest_price = Decimal(str(min(prices)))
                    product.l1y_highest_price = Decimal(str(max(prices)))
                else:
                    product.l1y_lowest_price = None
                    product.l1y_highest_price = None

        await db.commit()
        stats["fixed"] += 1


async def run_daily_verification() -> dict:
    """Günlük pipeline'dan çağrılacak wrapper."""
    return await verify_akakce_matches(limit=DAILY_LIMIT, fix=True)
