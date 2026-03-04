"""
Hepsiburada arama adaptörü.
Arama sonuçları sayfasını ScraperAPI (render=True) ile parse eder.
"""
import re
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup

from app.services.scraper.base import scraper_api_url
from app.services.store_search.base import BaseSearcher, SearchResult

_BASE = "https://www.hepsiburada.com"


class HepsiburadaSearcher(BaseSearcher):
    store_name = "hepsiburada"

    async def search(self, query: str, limit: int = 5) -> list[SearchResult]:
        search_url = f"{_BASE}/ara?q={query.replace(' ', '+')}"
        proxy_url = scraper_api_url(search_url, render=True)

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(proxy_url)
                if resp.status_code != 200:
                    return []
                html = resp.text
        except Exception as e:
            print(f"[hepsiburada_search] Hata ({query}): {e}")
            return []

        return self._parse_results(html, limit)

    def _parse_results(self, html: str, limit: int) -> list[SearchResult]:
        soup = BeautifulSoup(html, "lxml")
        results: list[SearchResult] = []

        # Hepsiburada ürün kartları — birden fazla olası selector
        cards = (
            soup.select("li[data-test-id='product-card']")
            or soup.select("li.product-list-item")
            or soup.select("[data-test-id='product-card']")
            or soup.select(".product-card")
        )

        for card in cards[:limit]:
            try:
                # Başlık
                title_el = (
                    card.select_one("[data-test-id='product-card-name']")
                    or card.select_one("h3")
                    or card.select_one(".product-title")
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                # URL
                link_el = card.select_one("a[href]")
                if not link_el:
                    continue
                href = link_el.get("href", "")
                url = href if href.startswith("http") else f"{_BASE}{href}"

                # Fiyat
                price_el = (
                    card.select_one("[data-test-id='price-current-price']")
                    or card.select_one(".price-value")
                    or card.select_one("[class*='price']")
                )
                price = self._parse_price(price_el.get_text(strip=True) if price_el else "0")

                # Görsel
                img_el = card.select_one("img")
                image_url = None
                if img_el:
                    image_url = img_el.get("src") or img_el.get("data-src")

                # store_product_id — URL'den çıkar
                store_product_id = self._extract_product_id(url)

                results.append(SearchResult(
                    title=title,
                    url=url,
                    store=self.store_name,
                    price=price,
                    image_url=image_url,
                    store_product_id=store_product_id,
                ))
            except Exception:
                continue

        return results

    def _parse_price(self, text: str) -> Decimal:
        cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        try:
            return Decimal(cleaned) if cleaned else Decimal("0")
        except Exception:
            return Decimal("0")

    def _extract_product_id(self, url: str) -> str | None:
        match = re.search(r"-(pm-[^?/]+)", url)
        return match.group(1) if match else None
