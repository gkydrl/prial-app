"""
Akakce kategori crawler — katalog genisletme.
Akakce'nin elektronik kategorilerini crawl ederek yeni urunleri DB'ye ekler.
Mevcut urunlerle Jaccard + Haiku ile dedup yapar.
"""
from __future__ import annotations

import asyncio
import re
import urllib.parse
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.category import Category
from app.models.product import Product, ProductStore, ProductVariant, StoreName
from app.services.akakce.searcher import (
    HEADERS,
    AkakceSearchResult,
    _parse_price,
    _extract_price_from_li,
)
from app.services.akakce.importer import (
    _extract_brand_from_title,
    _is_junk_product,
    import_product_history,
    random_delay,
)
from app.services.catalog_matcher import _normalize


# ── Kategori mapping: Akakce URL path → Prial DB category slug ──

AKAKCE_CATEGORIES = [
    # ── Telefon & Tablet ──
    ("/cep-telefonu/akilli.html", "telefon"),
    ("/bilgisayar/tablet.html", "tablet"),
    # ── Bilgisayar ──
    ("/bilgisayar/dizustu.html", "bilgisayar"),
    ("/monitor.html", "monitor"),
    ("/ekran-karti.html", "bilgisayar"),
    ("/yazici.html", "bilgisayar"),
    ("/projeksiyon-cihazi.html", "bilgisayar"),
    # ── TV & Ses ──
    ("/televizyon.html", "televizyon"),
    ("/soundbar.html", "hoparlor"),
    ("/hoparlor.html", "hoparlor"),
    # ── Kulaklik ──
    ("/telefon-aksesuarlari/kulaklik.html", "kulaklik"),
    # ── Akilli Saat & Giyilebilir ──
    ("/akilli-saat.html", "akilli-saat"),
    ("/akilli-bileklik.html", "akilli-saat"),
    # ── Oyun ──
    ("/oyun-konsolu.html", "oyun-konsolu"),
    ("/oyun-kolu.html", "oyun-konsolu"),
    # ── Kamera ──
    ("/fotograf-makinesi.html", "kamera"),
    ("/aksiyon-kamera.html", "kamera"),
    ("/drone.html", "kamera"),
    # ── Ev Aleti ──
    ("/elektrikli-supurge.html", "ev-aleti"),
    ("/robot-supurge.html", "ev-aleti"),
    ("/klima.html", "ev-aleti"),
    # ── Beyaz Esya ──
    ("/buzdolabi.html", "beyaz-esya"),
    ("/camasir-makinesi.html", "beyaz-esya"),
    ("/bulasik-makinesi.html", "beyaz-esya"),
    ("/camasir-kurutma-makinesi.html", "beyaz-esya"),
    ("/firin.html", "beyaz-esya"),
    # ── Kisisel Bakim ──
    ("/tiras-makinesi.html", "kisisel-bakim"),
    ("/sac-kurutma-makinesi.html", "kisisel-bakim"),
    ("/sac-duzlestirici.html", "kisisel-bakim"),
    # ── Depolama & Ag ──
    ("/harici-disk.html", "depolama"),
    ("/usb-flash-bellek.html", "depolama"),
    ("/ag-cihazi.html", "ag-cihazi"),
]

_CRAWL_CONCURRENCY = 5  # Kategori icinde 5 urun paralel


@dataclass
class CrawlStats:
    categories_crawled: int = 0
    products_found: int = 0
    duplicates_skipped: int = 0
    new_products_added: int = 0
    price_histories_fetched: int = 0
    haiku_calls: int = 0
    errors: int = 0


# ── Public API ──────────────────────────────────────────────────────────────


async def crawl_all_categories(max_pages_per_category: int = 3) -> dict:
    """Tum Akakce kategorilerini sirayla crawl et."""
    stats = CrawlStats()

    for category_path, category_slug in AKAKCE_CATEGORIES:
        try:
            print(f"\n[category_crawler] ── {category_slug} ({category_path}) ──", flush=True)
            cat_stats = await crawl_category(category_path, category_slug, max_pages_per_category)
            stats.categories_crawled += 1
            stats.products_found += cat_stats.products_found
            stats.duplicates_skipped += cat_stats.duplicates_skipped
            stats.new_products_added += cat_stats.new_products_added
            stats.price_histories_fetched += cat_stats.price_histories_fetched
            stats.haiku_calls += cat_stats.haiku_calls
            stats.errors += cat_stats.errors
        except Exception as e:
            print(f"[category_crawler] Kategori hatası ({category_slug}): {e}", flush=True)
            stats.errors += 1

    estimated_cost = stats.haiku_calls * 1000 * 0.00000080  # ~$0.80/M input tokens
    result = {
        "categories_crawled": stats.categories_crawled,
        "products_found": stats.products_found,
        "duplicates_skipped": stats.duplicates_skipped,
        "new_products_added": stats.new_products_added,
        "price_histories_fetched": stats.price_histories_fetched,
        "haiku_calls": stats.haiku_calls,
        "errors": stats.errors,
        "estimated_cost_usd": round(estimated_cost, 2),
    }
    print(f"\n[category_crawler] ═══ TAMAMLANDI ═══\n{result}", flush=True)
    return result


