import re
from decimal import Decimal
from playwright.async_api import async_playwright
from app.services.scraper.base import BaseScraper, ScrapedProduct


class AmazonScraper(BaseScraper):
    store_name = "amazon"

    def can_handle(self, url: str) -> bool:
        return "amazon.com.tr" in url or "amazon.com" in url

    async def scrape(self, url: str) -> ScrapedProduct:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="tr-TR",
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_selector("#productTitle", timeout=10000)

                title = await page.text_content("#productTitle") or ""

                # Amazon fiyat yapısı karmaşık, birden fazla seçici dene
                current_price = None
                for selector in [
                    ".a-price-whole",
                    "#priceblock_ourprice",
                    "#priceblock_dealprice",
                    ".priceToPay .a-price-whole",
                ]:
                    el = await page.query_selector(selector)
                    if el:
                        text = await el.text_content() or ""
                        current_price = self._parse_price(text)
                        break

                if current_price is None:
                    current_price = Decimal("0")

                # Mağaza fiyatı (was price)
                original_price = None
                orig_el = await page.query_selector(".a-text-price .a-offscreen")
                if orig_el:
                    orig_text = await orig_el.text_content() or ""
                    original_price = self._parse_price(orig_text)

                image_url = None
                img_el = await page.query_selector("#landingImage")
                if img_el:
                    image_url = await img_el.get_attribute("src")

                in_stock = True
                oos_el = await page.query_selector("#availability .a-color-price")
                if oos_el:
                    oos_text = (await oos_el.text_content() or "").lower()
                    if "stokta yok" in oos_text or "out of stock" in oos_text:
                        in_stock = False

                store_product_id = self._extract_asin(url)

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
                await context.close()
                await browser.close()

    def _parse_price(self, text: str) -> Decimal:
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        return Decimal(cleaned) if cleaned else Decimal("0")

    def _extract_asin(self, url: str) -> str | None:
        match = re.search(r"/dp/([A-Z0-9]{10})", url)
        return match.group(1) if match else None
