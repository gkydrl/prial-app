"""
Admin endpoints — ürün kataloğu yönetimi.
X-Admin-Key header ile korunur.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
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


@router.post("/crawl/trigger")
async def trigger_crawl(
    _: None = Depends(require_admin),
):
    """Katalog crawler'ını manuel tetikler (test/debug için)."""
    import asyncio
    from app.services.catalog_crawler import crawl_all_variants
    asyncio.create_task(crawl_all_variants())
    return {"message": "Crawler başlatıldı (arka planda çalışıyor)"}
