"""
Akakce urun sayfasindan fiyat grafigi verisini ceker.
Uc yaklasim sirayla denenir:
1. Network intercept — XHR isteklerini yakala
2. DOM/Script parse — Inline JS'den chart data cek
3. SVG parse — SVG elementlerinden data point'leri cikar
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, date

from app.services.akakce.browser import get_page, random_delay, wait_for_cloudflare


@dataclass
class PriceDataPoint:
    date: date
    price: float


async def extract_price_history(akakce_url: str) -> list[PriceDataPoint]:
    """
    Akakce urun sayfasindan fiyat gecmisini ceker.
    Uc yaklasimi sirayla dener.
    Returns: list of PriceDataPoint (date, price) — kronolojik sira
    """
    data_points: list[PriceDataPoint] = []

    async with get_page() as page:
        # Network intercept setup — XHR responses'lari yakala
        intercepted_data: list[dict] = []

        async def handle_response(response):
            url = response.url.lower()
            keywords = ["chart", "price", "fiyat", "grafik", "history", "graph"]
            if any(kw in url for kw in keywords):
                try:
                    body = await response.text()
                    intercepted_data.append({"url": response.url, "body": body})
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            await page.goto(akakce_url, wait_until="domcontentloaded", timeout=30000)
            passed = await wait_for_cloudflare(page)
            if not passed:
                return []

            # Wait for page to fully load (chart may load lazily)
            await page.wait_for_timeout(3000)

            # Try clicking "Fiyat Gecmisi" tab/button if it exists
            for selector in [
                "text=Fiyat Geçmişi",
                "text=fiyat geçmişi",
                "a:has-text('Fiyat')",
                "[data-tab='chart']",
                ".price-history-tab",
            ]:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        await el.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

        except Exception as e:
            print(f"[akakce/chart] Sayfa yükleme hatası: {e}", flush=True)
            return []

        # --- Approach 1: Network intercept ---
        data_points = _parse_intercepted_data(intercepted_data)
        if data_points:
            print(f"[akakce/chart] Network intercept: {len(data_points)} data point", flush=True)
            return sorted(data_points, key=lambda dp: dp.date)

        # --- Approach 2: Inline JS/DOM parse ---
        data_points = await _parse_inline_scripts(page)
        if data_points:
            print(f"[akakce/chart] Inline script: {len(data_points)} data point", flush=True)
            return sorted(data_points, key=lambda dp: dp.date)

        # --- Approach 3: SVG parse ---
        data_points = await _parse_svg_chart(page)
        if data_points:
            print(f"[akakce/chart] SVG parse: {len(data_points)} data point", flush=True)
            return sorted(data_points, key=lambda dp: dp.date)

        print(f"[akakce/chart] Veri bulunamadı: {akakce_url}", flush=True)
        return []


def _parse_intercepted_data(intercepted: list[dict]) -> list[PriceDataPoint]:
    """Network intercept ile yakalanan response'lardan fiyat datasini parse et."""
    results: list[PriceDataPoint] = []

    for item in intercepted:
        body = item["body"]
        try:
            data = json.loads(body)
            points = _extract_from_json(data)
            if points:
                results.extend(points)
        except json.JSONDecodeError:
            # Try regex extraction from non-JSON responses
            points = _extract_from_text(body)
            results.extend(points)

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
        for key in ["data", "series", "prices", "priceHistory", "fiyatlar"]:
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
                        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                            try:
                                dt = datetime.strptime(raw, fmt).date()
                                break
                            except ValueError:
                                continue
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


