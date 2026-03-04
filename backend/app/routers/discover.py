import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.product import Product, ProductStore
from app.models.category import Category
from app.schemas.product import CategoryResponse, ProductResponse

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("/products", response_model=list[ProductResponse])
async def get_all_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort_by: str = Query("alarm_count", regex="^(price_asc|price_desc|alarm_count|newest)$"),
    db: AsyncSession = Depends(get_db),
):
    """Tüm ürünleri listeler (store olmayan ürünler dahil)."""
    from sqlalchemy.orm import selectinload

    query = select(Product).options(
        selectinload(Product.variants),
        selectinload(Product.stores),
    )

    if sort_by == "price_asc":
        query = query.order_by(Product.lowest_price_ever.asc().nulls_last())
    elif sort_by == "price_desc":
        query = query.order_by(Product.lowest_price_ever.desc().nulls_last())
    elif sort_by == "newest":
        query = query.order_by(desc(Product.created_at))
    else:
        query = query.order_by(desc(Product.alarm_count))

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return result.scalars().all()


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Tüm üst kategoriler ve alt kategorileri."""
    result = await db.execute(
        select(Category).where(Category.parent_id.is_(None))
    )
    return result.scalars().all()


@router.get("/categories/{slug}/products", response_model=list[ProductResponse])
async def get_category_products(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort_by: str = Query("alarm_count", regex="^(price_asc|price_desc|alarm_count)$"),
    db: AsyncSession = Depends(get_db),
):
    """Kategori bazlı ürün listeleme. Store olmayan ürünler de dahil edilir."""
    from fastapi import HTTPException
    from sqlalchemy.orm import selectinload

    cat_result = await db.execute(select(Category).where(Category.slug == slug))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")

    query = (
        select(Product)
        .where(Product.category_id == category.id)
        .options(
            selectinload(Product.variants),
            selectinload(Product.stores),
        )
    )

    if sort_by == "price_asc":
        query = query.order_by(Product.lowest_price_ever.asc().nulls_last())
    elif sort_by == "price_desc":
        query = query.order_by(Product.lowest_price_ever.desc().nulls_last())
    else:
        query = query.order_by(desc(Product.alarm_count))

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return result.scalars().all()


@router.get("/search", response_model=list[ProductResponse])
async def search_products(
    q: str = Query(min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Ürün arama (başlık ve marka üzerinden)."""
    from sqlalchemy.orm import selectinload

    search_term = f"%{q}%"
    query = (
        select(Product)
        .where(Product.title.ilike(search_term) | Product.brand.ilike(search_term))
        .options(selectinload(Product.variants), selectinload(Product.stores))
        .order_by(desc(Product.alarm_count))
    )
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return result.scalars().all()