async def crawl_category(
    category_path: str,
    category_slug: str,
    max_pages: int = 3,
) -> CrawlStats:
    """Tek bir Akakce kategorisini crawl et, parse et, dedup et, kaydet."""
    stats = CrawlStats()

    # 1. Kategori sayfalarini cek ve parse et
    all_results: list[AkakceSearchResult] = []
    for page_num in range(1, max_pages + 1):
        html = await _fetch_category_page(category_path, page_num)
        if not html:
            break
        results = _parse_category_page(html)
        if not results:
            break
        all_results.extend(results)
        print(f"[category_crawler] Sayfa {page_num}: {len(results)} ürün bulundu", flush=True)
        await random_delay(1.0, 2.0)

    stats.products_found = len(all_results)
    if not all_results:
        print(f"[category_crawler] {category_slug}: Ürün bulunamadı", flush=True)
        return stats

    # 2. Junk filtre
    filtered = [r for r in all_results if not _is_junk_product(r.title)]
    junk_count = len(all_results) - len(filtered)
    if junk_count:
        print(f"[category_crawler] {junk_count} junk ürün filtrelendi", flush=True)

    # 3. DB'den mevcut urunleri cek (dedup icin)
    async with AsyncSessionLocal() as db:
        category_id = await _get_category_id(db, category_slug)

        # Mevcut urun title'lari (tum DB, bu kategorideki)
        existing_query = select(Product.title)
        if category_id:
            existing_query = existing_query.where(Product.category_id == category_id)
        result = await db.execute(existing_query)
        existing_titles = [row[0] for row in result.fetchall()]

        # Ayrica tum URL'leri de cek (URL bazli dedup)
        url_query = select(Product.akakce_url).where(Product.akakce_url.isnot(None))
        url_result = await db.execute(url_query)
        existing_urls = {row[0] for row in url_result.fetchall()}

    # 4. URL bazli dedup (hizli)
    url_new = []
    for r in filtered:
        full_url = r.url if r.url.startswith("http") else f"https://www.akakce.com{r.url}"
        if full_url in existing_urls:
            stats.duplicates_skipped += 1
        else:
            url_new.append(r)

    if not url_new:
        print(f"[category_crawler] {category_slug}: Tüm ürünler zaten mevcut (URL dedup)", flush=True)
        return stats

    # 5. Jaccard + Haiku dedup
    new_products, haiku_calls = await _dedup_candidates(url_new, existing_titles)
    stats.haiku_calls = haiku_calls
    stats.duplicates_skipped += len(url_new) - len(new_products)

    print(f"[category_crawler] {category_slug}: {len(new_products)} yeni ürün (dedup sonrası)", flush=True)

    if not new_products:
        return stats

    # 6. Yeni urunleri DB'ye kaydet ve fiyat gecmisi cek
    semaphore = asyncio.Semaphore(_CRAWL_CONCURRENCY)

    async def _save_one(akakce_result: AkakceSearchResult) -> None:
        async with semaphore:
            try:
                async with AsyncSessionLocal() as db:
                    saved = await _save_new_product(
                        akakce_result, category_slug, category_id, db,
                    )
                    if saved:
                        stats.new_products_added += 1

                        # Fiyat gecmisi cek
                        product = saved
                        history_result = await import_product_history(product, db)
                        if history_result["status"] == "ok":
                            stats.price_histories_fetched += 1
                            print(
                                f"  → {product.title[:50]}: {history_result['data_points']} data point",
                                flush=True,
                            )
                        await db.commit()
                        await random_delay(0.5, 1.5)
            except Exception as e:
                stats.errors += 1
                print(f"[category_crawler] Kayıt hatası: {e}", flush=True)

    tasks = [_save_one(r) for r in new_products]
    await asyncio.gather(*tasks, return_exceptions=True)

    return stats


# ── Sayfa Cekme ─────────────────────────────────────────────────────────────


