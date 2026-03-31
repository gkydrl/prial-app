"""
Price history import orchestrator.
Her Prial urunu icin Akakce'de arama, bulunamazsa Epey'de arama,
fiyat gecmisi cekme, DB'ye kayit.

Concurrent: 5 ürün aynı anda işlenir (ScraperAPI rate limit'e dikkat).
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


# ── Concurrency ──
_IMPORT_CONCURRENCY = 5  # Aynı anda kaç ürün işlensin


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
    "Robotist", "Sennheiser", "DJI", "Honor", "Harman",
    "Bang", "Bilbor",
]


def _extract_brand_from_title(title: str) -> tuple[str | None, str]:
    """
    'SamsungGalaxy S24...' → ('Samsung', 'Galaxy S24...')
    'AppleiPad Pro...' → ('Apple', 'iPad Pro...')
    Title'ın başında boşluksuz brand varsa ayırır.
    """
    for brand in _KNOWN_BRANDS:
        if title.startswith(brand) and len(title) > len(brand):
            rest = title[len(brand):]
            # Brand'dan sonra harf veya rakam geliyorsa (boşluk değilse) gömülü demektir
            if rest[0] != " ":
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

        # 5. Price history kaydet (batch insert — duplicate'leri toplu kontrol)
        saved = await _save_price_points_batch(store.id, data_points, db, source=source)

        # 6. l1y istatistiklerini guncelle (outlier filtreli)
        prices = sorted([dp.price for dp in data_points if dp.price > 0])
        if len(prices) >= 3:
            # IQR-based outlier removal
            q1 = prices[len(prices) // 4]
            q3 = prices[3 * len(prices) // 4]
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            clean_prices = [p for p in prices if lower <= p <= upper]
            if not clean_prices:
                clean_prices = prices  # fallback
        elif prices:
            clean_prices = prices
        else:
            clean_prices = []

        if clean_prices:
            product.l1y_lowest_price = Decimal(str(min(clean_prices)))
            product.l1y_highest_price = Decimal(str(max(clean_prices)))

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


async def _save_price_points_batch(
    product_store_id: uuid.UUID,
    data_points: list[PriceDataPoint],
    db: AsyncSession,
    source: str = "akakce_import",
) -> int:
    """
    Price data point'lerini toplu kaydet.
    Önce mevcut tarihleri tek sorguda çek, sonra sadece yenileri ekle.
    """
    if not data_points:
        return 0

    # Mevcut tarihleri tek sorguda al
    existing_dates_result = await db.execute(
        select(func.date(PriceHistory.recorded_at)).where(
            PriceHistory.product_store_id == product_store_id,
            PriceHistory.source == source,
        )
    )
    existing_dates = {row[0] for row in existing_dates_result.fetchall()}

    saved = 0
    for dp in data_points:
        if dp.date in existing_dates:
            continue
        # Skip invalid prices
        if dp.price <= 0:
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
    Toplu Akakce import — concurrent.
    5 ürün aynı anda işlenir (ScraperAPI rate limit'e uygun).
    """
    stats = {"total": 0, "ok": 0, "no_match": 0, "no_data": 0, "skipped": 0, "error": 0}
    semaphore = asyncio.Semaphore(_IMPORT_CONCURRENCY)

    async with AsyncSessionLocal() as db:
        # Hedef urunleri sec
        query = select(Product)
        if only_new:
            query = query.where(Product.akakce_url.is_(None))
        query = query.order_by(Product.created_at.desc()).limit(batch_size)

        result = await db.execute(query)
        products = result.scalars().all()

    total = len(products)
    print(f"[akakce/importer] {total} ürün işlenecek (batch={batch_size}, concurrency={_IMPORT_CONCURRENCY})", flush=True)

    processed = 0

    async def _process_one(product: Product, idx: int):
        nonlocal processed
        async with semaphore:
            async with AsyncSessionLocal() as db:
                # Re-attach product to this session
                db_product = await db.get(Product, product.id)
                if not db_product:
                    return

                res = await import_product_history(db_product, db)
                status = res["status"]

                processed += 1
                if status == "skipped":
                    print(f"[akakce/importer] [{processed}/{total}] ATLA: {db_product.title[:50]}", flush=True)
                else:
                    print(f"[akakce/importer] [{processed}/{total}] {db_product.brand} {db_product.title[:40]} → {status}", flush=True)

                if res["data_points"] > 0:
                    print(f"  → {res['data_points']} data point kaydedildi", flush=True)

                await db.commit()

                stats["total"] += 1
                stats[status] = stats.get(status, 0) + 1

                # Rate limiting — skip edilenlerde bekleme yok
                if status != "skipped":
                    await random_delay(0.5, 1.5)

    # Tüm ürünleri concurrent olarak işle
    tasks = [_process_one(p, i) for i, p in enumerate(products)]
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"[akakce/importer] Tamamlandı: {stats}", flush=True)
    return stats


