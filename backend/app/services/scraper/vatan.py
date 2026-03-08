"""
Vatan Bilgisayar scraper — direkt HTTP, LLM gerekmez.
ld+json @type=Product yapısı kullanılır.
"""
import re
import json
import html as html_module
from decimal import Decimal
import httpx
from app.services.scraper.base import BaseScraper, ScrapedProduct, scraper_api_url

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.vatanbilgisayar.com/",
}


class VatanScraper(BaseScraper):
    store_name = "vatan"

    def can_handle(self, url: str) -> bool:
        return "vatanbilgisayar.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        html_text = await self._fetch(url)
        product = self._parse_ld_json(html_text)
        if product:
            return self._from_ld_json(url, product)
        return self._from_regex(url, html_text)

    async def _fetch(self, url: str) -> str:
        """Direkt dene, 403 → ScraperAPI fallback."""
        try:
            async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    return resp.text
        except Exception:
            pass
        proxy = scraper_api_url(url, render=False)
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(proxy)
            resp.raise_for_status()
            return resp.text

    def _parse_ld_json(self, html_text: str) -> dict | None:
        matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html_text, re.DOTALL,
        )
        for raw in matches:
            try:
                data = json.loads(raw.strip())
                if data.get("@type") == "Product":
                    return data
            except json.JSONDecodeError:
                continue
        return None

    def _from_ld_json(self, url: str, product: dict) -> ScrapedProduct:
        # Vatan ld+json HTML entities içerebilir (&#x131; → ı)
        title = html_module.unescape(product.get("name", "").strip())
        brand = None
        brand_data = product.get("brand", {})
        if isinstance(brand_data, dict):
            brand = brand_data.get("name")
        elif isinstance(brand_data, str):
            brand = brand_data

        offers = product.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        current_price = Decimal(str(offers.get("price", 0) or 0))
        currency = offers.get("priceCurrency", "TRY")

        original_price = None
        high = offers.get("highPrice")
        if high and Decimal(str(high)) > current_price:
            original_price = Decimal(str(high))

        availability = offers.get("availability", "")
        in_stock = "OutOfStock" not in availability

        image_url = product.get("image")
        if isinstance(image_url, list):
            image_url = image_url[0] if image_url else None

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            currency=currency,
            brand=brand,
            image_url=image_url,
            store_product_id=None,
            in_stock=in_stock,
        )

    def _from_regex(self, url: str, html_text: str) -> ScrapedProduct:
        """ld+json yoksa regex fallback."""
        title = ""
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.DOTALL)
        if m:
            title = re.sub(r'<[^>]+>', '', m.group(1)).strip()

        current_price = Decimal("0")
        # data-price attribute
        m = re.search(r'data-price="([\d.,]+)"', html_text)
        if m:
            current_price = self._parse_price(m.group(1))

        if current_price <= 0:
            m = re.search(r'"price"\s*:\s*"?(\d+(?:\.\d+)?)"?', html_text)
            if m:
                current_price = Decimal(m.group(1))

        image_url = None
        m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html_text)
        if m:
            image_url = m.group(1)

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            image_url=image_url,
        )

    def _parse_price(self, text: str) -> Decimal:
        cleaned = re.sub(r"[^\d,.]", "", text)
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return Decimal(cleaned) if cleaned else Decimal("0")
        except Exception:
            return Decimal("0")
