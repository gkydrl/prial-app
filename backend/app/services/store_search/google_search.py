"""
Google arama adaptörü.
ScraperAPI'nin /search endpoint'ini kullanarak Google'da ürün arar.
Trendyol, Hepsiburada, Amazon TR, MediaMarkt, Vatan, N11 ve diğer
tüm Türk e-ticaret sitelerini tek sorguda kapsar.
"""
import re
from urllib.parse import urlencode

import httpx

from app.services.scraper.base import scraper_api_url
from app.services.store_search.base import BaseSearcher, SearchResult
from decimal import Decimal

# Ürün sayfası olduğunu güçlü biçimde gösteren URL pattern'leri
_PRODUCT_URL_PATTERNS = [
    re.compile(r"-p-\d+"),              # Trendyol: /urun-adi-p-123456
    re.compile(r"-pm-[A-Z0-9]+"),       # Hepsiburada: /urun-pm-XXXXX
    re.compile(r"-p-[A-Z][A-Z0-9]{7,}"),# Hepsiburada: /urun-p-HBCV00006Y4HBN
    re.compile(r"/dp/[A-Z0-9]{10}"),    # Amazon: /dp/B08XXXXX
    re.compile(r"/product/\d+"),        # Genel pattern
    re.compile(r"/urun[-/]"),           # Türkçe "ürün" içeren path
    re.compile(r"/p/\d+"),              # MediaMarkt, Teknosa ürün sayfası
]

# Kesinlikle ürün sayfası OLMAYAN domain'ler (fiyat karşılaştırma, sosyal medya, vb.)
_SKIP_DOMAINS = {
    "google.com", "google.com.tr",
    "youtube.com", "instagram.com", "facebook.com", "twitter.com",
    "wikipedia.org", "reddit.com",
    "akakce.com",       # Fiyat karşılaştırma
    "cimri.com",        # Fiyat karşılaştırma
    "incehesap.com",    # Fiyat karşılaştırma
    "fiyatlar.com",     # Fiyat karşılaştırma
    "sahibinden.com",   # İkinci el
    "letgo.com",        # İkinci el
    "apple.com",        # Marka sitesi (ürün sayfası ama mağaza değil)
    "samsung.com",
    "tommy.com",        # Marka sitesi
    "nike.com",
    "adidas.com",
}

_SKIP_PATH_KEYWORDS = [
    "/kategori/", "/category/", "/blog/", "/haber/", "/yorum/",
    "/search", "/ara?", "/liste/", "/collection/",
    # Trendyol kategori URL pattern'leri
    "-x-c",   # Trendyol kategori: /brand-x-c12345-v678
    "-x-b",   # Trendyol brand/kategori: /brand-x-b300-g2-c12345
    "-g2-c",  # Trendyol alt kategori
    # Teknosa/MediaMarkt kategori
    "/c-1",   # Teknosa: /iphone-c-100001
    # Amazon search/liste sayfaları
    "/s?k=",  # Amazon arama: /s?k=query
]


def _is_product_url(url: str) -> bool:
    """URL'nin bir ürün sayfası olup olmadığını heuristiklerle tahmin eder."""
    url_lower = url.lower()

    # Bilinen non-product domain'leri atla
    for domain in _SKIP_DOMAINS:
        if domain in url_lower:
            return False

    # Kategori/liste sayfası pattern'leri atla
    for keyword in _SKIP_PATH_KEYWORDS:
        if keyword in url_lower:
            # Trendyol-specific pattern'ler sadece trendyol URL'lerinde geçerli
            if keyword in ("-x-c", "-x-b", "-g2-c") and "trendyol.com" not in url_lower:
                continue
            return False

    # Skip domain/path filtresine takılmadıysa kabul et.
    # Scraper zaten fiyat bulamazsa eşleşmez, matcher da yanlış ürünleri reddeder.
    return True


class GoogleSearcher(BaseSearcher):
    store_name = "google"

    async def search(self, query: str, limit: int = 8) -> list[SearchResult]:
        """
        Google'da arama yapar ve ürün URL'lerini döner.
        ScraperAPI /search endpoint'i JSON sonuç döner.
        """
        params = {
            "query": query,
            "country_code": "tr",
            "hl": "tr",
            "num": min(limit * 3, 30),  # Filtreleme sonrası limit'e ulaşmak için fazla çek
        }
        target = "https://api.scraperapi.com/structured/google/search?" + urlencode(params)

        from app.config import settings
        url_with_key = target + f"&api_key={settings.scraper_api_key}"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(url_with_key)
                if resp.status_code != 200:
                    print(f"[google_search] HTTP {resp.status_code} ({query})")
                    return []
                data = resp.json()
        except Exception as e:
            print(f"[google_search] Hata ({query}): {e}")
            return []

        organic = data.get("organic_results", [])
        if not organic:
            print(f"[google_search] organic_results boş, keys: {list(data.keys())[:10]}", flush=True)
        results: list[SearchResult] = []

        for item in organic:
            url = item.get("link", "")
            if not url:
                continue
            if not _is_product_url(url):
                print(f"[google_search] Filtre: {url[:80]}", flush=True)
                continue

            title = item.get("title", "").strip()
            snippet = item.get("snippet", "")

            results.append(SearchResult(
                title=title or snippet[:100],
                url=url,
                store=self._store_from_url(url),
                price=Decimal("0"),   # Fiyatı scrape adımında alacağız
                image_url=None,
            ))

            if len(results) >= limit:
                break

        return results

    def _store_from_url(self, url: str) -> str:
        """URL'den store adını çıkarır."""
        try:
            from urllib.parse import urlparse
            hostname = urlparse(url).hostname or ""
            hostname = hostname.removeprefix("www.")
            # Bilinen store'lar
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
            if "ciceksepeti.com" in hostname:
                return "ciceksepeti"
            return hostname.split(".")[0]
        except Exception:
            return "other"
