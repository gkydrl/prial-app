"""
Akakce urun sayfasindan magaza listesini parse eder.
Ilk 2 FARKLI marketplace'i doner.

Strateji:
1. ScraperAPI ile Akakce sayfasini cek (1 kredi, render=false — Cloudflare bypass)
2. ld+json ProductGroup/Product yapisindan offers'lari oku
   → direkt magaza URL'leri geliyor (redirect cozmeye gerek yok)
3. Fallback: HTML'deki <ul id="PL"> store listesini parse et
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin, quote

import httpx

from app.models.product import StoreName


@dataclass
class AkakceStoreListing:
    store_name: str                    # Normalized: "TRENDYOL", "HEPSIBURADA", etc.
    store_enum: StoreName | None       # Mapped enum or None for unknown stores
    price: float
    url: str                           # Direkt magaza URL'si (ld+json'dan)
    redirect_url: str | None = None    # Akakce redirect (fallback parse icin)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
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
    """Raw store/seller text -> (normalized_name, StoreName enum or None)."""
    cleaned = raw.strip().lower()
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

    1. ld+json'dan offers parse et (direkt URL'ler)
    2. Fallback: HTML store list parse et
    """
    html = await _fetch_akakce_page(akakce_url)
    if not html:
        return []

    # 1. ld+json'dan dene (en temiz kaynak)
    listings = _parse_ldjson_offers(html)

    # 2. Fallback: HTML parse
    if not listings:
        listings = _parse_html_listings(html)

    if not listings:
        return []

    # Deduplicate: her store'dan sadece en ucuzunu tut
    seen: dict[str, AkakceStoreListing] = {}
    for listing in listings:
        key = listing.store_name
        if key not in seen or listing.price < seen[key].price:
            seen[key] = listing

    # Fiyata gore sirala, ilk N unique store'u don
    result = sorted(seen.values(), key=lambda x: x.price)[:max_unique_stores]
    return result


# ── ld+json Parse ──────────────────────────────────────────────────────────


def _parse_ldjson_offers(html: str) -> list[AkakceStoreListing]:
    """
    ld+json structured data'dan store offers parse et.
    Akakce ProductGroup/Product icinde offers array'i var,
    her offer'da seller name, price ve direkt URL mevcut.
    """
    listings: list[AkakceStoreListing] = []

    # Tum ld+json script bloklarini bul
    scripts = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )

    for script_text in scripts:
        try:
            data = json.loads(script_text.strip())
        except (json.JSONDecodeError, ValueError):
            continue

        # offers direkt root'ta veya @graph icinde olabilir
        offers = _extract_offers(data)
        for offer in offers:
            listing = _parse_single_offer(offer)
            if listing:
                listings.append(listing)

    return listings


def _extract_offers(data: dict | list) -> list[dict]:
    """ld+json yapisindan tum offer'lari cikar."""
    offers: list[dict] = []

    if isinstance(data, list):
        for item in data:
            offers.extend(_extract_offers(item))
        return offers

    if not isinstance(data, dict):
        return offers

    # @graph varsa icine bak
    if "@graph" in data:
        for item in data["@graph"]:
            offers.extend(_extract_offers(item))

    # offers alanini kontrol et
    raw_offers = data.get("offers")
    if isinstance(raw_offers, dict):
        # Tek offer veya AggregateOffer
        if raw_offers.get("@type") == "AggregateOffer":
            inner = raw_offers.get("offers", [])
            if isinstance(inner, list):
                offers.extend(inner)
            elif isinstance(inner, dict):
                offers.append(inner)
        else:
            offers.append(raw_offers)
    elif isinstance(raw_offers, list):
        offers.extend(raw_offers)

    return offers


def _parse_single_offer(offer: dict) -> AkakceStoreListing | None:
    """Tek bir ld+json Offer'dan AkakceStoreListing olustur."""
    # Fiyat
    price = offer.get("price")
    if not price:
        price_spec = offer.get("priceSpecification", {})
        price = price_spec.get("price")
    if not price:
        return None
    try:
        price = float(price)
    except (ValueError, TypeError):
        return None
    if price <= 0:
        return None

    # URL
    url = offer.get("url", "")
    if not url:
        return None

    # Seller / store name
    seller = offer.get("seller", {})
    seller_name = ""
    if isinstance(seller, dict):
        seller_name = seller.get("name", "")
    elif isinstance(seller, str):
        seller_name = seller

    if not seller_name:
        # URL'den store tahmin et
        seller_name = _guess_store_from_url(url)

    if not seller_name:
        return None

    normalized, enum_val = _normalize_store_name(seller_name)

    return AkakceStoreListing(
        store_name=normalized,
        store_enum=enum_val,
        price=price,
        url=url,
    )


