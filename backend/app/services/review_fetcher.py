"""
Mağaza yorumlarını çeken servis.
Trendyol: Ürün sayfası HTML'inden rating + yorum sayfasından review text
Hepsiburada: User content API (ScraperAPI fallback)

Not: public.trendyol.com DNS çözümlenemiyor (Railway dahil).
     Trendyol scraper da HTML fallback kullanıyor.
"""
import re
import json
from dataclasses import dataclass, field
import httpx
from app.services.scraper.base import scraper_api_url

_TRENDYOL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.trendyol.com/",
    "Origin": "https://www.trendyol.com",
}

_HEPSIBURADA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.hepsiburada.com/",
    "Origin": "https://www.hepsiburada.com",
}


@dataclass
class ReviewResult:
    """Tek bir mağaza için yorum çekme sonucu."""
    product_title: str
    store: str
    store_product_id: str
    status: str  # "ok" | "error"
    review_count: int = 0
    rating: float | None = None
    sample_reviews: list[str] = field(default_factory=list)
    error: str | None = None


# ─── Trendyol ────────────────────────────────────────────────────────────────


async def fetch_trendyol_reviews(
    store_product_id: str,
    product_title: str,
    product_url: str = "",
    max_reviews: int = 5,
) -> ReviewResult:
    """
    Trendyol'dan review bilgisi çeker.

    Strateji (public.trendyol.com DNS çözümlenmediği için):
    1) Ürün sayfası HTML'inden ratingScore JSON'u parse et (count + avg)
    2) Yorum sayfası URL'sinden (/yorumlar) review text'leri çek (ScraperAPI)
    """
    base = ReviewResult(
        product_title=product_title,
        store="trendyol",
        store_product_id=store_product_id,
        status="error",
    )

    try:
        html = await _fetch_trendyol_html(product_url, store_product_id)
        if not html:
            base.error = "HTML alınamadı"
            return base

        # ratingScore JSON'u parse et
        rating_match = re.search(
            r'"ratingScore"\s*:\s*\{[^}]*"averageRating"\s*:\s*([\d.]+)[^}]*"totalCount"\s*:\s*(\d+)',
            html,
        )
        if not rating_match:
            # Alternatif sıra
            rating_match = re.search(
                r'"ratingScore"\s*:\s*\{[^}]*"totalCount"\s*:\s*(\d+)[^}]*"averageRating"\s*:\s*([\d.]+)',
                html,
            )
            if rating_match:
                total_count = int(rating_match.group(1))
                avg_rating = float(rating_match.group(2))
            else:
                base.error = "ratingScore bulunamadı"
                return base
        else:
            avg_rating = float(rating_match.group(1))
            total_count = int(rating_match.group(2))

        base.status = "ok"
        base.review_count = total_count
        base.rating = round(avg_rating, 2)

        # Yorum text'lerini çekmeye çalış (bonus — başarısız olsa da rating döner)
        if total_count > 0:
            reviews = await _fetch_trendyol_review_texts(
                html, product_url, store_product_id, max_reviews
            )
            if reviews:
                base.sample_reviews = reviews

        return base

    except Exception as e:
        base.error = str(e)
        return base


async def _fetch_trendyol_html(product_url: str, store_product_id: str) -> str | None:
    """Trendyol ürün sayfası HTML'ini çeker. Direkt dener, yoksa ScraperAPI."""
    # URL yoksa oluşturamayız — store_product_id ile bir şey yapamayız
    if not product_url:
        return None

    # 1) Direkt dene
    try:
        async with httpx.AsyncClient(timeout=15, headers=_TRENDYOL_HEADERS) as client:
            resp = await client.get(product_url)
            if resp.status_code == 200 and len(resp.text) > 10000:
                return resp.text
    except Exception:
        pass

    # 2) ScraperAPI fallback
    try:
        proxy_url = scraper_api_url(product_url, render=False)
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(proxy_url)
            if resp.status_code == 200:
                return resp.text
    except Exception:
        pass

    return None


async def _fetch_trendyol_review_texts(
    html: str,
    product_url: str,
    store_product_id: str,
    max_reviews: int,
) -> list[str]:
    """
    Trendyol yorum metinlerini çeker.
    1) HTML'den contentId çıkar → review API (ScraperAPI proxy)
    2) Fallback: HTML içindeki gömülü yorum verilerinden parse et
    """
    # ── Yöntem 1: Review API via ScraperAPI ──
    content_id = _extract_content_id(html, store_product_id)
    if content_id:
        api_reviews = await _fetch_trendyol_review_api(content_id, max_reviews)
        if api_reviews:
            return api_reviews

    # ── Yöntem 2: HTML'deki gömülü yorumlar (fallback) ──
    reviews: list[str] = []

    # Pattern 1: "comment":"..." şeklinde gömülü yorumlar
    comment_matches = re.findall(r'"comment"\s*:\s*"([^"]{20,300})"', html)
    for c in comment_matches[:max_reviews]:
        try:
            decoded = json.loads(f'"{c}"')
            reviews.append(decoded.strip())
        except Exception:
            reviews.append(c.strip())

    # Pattern 2: "reviewText":"..." formatı
    if not reviews:
        review_matches = re.findall(r'"reviewText"\s*:\s*"([^"]{20,300})"', html)
        for r in review_matches[:max_reviews]:
            try:
                decoded = json.loads(f'"{r}"')
                reviews.append(decoded.strip())
            except Exception:
                reviews.append(r.strip())

    return reviews


