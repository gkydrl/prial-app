import re
import json
from decimal import Decimal
from playwright.async_api import async_playwright
from app.services.scraper.base import BaseScraper, ScrapedProduct


class TrendyolScraper(BaseScraper):
    store_name = "trendyol"

    def can_handle(self, url: str) -> bool:
        return "trendyol.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector(".pr-new-br", timeout=10000)

                title = await page.text_content(".pr-new-br span") or ""
                brand = await page.text_content(".pr-new-br a") or None

                price_text = await page.text_content(".prc-dsc") or ""
                current_price = self._parse_price(price_text)

                original_price = None
                orig_el = await page.query_selector(".prc-org")
                if orig_el:
                    orig_text = await orig_el.text_content() or ""
                    original_price = self._parse_price(orig_text)

                image_url = None
                img_el = await page.query_selector(".base-product-image img")
                if img_el:
                    image_url = await img_el.get_attribute("src")

                # Stok durumu
                in_stock = True
                out_of_stock_el = await page.query_selector(".out-of-stock")
                if out_of_stock_el:
                    in_stock = False

                # Trendyol ürün ID'si URL'den
                store_product_id = self._extract_product_id(url)

                return ScrapedProduct(
                    title=title.strip(),
                    url=url,
                    store=self.store_name,
                    current_price=current_price,
                    original_price=original_price,
                    brand=brand.strip() if brand else None,
                    image_url=image_url,
                    store_product_id=store_product_id,
                    in_stock=in_stock,
                )
            finally:
                await browser.close()

    def _parse_price(self, text: str) -> Decimal:
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        return Decimal(cleaned) if cleaned else Decimal("0")

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-p-(\d+)", url)
        return match.group(1) if match else None
