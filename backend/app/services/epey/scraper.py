"""
Epey.com urun arama, eslestirme ve fiyat gecmisi cekme.

Epey direkt erisime acik (ScraperAPI gereksiz):
- Arama: POST /kat/aramayap/ {aranan, bolum}
- Fiyat gecmisi: POST /kat/fg/ {id, fiyat} → JSON [[tarih, fiyat, ay]]

Akakce'de bulunamayan urunler icin fallback olarak kullanilir.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date

import httpx

from app.services.catalog_matcher import _normalize


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.epey.com/",
}

AJAX_HEADERS = {
    **HEADERS,
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
}


@dataclass
class EpeySearchResult:
    title: str
    url: str
    epey_id: int | None = None


@dataclass
class EpeyPricePoint:
    date: date
    price: float


async def search_epey(query: str) -> list[EpeySearchResult]:
    """
    Epey autocomplete API ile urun arar.
    Direkt erisim — ScraperAPI gereksiz.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        try:
            resp = await client.post(
                "https://www.epey.com/kat/aramayap/",
                data={"aranan": query, "bolum": "genel"},
                headers=AJAX_HEADERS,
            )
            if resp.status_code != 200:
                return []
        except Exception as e:
            print(f"[epey] Arama hatası: {e}", flush=True)
            return []

    results: list[EpeySearchResult] = []
    # Parse: <li><a href="URL" onClick="getval(ID)">Title</a></li>
    items = re.findall(
        r'<li><a\s+href="([^"]+)"(?:\s+onClick="getval\((\d+)\)")?>(.*?)</a></li>',
        resp.text,
        re.DOTALL,
    )
    for url, epey_id, title_html in items[:10]:
        # Strip HTML tags from title
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        if not title:
            continue
        results.append(EpeySearchResult(
            title=title,
            url=url if url.startswith("http") else f"https://www.epey.com{url}",
            epey_id=int(epey_id) if epey_id else None,
        ))

    return results


async def find_epey_url(product_title: str, brand: str | None = None) -> tuple[str | None, int | None]:
    """
    Prial urunu icin Epey'deki en iyi eslesen URL ve ID'yi bulur.
    Returns: (url, epey_product_id) or (None, None)
    """
    query = f"{brand} {product_title}" if brand else product_title
    words = query.split()
    if len(words) > 8:
        query = " ".join(words[:8])

    print(f"[epey] Aranıyor: {query}", flush=True)

    results = await search_epey(query)
    if not results:
        print(f"[epey] Sonuç bulunamadı: {query}", flush=True)
        return None, None

    # Jaccard match
    catalog_label = f"{brand or ''} {product_title}".strip()
    best_match: EpeySearchResult | None = None
    best_score = 0.0

    for r in results:
        cat_words = _normalize(catalog_label)
        scr_words = _normalize(r.title)
        if not cat_words or not scr_words:
            continue
        intersection = cat_words & scr_words
        union = cat_words | scr_words
        score = len(intersection) / len(union)
        if score > best_score:
            best_score = score
            best_match = r

    if best_match and best_score >= 0.30:
        print(f"[epey] Eşleşme bulundu (jaccard={best_score:.2f}): {best_match.title}", flush=True)
        return best_match.url, best_match.epey_id

    # LLM fallback
    if results:
        llm_match = await _llm_match(catalog_label, results[:8])
        if llm_match:
            print(f"[epey] LLM eşleşme bulundu: {llm_match.title}", flush=True)
            return llm_match.url, llm_match.epey_id

    print(f"[epey] Eşleşme yok (jaccard={best_score:.2f}): {query}", flush=True)
    return None, None


async def extract_price_history(epey_url: str, epey_id: int | None = None) -> list[EpeyPricePoint]:
    """
    Epey urun sayfasindan fiyat gecmisini ceker.
    1. epey_id bilinmiyorsa sayfa HTML'inden cikar
    2. POST /kat/fg/ ile fiyat verisini al
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        product_id = epey_id
        current_price = None

        # Sayfa HTML'inden id ve fiyat cikar
        if not product_id:
            try:
                resp = await client.get(epey_url, headers=HEADERS)
                if resp.status_code != 200:
                    return []
                match = re.search(r'id=(\d+)&fiyat=([\d.]+)', resp.text)
                if match:
                    product_id = int(match.group(1))
                    current_price = match.group(2)
            except Exception as e:
                print(f"[epey] Sayfa hatası: {e}", flush=True)
                return []

        if not product_id:
            print(f"[epey] Product ID bulunamadı: {epey_url}", flush=True)
            return []

        # Fiyat bilinmiyorsa sayfadan cek
        if not current_price:
            try:
                resp = await client.get(epey_url, headers=HEADERS)
                match = re.search(r'fiyat=([\d.]+)', resp.text)
                current_price = match.group(1) if match else "0"
            except Exception:
                current_price = "0"

        # Fiyat gecmisi API
        try:
            resp = await client.post(
                "https://www.epey.com/kat/fg/",
                data={"id": str(product_id), "fiyat": current_price},
                headers={
                    **AJAX_HEADERS,
                    "Referer": epey_url,
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                },
            )
            if resp.status_code != 200:
                print(f"[epey] Fiyat API hatası: {resp.status_code}", flush=True)
                return []

            data = resp.json()
        except Exception as e:
            print(f"[epey] Fiyat API hatası: {e}", flush=True)
            return []

    # Parse: [[tarih_str, fiyat_str, ay_araligi], ...]
    results: list[EpeyPricePoint] = []
    for item in data:
        try:
            date_str = item[0]  # "13.09.2024"
            price_str = item[1]  # "82999.00"
            dt = datetime.strptime(date_str, "%d.%m.%Y").date()
            price = float(price_str)
            if price > 0:
                results.append(EpeyPricePoint(date=dt, price=price))
        except (ValueError, IndexError):
            continue

    if results:
        print(f"[epey] {len(results)} data point çekildi ({results[0].date} - {results[-1].date})", flush=True)

    return results


async def _llm_match(
    product_label: str,
    candidates: list[EpeySearchResult],
) -> EpeySearchResult | None:
    """Claude Haiku ile urun eslestirme."""
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
                    "Bu ürünle aynı olan aday hangisi? "
                    "Sadece numarasını yaz (1-{len}). "
                    "Hiçbiri aynı değilse 0 yaz."
                ).format(len=len(candidates)),
            }],
        )

        answer = resp.content[0].text.strip()
        num_match = re.search(r"(\d+)", answer)
        if not num_match:
            return None

        idx = int(num_match.group(1))
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1]

    except Exception as e:
        print(f"[epey] LLM match hatası: {e}", flush=True)

    return None