async def _fetch_category_page(category_path: str, page_num: int) -> str | None:
    """Akakce kategori sayfasini cek. Pagination: base,2.html, base,3.html"""
    from app.config import settings

    if page_num == 1:
        url = f"https://www.akakce.com{category_path}"
    else:
        # /cep-telefonu/akilli.html → /cep-telefonu/akilli,2.html
        base = category_path.replace(".html", "")
        url = f"https://www.akakce.com{base},{page_num}.html"

    html = None
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        # Direkt erisim
        try:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200:
                html = resp.text
        except Exception:
            pass

        # ScraperAPI fallback
        if html is None and settings.scraper_api_key:
            try:
                proxy_url = (
                    f"http://api.scraperapi.com"
                    f"?api_key={settings.scraper_api_key}"
                    f"&url={urllib.parse.quote(url, safe='')}"
                )
                resp = await client.get(proxy_url, timeout=30)
                if resp.status_code == 200:
                    html = resp.text
                    print(f"[category_crawler] ScraperAPI ile alındı: {url}", flush=True)
            except Exception as e:
                print(f"[category_crawler] ScraperAPI hatası: {e}", flush=True)

    return html


# ── HTML Parse ──────────────────────────────────────────────────────────────


def _parse_category_page(html: str) -> list[AkakceSearchResult]:
    """
    Akakce kategori sayfasindaki urunleri parse et.
    searcher.py ile ayni regex pattern'leri kullanir.
    """
    results: list[AkakceSearchResult] = []

    # Primary pattern: ul.pl_v9 > li[data-pr]
    items = re.findall(
        r'<li\s+data-pr="(\d+)"[^>]*>.*?'
        r'<a\s+href="([^"]+)"\s+title="([^"]+)".*?'
        r'(?:<span\s+class="pt_v9[^"]*"[^>]*>\s*(?:<!--[^>]*-->)?\s*([\d.,]+))?',
        html,
        re.DOTALL,
    )

    if items:
        for product_id, href, title, price_str in items:
            if href.startswith("/"):
                href = f"https://www.akakce.com{href}"
            price = _parse_price(price_str) if price_str else None
            results.append(AkakceSearchResult(title=title, url=href, price=price))
        return results

    # Fallback: broader li match
    items = re.findall(
        r'<li\s+data-pr="(\d+)"[^>]*>(.*?)</li>',
        html,
        re.DOTALL,
    )
    for product_id, li_html in items:
        title_match = re.search(r'title="([^"]{5,})"', li_html)
        href_match = re.search(r'href="(/[^"]+\.html[^"]*)"', li_html)
        if not title_match or not href_match:
            continue

        title = title_match.group(1)
        href = href_match.group(1)
        if href.startswith("/"):
            href = f"https://www.akakce.com{href}"

        price = _extract_price_from_li(li_html)
        results.append(AkakceSearchResult(title=title, url=href, price=price))

    return results


# ── Dedup ───────────────────────────────────────────────────────────────────


async def _dedup_candidates(
    candidates: list[AkakceSearchResult],
    existing_titles: list[str],
) -> tuple[list[AkakceSearchResult], int]:
    """
    Adaylari mevcut urunlerle karsilastirip yenileri doner.
    1. Jaccard > 0.5 → duplicate (atla)
    2. Jaccard < 0.2 → yeni (ekle)
    3. Jaccard 0.2-0.5 → Haiku batch ile kontrol

    Returns: (new_products, haiku_call_count)
    """
    if not existing_titles:
        return candidates, 0

    # Mevcut title'larin normalize edilmis formunu once hesapla
    existing_normalized = [(t, _normalize(t)) for t in existing_titles]

    new_products: list[AkakceSearchResult] = []
    uncertain: list[AkakceSearchResult] = []

    for candidate in candidates:
        cand_words = _normalize(candidate.title)
        if not cand_words:
            continue

        max_jaccard = 0.0
        for _, ex_words in existing_normalized:
            if not ex_words:
                continue
            intersection = cand_words & ex_words
            union = cand_words | ex_words
            score = len(intersection) / len(union)
            if score > max_jaccard:
                max_jaccard = score

        if max_jaccard > 0.5:
            # Yuksek benzerlik → duplicate
            continue
        elif max_jaccard < 0.2:
            # Dusuk benzerlik → yeni urun
            new_products.append(candidate)
        else:
            # Belirsiz → Haiku ile kontrol gerekli
            uncertain.append(candidate)

    # Haiku batch dedup (belirsiz olanlar icin)
    haiku_calls = 0
    if uncertain:
        is_new_flags, calls = await _haiku_batch_dedup(uncertain, existing_titles)
        haiku_calls = calls
        for candidate, is_new in zip(uncertain, is_new_flags):
            if is_new:
                new_products.append(candidate)

    return new_products, haiku_calls


