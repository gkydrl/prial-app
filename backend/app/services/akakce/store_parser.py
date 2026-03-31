"""
Akakce urun sayfasindan magaza listesini parse eder.
Ilk 2 FARKLI marketplace'i doner (ayni store'dan en ucuzunu alir).

Akakce urun sayfasinda magaza listesi `<ul class="pl_v8">` icinde `<li>` olarak yer alir.
Her li icinde:
  - Magaza adi: alt img veya span icinde
  - Fiyat: span.pt_v8 icinde
  - Redirect link: a[href="/r/..."]
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx

from app.models.product import StoreName


@dataclass
class AkakceStoreListing:
    store_name: str          # Normalized: "trendyol", "hepsiburada", etc.
    store_enum: StoreName | None  # Mapped enum or None for unknown stores
    price: float
    redirect_url: str        # Akakce redirect link (e.g. https://www.akakce.com/r/...)
    final_url: str | None = None  # Resolved marketplace URL (UTM stripped)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.akakce.com/",
}

# Store name normalization map
_STORE_MAP: dict[str, StoreName] = {
    "trendyol": StoreName.TRENDYOL,
    "hepsiburada": StoreName.HEPSIBURADA,
    "amazon": StoreName.AMAZON,
    "n11": StoreName.N11,
    "ciceksepeti": StoreName.CICEKSEPETI,
    "çiçeksepeti": StoreName.CICEKSEPETI,
    "mediamarkt": StoreName.MEDIAMARKT,
    "media markt": StoreName.MEDIAMARKT,
    "teknosa": StoreName.TEKNOSA,
    "vatan": StoreName.VATAN,
    "vatan bilgisayar": StoreName.VATAN,
    "vatanbilgisayar": StoreName.VATAN,
}


def _normalize_store_name(raw: str) -> tuple[str, StoreName | None]:
    """Raw store text -> (normalized_name, StoreName enum or None)."""
    cleaned = raw.strip().lower()
    # Remove common suffixes
    for suffix in [".com", ".com.tr", " marketplace"]:
        cleaned = cleaned.removesuffix(suffix)
    cleaned = cleaned.strip()

    for key, enum_val in _STORE_MAP.items():
        if key in cleaned:
            return enum_val.value, enum_val

    return cleaned, None


async def parse_store_listings(
    akakce_url: str,
    max_unique_stores: int = 2,
) -> list[AkakceStoreListing]:
    """
    Akakce urun sayfasindan magaza listesini parse eder.
    Ilk N FARKLI marketplace'i doner (ayni store'dan en ucuzunu alir).
    """
    html = await _fetch_akakce_page(akakce_url)
    if not html:
        return []

    listings = _parse_listings_html(html)
    if not listings:
        return []

    # Deduplicate: keep cheapest per store
    seen: dict[str, AkakceStoreListing] = {}
    for listing in listings:
        key = listing.store_name
        if key not in seen:
            seen[key] = listing
        # Already sorted by price (Akakce default), so first is cheapest

    # Return first N unique stores
    result = list(seen.values())[:max_unique_stores]
    return result


def _parse_listings_html(html: str) -> list[AkakceStoreListing]:
    """
    Parse store listings from Akakce product page HTML.
    Tries multiple patterns since Akakce layout can vary.
    """
    listings: list[AkakceStoreListing] = []

    # Pattern 1: <li> items with store info and price
    # Akakce uses <ul class="pl_v8"> or similar, with <li> per store
    li_blocks = re.findall(
        r'<li\b[^>]*(?:class="[^"]*(?:p[lr]_|dp_)[^"]*")[^>]*>(.*?)</li>',
        html,
        re.DOTALL,
    )

    if not li_blocks:
        # Fallback: broader li pattern within product store area
        li_blocks = re.findall(
            r'<li\b[^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )

    for li_html in li_blocks:
        listing = _parse_single_listing(li_html)
        if listing:
            listings.append(listing)

    # Pattern 2: Try <a> blocks with /r/ redirect pattern
    if not listings:
        redirect_blocks = re.findall(
            r'<a\s+href="(/r/[^"]+)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )
        for href, inner in redirect_blocks:
            store_name = _extract_store_name(inner)
            price = _extract_price(inner)
            if store_name and price and price > 0:
                normalized, enum_val = _normalize_store_name(store_name)
                listings.append(AkakceStoreListing(
                    store_name=normalized,
                    store_enum=enum_val,
                    price=price,
                    redirect_url=f"https://www.akakce.com{href}",
                ))

    return listings


def _parse_single_listing(li_html: str) -> AkakceStoreListing | None:
    """Parse a single <li> block for store info."""
    # Must have a redirect link
    redirect_match = re.search(r'href="(/r/[^"]+)"', li_html)
    if not redirect_match:
        return None

    redirect_url = f"https://www.akakce.com{redirect_match.group(1)}"

    # Extract store name from img alt, title attr, or text
    store_name = _extract_store_name(li_html)
    if not store_name:
        return None

    # Extract price
    price = _extract_price(li_html)
    if not price or price <= 0:
        return None

    normalized, enum_val = _normalize_store_name(store_name)

    return AkakceStoreListing(
        store_name=normalized,
        store_enum=enum_val,
        price=price,
        redirect_url=redirect_url,
    )


def _extract_store_name(html_fragment: str) -> str | None:
    """Extract store name from HTML fragment."""
    # 1. img alt attribute (most common)
    m = re.search(r'<img[^>]+alt="([^"]{2,50})"', html_fragment)
    if m:
        name = m.group(1).strip()
        if name and not name.startswith("http"):
            return name

    # 2. title attribute on link
    m = re.search(r'title="([^"]{2,50})"', html_fragment)
    if m:
        name = m.group(1).strip()
        if name and not name.startswith("http"):
            return name

    # 3. span with store class
    m = re.search(r'class="[^"]*(?:v_|dp_s|mc_)[^"]*"[^>]*>([^<]{2,50})<', html_fragment)
    if m:
        return m.group(1).strip()

    return None


def _extract_price(html_fragment: str) -> float | None:
    """Extract price from HTML fragment."""
    # Pattern: class="pt_v8" or similar price class
    m = re.search(r'class="[^"]*pt_[^"]*"[^>]*>[\s\S]*?([\d.]+(?:,\d+)?)', html_fragment)
    if m:
        return _parse_price(m.group(1))

    # Fallback: any price-like pattern after store name
    m = re.search(r'([\d.]+(?:,\d{2}))\s*(?:TL|₺)?', html_fragment)
    if m:
        return _parse_price(m.group(1))

    return None


def _parse_price(text: str) -> float | None:
    """Parse Turkish price format: '12.345,67' or '12345'."""
    if not text:
        return None
    text = re.sub(r'[^\d.,]', '', text)
    # Turkish format: 115.817,03 → 115817.03
    if ',' in text and '.' in text:
        text = text.replace('.', '').replace(',', '.')
    elif ',' in text:
        text = text.replace(',', '.')
    else:
        # Only dots → remove thousands separators
        text = re.sub(r'\.(?=\d{3})', '', text)
    try:
        return float(text)
    except ValueError:
        return None


async def _fetch_akakce_page(url: str) -> str | None:
    """Fetch Akakce product page HTML (direct, no proxy needed)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        try:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
        except Exception as e:
            print(f"[akakce/store_parser] Sayfa alma hatası: {e}", flush=True)

    # ScraperAPI fallback
    from app.config import settings
    if settings.scraper_api_key:
        try:
            from urllib.parse import quote
            proxy_url = (
                f"http://api.scraperapi.com"
                f"?api_key={settings.scraper_api_key}"
                f"&url={quote(url, safe='')}"
            )
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(proxy_url)
                if resp.status_code == 200 and len(resp.text) > 500:
                    return resp.text
        except Exception as e:
            print(f"[akakce/store_parser] ScraperAPI hatası: {e}", flush=True)

    return None


async def resolve_redirect(redirect_url: str) -> str | None:
    """
    Akakce redirect URL'sini takip edip gerçek mağaza URL'sini al.
    UTM parametrelerini temizle.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.head(redirect_url, headers=HEADERS)
            final_url = str(resp.url)

        # Strip query params (UTM etc.)
        if "?" in final_url:
            final_url = final_url.split("?")[0]

        return final_url
    except Exception as e:
        print(f"[akakce/store_parser] Redirect çözme hatası: {e}", flush=True)
        return None
