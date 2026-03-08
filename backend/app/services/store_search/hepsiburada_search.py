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

        # Önce direkt dene (0 kredi)
        html = None
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "tr-TR,tr;q=0.9",
                "Referer": "https://www.hepsiburada.com/",
            }
            async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
                resp = await client.get(search_url)
                if resp.status_code == 200 and len(resp.text) > 2000:
                    html = resp.text
                    print(f"[hepsiburada_search] Direkt OK ({len(html)} chars)", flush=True)
        except Exception as e:
            print(f"[hepsiburada_search] Direkt hata: {e}", flush=True)

        # ScraperAPI fallback (5 kredi)
        if not html:
            proxy_url = scraper_api_url(search_url, render=True)
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.get(proxy_url)
                    if resp.status_code != 200:
                        print(f"[hepsiburada_search] Proxy HTTP {resp.status_code}", flush=True)
                        return []
                    html = resp.text
                    print(f"[hepsiburada_search] Proxy OK ({len(html)} chars)", flush=True)
            except Exception as e:
                print(f"[hepsiburada_search] Proxy hata ({query}): {e}", flush=True)
                return []

        results = self._parse_results(html, limit)
        if not results:
            # Debug: HTML'de ne var?
            import re
            card_count = len(re.findall(r'product-card', html, re.I))
            li_count = len(re.findall(r'<li[^>]*class', html))
            print(f"[hepsiburada_search] Parse 0 sonuç — 'product-card' x{card_count}, <li> x{li_count}", flush=True)
        return results

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
