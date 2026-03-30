"""
Akakce urun sayfasindan fiyat grafigi verisini ceker.
httpx ile HTML'den graph URL'sini bulur, sonra Akamai CDN'den
fiyat verisini indirir. Playwright gereksiz.

Akakce format:
- HTML'de: initGraph('https://akakce-g.akamaized.net/{id}:{price}:{ratio}', ...)
- Data URL: yukaridaki URL + ':s' suffix
- Response: window._PRGJ='price1,price2.,price3n3,...'
  - Fiyatlar kurus cinsinden (ornegin 1162800 = 11.628,00 TL)
  - '.' = sonraki gun ayni fiyat tekrari
  - 'nN' = N gun ayni fiyat tekrari
  - Veriler bugunden geriye dogru siralanmis
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from datetime import date, timedelta

import httpx


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.akakce.com/",
}


@dataclass
class PriceDataPoint:
    date: date
    price: float


async def extract_price_history(akakce_url: str) -> list[PriceDataPoint]:
    """
    Akakce urun sayfasindan fiyat gecmisini ceker.
    1. Sayfa HTML'inden graph data URL'sini bul
    2. Akamai CDN'den fiyat verisini indir
    3. Parse et ve PriceDataPoint listesi don
    """
    # 1. Sayfa HTML'ini cek
    html = await _fetch_page(akakce_url)
    if not html:
        print(f"[akakce/chart] Sayfa alınamadı: {akakce_url}", flush=True)
        return []

    # 2. initGraph(...) cagrisindan data URL'sini cikar
    graph_url = _extract_graph_url(html)
    if not graph_url:
        print(f"[akakce/chart] Graph URL bulunamadı: {akakce_url}", flush=True)
        return []

    # 3. Data URL'sine ':s' ekle ve fiyat verisini cek
    data_url = graph_url + ":s"
    raw_data = await _fetch_graph_data(data_url)
    if not raw_data:
        print(f"[akakce/chart] Graph data alınamadı: {data_url}", flush=True)
        return []

    # 4. Parse et
    data_points = _parse_prgj_data(raw_data)
    if data_points:
        print(f"[akakce/chart] {len(data_points)} data point çekildi ({data_points[0].date} - {data_points[-1].date})", flush=True)

    return data_points


async def _fetch_page(url: str) -> str | None:
    """Sayfa HTML'ini cek: direkt → ScraperAPI fallback."""
    from app.config import settings

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        # 1. Direkt erisim
        try:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200 and len(resp.text) > 1000:
                return resp.text
        except Exception:
            pass

        # 2. ScraperAPI fallback (render=false yeterli, graph URL HTML'de)
        if settings.scraper_api_key:
            try:
                proxy_url = (
                    f"http://api.scraperapi.com"
                    f"?api_key={settings.scraper_api_key}"
                    f"&url={urllib.parse.quote(url, safe='')}"
                )
                resp = await client.get(proxy_url, timeout=30)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    print(f"[akakce/chart] ScraperAPI ile sayfa alındı", flush=True)
                    return resp.text
            except Exception as e:
                print(f"[akakce/chart] ScraperAPI hatası: {e}", flush=True)

    return None


def _extract_graph_url(html: str) -> str | None:
    """HTML'den initGraph('url', ...) cagrisindaki URL'yi cikar."""
    match = re.search(r"initGraph\s*\(\s*['\"]([^'\"]+)['\"]", html)
    if match:
        url = match.group(1)
        # Ensure it's absolute
        if url.startswith("//"):
            url = "https:" + url
        return url
    return None


async def _fetch_graph_data(data_url: str) -> str | None:
    """
    Akamai CDN'den graph data script'ini cek.
    Bu endpoint Cloudflare arkasinda degil, direkt erisim yeterli.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        try:
            resp = await client.get(data_url, headers=HEADERS)
            if resp.status_code == 200 and "_PRGJ" in resp.text:
                return resp.text
        except Exception as e:
            print(f"[akakce/chart] Graph data fetch hatası: {e}", flush=True)

    return None


def _parse_prgj_data(raw: str) -> list[PriceDataPoint]:
    """
    window._PRGJ='...' formatindaki veriyi parse et.

    Akakce formati:
    - Her entry virgul ile ayrilmis
    - Sayi: o gunun fiyati (kurus x 100)
    - '.': sonraki gun ayni fiyat
    - 'nN': N gun ayni fiyat
    - Veriler bugunden geriye dogru
    """
    # Extract _PRGJ value
    match = re.search(r"_PRGJ\s*=\s*'([^']+)'", raw)
    if not match:
        return []

    data_str = match.group(1)

    # Step 1: Replace nN with N dots
    data_str = re.sub(r'n(\d+)', lambda m: '.' * int(m.group(1)), data_str)

    # Step 2: Replace vN with N commas (empty slots)
    data_str = re.sub(r'v(\d+)', lambda m: ',' * int(m.group(1)), data_str)

    # Step 3: Remove '#'
    data_str = data_str.replace('#', '')

    # Step 4: Split by comma
    items = data_str.split(',')

    # Step 5: Expand dots — each '.' in a value means "repeat this price"
    expanded: list[str] = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        # Count and remove dots
        dot_count = item.count('.')
        price_text = item.replace('.', '')
        if not price_text:
            continue
        # First occurrence is the price itself
        expanded.append(price_text)
        # Each dot means one more day with the same price
        for _ in range(dot_count):
            expanded.append(price_text)

    # Step 6: Reverse (data is newest-first, we want oldest-first)
    expanded.reverse()

    # Step 7: Map to dates (each entry = 1 day, counting back from today)
    today = date.today()
    total_days = len(expanded)
    results: list[PriceDataPoint] = []

    for i, price_str in enumerate(expanded):
        try:
            price_val = int(price_str)
            if price_val <= 0:
                continue
            # Convert from kuruş (x100) to TL
            price_tl = price_val / 100.0
            # Date: oldest entry = today - (total_days - 1), newest = today
            day_offset = i  # 0 = oldest
            entry_date = today - timedelta(days=total_days - 1 - day_offset)
            results.append(PriceDataPoint(date=entry_date, price=price_tl))
        except (ValueError, OverflowError):
            continue

    return results
