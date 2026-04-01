"""
SEO Pipeline — günlük otomatik SEO bakımı.

İki aşama:
1. seo_revalidate (08:30) — Gece pipeline'ı bittikten sonra web cache'i temizle + sitemap ping
2. seo_audit (09:00) — SEO sağlık kontrolü: kırık URL, eksik image, sitemap coverage
"""
from __future__ import annotations

import httpx
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore


# ─────────────────────────────────────────────
# 1. REVALIDATE + SITEMAP PING
# ─────────────────────────────────────────────

async def seo_revalidate() -> dict:
    """
    Gece pipeline'ı bittikten sonra çalışır.
    - Web ISR cache'ini temizler (tüm ana tag'ler)
    - Google & Bing'e sitemap ping atar
    """
    stats: dict = {
        "revalidated_tags": [],
        "revalidation_ok": False,
        "google_ping": False,
        "bing_ping": False,
    }

    base = settings.web_base_url.rstrip("/")
    secret = settings.revalidate_secret

    # ── 1a. Web Cache Revalidation ──
    if secret:
        tags_to_revalidate = [
            "product",
            "category",
        ]

        # Ayrıca son 24 saatte fiyatı değişen ürünlerin tag'lerini ekle
        changed_tags = await _get_changed_product_tags()
        tags_to_revalidate.extend(changed_tags)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{base}/api/revalidate",
                    headers={"x-revalidate-secret": secret},
                    json={"tags": tags_to_revalidate},
                )
                if resp.status_code == 200:
                    stats["revalidated_tags"] = tags_to_revalidate
                    stats["revalidation_ok"] = True
                    print(f"[seo_pipeline] Revalidation OK: {len(tags_to_revalidate)} tag", flush=True)
                else:
                    print(f"[seo_pipeline] Revalidation HATA: HTTP {resp.status_code}", flush=True)
        except Exception as e:
            print(f"[seo_pipeline] Revalidation HATA: {e}", flush=True)
    else:
        print("[seo_pipeline] REVALIDATE_SECRET tanımlı değil, revalidation atlandı", flush=True)

    # ── 1b. Sitemap Ping ──
    sitemap_url = f"{base}/sitemap.xml"

    async with httpx.AsyncClient(timeout=15) as client:
        # Google
        try:
            resp = await client.get(
                "https://www.google.com/ping",
                params={"sitemap": sitemap_url},
            )
            stats["google_ping"] = resp.status_code == 200
            print(f"[seo_pipeline] Google ping: {resp.status_code}", flush=True)
        except Exception as e:
            print(f"[seo_pipeline] Google ping HATA: {e}", flush=True)

        # Bing
        try:
            resp = await client.get(
                "https://www.bing.com/ping",
                params={"sitemap": sitemap_url},
            )
            stats["bing_ping"] = resp.status_code == 200
            print(f"[seo_pipeline] Bing ping: {resp.status_code}", flush=True)
        except Exception as e:
            print(f"[seo_pipeline] Bing ping HATA: {e}", flush=True)

    return stats


async def _get_changed_product_tags() -> list[str]:
    """Son 24 saatte fiyatı değişen ürünlerin ISR tag'lerini döner."""
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)

    async with AsyncSessionLocal() as db:
        # Son 24 saatte güncellenen store'ların product_id'leri
        result = await db.execute(
            select(ProductStore.product_id)
            .where(ProductStore.last_checked_at >= yesterday)
            .distinct()
            .limit(500)  # Çok fazla tag göndermemek için sınırla
        )
        product_ids = [row[0] for row in result.all()]

    # Her ürün için ISR tag'i: "product-{id}" formatında
    tags = [f"product-{pid}" for pid in product_ids]

    # Ayrıca ilgili kategorileri de ekle
    if product_ids:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product.category_id)
                .where(Product.id.in_(product_ids[:100]))
                .distinct()
            )
            cat_ids = [row[0] for row in result.all() if row[0]]
            tags.extend(f"category-{cid}" for cid in cat_ids)

    return tags


# ─────────────────────────────────────────────
# 2. SEO AUDIT
# ─────────────────────────────────────────────

