"""
N11 scraper — direkt HTTP, LLM/ScraperAPI gerekmez.
Fiyat inline JS objesinden regex ile çekilir (ld+json Product yok).
"""
import re
from decimal import Decimal
import httpx
from app.services.scraper.base import BaseScraper, ScrapedProduct

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.n11.com/",
}


class N11Scraper(BaseScraper):
    store_name = "n11"

    def can_handle(self, url: str) -> bool:
        return "n11.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        html = resp.text

        # Title — <h1>
        title = ""
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        if m:
            title = re.sub(r'<[^>]+>', '', m.group(1)).strip()

        # Price — inline JS'deki displayPriceNumber veya lowPrice
        current_price = Decimal("0")
        for pat in [
            r'"displayPriceNumber"\s*:\s*(\d+(?:\.\d+)?)',
            r'"displayPriceFloat"\s*:\s*(\d+(?:\.\d+)?)',
            r'"lowPrice"\s*:\s*"?(\d+(?:\.\d+)?)"?',
        ]:
            m = re.search(pat, html)
            if m:
                current_price = Decimal(m.group(1))
                if current_price > 0:
                    break

        # Original price
        original_price = None
        m = re.search(r'"originalPrice"\s*:\s*"?(\d+(?:\.\d+)?)"?', html)
        if m:
            op = Decimal(m.group(1))
            if op > current_price:
                original_price = op

        # Image — og:image veya product image
        image_url = None
        m = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html)
        if m:
            image_url = m.group(1)

        # In stock
        in_stock = '"inStock"' not in html or '"inStock":true' in html.lower() or '"inStock": true' in html

        # Store product ID from URL
        store_product_id = self._extract_product_id(url)

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            image_url=image_url,
            store_product_id=store_product_id,
            in_stock=in_stock,
        )

    def _extract_product_id(self, url: str) -> str | None:
        # N11 URL: /urun/urun-adi-12345678
        m = re.search(r'-(\d{6,})(?:\?|$)', url)
        return m.group(1) if m else None