async def _haiku_batch_dedup(
    candidates: list[AkakceSearchResult],
    existing_titles: list[str],
) -> tuple[list[bool], int]:
    """
    Haiku ile batch dedup. 10 aday urun tek cagri.
    Returns: (is_new_flags, call_count)
    """
    from app.config import settings

    if not settings.anthropic_api_key:
        # API key yoksa hepsini yeni say
        return [True] * len(candidates), 0

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    is_new_flags: list[bool] = []
    call_count = 0
    batch_size = 10

    # Mevcut urunlerden ozetlenmis liste (max 100 — token tasarrufu)
    existing_sample = existing_titles[:100]
    existing_text = "\n".join(f"- {t}" for t in existing_sample)

    for i in range(0, len(candidates), batch_size):
        batch = candidates[i : i + batch_size]
        candidate_lines = "\n".join(
            f"{j + 1}. {c.title}" for j, c in enumerate(batch)
        )

        prompt = (
            "Aşağıdaki numaralı ürünlerden hangisi mevcut listede zaten var?\n"
            "Sadece MEVCUT listede olan ürünlerin numaralarını virgülle yaz.\n"
            "Hiçbiri yoksa 'YOK' yaz.\n\n"
            f"Mevcut ürünler:\n{existing_text}\n\n"
            f"Kontrol edilecek ürünler:\n{candidate_lines}"
        )

        try:
            resp = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            call_count += 1
            answer = resp.content[0].text.strip()

            # Parse answer: "1, 3, 5" or "YOK"
            if "YOK" in answer.upper():
                duplicate_nums = set()
            else:
                duplicate_nums = set()
                for num_match in re.finditer(r"(\d+)", answer):
                    num = int(num_match.group(1))
                    if 1 <= num <= len(batch):
                        duplicate_nums.add(num)

            for j in range(len(batch)):
                is_new_flags.append((j + 1) not in duplicate_nums)

        except Exception as e:
            print(f"[category_crawler] Haiku dedup hatası: {e}", flush=True)
            call_count += 1
            # Hata durumunda hepsini yeni say
            is_new_flags.extend([True] * len(batch))

    return is_new_flags, call_count


# ── DB Kayit ────────────────────────────────────────────────────────────────


async def _get_category_id(db: AsyncSession, slug: str) -> str | None:
    """Kategori slug'ından ID döner."""
    result = await db.execute(select(Category.id).where(Category.slug == slug))
    row = result.first()
    return row[0] if row else None


async def _save_new_product(
    akakce_result: AkakceSearchResult,
    category_slug: str,
    category_id: str | None,
    db: AsyncSession,
) -> Product | None:
    """
    Yeni urunu DB'ye kaydet.
    Ayni title + brand varsa atlar (son savunma hatti).
    """
    title = akakce_result.title
    full_url = (
        akakce_result.url
        if akakce_result.url.startswith("http")
        else f"https://www.akakce.com{akakce_result.url}"
    )

    # Brand extraction
    brand = None
    extracted_brand, cleaned_title = _extract_brand_from_title(title)
    if extracted_brand:
        brand = extracted_brand
        title = cleaned_title
    else:
        # Title'in ilk kelimesini brand olarak dene
        parts = title.split(None, 1)
        if len(parts) == 2:
            from app.services.akakce.importer import _KNOWN_BRANDS
            first_word = parts[0]
            for kb in _KNOWN_BRANDS:
                if first_word.lower() == kb.lower():
                    brand = kb
                    title = parts[1]
                    break

    # Son savunma: ayni title + brand varsa atla
    dup_q = select(Product.id).where(Product.title == title)
    if brand:
        dup_q = dup_q.where(Product.brand == brand)
    dup = (await db.execute(dup_q)).first()
    if dup:
        return None

    # URL dedup (ayni akakce URL varsa atla)
    url_dup = (await db.execute(
        select(Product.id).where(Product.akakce_url == full_url)
    )).first()
    if url_dup:
        return None

    # Product olustur
    product = Product(
        title=title,
        brand=brand,
        category_id=category_id,
        akakce_url=full_url,
    )
    db.add(product)
    await db.flush()

    # Default variant olustur
    variant = ProductVariant(
        product_id=product.id,
        attributes={},
    )
    db.add(variant)

    # ProductStore olustur (Akakce kaynagi olarak)
    store = ProductStore(
        product_id=product.id,
        store=StoreName.OTHER,
        url=full_url,
        current_price=akakce_result.price,
        currency="TRY",
        is_active=True,
        check_priority=3,
    )
    db.add(store)
    await db.flush()

    print(f"[category_crawler] + {brand or ''} {title[:60]}", flush=True)
    return product
