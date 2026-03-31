import re
import json
from decimal import Decimal
import httpx
from app.services.scraper.base import BaseScraper, ScrapedProduct, scraper_api_url

# Trendyol public API için browser-like header'lar
_DIRECT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.trendyol.com/",
    "Origin": "https://www.trendyol.com",
}


class TrendyolScraper(BaseScraper):
    store_name = "trendyol"

    def can_handle(self, url: str) -> bool:
        return "trendyol.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        product_id = self._extract_product_id(url)
        if product_id:
            # 1) Direkt API dene (0 kredi)
            result = await self._scrape_direct_api(url, product_id)
            if result:
                return result
            # 2) ScraperAPI fallback (1 kredi)
            result = await self._scrape_proxy_api(url, product_id)
            if result:
                return result
        # 3) HTML fallback — önce direkt, sonra ScraperAPI
        return await self._scrape_html_with_fallback(url)

    async def _scrape_direct_api(self, url: str, product_id: str) -> ScrapedProduct | None:
        """Direkt Trendyol API — 0 kredi."""
        target = (
            f"https://public.trendyol.com/discovery-web-productgw-service/api/"
            f"renderingserviceproductpage/pdp/{product_id}?channelId=1&gender=na"
        )
        try:
            async with httpx.AsyncClient(timeout=15, headers=_DIRECT_HEADERS) as client:
                resp = await client.get(target)
                if resp.status_code in (403, 429):
                    print(f"[trendyol] Direkt API bloklandı ({resp.status_code}), fallback'e geçiliyor")
                    return None
                if resp.status_code != 200:
                    return None
                return self._parse_api_response(url, product_id, resp.json())
        except Exception:
            return None

    async def _scrape_proxy_api(self, url: str, product_id: str) -> ScrapedProduct | None:
        """ScraperAPI proxy ile API — 1 kredi."""
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
                return self._parse_api_response(url, product_id, resp.json())
        except Exception:
            return None

    def _parse_api_response(self, url: str, product_id: str, data: dict) -> ScrapedProduct | None:
        """API JSON response'unu ScrapedProduct'a çevirir."""
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

        # Delivery info
        delivery_text, estimated_days = self._extract_delivery_from_api(result)

        # Installment info
        installment_text = self._extract_installment_from_api(result)

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
            estimated_delivery_days=estimated_days,
            delivery_text=delivery_text,
            installment_text=installment_text,
        )

    async def _scrape_html_with_fallback(self, url: str) -> ScrapedProduct:
        """HTML scraping — önce direkt, sonra ScraperAPI."""
        # Direkt dene
        try:
            async with httpx.AsyncClient(timeout=15, headers={
                **_DIRECT_HEADERS,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return self._parse_ld_json(url, resp.text)
        except Exception:
            pass

        # ScraperAPI fallback
        proxy_url = scraper_api_url(url, render=False)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(proxy_url)
            resp.raise_for_status()
            return self._parse_ld_json(url, resp.text)

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

        image_raw = product_data.get("image", {})
        image_url: str | None = None
        if isinstance(image_raw, dict):
            content_urls = image_raw.get("contentUrl", [])
            image_url = content_urls[0] if content_urls else None
        elif isinstance(image_raw, str):
            image_url = image_raw

        offers = product_data.get("offers", {})
        current_price = Decimal(str(offers.get("price", 0) or 0))
        original_price: Decimal | None = None
        high_price = offers.get("highPrice")
        if high_price and Decimal(str(high_price)) > current_price:
            original_price = Decimal(str(high_price))

        availability = offers.get("availability", "")
        in_stock = "OutOfStock" not in availability

        store_product_id = self._extract_product_id(url)

        # Delivery & installment from HTML
        delivery_text, estimated_days = self._extract_delivery_from_html(html)
        installment_text = self._extract_installment_from_html(html)

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
            estimated_delivery_days=estimated_days,
            delivery_text=delivery_text,
            installment_text=installment_text,
        )

    def _extract_delivery_from_api(self, result: dict) -> tuple[str | None, int | None]:
        """API JSON'dan kargo bilgisi çıkar."""
        try:
            campaign = result.get("product", {}).get("campaign", {})
            delivery = result.get("product", {}).get("deliveryInformation", {})

            text = delivery.get("deliveryDate") or delivery.get("estimatedDelivery") or ""
            if not text:
                # Alternative path
                for key in ("deliveryInfo", "shippingInfo"):
                    info = result.get("product", {}).get(key, {})
                    if isinstance(info, dict):
                        text = info.get("text", "") or info.get("deliveryDate", "")
                        if text:
                            break

            if not text:
                return None, None

            # Extract days from common patterns
            days = None
            m = re.search(r"(\d+)", text)
            if m:
                days = int(m.group(1))
            if "yarın" in text.lower():
                days = 1

            return text[:200], days
        except Exception:
            return None, None

    def _extract_installment_from_api(self, result: dict) -> str | None:
        """API JSON'dan taksit bilgisi çıkar."""
        try:
            product = result.get("product", {})
            installment = product.get("installmentTable") or product.get("installment", {})
            if isinstance(installment, list) and installment:
                max_count = max(
                    (item.get("installmentCount", 0) for item in installment if isinstance(item, dict)),
                    default=0,
                )
                if max_count > 1:
                    return f"{max_count} aya varan taksit"
            elif isinstance(installment, dict):
                count = installment.get("maxInstallmentCount") or installment.get("installmentCount")
                if count and int(count) > 1:
                    return f"{count} aya varan taksit"
        except Exception:
            pass
        return None

    def _extract_delivery_from_html(self, html: str) -> tuple[str | None, int | None]:
        """HTML içindeki kargo bilgisini parse et."""
        # JSON embedded patterns
        for pattern in [
            r'"deliveryDate"\s*:\s*"([^"]{3,100})"',
            r'"estimatedDelivery"\s*:\s*"([^"]{3,100})"',
            r'"deliveryInfo"\s*:\s*\{[^}]*"text"\s*:\s*"([^"]{3,100})"',
        ]:
            m = re.search(pattern, html)
            if m:
                text = m.group(1)
                days = None
                dm = re.search(r"(\d+)", text)
                if dm:
                    days = int(dm.group(1))
                if "yarın" in text.lower():
                    days = 1
                return text[:200], days
        return None, None

    def _extract_installment_from_html(self, html: str) -> str | None:
        """HTML içindeki taksit bilgisini parse et."""
        m = re.search(r'"maxInstallmentCount"\s*:\s*(\d+)', html)
        if m and int(m.group(1)) > 1:
            return f"{m.group(1)} aya varan taksit"
        m = re.search(r'"installmentCount"\s*:\s*(\d+)', html)
        if m and int(m.group(1)) > 1:
            return f"{m.group(1)} aya varan taksit"
        return None

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-p-(\d+)", url)
        return match.group(1) if match else None
