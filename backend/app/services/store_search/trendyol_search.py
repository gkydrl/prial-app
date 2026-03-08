"""
Trendyol arama adaptörü.
Önce direkt API dener (0 kredi), başarısız olursa ScraperAPI fallback (1 kredi).
"""
from decimal import Decimal
from urllib.parse import urlencode

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
        "https://public.trendyol.com/discovery-web-searchgw-service/api/filter/"
        "search/v2"
    )

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        params = {
            "q": query,
            "culture": "tr-TR",
            "channelId": "1",
            "userGenderId": "2",
            "searchStrategyType": "DEFAULT",
            "productStampType": "TypeA",
            "fixSlotProductAdsIncluded": "true",
        }
        target = self._SEARCH_API + "?" + urlencode(params)

        # 1) Direkt dene (0 kredi)
        data = await self._fetch_direct(target, query)
        # 2) Fallback: ScraperAPI (1 kredi)
        if data is None:
            data = await self._fetch_proxy(target, query)
        if data is None:
            return []

        return self._parse_results(data, limit)

    async def _fetch_direct(self, url: str, query: str) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=15, headers=_DIRECT_HEADERS) as client:
                resp = await client.get(url)
                if resp.status_code in (403, 429):
                    print(f"[trendyol_search] Direkt bloklandı ({resp.status_code}), fallback'e geçiliyor")
                    return None
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception as e:
            print(f"[trendyol_search] Direkt hata ({query}): {e}")
            return None

    async def _fetch_proxy(self, target: str, query: str) -> dict | None:
        proxy_url = scraper_api_url(target, render=False)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(proxy_url)
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception as e:
            print(f"[trendyol_search] Proxy hata ({query}): {e}")
            return None

    def _parse_results(self, data: dict, limit: int) -> list[SearchResult]:
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

    def _build_url(self, p: dict) -> str | None:
        url = p.get("url", "")
        if not url:
            return None
        if url.startswith("http"):
            return url
        return f"https://www.trendyol.com{url}"
