"""
Akakce urun sayfasindan fiyat grafigi verisini ceker.
httpx + ScraperAPI (render=true) kullanir — Playwright'a gerek yok.

Uc yaklasim sirayla denenir:
1. Inline JS parse — Highcharts data pattern'leri
2. Regex timestamp/price cifleri
3. Akakce chart API endpoint'i (varsa)
"""
from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, date

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


async def _fetch_page(url: str) -> str | None:
    """Sayfa HTML'ini cek: direkt → ScraperAPI render fallback."""
    from app.config import settings

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        # 1. Direkt erisim
        try:
            resp = await client.get(url, headers=HEADERS)
            if resp.status_code == 200 and len(resp.text) > 1000:
                return resp.text
        except Exception:
            pass

        # 2. ScraperAPI with render=true (JS render — chart data icin sart)
        if settings.scraper_api_key:
            try:
                proxy_url = (
                    f"http://api.scraperapi.com"
                    f"?api_key={settings.scraper_api_key}"
                    f"&url={urllib.parse.quote(url, safe='')}"
                    f"&render=true"
                    f"&country_code=tr"
                )
                resp = await client.get(proxy_url, timeout=60)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    print(f"[akakce/chart] ScraperAPI render ile alındı", flush=True)
                    return resp.text
            except Exception as e:
                print(f"[akakce/chart] ScraperAPI hatası: {e}", flush=True)

        # 3. ScraperAPI without render (daha hizli, belki inline data vardir)
        if settings.scraper_api_key:
            try:
                proxy_url = (
                    f"http://api.scraperapi.com"
                    f"?api_key={settings.scraper_api_key}"
                    f"&url={urllib.parse.quote(url, safe='')}"
                )
                resp = await client.get(proxy_url, timeout=30)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    print(f"[akakce/chart] ScraperAPI (no-render) ile alındı", flush=True)
                    return resp.text
            except Exception as e:
                print(f"[akakce/chart] ScraperAPI (no-render) hatası: {e}", flush=True)

    return None


async def extract_price_history(akakce_url: str) -> list[PriceDataPoint]:
    """
    Akakce urun sayfasindan fiyat gecmisini ceker.
    Returns: list of PriceDataPoint (date, price) — kronolojik sira
    """
    html = await _fetch_page(akakce_url)
    if not html:
        print(f"[akakce/chart] Sayfa alınamadı: {akakce_url}", flush=True)
        return []

    # Debug: log page size and key indicators
    has_chart = any(kw in html.lower() for kw in ["highcharts", "chart", "grafik", "fiyat geçmişi"])
    print(f"[akakce/chart] HTML alındı ({len(html)} bytes, chart indicators: {has_chart})", flush=True)

    # --- Approach 1: Highcharts inline data ---
    data_points = _parse_highcharts_data(html)
    if data_points:
        print(f"[akakce/chart] Highcharts data: {len(data_points)} data point", flush=True)
        return sorted(data_points, key=lambda dp: dp.date)

    # --- Approach 2: Generic inline script data ---
    data_points = _parse_inline_scripts(html)
    if data_points:
        print(f"[akakce/chart] Inline script: {len(data_points)} data point", flush=True)
        return sorted(data_points, key=lambda dp: dp.date)

    # --- Approach 3: Regex timestamp/price pairs ---
    data_points = _extract_from_text(html)
    if data_points:
        print(f"[akakce/chart] Regex extract: {len(data_points)} data point", flush=True)
        return sorted(data_points, key=lambda dp: dp.date)

    # --- Approach 4: Try fetching chart API directly ---
    data_points = await _try_chart_api(akakce_url, html)
    if data_points:
        print(f"[akakce/chart] Chart API: {len(data_points)} data point", flush=True)
        return sorted(data_points, key=lambda dp: dp.date)

    print(f"[akakce/chart] Veri bulunamadı: {akakce_url}", flush=True)

    # Debug: dump a snippet of script tags for investigation
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    chart_scripts = [s[:500] for s in scripts if any(kw in s.lower() for kw in ["chart", "data", "series", "fiyat", "price", "highchart"])]
    if chart_scripts:
        print(f"[akakce/chart] DEBUG — Chart-related script snippets found: {len(chart_scripts)}", flush=True)
        for i, snippet in enumerate(chart_scripts[:3]):
            print(f"[akakce/chart] DEBUG script[{i}]: {snippet[:300]}...", flush=True)

    return []


