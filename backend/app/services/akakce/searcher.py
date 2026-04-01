"""
Akakce'de urun arama ve eslestirme.
catalog_matcher.py'deki _fuzzy_title_match() ve _normalize() fonksiyonlarini reuse eder.

Akakce arama sonuclari statik HTML'de geliyor (SSR), Playwright gereksiz.
httpx ile dogrudan cekilir.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass

import httpx

from app.services.catalog_matcher import _normalize


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.akakce.com/",
}


@dataclass
class AkakceSearchResult:
    title: str
    url: str
    price: float | None = None


async def search_akakce(query: str) -> list[AkakceSearchResult]:
    """
    Akakce'de arama yapar ve sonuclari doner.
    Statik HTML parse — Playwright gerekmez.
    Direkt erisim 403 alirsa ScraperAPI proxy ile dener.
    """
    from app.config import settings

    encoded = urllib.parse.quote_plus(query)
    search_url = f"https://www.akakce.com/arama/?q={encoded}"

    html = None
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        # 1. Direkt erisim
        try:
            resp = await client.get(search_url, headers=HEADERS)
            if resp.status_code == 200:
                html = resp.text
        except Exception:
            pass

        # 2. ScraperAPI fallback
        if html is None and settings.scraper_api_key:
            try:
                proxy_url = (
                    f"http://api.scraperapi.com"
                    f"?api_key={settings.scraper_api_key}"
                    f"&url={urllib.parse.quote(search_url, safe='')}"
                )
                resp = await client.get(proxy_url, timeout=30)
                if resp.status_code == 200:
                    html = resp.text
                    print(f"[akakce/searcher] ScraperAPI ile alındı", flush=True)
            except Exception as e:
                print(f"[akakce/searcher] ScraperAPI hatası: {e}", flush=True)

    if not html:
        print(f"[akakce/searcher] Sayfa alınamadı: {query}", flush=True)
        return []

    results: list[AkakceSearchResult] = []

    # Parse product items from ul.pl_v9 > li[data-pr]
    # Each li has: data-pr (id), a[title] (name), a[href] (url), span.pt_v9 (price)
    items = re.findall(
        r'<li\s+data-pr="(\d+)"[^>]*>.*?'
        r'<a\s+href="([^"]+)"\s+title="([^"]+)".*?'
        r'(?:<span\s+class="pt_v9[^"]*"[^>]*>\s*(?:<!--[^>]*-->)?\s*([\d.,]+))?',
        html,
        re.DOTALL,
    )

    if not items:
        # Fallback: try broader pattern
        items = re.findall(
            r'<li\s+data-pr="(\d+)"[^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )
        for product_id, li_html in items[:15]:
            title_match = re.search(r'title="([^"]{5,})"', li_html)
            href_match = re.search(r'href="(/[^"]+\.html[^"]*)"', li_html)
            if not title_match or not href_match:
                continue

            title = title_match.group(1)
            href = href_match.group(1)
            if href.startswith("/"):
                href = f"https://www.akakce.com{href}"

            price = _extract_price_from_li(li_html)
            results.append(AkakceSearchResult(title=title, url=href, price=price))

        return results

    for product_id, href, title, price_str in items[:15]:
        if href.startswith("/"):
            href = f"https://www.akakce.com{href}"

        price = _parse_price(price_str) if price_str else None
        results.append(AkakceSearchResult(title=title, url=href, price=price))

    return results


# Aksesuar / yanlış ürün tespiti için anahtar kelimeler
_ACCESSORY_WORDS = {
    "kılıf", "kilif", "kapak", "koruyucu", "cam", "koruma", "temperli",
    "şarj", "sarj", "kablo", "adaptör", "adaptor", "çevirici",
    "aksesuar", "yedek", "batarya", "pil", "tutucu", "standı", "stand",
    "çanta", "canta", "kayış", "kayis", "kordon", "bileklik",
    "sticker", "etiket", "dekor", "süs", "mouse", "pad", "mousepad",
    "toner", "kartuş", "kartus", "mürekkep", "murekkep",
}


def _is_accessory(title: str) -> bool:
    """Sonuç başlığı aksesuar/parça mı kontrol et."""
    words = set(re.findall(r'[a-zçğıöşü0-9]+', title.lower()))
    return bool(words & _ACCESSORY_WORDS)


async def find_akakce_url(product_title: str, brand: str | None = None) -> str | None:
    """
    Bir Prial urunu icin Akakce'deki en iyi eslesen URL'yi bulur.
    1. Aksesuar sonuçlarını filtrele (kılıf, koruyucu, şarj vb.)
    2. Jaccard >= 0.50 → direkt kabul
    3. Jaccard düşükse → Claude Haiku ile LLM matching
    """
    # Sorgu oluştur — gereksiz kelimeleri temizle
    if brand and product_title.upper().startswith(brand.upper()):
        query = product_title
    elif brand:
        query = f"{brand} {product_title}"
    else:
        query = product_title
    # Parantez, tırnak, özel karakterleri temizle
    query = re.sub(r'["""\'\(\)&;,]', ' ', query)
    # "Fiyat" ve sonrasını kes
    query = re.split(r'\b[Ff]iyat\b', query)[0].strip()
    query = re.sub(r'\s+', ' ', query).strip()
    words = query.split()
    if len(words) > 8:
        query = " ".join(words[:8])

    print(f"[akakce/searcher] Aranıyor: {query}", flush=True)

    results = await search_akakce(query)
    if not results:
        print(f"[akakce/searcher] Sonuç bulunamadı: {query}", flush=True)
        return None

    # Ürünün kendisi aksesuar değilse, aksesuar sonuçlarını filtrele
    catalog_label = f"{brand or ''} {product_title}".strip()
    product_is_accessory = _is_accessory(catalog_label)

    if not product_is_accessory:
        filtered = [r for r in results if not _is_accessory(r.title)]
        # Filtreden sonuç kalmadıysa orijinali kullan
        if filtered:
            results = filtered

    # Fuzzy match — tüm sonuçları skorla, EN İYİSİNİ seç
    scored: list[tuple[float, AkakceSearchResult]] = []

    cat_words = _normalize(catalog_label)
    if not cat_words:
        return None

    for r in results:
        scr_words = _normalize(r.title)
        if not scr_words:
            continue

        intersection = cat_words & scr_words
        union = cat_words | scr_words
        score = len(intersection) / len(union)

        # Bonus: ürün kelimelerinin tamamı sonuçta varsa ekstra puan
        coverage = len(intersection) / len(cat_words) if cat_words else 0
        if coverage >= 1.0:
            score += 0.10  # Tüm kelimeler eşleşti → bonus

        scored.append((score, r))

    # En yüksek skorlu sonucu seç
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score = scored[0][0] if scored else 0.0
    best_match = scored[0][1] if scored else None

    # Jaccard yeterli → direkt kabul (threshold: 0.50)
    if best_match and best_score >= 0.50:
        print(f"[akakce/searcher] Eşleşme bulundu (score={best_score:.2f}): {best_match.title}", flush=True)
        return best_match.url

    # Jaccard düşük → Haiku ile LLM matching dene
    if results:
        haiku_match = await _llm_match(catalog_label, results[:8])
        if haiku_match:
            print(f"[akakce/searcher] LLM eşleşme bulundu: {haiku_match.title}", flush=True)
            return haiku_match.url

    print(f"[akakce/searcher] Eşleşme yok (score={best_score:.2f}): {query}", flush=True)
    return None


