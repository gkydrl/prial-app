import re
from decimal import Decimal
from playwright.async_api import async_playwright
from app.services.scraper.base import BaseScraper, ScrapedProduct


class HepsiburadaScraper(BaseScraper):
    store_name = "hepsiburada"

    def can_handle(self, url: str) -> bool:
        return "hepsiburada.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector("[data-test-id='price-current-price']", timeout=10000)

                title = await page.text_content("h1[itemprop='name']") or ""

                price_text = await page.text_content("[data-test-id='price-current-price']") or ""
                current_price = self._parse_price(price_text)

                original_price = None
                orig_el = await page.query_selector("[data-test-id='price-original-price']")
                if orig_el:
                    orig_text = await orig_el.text_content() or ""
                    original_price = self._parse_price(orig_text)

                image_url = None
                img_el = await page.query_selector(".product-image img")
                if img_el:
                    image_url = await img_el.get_attribute("src")

                in_stock = True
                stock_el = await page.query_selector("[data-test-id='add-to-cart-button']")
                if not stock_el:
                    in_stock = False

                store_product_id = self._extract_product_id(url)

                return ScrapedProduct(
                    title=title.strip(),
                    url=url,
                    store=self.store_name,
                    current_price=current_price,
                    original_price=original_price,
                    image_url=image_url,
                    store_product_id=store_product_id,
                    in_stock=in_stock,
                )
            finally:
                await browser.close()

    def _parse_price(self, text: str) -> Decimal:
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        parts = cleaned.split(".")
        if len(parts) > 2:
            # Binlik ayracı nokta, ondalık virgül: 1.299,00 → 1299.00
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        return Decimal(cleaned) if cleaned else Decimal("0")

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-(pm-[^?]+)", url)
        return match.group(1) if match else None
