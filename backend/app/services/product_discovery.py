"""
Google Shopping üzerinden otomatik ürün keşif servisi.

Serper.dev API kullanarak Google'da arama yapar,
ürün URL'lerini mevcut scraper altyapısıyla çeker ve DB'ye kaydeder.

İki mod:
  - discover_all()    → Tüm terimleri tarar (toplu keşif, 2500 kredi)
  - discover_daily()  → Sadece yeni/trend terimleri tarar (günlük, ~80 kredi)
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, func

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore, ProductVariant, StoreName
from app.models.price_history import PriceHistory
from app.models.category import Category
from app.services.discovery_terms import DISCOVERY_TERMS, get_all_terms
from app.services.store_search.google_search import _is_product_url

# ─── Store Mapping ───────────────────────────────────────────────────────────

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

# Desteklenen mağaza domainleri (site: filtresi için)
_SUPPORTED_SITES = [
    "trendyol.com",
    "hepsiburada.com",
    "n11.com",
    "mediamarkt.com.tr",
]

_SITE_FILTER = " OR ".join(f"site:{s}" for s in _SUPPORTED_SITES)


def _store_from_url(url: str) -> str:
    """URL'den store adını çıkarır."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.removeprefix("www.")
        if "trendyol.com" in hostname:
            return "trendyol"
        if "hepsiburada.com" in hostname:
            return "hepsiburada"
        if "amazon.com.tr" in hostname:
            return "amazon"
        if "n11.com" in hostname:
            return "n11"
        if "mediamarkt.com.tr" in hostname:
            return "mediamarkt"
        if "teknosa.com" in hostname:
            return "teknosa"
        if "vatanbilgisayar.com" in hostname:
            return "vatan"
        return "other"
    except Exception:
        return "other"


# ─── Serper API ──────────────────────────────────────────────────────────────

