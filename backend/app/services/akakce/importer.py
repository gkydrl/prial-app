"""
Akakce import orchestrator.
Her Prial urunu icin Akakce'de arama, fiyat gecmisi cekme, DB'ye kayit.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory, PriceSource
from app.services.akakce.browser import random_delay, close_browser
from app.services.akakce.searcher import find_akakce_url
from app.services.akakce.chart_extractor import extract_price_history, PriceDataPoint


async def import_product_history(
    product: Product,
    db: AsyncSession,
) -> dict:
    """
    Tek bir urun icin Akakce fiyat gecmisini ceker ve kaydeder.
    Returns: {"status": "ok"|"no_match"|"no_data"|"error", "data_points": int}
    """
    try:
        # 1. akakce_url cache'i var mi?
        akakce_url = product.akakce_url
        if not akakce_url:
            akakce_url = await find_akakce_url(product.title, product.brand)
            if not akakce_url:
                return {"status": "no_match", "data_points": 0}
            # Cache the URL
            product.akakce_url = akakce_url
            await db.flush()
            await random_delay()

        # 2. Fiyat gecmisini cek
        data_points = await extract_price_history(akakce_url)
        if not data_points:
            return {"status": "no_data", "data_points": 0}

        # 3. Product'a ait bir store bul (kayit icin product_store_id gerekli)
        store = await _get_or_create_akakce_store(product, db)
        if not store:
            return {"status": "no_store", "data_points": 0}

        # 4. Price history kaydet
        saved = await _save_price_points(store.id, data_points, db)

        # 5. l1y istatistiklerini guncelle
        prices = [dp.price for dp in data_points]
        product.l1y_lowest_price = Decimal(str(min(prices)))
        product.l1y_highest_price = Decimal(str(max(prices)))

        await db.flush()
        return {"status": "ok", "data_points": saved}

    except Exception as e:
        print(f"[akakce/importer] Hata ({product.title[:50]}): {e}", flush=True)
        return {"status": "error", "data_points": 0, "error": str(e)}


async def _get_or_create_akakce_store(
    product: Product, db: AsyncSession
) -> ProductStore | None:
    """
    Urunun mevcut bir store'unu doner.
    Yoksa akakce_url ile yeni bir store olusturur.
    """
    # Mevcut store var mi?
    result = await db.execute(
        select(ProductStore)
        .where(ProductStore.product_id == product.id)
        .where(ProductStore.is_active == True)  # noqa: E712
        .limit(1)
    )
    store = result.scalar_one_or_none()
    if store:
        return store

    # Akakce URL varsa yeni store olustur
    if product.akakce_url:
        from app.models.product import StoreName
        store = ProductStore(
            product_id=product.id,
            store=StoreName.OTHER,
            url=product.akakce_url,
            is_active=True,
            check_priority=3,  # LOW — sadece akakce veri kaynagi
        )
        db.add(store)
        await db.flush()
        return store

    return None


async def _save_price_points(
    product_store_id: uuid.UUID,
    data_points: list[PriceDataPoint],
    db: AsyncSession,
) -> int:
    """Price data point'lerini price_history'ye kaydet. Returns: kayit sayisi."""
    saved = 0
    for dp in data_points:
        # Ayni tarihte ayni store icin kayit var mi kontrol et
        existing = await db.execute(
            select(PriceHistory.id).where(
                PriceHistory.product_store_id == product_store_id,
                func.date(PriceHistory.recorded_at) == dp.date,
                PriceHistory.source == "akakce_import",
            )
        )
        if existing.scalar_one_or_none():
            continue

        record = PriceHistory(
            product_store_id=product_store_id,
            price=Decimal(str(dp.price)),
            currency="TRY",
            in_stock=True,
            source="akakce_import",
            recorded_at=datetime(dp.date.year, dp.date.month, dp.date.day, tzinfo=timezone.utc),
        )
        db.add(record)
        saved += 1

    return saved


async def bulk_import(batch_size: int = 50, only_new: bool = True) -> dict:
    """
    Toplu Akakce import. Scheduler veya admin endpoint'inden cagrilir.
    only_new=True: sadece akakce_url'si olmayan urunler
    only_new=False: tum urunler (guncelleme)
    Returns: {"total": N, "ok": N, "no_match": N, ...}
    """
    stats = {"total": 0, "ok": 0, "no_match": 0, "no_data": 0, "error": 0}

    async with AsyncSessionLocal() as db:
        # Hedef urunleri sec
        query = select(Product)
        if only_new:
            query = query.where(Product.akakce_url.is_(None))
        query = query.order_by(Product.created_at.desc()).limit(batch_size)

        result = await db.execute(query)
        products = result.scalars().all()

        print(f"[akakce/importer] {len(products)} ürün işlenecek (batch={batch_size})", flush=True)

        for i, product in enumerate(products):
            stats["total"] += 1
            print(f"[akakce/importer] [{i+1}/{len(products)}] {product.brand} {product.title[:40]}", flush=True)

            result = await import_product_history(product, db)
            status = result["status"]
            stats[status] = stats.get(status, 0) + 1

            if result["data_points"] > 0:
                print(f"  → {result['data_points']} data point kaydedildi", flush=True)

            # Commit after each product to avoid long transactions
            await db.commit()

            # Rate limiting between products
            await random_delay(3.0, 6.0)

    # Cleanup
    await close_browser()

    print(f"[akakce/importer] Tamamlandı: {stats}", flush=True)
    return stats


async def daily_enrichment(batch_size: int = 20) -> dict:
    """
    Mevcut akakce eslesmeleri guncelle — yeni fiyat verileri cek.
    Scheduler'dan her gun 05:00'da cagrilir.
    """
    stats = {"total": 0, "ok": 0, "no_data": 0, "error": 0}

    async with AsyncSessionLocal() as db:
        query = (
            select(Product)
            .where(Product.akakce_url.isnot(None))
            .order_by(func.random())
            .limit(batch_size)
        )
        result = await db.execute(query)
        products = result.scalars().all()

        print(f"[akakce/enrichment] {len(products)} ürün güncellenecek", flush=True)

        for i, product in enumerate(products):
            stats["total"] += 1
            result = await import_product_history(product, db)
            status = result["status"]
            stats[status] = stats.get(status, 0) + 1
            await db.commit()
            await random_delay(3.0, 6.0)

    await close_browser()
    print(f"[akakce/enrichment] Tamamlandı: {stats}", flush=True)
    return stats
