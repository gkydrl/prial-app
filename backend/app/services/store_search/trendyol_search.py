"""
Trendyol arama adaptörü.
public.trendyol.com arama API'sini ScraperAPI proxy üzerinden kullanır.
"""
from decimal import Decimal
from urllib.parse import urlencode

import httpx

from app.services.scraper.base import scraper_api_url
from app.services.store_search.base import BaseSearcher, SearchResult


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
        proxy_url = scraper_api_url(target, render=False)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(proxy_url)
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception as e:
            print(f"[trendyol_search] Hata ({query}): {e}")
            return []

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
