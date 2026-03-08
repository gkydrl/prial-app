"""
MediaMarkt TR scraper — direkt HTTP, LLM gerekmez.
ld+json @type=BuyAction > object.@type=Product yapısı kullanılır.
Not: BeautifulSoup lxml data-rh attribute'lu script'leri kaçırır, regex kullanılır.
"""
import re
import json
from decimal import Decimal
import httpx
from app.services.scraper.base import BaseScraper, ScrapedProduct

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.mediamarkt.com.tr/",
}


class MediaMarktScraper(BaseScraper):
    store_name = "mediamarkt"

    def can_handle(self, url: str) -> bool:
        return "mediamarkt.com.tr" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        html = resp.text
        product = self._parse_ld_json(html)
        if product:
            return self._from_ld_json(url, product)
        return self._from_regex(url, html)

    def _parse_ld_json(self, html: str) -> dict | None:
        """ld+json'dan Product verisini çıkarır (regex ile, lxml kaçırabilir)."""
        matches = re.findall(
            r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        for raw in matches:
            try:
                data = json.loads(raw.strip())
                # MediaMarkt: @type=BuyAction, product data data["object"] içinde
                if data.get("@type") == "BuyAction" and "object" in data:
                    obj = data["object"]
                    if obj.get("@type") == "Product":
                        return obj
                if data.get("@type") == "Product":
                    return data
            except json.JSONDecodeError:
                continue
        return None

    def _from_ld_json(self, url: str, product: dict) -> ScrapedProduct:
        title = product.get("name", "").strip()
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

        sku = product.get("sku") or self._extract_sku(url)

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            currency=currency,
            brand=brand,
            image_url=image_url,
            store_product_id=sku,
            in_stock=in_stock,
        )

    def _from_regex(self, url: str, html: str) -> ScrapedProduct:
        """ld+json yoksa regex fallback."""
        title = ""
        m = re.search(r'<title[^>]*>([^<]+)</title>', html)
        if m:
            title = m.group(1).strip()

        current_price = Decimal("0")
        for pat in [
            r'"price"\s*:\s*"?(\d+(?:\.\d+)?)"?',
            r'"currentPrice"\s*:\s*"?(\d+(?:\.\d+)?)"?',
        ]:
            m = re.search(pat, html)
            if m:
                current_price = Decimal(m.group(1))
                if current_price > 0:
                    break

        image_url = None
        m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
        if m:
            image_url = m.group(1)

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            image_url=image_url,
            store_product_id=self._extract_sku(url),
        )

    def _extract_sku(self, url: str) -> str | None:
        # MediaMarkt URL: ...-1239560.html
        m = re.search(r'-(\d{6,})\.html', url)
        return m.group(1) if m else None
