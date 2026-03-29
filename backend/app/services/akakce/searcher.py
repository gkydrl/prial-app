"""
Akakce'de urun arama ve eslestirme.
catalog_matcher.py'deki _fuzzy_title_match() ve _normalize() fonksiyonlarini reuse eder.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from app.services.akakce.browser import get_page, random_delay, wait_for_cloudflare
from app.services.catalog_matcher import _fuzzy_title_match, _normalize


@dataclass
class AkakceSearchResult:
    title: str
    url: str
    price: float | None = None


async def search_akakce(query: str) -> list[AkakceSearchResult]:
    """
    Akakce'de arama yapar ve sonuclari doner.
    Returns: list of AkakceSearchResult (title, url, price)
    """
    encoded = urllib.parse.quote_plus(query)
    search_url = f"https://www.akakce.com/arama/?q={encoded}"

    async with get_page() as page:
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            passed = await wait_for_cloudflare(page)
            if not passed:
                print(f"[akakce/searcher] Cloudflare gecilmedi: {query}", flush=True)
                return []

            # Wait for search results to load
            await page.wait_for_selector("li.pl_v8, ul.pl_v8 li, div.pl_v8", timeout=10000)

        except Exception as e:
            print(f"[akakce/searcher] Sayfa yukleme hatasi: {e}", flush=True)
            return []

        results: list[AkakceSearchResult] = []

        # Try multiple selectors — Akakce may use different layouts
        items = await page.query_selector_all("li.pl_v8")
        if not items:
            items = await page.query_selector_all("ul.pl_v8 li")
        if not items:
            items = await page.query_selector_all("div.p_w")

        for item in items[:10]:  # Max 10 results
            try:
                # Title + URL
                link_el = await item.query_selector("a[title], a.pl_v8_img, a")
                if not link_el:
                    continue

                title = await link_el.get_attribute("title")
                if not title:
                    title = (await link_el.inner_text()).strip()
                href = await link_el.get_attribute("href")

                if not title or not href:
                    continue

                # Build full URL
                if href.startswith("/"):
                    href = f"https://www.akakce.com{href}"

                # Price (optional)
                price = None
                price_el = await item.query_selector("span.pt_v8, span.fiyat, span.prc")
                if price_el:
                    price_text = (await price_el.inner_text()).strip()
                    price = _parse_price(price_text)

                results.append(AkakceSearchResult(title=title, url=href, price=price))
            except Exception:
                continue

    return results


async def find_akakce_url(product_title: str, brand: str | None = None) -> str | None:
    """
    Bir Prial urunu icin Akakce'deki en iyi eslesen URL'yi bulur.
    Input: urun adi + brand
    Returns: Akakce urun sayfasi URL'si veya None
    """
    # Search query olustur
    query = f"{brand} {product_title}" if brand else product_title
    # Uzun query'leri kisalt (Akakce arama limiti)
    words = query.split()
    if len(words) > 8:
        query = " ".join(words[:8])

    print(f"[akakce/searcher] Aranıyor: {query}", flush=True)

    results = await search_akakce(query)
    if not results:
        print(f"[akakce/searcher] Sonuç bulunamadı: {query}", flush=True)
        return None

    # Fuzzy match ile en iyi eslesmeyi bul
    catalog_label = f"{brand or ''} {product_title}".strip()
    best_match: AkakceSearchResult | None = None
    best_score = 0.0

    for r in results:
        cat_words = _normalize(catalog_label)
        scr_words = _normalize(r.title)
        if not cat_words or not scr_words:
            continue

        intersection = cat_words & scr_words
        union = cat_words | scr_words
        score = len(intersection) / len(union)

        if score > best_score:
            best_score = score
            best_match = r

    # Minimum threshold: 0.30 (Akakce titles may differ from catalog)
    if best_match and best_score >= 0.30:
        print(f"[akakce/searcher] Eşleşme bulundu (score={best_score:.2f}): {best_match.title}", flush=True)
        return best_match.url

    print(f"[akakce/searcher] Yeterli eşleşme yok (best={best_score:.2f}): {query}", flush=True)
    return None


def _parse_price(text: str) -> float | None:
    """'12.345,67 TL' veya '12.345 TL' formatindaki fiyati parse et."""
    import re
    text = text.replace("TL", "").replace("₺", "").strip()
    # Remove thousands separator dots, replace comma with dot for decimal
    text = re.sub(r'\.(?=\d{3})', '', text)
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None
