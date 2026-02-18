import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.product import Product, ProductStore
from app.models.category import Category
from app.schemas.product import CategoryResponse, ProductResponse

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Tüm üst kategoriler ve alt kategorileri."""
    result = await db.execute(
        select(Category).where(Category.parent_id.is_(None))
    )
    return result.scalars().all()


@router.get("/categories/{slug}/products")
async def get_category_products(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort_by: str = Query("discount", regex="^(discount|price_asc|price_desc|alarm_count)$"),
    db: AsyncSession = Depends(get_db),
):
    """Kategori bazlı ürün listeleme."""
    cat_result = await db.execute(select(Category).where(Category.slug == slug))
    category = cat_result.scalar_one_or_none()
    if not category:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")

    query = (
        select(ProductStore)
        .join(Product)
        .where(Product.category_id == category.id)
        .where(ProductStore.in_stock == True)
    )

    if sort_by == "discount":
        query = query.order_by(desc(ProductStore.discount_percent))
    elif sort_by == "price_asc":
        query = query.order_by(ProductStore.current_price)
    elif sort_by == "price_desc":
        query = query.order_by(desc(ProductStore.current_price))
    elif sort_by == "alarm_count":
        query = query.order_by(desc(Product.alarm_count))

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return result.scalars().all()


@router.get("/search")
async def search_products(
    q: str = Query(min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Ürün arama (başlık ve marka üzerinden)."""
    search_term = f"%{q}%"
    query = (
        select(Product)
        .where(Product.title.ilike(search_term) | Product.brand.ilike(search_term))
        .order_by(desc(Product.alarm_count))
    )
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return result.scalars().all()