async def seo_audit() -> dict:
    """
    Günlük SEO sağlık kontrolü.
    Sorunları tespit eder ve rapor üretir.
    """
    report: dict = {}

    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # ── 2a. Toplam ürün & sitemap coverage ──
        total_products = await _count(db, select(func.count(Product.id)))
        products_with_image = await _count(db, select(func.count(Product.id)).where(
            Product.image_url.isnot(None),
        ))
        products_with_category = await _count(db, select(func.count(Product.id)).where(
            Product.category_id.isnot(None),
        ))
        products_with_price = await _count(db, select(func.count(func.distinct(ProductStore.product_id))).where(
            ProductStore.is_active == True,  # noqa: E712
            ProductStore.current_price.isnot(None),
        ))

        report["coverage"] = {
            "total_products": total_products,
            "with_image": products_with_image,
            "with_category": products_with_category,
            "with_active_price": products_with_price,
            "image_pct": _pct(products_with_image, total_products),
            "category_pct": _pct(products_with_category, total_products),
            "price_pct": _pct(products_with_price, total_products),
        }

        # ── 2b. Görüntülenebilir ürünler (SEO'da değerli = image + fiyat + kategori) ──
        seo_ready = await _count(db, select(func.count(Product.id)).where(
            Product.image_url.isnot(None),
            Product.category_id.isnot(None),
            Product.id.in_(
                select(ProductStore.product_id).where(
                    ProductStore.is_active == True,  # noqa: E712
                    ProductStore.current_price.isnot(None),
                ).distinct()
            ),
        ))
        report["seo_ready_products"] = seo_ready

        # ── 2c. Eksik image'ler (yüksek öncelik — alarm_count > 0 ama image yok) ──
        missing_image_important = await _count(db, select(func.count(Product.id)).where(
            Product.image_url.is_(None),
            Product.alarm_count > 0,
        ))
        report["missing_image_with_alarms"] = missing_image_important

        # ── 2d. Kategorisiz ürünler ──
        no_category = await _count(db, select(func.count(Product.id)).where(
            Product.category_id.is_(None),
        ))
        report["no_category"] = no_category

        # ── 2e. Description eksik (SEO açısından thin content) ──
        no_description = await _count(db, select(func.count(Product.id)).where(
            Product.description.is_(None),
            Product.image_url.isnot(None),  # sadece görüntülenebilir ürünler
        ))
        report["no_description"] = no_description

        # ── 2f. Son 24 saatte eklenen yeni ürünler (indexlenmesi gereken) ──
        yesterday = now - timedelta(hours=24)
        new_products = await _count(db, select(func.count(Product.id)).where(
            Product.created_at >= yesterday,
        ))
        report["new_products_24h"] = new_products

        # ── 2g. Brand dağılımı (marka sayfaları için) ──
        brand_result = await db.execute(
            select(func.count(func.distinct(Product.brand))).where(
                Product.brand.isnot(None),
            )
        )
        unique_brands = brand_result.scalar() or 0
        report["unique_brands"] = unique_brands

        # ── 2h. Store dağılımı (her mağazadan kaç aktif listing) ──
        store_result = await db.execute(
            select(ProductStore.store, func.count())
            .where(
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.current_price.isnot(None),
            )
            .group_by(ProductStore.store)
        )
        report["active_store_listings"] = {
            row[0].value: row[1] for row in store_result.all()
        }

    # ── Sağlık değerlendirmesi ──
    issues = []

    if report["coverage"]["image_pct"] < 80:
        issues.append(f"Image coverage düşük: %{report['coverage']['image_pct']}")
    if report["coverage"]["category_pct"] < 90:
        issues.append(f"Kategori coverage düşük: %{report['coverage']['category_pct']}")
    if report["missing_image_with_alarms"] > 10:
        issues.append(f"Alarm'lı ama image'sız ürün: {report['missing_image_with_alarms']}")
    if report["no_category"] > total_products * 0.1:
        issues.append(f"Kategorisiz ürün oranı yüksek: {report['no_category']}")

    report["health"] = {
        "status": "healthy" if not issues else "needs_attention",
        "issues": issues,
        "seo_ready_pct": _pct(seo_ready, total_products),
    }

    print(
        f"[seo_audit] Tamamlandı: {report['health']['status']} | "
        f"SEO-ready: {seo_ready}/{total_products} (%{report['health']['seo_ready_pct']}) | "
        f"Yeni ürün (24h): {new_products} | "
        f"Sorunlar: {len(issues)}",
        flush=True,
    )

    return report


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

async def _count(db, query) -> int:
    result = await db.execute(query)
    return result.scalar() or 0


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total else 0.0
