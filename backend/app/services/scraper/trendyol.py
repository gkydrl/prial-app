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
        """ScraperAPI (render=False) ile HTML çeker, ld+json'dan ürün bilgisi parse eder."""
        proxy_url = scraper_api_url(url, render=False)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(proxy_url)
            resp.raise_for_status()
            html = resp.text

        return self._parse_ld_json(url, html)

    def _parse_ld_json(self, url: str, html: str) -> ScrapedProduct:
        """HTML içindeki application/ld+json ProductGroup verisini parse eder."""
        matches = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )

        product_data: dict = {}
        for raw in matches:
            try:
                d = json.loads(raw.strip())
                if d.get("@type") in ("ProductGroup", "Product"):
                    product_data = d
                    break
            except json.JSONDecodeError:
                continue

        if not product_data:
            raise ValueError("Trendyol ld+json ürün verisi bulunamadı")

        title = product_data.get("name", "").strip()
        brand = product_data.get("manufacturer") or product_data.get("brand", {}).get("name")

        # Görsel
        image_raw = product_data.get("image", {})
        image_url: str | None = None
        if isinstance(image_raw, dict):
            content_urls = image_raw.get("contentUrl", [])
            image_url = content_urls[0] if content_urls else None
        elif isinstance(image_raw, str):
            image_url = image_raw

        # Fiyat
        offers = product_data.get("offers", {})
        current_price = Decimal(str(offers.get("price", 0) or 0))
        original_price: Decimal | None = None
        high_price = offers.get("highPrice")
        if high_price and Decimal(str(high_price)) > current_price:
            original_price = Decimal(str(high_price))

        # Stok
        availability = offers.get("availability", "")
        in_stock = "OutOfStock" not in availability

        store_product_id = self._extract_product_id(url)

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            brand=brand,
            image_url=image_url,
            store_product_id=store_product_id,
            in_stock=in_stock,
        )

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-p-(\d+)", url)
        return match.group(1) if match else None
