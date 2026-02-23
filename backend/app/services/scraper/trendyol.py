import re
import json
from decimal import Decimal
import httpx
from app.services.scraper.base import BaseScraper, ScrapedProduct, scraper_api_url


class TrendyolScraper(BaseScraper):
    store_name = "trendyol"

    def can_handle(self, url: str) -> bool:
        return "trendyol.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        product_id = self._extract_product_id(url)

        if product_id:
            result = await self._scrape_via_api(url, product_id)
            if result:
                return result

        return await self._scrape_via_html(url)

    async def _scrape_via_api(self, url: str, product_id: str) -> ScrapedProduct | None:
        """Trendyol internal product API'si üzerinden ScraperAPI proxy ile çeker."""
        target = (
            f"https://public.trendyol.com/discovery-web-productgw-service/api/"
            f"renderingserviceproductpage/pdp/{product_id}?channelId=1&gender=na"
        )
        proxy_url = scraper_api_url(target, render=False)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(proxy_url)
                if resp.status_code != 200:
                    return None

                data = resp.json()
                result = data.get("result", {})
                product = result.get("product", {})
                if not product:
                    return None

                price_info = product.get("price", {})
                current_price = Decimal(str(
                    price_info.get("discountedPrice", {}).get("value", 0)
                    or price_info.get("originalPrice", {}).get("value", 0)
                ))
                original_price_val = price_info.get("originalPrice", {}).get("value")
                original_price = Decimal(str(original_price_val)) if original_price_val else None

                images = product.get("images", [])
                image_url = None
                if images:
                    img = images[0]
                    image_url = f"https://cdn.dsmcdn.com{img}" if img.startswith("/") else img

                return ScrapedProduct(
                    title=product.get("name", "").strip(),
                    url=url,
                    store=self.store_name,
                    current_price=current_price,
                    original_price=original_price,
                    brand=product.get("brand", {}).get("name"),
                    image_url=image_url,
                    store_product_id=product_id,
                    in_stock=product.get("inStock", True),
                )
        except Exception:
            return None

    async def _scrape_via_html(self, url: str) -> ScrapedProduct:
        """HTML içindeki embedded JSON'u ScraperAPI üzerinden parse eder."""
        proxy_url = scraper_api_url(url, render=True)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(proxy_url)
            resp.raise_for_status()
            html = resp.text

        match = re.search(
            r"window\.__PRODUCT_DETAIL_APP_INITIAL_STATE__\s*=\s*(\{[\s\S]*?\});\s*(?:window\.|</script>)",
            html,
        )
        if not match:
            raise ValueError("Ürün verisi HTML içinde bulunamadı")

        data = json.loads(match.group(1))
        product = data.get("product", {})

        price_info = product.get("priceInfo", {})
        current_price = Decimal(str(
            price_info.get("discountedPrice", 0) or price_info.get("price", 0)
        ))
        original_price_val = price_info.get("price")
        original_price = (
            Decimal(str(original_price_val))
            if original_price_val and original_price_val != price_info.get("discountedPrice")
            else None
        )

        images = product.get("images", [])
        image_url = f"https://cdn.dsmcdn.com{images[0]}" if images else None

        return ScrapedProduct(
            title=product.get("name", "").strip(),
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            image_url=image_url,
            store_product_id=self._extract_product_id(url),
            in_stock=not product.get("isOutOfStock", False),
        )

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-p-(\d+)", url)
        return match.group(1) if match else None
