import re
import json
from decimal import Decimal
import httpx
from app.services.scraper.base import BaseScraper, ScrapedProduct

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class TrendyolScraper(BaseScraper):
    store_name = "trendyol"

    def can_handle(self, url: str) -> bool:
        return "trendyol.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        product_id = self._extract_product_id(url)

        # Trendyol'un internal API'sini kullan
        if product_id:
            result = await self._scrape_via_api(url, product_id)
            if result:
                return result

        # Fallback: HTML'den JSON parse et
        return await self._scrape_via_html(url)

    async def _scrape_via_api(self, url: str, product_id: str) -> ScrapedProduct | None:
        """Trendyol internal product API'si üzerinden veri çeker."""
        api_url = (
            f"https://public.trendyol.com/discovery-web-productgw-service/api/"
            f"renderingserviceproductpage/pdp/{product_id}?channelId=1&gender=na"
        )
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(api_url, headers={
                    **HEADERS,
                    "Accept": "application/json",
                    "Referer": "https://www.trendyol.com/",
                })
                if resp.status_code != 200:
                    return None

                data = resp.json()
                result = data.get("result", {})
                product = result.get("product", {})

                if not product:
                    return None

                title = product.get("name", "")
                brand = product.get("brand", {}).get("name")

                # Fiyat
                price_info = product.get("price", {})
                current_price = Decimal(str(price_info.get("discountedPrice", {}).get("value", 0) or
                                           price_info.get("originalPrice", {}).get("value", 0)))
                original_price_val = price_info.get("originalPrice", {}).get("value")
                original_price = Decimal(str(original_price_val)) if original_price_val else None

                # Görsel
                images = product.get("images", [])
                image_url = None
                if images:
                    img = images[0]
                    image_url = f"https://cdn.dsmcdn.com{img}" if img.startswith("/") else img

                in_stock = product.get("inStock", True)

                return ScrapedProduct(
                    title=title.strip(),
                    url=url,
                    store=self.store_name,
                    current_price=current_price,
                    original_price=original_price,
                    brand=brand,
                    image_url=image_url,
                    store_product_id=product_id,
                    in_stock=in_stock,
                )
        except Exception:
            return None

    async def _scrape_via_html(self, url: str) -> ScrapedProduct:
        """HTML içindeki window.__PRODUCT_DETAIL_APP_INITIAL_STATE__ JSON'unu parse eder."""
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
            html = resp.text

        # Embedded JSON'u bul
        match = re.search(
            r"window\.__PRODUCT_DETAIL_APP_INITIAL_STATE__\s*=\s*(\{.*?\});?\s*(?:window\.|</script>)",
            html,
            re.DOTALL,
        )
        if not match:
            raise ValueError("Ürün verisi HTML içinde bulunamadı")

        data = json.loads(match.group(1))
        product = data.get("product", {})

        title = product.get("name", "")
        brand_info = product.get("brand", {})
        brand = brand_info.get("name") if isinstance(brand_info, dict) else None

        price_info = product.get("priceInfo", {})
        current_price = Decimal(str(price_info.get("discountedPrice", 0) or price_info.get("price", 0)))
        original_price_val = price_info.get("price")
        original_price = Decimal(str(original_price_val)) if original_price_val and original_price_val != price_info.get("discountedPrice") else None

        images = product.get("images", [])
        image_url = f"https://cdn.dsmcdn.com{images[0]}" if images else None

        in_stock = not product.get("isOutOfStock", False)

        return ScrapedProduct(
            title=title.strip(),
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            brand=brand,
            image_url=image_url,
            store_product_id=self._extract_product_id(url),
            in_stock=in_stock,
        )

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-p-(\d+)", url)
        return match.group(1) if match else None
