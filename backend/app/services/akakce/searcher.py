"""
Akakce'de urun arama ve eslestirme.
catalog_matcher.py'deki _fuzzy_title_match() ve _normalize() fonksiyonlarini reuse eder.

Akakce arama sonuclari statik HTML'de geliyor (SSR), Playwright gereksiz.
httpx ile dogrudan cekilir.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

import httpx

from app.services.catalog_matcher import _normalize


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.akakce.com/",
}


@dataclass
class AkakceSearchResult:
    title: str
    url: str
    price: float | None = None


async def search_akakce(query: str) -> list[AkakceSearchResult]:
    """
    Akakce'de arama yapar ve sonuclari doner.
    Statik HTML parse — Playwright gerekmez.
    """
    encoded = urllib.parse.quote_plus(query)
    search_url = f"https://www.akakce.com/arama/?q={encoded}"

    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            resp = await client.get(search_url)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        print(f"[akakce/searcher] HTTP hatası: {e}", flush=True)
        return []

    results: list[AkakceSearchResult] = []

    # Parse product items from ul.pl_v9 > li[data-pr]
    # Each li has: data-pr (id), a[title] (name), a[href] (url), span.pt_v9 (price)
    items = re.findall(
        r'<li\s+data-pr="(\d+)"[^>]*>.*?'
        r'<a\s+href="([^"]+)"\s+title="([^"]+)".*?'
        r'(?:<span\s+class="pt_v9[^"]*"[^>]*>\s*(?:<!--[^>]*-->)?\s*([\d.,]+))?',
        html,
        re.DOTALL,
    )

    if not items:
        # Fallback: try broader pattern
        items = re.findall(
            r'<li\s+data-pr="(\d+)"[^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )
        for product_id, li_html in items[:15]:
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

    for product_id, href, title, price_str in items[:15]:
        if href.startswith("/"):
            href = f"https://www.akakce.com{href}"

        price = _parse_price(price_str) if price_str else None
        results.append(AkakceSearchResult(title=title, url=href, price=price))

    return results


async def find_akakce_url(product_title: str, brand: str | None = None) -> str | None:
    """
    Bir Prial urunu icin Akakce'deki en iyi eslesen URL'yi bulur.
    """
    query = f"{brand} {product_title}" if brand else product_title
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

    if best_match and best_score >= 0.30:
        print(f"[akakce/searcher] Eşleşme bulundu (score={best_score:.2f}): {best_match.title}", flush=True)
        return best_match.url

    print(f"[akakce/searcher] Yeterli eşleşme yok (best={best_score:.2f}): {query}", flush=True)
    return None


def _extract_price_from_li(li_html: str) -> float | None:
    """li HTML'inden fiyat cikar."""
    # Pattern: 79.068,74 TL or similar inside pt_v9
    match = re.search(r'class="pt_v9[^"]*"[^>]*>[\s\S]*?([\d.]+)[,<]', li_html)
    if match:
        return _parse_price(match.group(1))
    return None


def _parse_price(text: str) -> float | None:
    """'12.345' veya '12345' formatindaki fiyati parse et."""
    if not text:
        return None
    text = re.sub(r'[^\d.]', '', text)
    # Remove thousands separator dots
    text = re.sub(r'\.(?=\d{3})', '', text)
    try:
        return float(text)
    except ValueError:
        return None
