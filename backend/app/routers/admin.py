"""
Admin endpoints — ürün kataloğu yönetimi.
X-Admin-Key header ile korunur.
"""
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.product import Product, ProductVariant
from app.models.category import Category
from app.schemas.admin import AdminProductCreate, AdminProductResponse

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> None:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Yetkisiz")


@router.post("/products", response_model=AdminProductResponse, status_code=201)
async def seed_product(
    payload: AdminProductCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """
    Ürünü store URL'siz kataloga ekler.
    Crawler günlük olarak mağaza bağlantılarını otomatik kurar.
    """
    # Kategori bul
    category_id: uuid.UUID | None = None
    if payload.category_slug:
        res = await db.execute(
            select(Category).where(Category.slug == payload.category_slug)
        )
        cat = res.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail=f"Kategori bulunamadı: {payload.category_slug}")
        category_id = cat.id

    # Aynı brand+title zaten var mı?
    dup_q = select(Product).where(Product.title == payload.title)
    if payload.brand:
        dup_q = dup_q.where(Product.brand == payload.brand)
    dup = (await db.execute(dup_q)).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=409,
            detail={"code": "PRODUCT_EXISTS", "product_id": str(dup.id)},
        )

    # Ürünü oluştur
    product = Product(
        title=payload.title,
        brand=payload.brand,
        description=payload.description,
        image_url=payload.image_url,
        category_id=category_id,
        alarm_count=0,
    )
    db.add(product)
    await db.flush()

    # Variantları oluştur
    variant_inputs = payload.variants or [{"title": None, "attributes": {}, "image_url": None}]
    for vi in variant_inputs:
        attrs = vi.attributes if isinstance(vi, dict) else vi.attributes
        title = vi.title if isinstance(vi, dict) else vi.title
        img = vi.image_url if isinstance(vi, dict) else vi.image_url

        variant = ProductVariant(
            product_id=product.id,
            title=title,
            attributes=attrs or {},
            image_url=img or payload.image_url,
        )
        db.add(variant)

    await db.commit()

    return AdminProductResponse(
        id=product.id,
        title=product.title,
        brand=product.brand,
        variant_count=len(variant_inputs),
    )


@router.post("/products/{product_id}/variants", status_code=201)
async def add_variant(
    product_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Mevcut ürüne yeni variant ekler."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    variant = ProductVariant(
        product_id=product_id,
        title=payload.get("title"),
        attributes=payload.get("attributes", {}),
        image_url=payload.get("image_url"),
    )
    db.add(variant)
    await db.commit()
    return {"variant_id": str(variant.id)}


@router.get("/products", response_model=list[AdminProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Katalogdaki tüm ürünleri listeler (variant sayısıyla birlikte)."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Product).options(selectinload(Product.variants)).order_by(Product.created_at.desc())
    )
    products = result.scalars().all()
    return [
        AdminProductResponse(
            id=p.id,
            title=p.title,
            brand=p.brand,
            variant_count=len(p.variants),
        )
        for p in products
    ]


@router.get("/debug/config")
async def debug_config(_: None = Depends(require_admin)):
    """Railway'deki config değerlerini kontrol eder (key'ler maskelenir)."""
    key = settings.scraper_api_key
    anthropic = settings.anthropic_api_key
    return {
        "scraper_api_key": f"{key[:6]}...{key[-4:]}" if len(key) > 10 else f"({len(key)} karakter — ÇOK KISA)",
        "anthropic_api_key_set": bool(anthropic),
        "admin_api_key": f"{settings.admin_api_key[:4]}...",
        "crawler_search_concurrency": settings.crawler_search_concurrency,
        "crawler_results_per_store": settings.crawler_results_per_store,
    }


@router.get("/debug/scraper-test")
async def debug_scraper_test(_: None = Depends(require_admin)):
    """Tek bir ScraperAPI araması yaparak bağlantıyı test eder."""
    import httpx
    key = settings.scraper_api_key
    if not key:
        return {"error": "SCRAPER_API_KEY boş"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"https://api.scraperapi.com/structured/google/search?query=iphone+16+trendyol&country_code=tr&num=2&api_key={key}"
            )
            raw = resp.text[:500]
            try:
                data = resp.json()
                return {"status": resp.status_code, "result_count": len(data.get("organic_results", [])), "raw_preview": raw[:200]}
            except Exception:
                return {"status": resp.status_code, "raw_preview": raw}
    except Exception as e:
        return {"error": str(e)}


@router.post("/crawl/trigger")
async def trigger_crawl(
    background_tasks: BackgroundTasks,
    _: None = Depends(require_admin),
):
    """Katalog crawler'ını manuel tetikler (test/debug için)."""
    from app.services.catalog_crawler import crawl_all_variants

    async def _run():
        await crawl_all_variants()

    background_tasks.add_task(_run)
    return {"message": "Crawler başlatıldı (arka planda çalışıyor)"}
