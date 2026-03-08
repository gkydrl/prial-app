"""
Trendyol arama adaptörü.
Önce direkt API dener (0 kredi), başarısız olursa ScraperAPI ile
arama sayfası HTML'ini çeker ve regex ile ürün linklerini parse eder.
"""
import re
from decimal import Decimal
from urllib.parse import urlencode, quote_plus

import httpx

from app.services.scraper.base import scraper_api_url
from app.services.store_search.base import BaseSearcher, SearchResult

# Direkt istek için browser-like header'lar
_DIRECT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.trendyol.com/",
    "Origin": "https://www.trendyol.com",
}


class TrendyolSearcher(BaseSearcher):
    store_name = "trendyol"

    _SEARCH_API = (
        "https://public.trendyol.com/discovery-web-searchgw-service/v2/api/infinite-scroll/"
        "sr"
    )

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        # 1) Direkt API dene (0 kredi)
        data = await self._fetch_direct_api(query)
        if data:
            results = self._parse_api_results(data, limit)
            if results:
                return results

        # 2) ScraperAPI ile API dene (1 kredi)
        data = await self._fetch_proxy_api(query)
        if data:
            results = self._parse_api_results(data, limit)
            if results:
                return results

        # 3) ScraperAPI ile arama sayfası HTML (1 kredi)
        html = await self._fetch_search_html(query)
        if html:
            return self._parse_html_results(html, limit)

        return []

    async def _fetch_direct_api(self, query: str) -> dict | None:
        params = {
            "q": query,
            "pi": "1",
            "storefrontId": "1",
            "culture": "tr-TR",
            "userGenderId": "1",
            "pId": "0",
            "scoringAlgorithmId": "2",
            "categoryRelevancyEnabled": "false",
            "isLegalRequirementConfirmed": "false",
            "searchStrategyType": "DEFAULT",
            "productStampType": "TypeA",
        }
        url = self._SEARCH_API + "?" + urlencode(params)
        try:
            async with httpx.AsyncClient(timeout=15, headers=_DIRECT_HEADERS) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            print(f"[trendyol_search] Direkt API hata ({query}): {e}", flush=True)
        return None

    async def _fetch_proxy_api(self, query: str) -> dict | None:
        params = {
            "q": query,
            "pi": "1",
            "storefrontId": "1",
            "culture": "tr-TR",
            "userGenderId": "1",
            "pId": "0",
            "scoringAlgorithmId": "2",
            "categoryRelevancyEnabled": "false",
            "isLegalRequirementConfirmed": "false",
            "searchStrategyType": "DEFAULT",
            "productStampType": "TypeA",
        }
        target = self._SEARCH_API + "?" + urlencode(params)
        proxy_url = scraper_api_url(target, render=False)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(proxy_url)
                if resp.status_code == 200:
                    return resp.json()
                print(f"[trendyol_search] Proxy API HTTP {resp.status_code} ({query})", flush=True)
        except Exception as e:
            print(f"[trendyol_search] Proxy API hata ({query}): {type(e).__name__}", flush=True)
        return None

    async def _fetch_search_html(self, query: str) -> str | None:
        """Son çare: Trendyol arama sayfası HTML'ini ScraperAPI ile çek."""
        search_url = f"https://www.trendyol.com/sr?q={quote_plus(query)}"
        proxy_url = scraper_api_url(search_url, render=False)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(proxy_url)
                if resp.status_code == 200 and len(resp.text) > 2000:
                    print(f"[trendyol_search] HTML fallback OK ({len(resp.text)} chars)", flush=True)
                    return resp.text
                print(f"[trendyol_search] HTML fallback HTTP {resp.status_code}", flush=True)
        except Exception as e:
            print(f"[trendyol_search] HTML fallback hata: {type(e).__name__}", flush=True)
        return None

    def _parse_api_results(self, data: dict, limit: int) -> list[SearchResult]:
        products = (
            data.get("result", {}).get("products", [])
            or data.get("data", {}).get("products", [])
        )

        results: list[SearchResult] = []
        for p in products[:limit]:
            try:
                url = self._build_url(p)
                if not url:
                    continue

                price_info = p.get("price", {})
                price_val = (
                    price_info.get("discountedPrice", {}).get("value")
                    or price_info.get("sellingPrice", {}).get("value")
                    or price_info.get("originalPrice", {}).get("value")
                    or 0
                )
                price = Decimal(str(price_val))

                images = p.get("images", [])
                image_url = None
                if images:
                    img = images[0]
                    image_url = f"https://cdn.dsmcdn.com{img}" if str(img).startswith("/") else str(img)

                brand = p.get("brand", {}).get("name") if isinstance(p.get("brand"), dict) else p.get("brand")

                results.append(SearchResult(
                    title=p.get("name", "").strip(),
                    url=url,
                    store=self.store_name,
                    price=price,
                    image_url=image_url,
                    brand=brand,
                    store_product_id=str(p.get("id", "")),
                    in_stock=p.get("inStock", True),
                ))
            except Exception:
                continue

        return results

    def _parse_html_results(self, html: str, limit: int) -> list[SearchResult]:
        """Trendyol arama sayfası HTML'inden ürün linklerini regex ile çıkarır."""
        # Trendyol ürün URL pattern: /marka/urun-adi-p-123456
        urls = re.findall(r'href="(/[^"]*?-p-\d+[^"]*)"', html)
        seen = set()
        results = []

        for path in urls:
            # Temizle
            clean = path.split("?")[0]
            if clean in seen:
                continue
            seen.add(clean)

            full_url = f"https://www.trendyol.com{clean}"

            # URL'den title çıkar: /marka/urun-adi-p-123 → "urun adi"
            m = re.search(r'/[^/]+/(.+?)-p-\d+', clean)
            title = m.group(1).replace("-", " ").title() if m else ""

            results.append(SearchResult(
                title=title,
                url=full_url,
                store=self.store_name,
                price=Decimal("0"),
            ))
            if len(results) >= limit:
                break

        if results:
            print(f"[trendyol_search] HTML parse: {len(results)} ürün", flush=True)
        return results

    def _build_url(self, p: dict) -> str | None:
        url = p.get("url", "")
        if not url:
            return None
        if url.startswith("http"):
            return url
        return f"https://www.trendyol.com{url}"
