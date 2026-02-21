"""
LLM destekli evrensel e-ticaret scraper.
Bilinen site scraper'ları başarısız olduğunda fallback olarak kullanılır.
"""
import re
import json
import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import anthropic
from playwright.async_api import async_playwright

from app.services.scraper.base import BaseScraper, ScrapedProduct

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Sen bir e-ticaret ürün bilgisi çıkarma asistanısın.
Sana bir e-ticaret sayfasının metin içeriği verilecek.
Bu içerikten ürün bilgilerini çıkarıp yalnızca geçerli bir JSON nesnesi döndür.

Döndürmen gereken JSON formatı:
{
  "title": "ürün tam adı",
  "brand": "marka adı veya null",
  "current_price": 299.99,
  "original_price": 399.99,
  "currency": "TRY",
  "image_url": "https://... veya null",
  "category": "kategori adı veya null",
  "in_stock": true,
  "store_product_id": "ürün kodu/SKU veya null"
}

Kurallar:
- Fiyatları sayısal (float) döndür. Türkçe format: "1.299,00 TL" → 1299.0
- original_price yalnızca indirimli fiyat varsa doldur, yoksa null
- in_stock: sepete ekle butonu varsa true, "tükendi/stok yok" yazıyorsa false
- Sadece JSON döndür, başka hiçbir açıklama ekleme\
"""

USER_PROMPT = """\
URL: {url}

Sayfa içeriği:
{content}\
"""

# og:image için yaygın meta selector'ları
_IMAGE_SELECTORS = [
    ("meta[property='og:image']", "content"),
    ("meta[name='twitter:image']", "content"),
    (".product-image img", "src"),
    ("#main-image", "src"),
    (".product img", "src"),
]


class UniversalScraper(BaseScraper):
    """Bilinmeyen e-ticaret siteleri için LLM tabanlı fallback scraper."""

    store_name = "universal"

    def can_handle(self, url: str) -> bool:
        return True  # Her URL için fallback

    def _store_from_url(self, url: str) -> str:
        try:
            hostname = urlparse(url).hostname or "unknown"
            return hostname.removeprefix("www.")
        except Exception:
            return "unknown"

    async def scrape(self, url: str) -> ScrapedProduct:
        store = self._store_from_url(url)
        page_text, og_image = await self._fetch_page(url)
        data = await self._extract_with_llm(url, page_text)

        # LLM görsel bulamazsa og:image'ı kullan
        image_url = data.get("image_url") or og_image

        return ScrapedProduct(
            title=data.get("title") or "Bilinmeyen Ürün",
            url=url,
            store=store,
            current_price=self._to_decimal(data.get("current_price")) or Decimal("0"),
            original_price=self._to_decimal(data.get("original_price")),
            currency=data.get("currency") or "TRY",
            image_url=image_url,
            brand=data.get("brand"),
            category=data.get("category"),
            in_stock=bool(data.get("in_stock", True)),
            store_product_id=data.get("store_product_id"),
        )

    async def _fetch_page(self, url: str) -> tuple[str, str | None]:
        """Playwright ile sayfayı açar; metin içeriğini ve og:image URL'ini döndürür."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
            })

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)  # JS render bekle

                # Gürültülü script/style içeriklerini temizleyerek metin al
                await page.evaluate(
                    "document.querySelectorAll('script,style,nav,footer').forEach(el => el.remove())"
                )
                text = await page.inner_text("body")
                text = text[:8000]  # Token sınırı

                # og:image veya ürün görseli
                og_image: str | None = None
                for selector, attr in _IMAGE_SELECTORS:
                    try:
                        el = await page.query_selector(selector)
                        if el:
                            og_image = await el.get_attribute(attr)
                            if og_image:
                                break
                    except Exception:
                        continue

                return text, og_image
            finally:
                await browser.close()

    async def _extract_with_llm(self, url: str, content: str) -> dict:
        """Claude Haiku ile sayfa içeriğinden ürün bilgilerini çıkarır."""
        client = anthropic.AsyncAnthropic()

        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": USER_PROMPT.format(url=url, content=content),
                }
            ],
        )

        raw = message.content[0].text.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # LLM bazen ```json ... ``` bloğu döndürebilir
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.error("UniversalScraper: LLM yanıtı parse edilemedi: %s", raw[:300])
            return {}

    @staticmethod
    def _to_decimal(value) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None
