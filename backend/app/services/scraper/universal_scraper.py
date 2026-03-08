"""
Evrensel e-ticaret scraper — LLM kullanmaz.
ld+json, OpenGraph meta tag ve regex ile fiyat/title çıkarır.
Bilinen site scraper'ları başarısız olduğunda fallback olarak kullanılır.
"""
import re
import json
import html as html_module
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import httpx

from app.services.scraper.base import BaseScraper, ScrapedProduct, scraper_api_url


class UniversalScraper(BaseScraper):
    """Bilinmeyen e-ticaret siteleri için ld+json / meta tag tabanlı scraper."""

    store_name = "universal"

    def can_handle(self, url: str) -> bool:
        return True

    def _store_from_url(self, url: str) -> str:
        try:
            hostname = urlparse(url).hostname or "unknown"
            return hostname.removeprefix("www.")
        except Exception:
            return "unknown"

    async def scrape(self, url: str) -> ScrapedProduct:
        store = self._store_from_url(url)
        html = await self._fetch_page(url)
        return self._extract(url, store, html)

    async def _fetch_page(self, url: str) -> str:
        """Önce direkt dene, sonra ScraperAPI render=true fallback."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "tr-TR,tr;q=0.9",
        }
        # Direkt dene
        try:
            async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    return resp.text
        except Exception:
            pass

        # ScraperAPI fallback
        proxy_url = scraper_api_url(url, render=True)
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(proxy_url)
            resp.raise_for_status()
            return resp.text

    def _extract(self, url: str, store: str, html: str) -> ScrapedProduct:
        """ld+json > meta tags > regex sırasıyla ürün verisi çıkarır."""
        # 1. ld+json dene
        product_data = self._extract_ld_json(html)
        if product_data:
            return self._from_ld_json(url, store, product_data)

        # 2. Meta tags + regex fallback
        return self._from_meta_and_regex(url, store, html)

    def _extract_ld_json(self, html: str) -> dict | None:
        matches = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        for raw in matches:
            try:
                data = json.loads(raw.strip())
                # Direkt Product
                if data.get("@type") in ("Product", "ProductGroup"):
                    return data
                # BuyAction wrapper (MediaMarkt pattern)
                if data.get("@type") == "BuyAction" and "object" in data:
                    obj = data["object"]
                    if obj.get("@type") == "Product":
                        return obj
                # @graph array içinde Product
                if "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") in ("Product", "ProductGroup"):
                            return item
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _from_ld_json(self, url: str, store: str, data: dict) -> ScrapedProduct:
        title = html_module.unescape(data.get("name", "").strip())
        brand = None
        brand_data = data.get("brand", {})
        if isinstance(brand_data, dict):
            brand = brand_data.get("name")
        elif isinstance(brand_data, str):
            brand = brand_data
        brand = brand or data.get("manufacturer")

        offers = data.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}

        # AggregateOffer desteği
        if offers.get("@type") == "AggregateOffer":
            price_val = offers.get("lowPrice", offers.get("price", 0))
        else:
            price_val = offers.get("price", 0)

        current_price = _to_decimal(price_val)
        currency = offers.get("priceCurrency", "TRY")

        original_price = None
        high = offers.get("highPrice")
        if high:
            hp = _to_decimal(high)
            if hp and hp > current_price:
                original_price = hp

        availability = offers.get("availability", "")
        in_stock = "OutOfStock" not in availability

        image_url = data.get("image")
        if isinstance(image_url, dict):
            image_url = image_url.get("contentUrl") or image_url.get("url")
        if isinstance(image_url, list):
            image_url = image_url[0] if image_url else None

        sku = data.get("sku") or data.get("productID")

        return ScrapedProduct(
            title=title,
            url=url,
            store=store,
            current_price=current_price,
            original_price=original_price,
            currency=currency,
            brand=brand,
            image_url=image_url,
            store_product_id=str(sku) if sku else None,
            in_stock=in_stock,
        )

    def _from_meta_and_regex(self, url: str, store: str, html: str) -> ScrapedProduct:
        """Meta tags ve regex ile veri çıkarır."""
        # Title: og:title > <title> > <h1>
        title = (
            self._meta_content(html, 'property="og:title"')
            or self._meta_content(html, 'name="title"')
            or self._tag_text(html, "title")
            or self._tag_text(html, "h1")
            or ""
        )

        # Price: regex
        current_price = Decimal("0")
        for pat in [
            r'"price"\s*:\s*"?(\d+(?:\.\d+)?)"?',
            r'"currentPrice"\s*:\s*"?(\d+(?:\.\d+)?)"?',
            r'"salePrice"\s*:\s*"?(\d+(?:\.\d+)?)"?',
            r'"displayPriceNumber"\s*:\s*(\d+(?:\.\d+)?)',
            r'data-price="([\d.,]+)"',
        ]:
            m = re.search(pat, html)
            if m:
                p = _to_decimal(m.group(1))
                if p and p > 0:
                    current_price = p
                    break

        # Image: og:image
        image_url = (
            self._meta_content(html, 'property="og:image"')
            or self._meta_content(html, 'name="twitter:image"')
        )

        # Brand: og:brand or regex
        brand = self._meta_content(html, 'property="product:brand"')

        return ScrapedProduct(
            title=html_module.unescape(title.strip()),
            url=url,
            store=store,
            current_price=current_price,
            brand=brand,
            image_url=image_url,
        )

    @staticmethod
    def _meta_content(html: str, attr: str) -> str | None:
        m = re.search(rf'<meta[^>]*{attr}[^>]*content="([^"]*)"', html)
        if m:
            return m.group(1)
        # Ters sıra: content önce
        m = re.search(rf'<meta[^>]*content="([^"]*)"[^>]*{attr}', html)
        return m.group(1) if m else None

    @staticmethod
    def _tag_text(html: str, tag: str) -> str | None:
        m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL)
        if m:
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            return text if len(text) > 3 else None
        return None


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        s = str(value).replace(",", ".")
        return Decimal(s)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