async def _llm_match(
    product_label: str,
    candidates: list[AkakceSearchResult],
) -> AkakceSearchResult | None:
    """
    Claude Haiku ile urun eslestirme.
    Prial urun adini Akakce sonuclariyla karsilastirir.
    """
    from app.config import settings

    if not settings.anthropic_api_key:
        return None

    try:
        import anthropic

        candidate_lines = "\n".join(
            f"{i+1}. {c.title}" for i, c in enumerate(candidates)
        )

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": (
                    f"Ürün: {product_label}\n\n"
                    f"Adaylar:\n{candidate_lines}\n\n"
                    "Yukarıdaki ürünle BİREBİR AYNI ürün hangisi? "
                    "DİKKAT: Kılıf, koruyucu, şarj aleti, kablo gibi aksesuarlar AYNI ÜRÜN DEĞİLDİR. "
                    "Sadece numarasını yaz (1-{len}). "
                    "Hiçbiri aynı ürün değilse 0 yaz."
                ).format(len=len(candidates)),
            }],
        )

        answer = resp.content[0].text.strip()
        # İlk sayıyı çıkar
        num_match = re.search(r"(\d+)", answer)
        if not num_match:
            return None

        idx = int(num_match.group(1))
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1]

    except Exception as e:
        print(f"[akakce/searcher] LLM match hatası: {e}", flush=True)

    return None


def _extract_price_from_li(li_html: str) -> float | None:
    """li HTML'inden fiyat cikar."""
    # Pattern: 79.068,74 TL or similar inside pt_v9
    match = re.search(r'class="pt_v9[^"]*"[^>]*>[\s\S]*?([\d.]+)[,<]', li_html)
    if match:
        return _parse_price(match.group(1))
    return None


def _parse_price(text: str) -> float | None:
    """'12.345' veya '12345' formatindaki fiyati parse et."""
    if not text:
        return None
    text = re.sub(r'[^\d.]', '', text)
    # Remove thousands separator dots
    text = re.sub(r'\.(?=\d{3})', '', text)
    try:
        return float(text)
    except ValueError:
        return None
