"""
Günlük katalog crawler'ı.

Akış:
  1. Her ProductVariant için Google'da arama yap
  2. Gelen URL'leri teker teker scrape et
     - Trendyol/Hepsiburada → özel scraper (hızlı, güvenilir)
     - Diğer siteler → UniversalScraper (LLM tabanlı)
  3. Catalog matcher ile doğrula (regex → LLM)
  4. Eşleşirse ProductStore oluştur / güncelle

Scheduler: her gün 03:00'da çalışır (main.py).
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.product import Product, ProductVariant, ProductStore, StoreName
from app.models.price_history import PriceHistory
from app.services.store_search.google_search import GoogleSearcher
from app.services.store_search.base import SearchResult
from app.services.catalog_matcher import is_match

_google = GoogleSearcher()

# StoreName enum'unda olmayan değerler OTHER'a map edilir
_STORE_MAP = {
    "trendyol": StoreName.TRENDYOL,
    "hepsiburada": StoreName.HEPSIBURADA,
    "amazon": StoreName.AMAZON,
    "n11": StoreName.N11,
    "ciceksepeti": StoreName.CICEKSEPETI,
    "mediamarkt": StoreName.MEDIAMARKT,
    "teknosa": StoreName.TEKNOSA,
    "vatan": StoreName.VATAN,
}


def _build_search_query(product: Product, variant: ProductVariant) -> str:
    """
    Variant için optimize edilmiş Google arama sorgusu.
    Trendyol/Hepsiburada ürün sayfalarını hedefler.
    Ör: "Apple iPhone 16 Pro 256GB trendyol hepsiburada"
    """
    parts: list[str] = []
    if product.brand:
        parts.append(product.brand)
    parts.append(product.title)
    if variant.title:
        parts.append(variant.title)
    # Mağaza adları ekle → Google kategori yerine ürün sayfalarını önceliklendirir
    parts.append("trendyol hepsiburada")
    return " ".join(parts)


async def _scrape_candidate(url: str):
    """
    URL'yi en uygun scraper ile scrape eder.
    Bilinen site → özel scraper, diğerleri → UniversalScraper (LLM).
    """
    from app.services.scraper.dispatcher import scrape_url
    try:
        return await scrape_url(url)
    except Exception as e:
        print(f"[crawler] Scrape hatası ({url}): {e}")
        return None


async def _save_product_store(
    db,
    product: Product,
    variant: ProductVariant,
    scraped,
    search_result: SearchResult,
) -> bool:
    """
    Eşleşme onaylandıktan sonra ProductStore oluşturur veya fiyatı günceller.
    Returns: True eğer yeni store eklendiyse.
    """
    # URL zaten var mı?
    existing = (await db.execute(
        select(ProductStore).where(ProductStore.url == scraped.url)
    )).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        if existing.current_price != scraped.current_price:
            existing.current_price = scraped.current_price
            existing.original_price = scraped.original_price
            existing.discount_percent = scraped.discount_percent
            existing.in_stock = scraped.in_stock
            existing.last_checked_at = now
            db.add(existing)
        return False  # Yeni değil, güncellendi

    store_enum = _STORE_MAP.get(search_result.store, StoreName.OTHER)

    product_store = ProductStore(
        product_id=product.id,
        variant_id=variant.id,
        store=store_enum,
        store_product_id=scraped.store_product_id,
        url=scraped.url,
        current_price=scraped.current_price,
        original_price=scraped.original_price,
        discount_percent=scraped.discount_percent,
        in_stock=scraped.in_stock,
        last_checked_at=now,
    )
    db.add(product_store)
    await db.flush()

    db.add(PriceHistory(
        product_store_id=product_store.id,
        price=scraped.current_price,
        original_price=scraped.original_price,
        in_stock=scraped.in_stock,
    ))

    # image_url güncelle (henüz yoksa)
    if scraped.image_url:
        if not product.image_url:
            product.image_url = scraped.image_url
            db.add(product)
        if not variant.image_url:
            variant.image_url = scraped.image_url
            db.add(variant)

    # lowest_price_ever güncelle
    price = scraped.current_price
    if price:
        if product.lowest_price_ever is None or price < product.lowest_price_ever:
            product.lowest_price_ever = price
            db.add(product)
        if variant.lowest_price_ever is None or price < variant.lowest_price_ever:
            variant.lowest_price_ever = price
            db.add(variant)

    print(
        f"[crawler] ✓ Yeni store: {store_enum.value} → "
        f"{product.brand} {product.title} ({variant.title}) — {price}₺"
    )
    return True


async def crawl_variant(product: Product, variant: ProductVariant) -> dict:
    """
    Tek bir variant için Google araması yapar ve eşleşen store'ları kaydeder.
    Returns: {"found": int, "new": int}
    """
    query = _build_search_query(product, variant)
    limit = settings.crawler_results_per_store

    try:
        search_results = await _google.search(query, limit=limit)
    except Exception as e:
        print(f"[crawler] Google arama hatası ({query}): {e}")
        return {"found": 0, "new": 0}

    if not search_results:
        print(f"[crawler] Sonuç yok: {query}")
        return {"found": 0, "new": 0}

    stats = {"found": 0, "new": 0}

    async with AsyncSessionLocal() as db:
        # Session içinde taze nesneler al
        product_db = await db.get(Product, product.id)
        variant_db = await db.get(ProductVariant, variant.id)
        if not product_db or not variant_db:
            return stats

        for result in search_results:
            # 1. Scrape et
            scraped = await _scrape_candidate(result.url)
            if not scraped or not scraped.current_price or scraped.current_price <= 0:
                continue

            # 2. Catalog matcher — bu ürün doğru mu?
            matched = await is_match(
                product_brand=product_db.brand,
                product_title=product_db.title,
                variant_title=variant_db.title,
                variant_attrs=variant_db.attributes or {},
                scraped_title=scraped.title,
                scraped_brand=scraped.brand,
            )
            if not matched:
                continue

            stats["found"] += 1

            # 3. Kaydet / güncelle
            try:
                is_new = await _save_product_store(db, product_db, variant_db, scraped, result)
                if is_new:
                    stats["new"] += 1
            except Exception as e:
                print(f"[crawler] Kayıt hatası ({result.url}): {e}")
                continue

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"[crawler] Commit hatası (variant={variant.id}): {e}")

    return stats


async def crawl_all_variants(new_only: bool = False) -> None:
    """
    Tüm aktif variant'lar için katalog taraması.
    Scheduler veya admin endpoint tarafından çağrılır.

    new_only=True → Yalnızca hiç mağazası olmayan variant'ları işler (ilk dolum için).
    """
    print(f"[crawler] Katalog taraması başladı (new_only={new_only})...")
    start = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.product), selectinload(ProductVariant.stores))
            .join(Product)
        )
        all_variants: list[ProductVariant] = result.scalars().all()

    if not all_variants:
        print("[crawler] Katalogda variant yok.")
        return

    if new_only:
        variants = [v for v in all_variants if not v.stores]
        print(f"[crawler] {len(variants)}/{len(all_variants)} variant mağazasız → taranacak...")
    else:
        variants = all_variants
        print(f"[crawler] {len(variants)} variant taranacak...")

    if not variants:
        print("[crawler] Taranacak yeni variant yok.")
        return

    # new_only modunda concurrency biraz daha yüksek tutabiliriz
    concurrency = min(settings.crawler_search_concurrency * 2, 8) if new_only else settings.crawler_search_concurrency
    semaphore = asyncio.Semaphore(concurrency)
    total_found = 0
    total_new = 0

    async def process(v: ProductVariant) -> None:
        nonlocal total_found, total_new
        async with semaphore:
            stats = await crawl_variant(v.product, v)
            total_found += stats["found"]
            total_new += stats["new"]

    await asyncio.gather(*[process(v) for v in variants])

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(
        f"[crawler] Tarama tamamlandı. "
        f"Süre: {elapsed:.1f}s | "
        f"Variant: {len(variants)} | "
        f"Eşleşen: {total_found} | "
        f"Yeni store: {total_new}"
    )