async def _search_serper(query: str, num: int = 20) -> list[dict]:
    """
    Serper.dev regular search API ile Google'da arama yapar.
    Returns: [{"title": ..., "link": ..., "snippet": ...}, ...]
    """
    api_key = settings.serper_api_key
    if not api_key:
        print("[discovery] SERPER_API_KEY ayarlanmamış!", flush=True)
        return []

    payload = {
        "q": query,
        "gl": "tr",
        "hl": "tr",
        "num": num,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code != 200:
                print(f"[discovery] Serper HTTP {resp.status_code}: {resp.text[:200]}", flush=True)
                return []
            data = resp.json()
            return data.get("organic", [])
    except Exception as e:
        print(f"[discovery] Serper hata ({query}): {e}", flush=True)
        return []


# ─── URL Processing ──────────────────────────────────────────────────────────

def _extract_product_urls(organic_results: list[dict]) -> list[str]:
    """Serper sonuçlarından ürün sayfası URL'lerini filtreler."""
    urls: list[str] = []
    seen: set[str] = set()

    for item in organic_results:
        url = item.get("link", "")
        if not url:
            continue

        # URL'yi temizle (query params kaldır, normalize et)
        clean = url.split("?")[0].rstrip("/")
        if clean in seen:
            continue
        seen.add(clean)

        # Ürün sayfası mı?
        if not _is_product_url(url):
            continue

        # /en/ prefix'li Trendyol URL'lerini Türkçe'ye çevir
        if "/en/" in url and "trendyol.com" in url:
            url = url.replace("trendyol.com/en/", "trendyol.com/")

        urls.append(url)

    return urls


# ─── Product Saving ──────────────────────────────────────────────────────────

async def _get_or_create_category(db, slug: str) -> Category | None:
    """Kategori slug'ına göre bulur, yoksa None döner."""
    result = await db.execute(
        select(Category).where(Category.slug == slug)
    )
    return result.scalar_one_or_none()


async def _find_existing_product(db, brand: str | None, title: str) -> Product | None:
    """Aynı brand+title'a sahip mevcut ürünü bulur."""
    q = select(Product).where(Product.title == title)
    if brand:
        q = q.where(Product.brand == brand)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def _save_discovered_product(
    db,
    scraped,
    category_slug: str,
) -> str:
    """
    Keşfedilen ürünü DB'ye kaydeder (alarm olmadan).
    Returns: "new", "new_store", "exists", "skipped"
    """
    from app.services.variant_extractor import extract_attributes, find_or_create_variant
    from app.services.short_title_generator import generate_short_title

    # URL zaten var mı?
    existing_store = (await db.execute(
        select(ProductStore).where(ProductStore.url == scraped.url)
    )).scalar_one_or_none()

    if existing_store:
        return "exists"

    # Brand + title ile mevcut ürün var mı?
    existing_product = await _find_existing_product(db, scraped.brand, scraped.title)

    now = datetime.now(timezone.utc)
    store_name = _store_from_url(scraped.url)
    store_enum = _STORE_MAP.get(store_name, StoreName.OTHER)

    if existing_product:
        # Mevcut ürüne yeni mağaza ekle
        product = existing_product
        result_type = "new_store"
    else:
        # Yeni ürün oluştur
        category = await _get_or_create_category(db, category_slug)

        try:
            short_title = await generate_short_title(scraped.brand, scraped.title)
        except Exception:
            short_title = scraped.title[:40]

        product = Product(
            title=scraped.title,
            short_title=short_title,
            brand=scraped.brand,
            description=scraped.description,
            image_url=scraped.image_url,
            category_id=category.id if category else None,
            lowest_price_ever=scraped.current_price,
            alarm_count=0,
        )
        db.add(product)
        await db.flush()
        result_type = "new"

    # Variant
    attributes = extract_attributes(scraped.title)
    variant = await find_or_create_variant(
        db,
        product_id=product.id,
        attributes=attributes,
        image_url=scraped.image_url,
    )

    # lowest_price_ever güncelle
    price = scraped.current_price
    if price:
        if product.lowest_price_ever is None or price < product.lowest_price_ever:
            product.lowest_price_ever = price
            db.add(product)
        if variant.lowest_price_ever is None or price < variant.lowest_price_ever:
            variant.lowest_price_ever = price
            db.add(variant)

    # ProductStore
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

    # PriceHistory
    db.add(PriceHistory(
        product_store_id=product_store.id,
        price=scraped.current_price,
        original_price=scraped.original_price,
        currency="TRY",
        in_stock=scraped.in_stock,
    ))

    return result_type


# ─── Main Discovery Logic ────────────────────────────────────────────────────

async def _discover_term(
    term: str,
    category_slug: str,
    existing_urls: set[str],
    price_min: Decimal,
    price_max: Decimal,
) -> dict:
    """
    Tek bir arama terimi için keşif yapar.
    Returns: {"term": str, "urls_found": int, "new": int, "new_store": int, "skipped": int, "price_out": int, "errors": int}
    """
    from app.services.scraper.dispatcher import scrape_url

    query = f"{term} {_SITE_FILTER}"
    stats = {"term": term, "urls_found": 0, "new": 0, "new_store": 0,
             "skipped": 0, "price_out": 0, "errors": 0, "exists": 0}

    # 1. Serper'dan ara
    organic = await _search_serper(query, num=20)
    urls = _extract_product_urls(organic)
    stats["urls_found"] = len(urls)

    if not urls:
        print(f"[discovery] {term}: sonuç yok", flush=True)
        return stats

    # 2. DB'de zaten var olan URL'leri filtrele
    new_urls = [u for u in urls if u not in existing_urls]
    stats["exists"] = len(urls) - len(new_urls)

    if not new_urls:
        print(f"[discovery] {term}: {len(urls)} URL bulundu, hepsi zaten DB'de", flush=True)
        return stats

    print(f"[discovery] {term}: {len(new_urls)} yeni URL ({len(urls)} toplam)", flush=True)

    # 3. Her yeni URL'yi scrape et ve kaydet
    async with AsyncSessionLocal() as db:
        for url in new_urls:
            try:
                scraped = await scrape_url(url)
            except Exception as e:
                print(f"[discovery]   ✗ scrape hatası ({url[:60]}): {e}", flush=True)
                stats["errors"] += 1
                continue

            if not scraped or not scraped.current_price or scraped.current_price <= 0:
                print(f"[discovery]   ✗ fiyatsız: {url[:60]}", flush=True)
                stats["errors"] += 1
                continue

            # Fiyat aralığı kontrolü
            if scraped.current_price < price_min or scraped.current_price > price_max:
                print(
                    f"[discovery]   ✗ fiyat dışı ({scraped.current_price}₺): "
                    f"{scraped.title[:40]}",
                    flush=True,
                )
                stats["price_out"] += 1
                continue

            try:
                result = await _save_discovered_product(db, scraped, category_slug)
                stats[result] = stats.get(result, 0) + 1
                existing_urls.add(url)  # Aynı çalışmada tekrar eklemesin

                if result in ("new", "new_store"):
                    print(
                        f"[discovery]   ✓ {result}: {scraped.brand or ''} "
                        f"{scraped.title[:40]} — {scraped.current_price}₺",
                        flush=True,
                    )
            except Exception as e:
                print(f"[discovery]   ✗ kayıt hatası ({url[:60]}): {e}", flush=True)
                stats["errors"] += 1
                continue

            # Scrape arası bekleme (rate limit)
            await asyncio.sleep(2)

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"[discovery] Commit hatası ({term}): {e}", flush=True)

    return stats