async def _parse_inline_scripts(page) -> list[PriceDataPoint]:
    """Sayfadaki script tag'lerinden chart data'sini cikar."""
    results: list[PriceDataPoint] = []

    try:
        scripts = await page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                const texts = [];
                for (const s of scripts) {
                    const text = s.textContent || '';
                    if (text.includes('chart') || text.includes('Chart') ||
                        text.includes('series') || text.includes('data') ||
                        text.includes('fiyat') || text.includes('price')) {
                        texts.push(text);
                    }
                }
                return texts;
            }
        """)

        for script_text in scripts:
            # Try to find Highcharts/Chart.js data patterns
            # Pattern 1: data: [[timestamp, price], ...]
            data_match = re.search(r'data\s*:\s*(\[\[[\d,\s.]+\](?:,\s*\[[\d,\s.]+\])*\])', script_text)
            if data_match:
                try:
                    data = json.loads(data_match.group(1))
                    for item in data:
                        point = _try_parse_point(item)
                        if point:
                            results.append(point)
                except Exception:
                    pass

            # Pattern 2: categories/labels as dates + data as prices
            if not results:
                points = _extract_from_text(script_text)
                results.extend(points)

    except Exception as e:
        print(f"[akakce/chart] Inline script parse hatasi: {e}", flush=True)

    return results


async def _parse_svg_chart(page) -> list[PriceDataPoint]:
    """
    SVG chart elementlerinden data point'leri cikar.
    Highcharts SVG path veya circle elementlerini parse eder.
    """
    results: list[PriceDataPoint] = []

    try:
        # Get SVG chart bounds and data points
        svg_data = await page.evaluate("""
            () => {
                const svg = document.querySelector('svg.highcharts-root, svg[class*="chart"]');
                if (!svg) return null;

                const rect = svg.getBoundingClientRect();

                // Try to find data point markers (circles)
                const circles = svg.querySelectorAll('circle[class*="point"], circle.highcharts-point');
                const points = [];
                for (const c of circles) {
                    points.push({
                        cx: parseFloat(c.getAttribute('cx')),
                        cy: parseFloat(c.getAttribute('cy')),
                    });
                }

                // Get axis labels for date/price mapping
                const xLabels = [];
                const yLabels = [];
                svg.querySelectorAll('.highcharts-xaxis-labels text, .highcharts-axis-labels text').forEach(t => {
                    xLabels.push({text: t.textContent, x: parseFloat(t.getAttribute('x'))});
                });
                svg.querySelectorAll('.highcharts-yaxis-labels text').forEach(t => {
                    yLabels.push({text: t.textContent, y: parseFloat(t.getAttribute('y'))});
                });

                return {
                    width: rect.width,
                    height: rect.height,
                    points: points,
                    xLabels: xLabels,
                    yLabels: yLabels,
                };
            }
        """)

        if not svg_data or not svg_data.get("points"):
            return []

        # Parse axis labels to build coordinate mapping
        x_mapping = _build_date_mapping(svg_data.get("xLabels", []), svg_data["width"])
        y_mapping = _build_price_mapping(svg_data.get("yLabels", []), svg_data["height"])

        if not x_mapping or not y_mapping:
            return []

        for point in svg_data["points"]:
            cx, cy = point["cx"], point["cy"]
            dt = _interpolate_date(cx, x_mapping)
            price = _interpolate_price(cy, y_mapping)
            if dt and price:
                results.append(PriceDataPoint(date=dt, price=price))

    except Exception as e:
        print(f"[akakce/chart] SVG parse hatasi: {e}", flush=True)

    return results


def _build_date_mapping(labels: list[dict], width: float) -> list[tuple[float, date]]:
    """X axis label'larindan position -> date mapping olustur."""
    mapping = []
    for label in labels:
        text = label.get("text", "").strip()
        x = label.get("x", 0)
        # Common date formats in Turkish charts
        for fmt in ("%b %Y", "%m/%Y", "%d.%m.%Y", "%b '%y"):
            try:
                dt = datetime.strptime(text, fmt).date()
                mapping.append((x, dt))
                break
            except ValueError:
                continue
    return sorted(mapping, key=lambda m: m[0])


def _build_price_mapping(labels: list[dict], height: float) -> list[tuple[float, float]]:
    """Y axis label'larindan position -> price mapping olustur."""
    mapping = []
    for label in labels:
        text = label.get("text", "").strip()
        y = label.get("y", 0)
        price = _parse_axis_price(text)
        if price is not None:
            mapping.append((y, price))
    return sorted(mapping, key=lambda m: m[0])


def _parse_axis_price(text: str) -> float | None:
    """Axis label'daki fiyati parse et: '12.345', '12K', '12.345 TL' vb."""
    text = text.replace("TL", "").replace("₺", "").replace(" ", "").strip()
    text = re.sub(r'\.(?=\d{3})', '', text)  # Remove thousands separator
    text = text.replace(",", ".")
    if text.upper().endswith("K"):
        try:
            return float(text[:-1]) * 1000
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _interpolate_date(x: float, mapping: list[tuple[float, date]]) -> date | None:
    """X koordinatindan tarihi interpole et."""
    if not mapping or len(mapping) < 2:
        return None
    # Clamp to bounds
    if x <= mapping[0][0]:
        return mapping[0][1]
    if x >= mapping[-1][0]:
        return mapping[-1][1]
    # Linear interpolation
    for i in range(len(mapping) - 1):
        x0, d0 = mapping[i]
        x1, d1 = mapping[i + 1]
        if x0 <= x <= x1:
            ratio = (x - x0) / (x1 - x0) if x1 != x0 else 0
            days_diff = (d1 - d0).days
            interpolated_days = int(days_diff * ratio)
            from datetime import timedelta
            return d0 + timedelta(days=interpolated_days)
    return None


def _interpolate_price(y: float, mapping: list[tuple[float, float]]) -> float | None:
    """Y koordinatindan fiyati interpole et. (SVG'de y yukaridan asagi artar)"""
    if not mapping or len(mapping) < 2:
        return None
    if y <= mapping[0][0]:
        return mapping[0][1]
    if y >= mapping[-1][0]:
        return mapping[-1][1]
    for i in range(len(mapping) - 1):
        y0, p0 = mapping[i]
        y1, p1 = mapping[i + 1]
        if y0 <= y <= y1:
            ratio = (y - y0) / (y1 - y0) if y1 != y0 else 0
            return p0 + (p1 - p0) * ratio
    return None
