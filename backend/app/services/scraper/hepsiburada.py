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
        # render=False yeterli — fiyat ve başlık statik HTML'de gömülü JSON'da var
        proxy_url = scraper_api_url(url, render=False)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(proxy_url)
            resp.raise_for_status()

        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        # Başlık: h1[itemprop=name] veya h1
        title_el = soup.select_one("h1[itemprop='name']") or soup.select_one("h1.product-name") or soup.select_one("h1")
        title = title_el.get_text(strip=True) if title_el else ""

        # Fiyat: sayfaya gömülü JSON'dan çek (render gerekmez)
        current_price = Decimal("0")
        for pattern in [
            r'"currentPrice":([0-9]+(?:\.[0-9]+)?)',
            r'"listingPrice":\{"amount":([0-9]+(?:\.[0-9]+)?)',
            r'"price":([0-9]+(?:\.[0-9]+)?)',
        ]:
            m = re.search(pattern, html)
            if m:
                current_price = self._parse_price(m.group(1))
                if current_price > 0:
                    break

        # CSS selector ile de dene (render edilmişse)
        if current_price <= 0:
            price_el = soup.select_one("[data-test-id='price-current-price']") or \
                       soup.select_one(".price-value")
            if price_el:
                current_price = self._parse_price(price_el.get_text(strip=True))

        # Orijinal fiyat
        original_price = None
        for pattern in [r'"originalPrice":([0-9]+(?:\.[0-9]+)?)', r'"listPrice":([0-9]+(?:\.[0-9]+)?)']:
            m = re.search(pattern, html)
            if m:
                op = self._parse_price(m.group(1))
                if op > current_price:
                    original_price = op
                break

        # Görsel: productimages CDN URL
        image_url = None
        img_el = soup.select_one("img[src*='productimages']") or \
                 soup.select_one("img[data-src*='productimages']") or \
                 soup.select_one(".product-image img") or \
                 soup.select_one("[data-test-id='product-image'] img")
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
        cleaned = re.sub(r"[^\d,.]", "", str(text))
        # Türkçe format: 115.817,03 → 115817.03
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        # Sadece tam sayı (JSON'dan)
        try:
            return Decimal(cleaned) if cleaned else Decimal("0")
        except Exception:
            return Decimal("0")

    def _extract_product_id(self, url: str) -> str | None:
        m = re.search(r"-(pm-[^?/]+)", url) or re.search(r"-p-([A-Z][A-Z0-9]{7,})", url)
        return m.group(1) if m else None