async def _load_existing_urls() -> set[str]:
    """DB'deki tüm ProductStore URL'lerini set olarak döner."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ProductStore.url))
        return {row[0] for row in result.all()}


async def discover_all() -> dict:
    """
    Toplu keşif — tüm arama terimlerini çalıştırır.
    İlk kullanımda 2500 free krediyi kullanmak için ideal.
    """
    print("[discovery] ═══ TOPLU KEŞİF BAŞLADI ═══", flush=True)
    start = datetime.now(timezone.utc)

    all_terms = get_all_terms()
    existing_urls = await _load_existing_urls()
    print(f"[discovery] {len(all_terms)} arama terimi, DB'de {len(existing_urls)} mevcut URL", flush=True)

    price_min = Decimal(str(settings.discovery_price_min))
    price_max = Decimal(str(settings.discovery_price_max))
    concurrency = settings.discovery_concurrency
    semaphore = asyncio.Semaphore(concurrency)

    total_stats = {
        "terms_processed": 0, "urls_found": 0, "new": 0,
        "new_store": 0, "exists": 0, "price_out": 0, "errors": 0,
    }

    async def process(category_slug: str, term: str):
        async with semaphore:
            stats = await _discover_term(term, category_slug, existing_urls, price_min, price_max)
            total_stats["terms_processed"] += 1
            for key in ["urls_found", "new", "new_store", "exists", "price_out", "errors"]:
                total_stats[key] += stats.get(key, 0)

    tasks = [process(cat, term) for cat, term in all_terms]
    await asyncio.gather(*tasks)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(
        f"[discovery] ═══ TOPLU KEŞİF TAMAMLANDI ═══\n"
        f"  Süre: {elapsed:.0f}s\n"
        f"  Terim: {total_stats['terms_processed']}\n"
        f"  URL bulundu: {total_stats['urls_found']}\n"
        f"  Yeni ürün: {total_stats['new']}\n"
        f"  Yeni store: {total_stats['new_store']}\n"
        f"  Zaten var: {total_stats['exists']}\n"
        f"  Fiyat dışı: {total_stats['price_out']}\n"
        f"  Hata: {total_stats['errors']}",
        flush=True,
    )
    return total_stats


async def discover_daily() -> dict:
    """
    Günlük keşif — daha az kredi harcar.
    Her kategoriden birkaç terimi rastgele seçer.
    """
    import random

    print("[discovery] ─── Günlük keşif başladı ───", flush=True)
    start = datetime.now(timezone.utc)

    existing_urls = await _load_existing_urls()
    price_min = Decimal(str(settings.discovery_price_min))
    price_max = Decimal(str(settings.discovery_price_max))

    # Her kategoriden max 2 rastgele terim seç (~80 kredi/gün)
    daily_terms: list[tuple[str, str]] = []
    for category, terms in DISCOVERY_TERMS.items():
        selected = random.sample(terms, min(2, len(terms)))
        for term in selected:
            daily_terms.append((category, term))

    print(f"[discovery] {len(daily_terms)} terim seçildi, DB'de {len(existing_urls)} URL", flush=True)

    total_stats = {
        "terms_processed": 0, "urls_found": 0, "new": 0,
        "new_store": 0, "exists": 0, "price_out": 0, "errors": 0,
    }

    for cat, term in daily_terms:
        stats = await _discover_term(term, cat, existing_urls, price_min, price_max)
        total_stats["terms_processed"] += 1
        for key in ["urls_found", "new", "new_store", "exists", "price_out", "errors"]:
            total_stats[key] += stats.get(key, 0)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(
        f"[discovery] ─── Günlük keşif tamamlandı ───\n"
        f"  Süre: {elapsed:.0f}s | Yeni: {total_stats['new']} | "
        f"Store: {total_stats['new_store']} | Hata: {total_stats['errors']}",
        flush=True,
    )
    return total_stats
