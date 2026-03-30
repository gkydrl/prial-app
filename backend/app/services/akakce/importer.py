"""
Price history import orchestrator.
Her Prial urunu icin Akakce'de arama, bulunamazsa Epey'de arama,
fiyat gecmisi cekme, DB'ye kayit.
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory, PriceSource
from app.services.akakce.searcher import find_akakce_url
from app.services.akakce.chart_extractor import extract_price_history, PriceDataPoint


async def random_delay(min_sec: float = 3.0, max_sec: float = 6.0) -> None:
    """Rate limiting icin rastgele bekleme."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


# ── Jenerik / kategori sayfası ürünlerini atla ──
_JUNK_PATTERNS = [
    "fiyat", "modelleri", "ekipman", "çeşitleri",
    "2. el", "yenilenmiş",
]


def _is_junk_product(title: str) -> bool:
    """Kategori/arama sayfası olan ürünleri filtreler."""
    t = title.lower()
    if any(p in t for p in _JUNK_PATTERNS):
        return True
    # Çok kısa veya jenerik (ör. "IPS Monitör", "Lg Monitör")
    words = title.split()
    if len(words) <= 2 and not any(c.isdigit() for c in title):
        return True
    return False


# ── Brand title'a gömülü ise ayıkla ──
_KNOWN_BRANDS = [
    "Samsung", "Apple", "Sony", "LG", "Xiaomi", "Huawei", "Oppo",
    "Lenovo", "Dell", "Asus", "Acer", "HP", "MSI", "Monster",
    "Bosch", "Siemens", "Arçelik", "Beko", "Philips", "Dyson",
    "Marshall", "JBL", "Sonos", "Canon", "Nikon", "Fujifilm",
    "Qpart", "Casper", "TCL", "Hisense", "Vestel", "Grundig",
    "Seagate", "Sandisk", "Beats", "BenQ", "Bose", "Devialet",
    "Ecovacs", "Garmin", "GoPro", "KitchenAid", "Roborock",
    "Robotist", "Sennheiser",
]


def _extract_brand_from_title(title: str) -> tuple[str | None, str]:
    """
    'SamsungGalaxy S24...' → ('Samsung', 'Galaxy S24...')
    Title'ın başında boşluksuz brand varsa ayırır.
    """
    for brand in _KNOWN_BRANDS:
        if title.startswith(brand) and len(title) > len(brand):
            rest = title[len(brand):]
            # Brand'dan sonra büyük harf veya rakam geliyorsa gömülü demektir
            if rest[0].isupper() or rest[0].isdigit():
                return brand, rest
    return None, title


async def import_product_history(
    product: Product,
    db: AsyncSession,
) -> dict:
    """
    Tek bir urun icin Akakce fiyat gecmisini ceker ve kaydeder.
    Returns: {"status": "ok"|"no_match"|"no_data"|"error", "data_points": int}
    """
    try:
        # 0. Jenerik/kategori ürünlerini atla
        if _is_junk_product(product.title):
            return {"status": "skipped", "data_points": 0}

        # 0b. Brand title'a gömülüyse ayıkla
        title = product.title
        brand = product.brand
        if not brand:
            extracted_brand, cleaned_title = _extract_brand_from_title(title)
            if extracted_brand:
                brand = extracted_brand
                title = cleaned_title
                product.brand = brand
                product.title = cleaned_title
                await db.flush()

        # 1. akakce_url cache'i var mi?
        akakce_url = product.akakce_url
        if not akakce_url:
            akakce_url = await find_akakce_url(title, brand)
            if akakce_url:
                product.akakce_url = akakce_url
                await db.flush()

        # 2. Akakce'den fiyat gecmisini cek
        data_points = []
        source = "akakce_import"
        if akakce_url:
            data_points = await extract_price_history(akakce_url)

        # 3. Akakce'de bulunamadiysa Epey'de dene
        if not data_points:
            from app.services.epey.scraper import find_epey_url, extract_price_history as epey_extract

            epey_url, epey_id = await find_epey_url(product.title, product.brand)
            if epey_url:
                epey_points = await epey_extract(epey_url, epey_id)
                if epey_points:
                    # Convert EpeyPricePoint to PriceDataPoint
                    data_points = [
                        PriceDataPoint(date=p.date, price=p.price)
                        for p in epey_points
                    ]
                    source = "akakce_import"  # Reuse existing source enum
                    if not akakce_url:
                        # Epey URL'sini akakce_url alanina kaydet (genel "karsilastirma URL" olarak)
                        product.akakce_url = epey_url
                        await db.flush()

        if not data_points:
            if not akakce_url:
                return {"status": "no_match", "data_points": 0}
            return {"status": "no_data", "data_points": 0}

        # 4. Product'a ait bir store bul (kayit icin product_store_id gerekli)
        store = await _get_or_create_akakce_store(product, db)
        if not store:
            return {"status": "no_store", "data_points": 0}

        # 5. Price history kaydet
        saved = await _save_price_points(store.id, data_points, db, source=source)

        # 6. l1y istatistiklerini guncelle
        prices = [dp.price for dp in data_points]
        product.l1y_lowest_price = Decimal(str(min(prices)))
        product.l1y_highest_price = Decimal(str(max(prices)))

        await db.flush()
        return {"status": "ok", "data_points": saved}

    except Exception as e:
        print(f"[importer] Hata ({product.title[:50]}): {e}", flush=True)
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
    source: str = "akakce_import",
) -> int:
    """Price data point'lerini price_history'ye kaydet. Returns: kayit sayisi."""
    saved = 0
    for dp in data_points:
        # Ayni tarihte ayni store icin kayit var mi kontrol et
        existing = await db.execute(
            select(PriceHistory.id).where(
                PriceHistory.product_store_id == product_store_id,
                func.date(PriceHistory.recorded_at) == dp.date,
                PriceHistory.source == source,
            )
        )
        if existing.scalar_one_or_none():
            continue

        record = PriceHistory(
            product_store_id=product_store_id,
            price=Decimal(str(dp.price)),
            currency="TRY",
            in_stock=True,
            source=source,
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
    stats = {"total": 0, "ok": 0, "no_match": 0, "no_data": 0, "skipped": 0, "error": 0}

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

            result = await import_product_history(product, db)
            status = result["status"]
            stats[status] = stats.get(status, 0) + 1

            if status == "skipped":
                print(f"[akakce/importer] [{i+1}/{len(products)}] ATLA: {product.title[:50]}", flush=True)
            else:
                print(f"[akakce/importer] [{i+1}/{len(products)}] {product.brand} {product.title[:40]}", flush=True)

            if result["data_points"] > 0:
                print(f"  → {result['data_points']} data point kaydedildi", flush=True)

            # Commit after each product to avoid long transactions
            await db.commit()

            # Rate limiting — skip edilenlerde bekleme yok
            if status != "skipped":
                await random_delay(1.0, 2.0)

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
            await random_delay(1.0, 2.0)

    print(f"[akakce/enrichment] Tamamlandı: {stats}", flush=True)
    return stats