async def daily_enrichment(batch_size: int = 20) -> dict:
    """
    Mevcut akakce eslesmeleri guncelle — yeni fiyat verileri cek.
    Eski versiyon (kuçuk batch). daily_enrichment_full() ile değiştirildi.
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


async def daily_enrichment_full() -> dict:
    """
    TÜM ürünler için günlük zenginleştirme:
    1. Akakce chart'tan fiyat geçmişi güncelle (eksik günleri doldur)
    2. Akakce'den ilk 2 farklı marketplace linkini bul → scrape et (fiyat + kargo + taksit)
    3. ProductStore kayıtlarını güncelle
    4. daily_lowest_price güncelle
    5. l1y istatistiklerini güncelle

    Concurrency: 10, delay: 0.5s arası.
    """
    from app.services.akakce.store_parser import parse_store_listings, resolve_redirect
    from app.services.scraper.dispatcher import scrape_url, get_scraper
    from app.services.scraper.universal_scraper import UniversalScraper
    from app.models.product import StoreName

    stats = {
        "total": 0, "ok": 0, "no_data": 0, "error": 0, "skipped": 0,
        "stores_scraped": 0, "stores_created": 0, "stores_updated": 0,
    }
    semaphore = asyncio.Semaphore(10)

    # 1. Tüm akakce_url'si olan ürünleri çek — alarm sayısına göre sırala (yüksek öncelik önce)
    async with AsyncSessionLocal() as db:
        query = (
            select(Product)
            .where(Product.akakce_url.isnot(None))
            .order_by(Product.alarm_count.desc())
        )
        result = await db.execute(query)
        products = result.scalars().all()

    total = len(products)
    print(f"[akakce/enrichment_full] {total} ürün işlenecek (concurrency=10)", flush=True)

    processed = 0

    async def _process_one(product: Product):
        nonlocal processed
        async with semaphore:
            async with AsyncSessionLocal() as db:
                try:
                    db_product = await db.get(Product, product.id)
                    if not db_product or not db_product.akakce_url:
                        stats["skipped"] += 1
                        return

                    # a) Fiyat geçmişi güncelle
                    hist_result = await import_product_history(db_product, db)
                    hist_status = hist_result["status"]
                    stats[hist_status] = stats.get(hist_status, 0) + 1
                    stats["total"] += 1

                    # b) Akakce store listing'lerini parse et (ilk 2 unique marketplace)
                    store_listings = await parse_store_listings(db_product.akakce_url, max_unique_stores=2)

                    daily_lowest_price = None
                    daily_lowest_store = None

                    for listing in store_listings:
                        try:
                            # Bütçe kontrolü
                            from app.services.scraper_budget import can_scrape, record_credit
                            if not await can_scrape(priority=2):
                                break  # Bütçe doldu, kalan store'ları atla

                            # Sadece bilinen marketplace'leri scrape et
                            if listing.store_enum and listing.store_enum not in (StoreName.OTHER,):
                                # Redirect URL'den gerçek mağaza URL'sini çöz
                                final_url = await resolve_redirect(listing.redirect_url)
                                if not final_url:
                                    # Scrape edemiyorsak Akakce'deki fiyatı kullan
                                    _update_daily_lowest(listing, daily_lowest_price, daily_lowest_store)
                                    continue

                                # Scraper var mı kontrol et
                                scraper = get_scraper(final_url)
                                if isinstance(scraper, UniversalScraper):
                                    # Universal scraper ile scrape etme, sadece Akakce fiyatını kaydet
                                    pass
                                else:
                                    try:
                                        scraped = await scrape_url(final_url)
                                        await record_credit()
                                        stats["stores_scraped"] += 1

                                        # ProductStore güncelle veya oluştur
                                        await _upsert_product_store(
                                            db, db_product, listing, scraped, final_url
                                        )
                                    except Exception as e:
                                        print(f"[akakce/enrichment_full] Scrape hatası ({final_url[:60]}): {e}", flush=True)

                            # daily_lowest tracking
                            if daily_lowest_price is None or listing.price < daily_lowest_price:
                                daily_lowest_price = listing.price
                                daily_lowest_store = listing.store_name.upper() if listing.store_enum else listing.store_name

                        except Exception as e:
                            print(f"[akakce/enrichment_full] Store listing hatası: {e}", flush=True)

                    # c) daily_lowest_price güncelle
                    if daily_lowest_price:
                        db_product.daily_lowest_price = Decimal(str(daily_lowest_price))
                        db_product.daily_lowest_store = daily_lowest_store

                    await db.commit()

                except Exception as e:
                    print(f"[akakce/enrichment_full] Hata ({product.title[:50]}): {e}", flush=True)
                    stats["error"] = stats.get("error", 0) + 1

                finally:
                    processed += 1
                    if processed % 100 == 0:
                        print(f"[akakce/enrichment_full] İlerleme: {processed}/{total} — {stats}", flush=True)

            # Rate limiting
            await random_delay(0.3, 0.7)

    # Tüm ürünleri concurrent olarak işle
    tasks = [_process_one(p) for p in products]
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"[akakce/enrichment_full] Tamamlandı: {stats}", flush=True)
    return stats


async def _upsert_product_store(
    db: AsyncSession,
    product: Product,
    listing,
    scraped,
    final_url: str,
) -> None:
    """ProductStore kaydını güncelle veya oluştur."""
    from app.models.product import StoreName

    # Mevcut store'u URL ile bul
    result = await db.execute(
        select(ProductStore).where(
            ProductStore.product_id == product.id,
            ProductStore.url == final_url,
        )
    )
    store = result.scalar_one_or_none()

    if store:
        # Güncelle
        store.current_price = scraped.current_price
        store.original_price = scraped.original_price
        store.discount_percent = scraped.discount_percent
        store.in_stock = scraped.in_stock
        store.estimated_delivery_days = scraped.estimated_delivery_days
        store.delivery_text = scraped.delivery_text
        store.installment_text = scraped.installment_text
    else:
        # Yeni oluştur
        store_enum = listing.store_enum or StoreName.OTHER
        store = ProductStore(
            product_id=product.id,
            store=store_enum,
            url=final_url,
            current_price=scraped.current_price,
            original_price=scraped.original_price,
            discount_percent=scraped.discount_percent,
            in_stock=scraped.in_stock,
            store_product_id=scraped.store_product_id,
            estimated_delivery_days=scraped.estimated_delivery_days,
            delivery_text=scraped.delivery_text,
            installment_text=scraped.installment_text,
            check_priority=3,
            is_active=True,
        )
        db.add(store)

    await db.flush()
