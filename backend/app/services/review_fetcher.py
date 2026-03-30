"""
Mağaza yorumlarını çeken servis.
Trendyol: Public API (contentId üzerinden review endpoint)
Hepsiburada: User content API (sku üzerinden)
"""
import re
from dataclasses import dataclass
import httpx
from app.services.scraper.base import scraper_api_url

# Trendyol ile aynı header pattern
_TRENDYOL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
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
    sample_reviews: list[str] | None = None
    error: str | None = None


async def fetch_trendyol_reviews(
    store_product_id: str,
    product_title: str,
    max_reviews: int = 5,
) -> ReviewResult:
    """
    Trendyol'dan yorum çeker.
    1) Product API'den contentId al
    2) Review API'den yorumları çek
    """
    base = ReviewResult(
        product_title=product_title,
        store="trendyol",
        store_product_id=store_product_id,
        status="error",
    )

    try:
        # Adım 1: Product API'den contentId al
        product_api = (
            f"https://public.trendyol.com/discovery-web-productgw-service/api/"
            f"renderingserviceproductpage/pdp/{store_product_id}?channelId=1&gender=na"
        )
        async with httpx.AsyncClient(timeout=15, headers=_TRENDYOL_HEADERS) as client:
            resp = await client.get(product_api)
            if resp.status_code != 200:
                base.error = f"Product API {resp.status_code}"
                return base

            data = resp.json()
            product = data.get("result", {}).get("product", {})
            content_id = product.get("contentId")
            rating_score = product.get("ratingScore", {})

            if not content_id:
                base.error = "contentId bulunamadı"
                return base

        # Adım 2: Review API'den yorumları çek
        review_url = (
            f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/api/"
            f"review/{content_id}?order=most-recent&size={max_reviews}"
        )
        async with httpx.AsyncClient(timeout=15, headers=_TRENDYOL_HEADERS) as client:
            resp = await client.get(review_url)
            if resp.status_code != 200:
                base.error = f"Review API {resp.status_code}"
                return base

            review_data = resp.json()

        # Parse
        result = review_data.get("result", {})
        total_count = (
            result.get("totalReviewCount")
            or result.get("productReviewsCount")
            or result.get("totalCount")
            or 0
        )

        avg_rating = (
            rating_score.get("averageRating")
            or result.get("ratingScore", {}).get("averageRating")
        )

        reviews_list = result.get("productReviews", [])
        sample_texts = []
        for r in reviews_list[:max_reviews]:
            comment = r.get("comment", "").strip()
            if comment:
                sample_texts.append(comment[:300])

        base.status = "ok"
        base.review_count = total_count
        base.rating = round(float(avg_rating), 2) if avg_rating else None
        base.sample_reviews = sample_texts
        return base

    except Exception as e:
        base.error = str(e)
        return base


async def fetch_hepsiburada_reviews(
    store_product_id: str,
    product_title: str,
    product_url: str,
    max_reviews: int = 5,
) -> ReviewResult:
    """
    Hepsiburada'dan yorum çeker.
    User content API endpoint'i üzerinden.
    """
    base = ReviewResult(
        product_title=product_title,
        store="hepsiburada",
        store_product_id=store_product_id,
        status="error",
    )

    # store_product_id pm-XXXXX formatında — "pm-" prefix'ini kaldır
    sku = store_product_id
    if sku.startswith("pm-"):
        sku = sku[3:]

    try:
        # Yöntem 1: Direkt API dene
        review_url = (
            f"https://user-content-gw-hermes.hepsiburada.com/queryapi/v2/ApprovedUserContents"
            f"?skuList={sku}&from=0&size={max_reviews}"
        )
        async with httpx.AsyncClient(timeout=15, headers=_HEPSIBURADA_HEADERS) as client:
            resp = await client.get(review_url)

            if resp.status_code == 200:
                data = resp.json()
                return _parse_hepsiburada_reviews(data, base, max_reviews)

        # Yöntem 2: ScraperAPI fallback
        proxy_url = scraper_api_url(review_url, render=False)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(proxy_url)
            if resp.status_code == 200:
                data = resp.json()
                return _parse_hepsiburada_reviews(data, base, max_reviews)

        base.error = f"Her iki yöntem de başarısız (son status: {resp.status_code})"
        return base

    except Exception as e:
        base.error = str(e)
        return base


def _parse_hepsiburada_reviews(
    data: dict, base: ReviewResult, max_reviews: int
) -> ReviewResult:
    """Hepsiburada review API response'unu parse eder."""
    # Response yapısı: {"data": {"approvedUserContent": {"contents": [...], "total": N}}}
    # veya doğrudan {"contents": [...], "total": N}
    contents_wrapper = data.get("data", {}).get("approvedUserContent", data)
    contents = contents_wrapper.get("contents", [])
    total = contents_wrapper.get("total", len(contents))

    sample_texts = []
    ratings = []
    for item in contents[:max_reviews]:
        comment = item.get("content", "") or item.get("review", "") or item.get("comment", "")
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