def _guess_store_from_url(url: str) -> str:
    """URL'den magaza adini tahmin et."""
    url_lower = url.lower()
    if "trendyol.com" in url_lower:
        return "trendyol"
    if "hepsiburada.com" in url_lower:
        return "hepsiburada"
    if "amazon.com.tr" in url_lower:
        return "amazon"
    if "n11.com" in url_lower:
        return "n11"
    if "mediamarkt" in url_lower:
        return "mediamarkt"
    if "teknosa.com" in url_lower:
        return "teknosa"
    if "vatanbilgisayar" in url_lower or "vatan.com" in url_lower:
        return "vatan"
    if "ciceksepeti" in url_lower:
        return "ciceksepeti"
    return ""


# ── HTML Fallback Parse ────────────────────────────────────────────────────


def _parse_html_listings(html: str) -> list[AkakceStoreListing]:
    """
    Fallback: HTML'deki store listesini parse et.
    <ul id="PL" class="pl_v9 ..."> icindeki <li> bloklari.
    """
    listings: list[AkakceStoreListing] = []

    # Store listing <li> bloklari — redirect linki olanlari bul
    li_blocks = re.findall(
        r'<li\b[^>]*>(.*?)</li>',
        html,
        re.DOTALL,
    )

    for li_html in li_blocks:
        # Redirect linki olmayan li'leri atla
        redirect_match = re.search(r'href="(/r/[^"]+)"', li_html)
        if not redirect_match:
            continue

        redirect_url = f"https://www.akakce.com{redirect_match.group(1)}"

        # Store name: span.vds_v8 veya img alt
        store_name = None
        m = re.search(r'class="[^"]*vds_[^"]*"[^>]*>([^<]+)<', li_html)
        if m:
            store_name = m.group(1).strip()
        if not store_name:
            m = re.search(r'<img[^>]+alt="([^"]{2,50})"', li_html)
            if m:
                store_name = m.group(1).strip()
        if not store_name:
            m = re.search(r'title="([^"]{2,50})"', li_html)
            if m:
                store_name = m.group(1).strip()

        if not store_name:
            continue

        # Price: span.pt_v8 veya pt_v9
        price = None
        m = re.search(r'class="[^"]*pt_[^"]*"[^>]*>([\s\S]*?)</span>', li_html)
        if m:
            price = _parse_price(m.group(1))
        if not price:
            m = re.search(r'([\d.]+,\d{2})\s*(?:TL|₺)?', li_html)
            if m:
                price = _parse_price(m.group(1))

        if not price or price <= 0:
            continue

        normalized, enum_val = _normalize_store_name(store_name)

        listings.append(AkakceStoreListing(
            store_name=normalized,
            store_enum=enum_val,
            price=price,
            url="",  # HTML'den direkt URL yok, redirect var
            redirect_url=redirect_url,
        ))

    return listings


def _parse_price(text: str) -> float | None:
    """Turkish price format parse: '12.345,67' or '12345'."""
    if not text:
        return None
    text = re.sub(r'[^\d.,]', '', text)
    if ',' in text and '.' in text:
        text = text.replace('.', '').replace(',', '.')
    elif ',' in text:
        text = text.replace(',', '.')
    else:
        text = re.sub(r'\.(?=\d{3})', '', text)
    try:
        return float(text)
    except ValueError:
        return None


# ── Page Fetch ─────────────────────────────────────────────────────────────


def _is_cloudflare_challenge(html: str) -> bool:
    """Cloudflare challenge sayfasi mi kontrol et."""
    return "Just a moment" in html[:2000] or "_cf_chl" in html[:5000]


async def _fetch_akakce_page(url: str) -> str | None:
    """
    Akakce sayfasini cek.
    1. Direkt dene (0 kredi)
    2. Cloudflare varsa veya basarisizsa → ScraperAPI render=false (1 kredi)
    """
    # 1. Direkt erisim
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        try:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200 and len(resp.text) > 500:
                if not _is_cloudflare_challenge(resp.text):
                    return resp.text
                print("[akakce/store_parser] Cloudflare tespit edildi, ScraperAPI'ye geciliyor", flush=True)
        except Exception as e:
            print(f"[akakce/store_parser] Direkt erisim hatasi: {e}", flush=True)

    # 2. ScraperAPI fallback (render=false, 1 kredi)
    from app.config import settings
    if not settings.scraper_api_key:
        return None

    try:
        proxy_url = (
            f"http://api.scraperapi.com"
            f"?api_key={settings.scraper_api_key}"
            f"&url={quote(url, safe='')}"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(proxy_url)
            if resp.status_code == 200 and len(resp.text) > 500:
                if _is_cloudflare_challenge(resp.text):
                    print("[akakce/store_parser] ScraperAPI de Cloudflare gecemedi", flush=True)
                    return None
                return resp.text
    except Exception as e:
        print(f"[akakce/store_parser] ScraperAPI hatasi: {e}", flush=True)

    return None