def _extract_content_id(html: str, store_product_id: str) -> str | None:
    """HTML'den Trendyol contentId çıkarır."""
    # Pattern: "contentId":12345
    m = re.search(r'"contentId"\s*:\s*(\d+)', html)
    if m:
        return m.group(1)
    # Fallback: store_product_id'yi dene (bazen doğrudan contentId olarak çalışır)
    if store_product_id and store_product_id.isdigit():
        return store_product_id
    return None


async def _fetch_trendyol_review_api(
    content_id: str, max_reviews: int = 50
) -> list[str]:
    """
    Trendyol review API'sini ScraperAPI üzerinden çağırır.
    public.trendyol.com DNS çözümlenmediği için ScraperAPI proxy gerekli.
    """
    size = min(max_reviews, 50)
    review_api_url = (
        f"https://public.trendyol.com/discovery-web-socialgw-service"
        f"/api/review/{content_id}?order=most-recent&size={size}"
    )
    proxy_url = scraper_api_url(review_api_url, render=False)

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(proxy_url)
            if resp.status_code != 200:
                print(f"  [review_api] HTTP {resp.status_code} for contentId={content_id}")
                return []

            data = resp.json()
            result = data.get("result", {})
            product_reviews = result.get("productReviews", [])

            reviews: list[str] = []
            for pr in product_reviews:
                comment = (pr.get("comment") or "").strip()
                if comment and len(comment) >= 10:
                    reviews.append(comment)

            print(f"  [review_api] contentId={content_id} → {len(reviews)} yorum")
            return reviews

    except Exception as e:
        print(f"  [review_api] Hata: {e}")
        return []


# ─── Hepsiburada ─────────────────────────────────────────────────────────────


async def fetch_hepsiburada_reviews(
    store_product_id: str,
    product_title: str,
    product_url: str,
    max_reviews: int = 5,
) -> ReviewResult:
    """
    Hepsiburada'dan yorum çeker.
    1) Direkt review API
    2) ScraperAPI fallback
    """
    base = ReviewResult(
        product_title=product_title,
        store="hepsiburada",
        store_product_id=store_product_id,
        status="error",
    )

    # store_product_id formatları: "pm-XXXXX" veya "HBCV000..."
    sku = store_product_id
    if sku.startswith("pm-"):
        sku = sku[3:]

    try:
        review_url = (
            f"https://user-content-gw-hermes.hepsiburada.com/queryapi/v2/ApprovedUserContents"
            f"?skuList={sku}&from=0&size={max_reviews}"
        )

        # Yöntem 1: Direkt API dene
        try:
            async with httpx.AsyncClient(timeout=15, headers=_HEPSIBURADA_HEADERS) as client:
                resp = await client.get(review_url)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        return _parse_hepsiburada_reviews(data, base, max_reviews)
                    except Exception:
                        pass  # JSON parse hatası — fallback'e geç
        except Exception:
            pass

        # Yöntem 2: ScraperAPI fallback
        proxy_url = scraper_api_url(review_url, render=False)
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(proxy_url)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return _parse_hepsiburada_reviews(data, base, max_reviews)
                except Exception:
                    pass

        # Yöntem 3: Ürün sayfası HTML'inden review bilgisi çek
        return await _fetch_hepsiburada_from_html(product_url, base, max_reviews)

    except Exception as e:
        base.error = str(e)
        return base


def _parse_hepsiburada_reviews(
    data: dict, base: ReviewResult, max_reviews: int
) -> ReviewResult:
    """Hepsiburada review API response'unu parse eder."""
    # Response yapısı değişkenlik gösterebilir
    contents_wrapper = data.get("data", {}).get("approvedUserContent", data)
    contents = contents_wrapper.get("contents", [])
    total = contents_wrapper.get("total", len(contents))

    sample_texts = []
    ratings = []
    for item in contents[:max_reviews]:
        comment = (
            item.get("content", "")
            or item.get("review", "")
            or item.get("comment", "")
        )
        comment = comment.strip()
        if comment:
            sample_texts.append(comment[:300])
        star = item.get("star") or item.get("rating")
        if star:
            ratings.append(float(star))

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    base.status = "ok"
    base.review_count = total
    base.rating = avg_rating
    base.sample_reviews = sample_texts
    return base


async def _fetch_hepsiburada_from_html(
    product_url: str, base: ReviewResult, max_reviews: int
) -> ReviewResult:
    """Hepsiburada ürün sayfası HTML'inden review bilgisi çeker (ScraperAPI)."""
    if not product_url:
        base.error = "URL yok, HTML fallback yapılamadı"
        return base

    try:
        proxy_url = scraper_api_url(product_url, render=False)
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.get(proxy_url)
            if resp.status_code != 200:
                base.error = f"HTML fallback {resp.status_code}"
                return base

        html = resp.text

        # Rating bilgisi: sayfadaki JSON'dan
        rating_match = re.search(r'"ratingScore"\s*:\s*([\d.]+)', html)
        count_match = re.search(r'"reviewCount"\s*:\s*(\d+)', html)

        if rating_match:
            base.rating = round(float(rating_match.group(1)), 2)
        if count_match:
            base.review_count = int(count_match.group(1))

        if base.review_count > 0 or base.rating:
            base.status = "ok"
        else:
            base.error = "HTML'de review bilgisi bulunamadı"

        return base

    except Exception as e:
        base.error = f"HTML fallback hatası: {e}"
        return base
