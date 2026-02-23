import re
from decimal import Decimal
import httpx
from bs4 import BeautifulSoup
from app.services.scraper.base import BaseScraper, ScrapedProduct, scraper_api_url


class AmazonScraper(BaseScraper):
    store_name = "amazon"

    def can_handle(self, url: str) -> bool:
        return "amazon.com.tr" in url or "amazon.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        proxy_url = scraper_api_url(url, render=True)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(proxy_url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        title_el = soup.select_one("#productTitle")
        title = title_el.get_text(strip=True) if title_el else ""

        current_price = Decimal("0")
        for selector in [
            ".priceToPay .a-price-whole",
            ".a-price-whole",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
        ]:
            el = soup.select_one(selector)
            if el:
                current_price = self._parse_price(el.get_text(strip=True))
                if current_price > 0:
                    break

        original_price = None
        orig_el = soup.select_one(".a-text-price .a-offscreen")
        if orig_el:
            original_price = self._parse_price(orig_el.get_text(strip=True))

        image_url = None
        img_el = soup.select_one("#landingImage")
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-src")

        in_stock = True
        avail_el = soup.select_one("#availability .a-color-price")
        if avail_el:
            avail_text = avail_el.get_text(strip=True).lower()
            if "stokta yok" in avail_text or "out of stock" in avail_text:
                in_stock = False

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            image_url=image_url,
            store_product_id=self._extract_asin(url),
            in_stock=in_stock,
        )

    def _parse_price(self, text: str) -> Decimal:
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        return Decimal(cleaned) if cleaned else Decimal("0")

    def _extract_asin(self, url: str) -> str | None:
        match = re.search(r"/dp/([A-Z0-9]{10})", url)
        return match.group(1) if match else None