def _parse_highcharts_data(html: str) -> list[PriceDataPoint]:
    """Highcharts konfigurasyonundan fiyat datasini cikar."""
    results: list[PriceDataPoint] = []

    # Pattern 1: Highcharts series data: [[timestamp, price], ...]
    # Common in Akakce: new Highcharts.Chart({...series:[{data:[[ts,price],...]}]...})
    patterns = [
        # data: [[1234567890000, 1234.56], ...]
        r'data\s*:\s*(\[\s*\[\s*\d{10,13}\s*,\s*[\d.]+\s*\](?:\s*,\s*\[\s*\d{10,13}\s*,\s*[\d.]+\s*\])*\s*\])',
        # series data in various formats
        r'series\s*:\s*\[\s*\{[^}]*data\s*:\s*(\[\s*\[\s*\d{10,13}[\s\S]*?\]\s*\])',
        # pointStart + pointInterval pattern
        r'data\s*:\s*(\[[\d.,\s]+\])\s*,\s*pointStart',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        for match in matches:
            try:
                data = json.loads(match)
                for item in data:
                    point = _try_parse_point(item)
                    if point:
                        results.append(point)
            except json.JSONDecodeError:
                continue

    # Pattern 2: Separated arrays — categories (dates) and data (prices)
    if not results:
        cat_match = re.search(
            r'categories\s*:\s*(\[(?:"[^"]*"(?:\s*,\s*"[^"]*")*)\])',
            html,
        )
        data_match = re.search(
            r'data\s*:\s*(\[[\d.,\s]+\])',
            html,
        )
        if cat_match and data_match:
            try:
                categories = json.loads(cat_match.group(1))
                prices = json.loads(data_match.group(1))
                for cat, price in zip(categories, prices):
                    dt = _parse_date_label(cat)
                    if dt and isinstance(price, (int, float)):
                        results.append(PriceDataPoint(date=dt, price=float(price)))
            except (json.JSONDecodeError, ValueError):
                pass

    return results


def _parse_inline_scripts(html: str) -> list[PriceDataPoint]:
    """Script tag'lerinden chart data'sini cikar."""
    results: list[PriceDataPoint] = []

    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

    for script_text in scripts:
        # Skip external scripts and very short ones
        if len(script_text) < 50:
            continue

        # Look for chart-related keywords
        lower = script_text.lower()
        if not any(kw in lower for kw in ["chart", "series", "data", "fiyat", "price", "highchart"]):
            continue

        # Try to extract data arrays
        # Pattern: data: [[timestamp, price], ...]
        data_matches = re.findall(
            r'data\s*:\s*(\[\[[\d,\s.]+\](?:,\s*\[[\d,\s.]+\])*\])',
            script_text,
        )
        for dm in data_matches:
            try:
                data = json.loads(dm)
                for item in data:
                    point = _try_parse_point(item)
                    if point:
                        results.append(point)
            except json.JSONDecodeError:
                pass

        # Try timestamp/price pairs via regex
        if not results:
            points = _extract_from_text(script_text)
            results.extend(points)

    return results


async def _try_chart_api(akakce_url: str, html: str) -> list[PriceDataPoint]:
    """Akakce'nin chart API endpoint'ini bulmaya calis."""
    from app.config import settings

    results: list[PriceDataPoint] = []

    # Extract product ID from URL or page
    product_id = None

    # From URL: ...fiyati,123456789.html
    id_match = re.search(r',(\d+)\.html', akakce_url)
    if id_match:
        product_id = id_match.group(1)

    # From page: data-pr="123456" or similar
    if not product_id:
        id_match = re.search(r'data-pr["\s=]+["\']?(\d+)', html)
        if id_match:
            product_id = id_match.group(1)

    if not product_id:
        return []

    # Try common Akakce chart API patterns
    api_urls = [
        f"https://www.akakce.com/chart/{product_id}",
        f"https://www.akakce.com/api/chart/{product_id}",
        f"https://www.akakce.com/grafik/{product_id}",
        f"https://www.akakce.com/ph/{product_id}.json",
        f"https://www.akakce.com/p/{product_id}/chart",
    ]

    # Also look for API endpoints in the HTML
    api_matches = re.findall(r'["\'](/(?:api|chart|grafik|ph|price)[^"\']*)["\']', html)
    for api_path in api_matches:
        full_url = f"https://www.akakce.com{api_path}"
        if full_url not in api_urls:
            api_urls.insert(0, full_url)

    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        for api_url in api_urls[:5]:
            try:
                # Direct
                resp = await client.get(api_url, headers=HEADERS)
                if resp.status_code == 200:
                    points = _parse_api_response(resp.text)
                    if points:
                        return points
            except Exception:
                pass

            # ScraperAPI fallback for API endpoints
            if settings.scraper_api_key:
                try:
                    proxy_url = (
                        f"http://api.scraperapi.com"
                        f"?api_key={settings.scraper_api_key}"
                        f"&url={urllib.parse.quote(api_url, safe='')}"
                    )
                    resp = await client.get(proxy_url, timeout=20)
                    if resp.status_code == 200:
                        points = _parse_api_response(resp.text)
                        if points:
                            return points
                except Exception:
                    pass

    return results


def _parse_api_response(text: str) -> list[PriceDataPoint]:
    """API response'undan fiyat data point'lerini parse et."""
    results: list[PriceDataPoint] = []

    # Try JSON parse
    try:
        data = json.loads(text)
        results = _extract_from_json(data)
        if results:
            return results
    except json.JSONDecodeError:
        pass

    # Try regex extraction
    results = _extract_from_text(text)
    return results


def _extract_from_json(data: dict | list) -> list[PriceDataPoint]:
    """JSON chart data'sindan price point'leri cikar."""
    results: list[PriceDataPoint] = []

    if isinstance(data, list):
        for item in data:
            point = _try_parse_point(item)
            if point:
                results.append(point)
        return results

    if isinstance(data, dict):
        # Highcharts format: {series: [{data: [[timestamp, price], ...]}]}
        for key in ["data", "series", "prices", "priceHistory", "fiyatlar", "chart", "points"]:
            if key in data:
                val = data[key]
                if isinstance(val, list):
                    if val and isinstance(val[0], dict) and "data" in val[0]:
                        # series format
                        for series in val:
                            for item in series.get("data", []):
                                point = _try_parse_point(item)
                                if point:
                                    results.append(point)
                    else:
                        for item in val:
                            point = _try_parse_point(item)
                            if point:
                                results.append(point)
                if results:
                    return results

        # Recurse into nested dicts
        for key, val in data.items():
            if isinstance(val, (dict, list)):
                nested = _extract_from_json(val)
                if nested:
                    return nested

    return results


def _try_parse_point(item) -> PriceDataPoint | None:
    """Tek bir data point'i parse etmeye calis."""
    try:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            ts, price = item[0], item[1]
            if isinstance(ts, (int, float)) and ts > 1_000_000_000:
                # Unix timestamp (milliseconds or seconds)
                if ts > 1_000_000_000_000:
                    ts = ts / 1000
                dt = datetime.fromtimestamp(ts).date()
                return PriceDataPoint(date=dt, price=float(price))

        if isinstance(item, dict):
            price = None
            dt = None
            for pk in ["price", "y", "value", "fiyat"]:
                if pk in item:
                    price = float(item[pk])
                    break
            for dk in ["date", "x", "timestamp", "tarih"]:
                if dk in item:
                    raw = item[dk]
                    if isinstance(raw, (int, float)) and raw > 1_000_000_000:
                        if raw > 1_000_000_000_000:
                            raw = raw / 1000
                        dt = datetime.fromtimestamp(raw).date()
                    elif isinstance(raw, str):
                        dt = _parse_date_label(raw)
                    break
            if price and dt:
                return PriceDataPoint(date=dt, price=price)
    except Exception:
        pass
    return None


def _extract_from_text(text: str) -> list[PriceDataPoint]:
    """Regex ile text icerisinden timestamp/price ciftlerini cikar."""
    results: list[PriceDataPoint] = []

    # Pattern: [timestamp, price] pairs
    pattern = r'\[(\d{10,13})\s*,\s*([\d.]+)\]'
    for match in re.finditer(pattern, text):
        try:
            ts = int(match.group(1))
            price = float(match.group(2))
            if ts > 1_000_000_000_000:
                ts = ts // 1000
            dt = datetime.fromtimestamp(ts).date()
            results.append(PriceDataPoint(date=dt, price=price))
        except Exception:
            continue

    return results


def _parse_date_label(text: str) -> date | None:
    """Tarih label'ini parse et."""
    if not text:
        return None
    text = text.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%b %Y", "%m/%Y", "%b '%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
