import re
from decimal import Decimal
import httpx
from bs4 import BeautifulSoup
from app.services.scraper.base import BaseScraper, ScrapedProduct, scraper_api_url


class HepsiburadaScraper(BaseScraper):
    store_name = "hepsiburada"

    def can_handle(self, url: str) -> bool:
        return "hepsiburada.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        proxy_url = scraper_api_url(url, render=True)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(proxy_url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        title_el = soup.select_one("h1[itemprop='name']") or soup.select_one("h1.product-name")
        title = title_el.get_text(strip=True) if title_el else ""

        price_el = soup.select_one("[data-test-id='price-current-price']") or \
                   soup.select_one(".price-value")
        current_price = self._parse_price(price_el.get_text(strip=True) if price_el else "0")

        original_price = None
        orig_el = soup.select_one("[data-test-id='price-original-price']") or \
                  soup.select_one(".price-old-value")
        if orig_el:
            original_price = self._parse_price(orig_el.get_text(strip=True))

        image_url = None
        img_el = soup.select_one(".product-image img") or soup.select_one("[data-test-id='product-image'] img")
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-src")

        in_stock = bool(soup.select_one("[data-test-id='add-to-cart-button']"))

        return ScrapedProduct(
            title=title,
            url=url,
            store=self.store_name,
            current_price=current_price,
            original_price=original_price,
            image_url=image_url,
            store_product_id=self._extract_product_id(url),
            in_stock=in_stock,
        )

    def _parse_price(self, text: str) -> Decimal:
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        return Decimal(cleaned) if cleaned else Decimal("0")

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-(pm-[^?]+)", url)
        return match.group(1) if match else None
