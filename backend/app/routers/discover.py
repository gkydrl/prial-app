import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, exists, func

from app.database import get_db
from app.models.product import Product, ProductStore, ProductVariant
from app.models.category import Category
from app.schemas.product import CategoryResponse, ProductResponse

router = APIRouter(prefix="/discover", tags=["discover"])

# Teknoloji kategorileri — öncelikli sıra
_TECH_CATEGORY_SLUGS = [
    "akilli-telefon", "telefon", "tablet", "laptop",
    "akilli-saat", "kulaklik-ses", "televizyon",
    "fotograf-makinesi", "oyun-gaming", "bilgisayar-bilesenleri",
    "akilli-ev", "bilgisayar",
]


def _has_store_subquery():
    """En az bir aktif, fiyatlı store'u olan ürün filtresi."""
    return (
        exists()
        .where(
            ProductStore.product_id == Product.id,
            ProductStore.is_active == True,
            ProductStore.current_price > 0,
        )
        .correlate(Product)
    )


@router.get("/products", response_model=list[ProductResponse])
async def get_all_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort_by: str = Query("alarm_count", regex="^(price_asc|price_desc|alarm_count|newest)$"),
    db: AsyncSession = Depends(get_db),
):
    """Keşfet ana görünümü — yalnızca mağaza+fiyatı olan ürünler, teknoloji kategorileri önce."""
    from sqlalchemy.orm import selectinload

    # Teknoloji kategorisi sıralaması: tech slug'lar önce, diğerleri sonra
    tech_slugs = _TECH_CATEGORY_SLUGS
    tech_rank = (
        select(func.row_number().over(order_by=func.array_position(
            # PostgreSQL array_position ile sıralama
            func.cast(tech_slugs, type_=None),
            Category.slug,
        )))
    )

    # Sadece aktif mağazası olan ürünler
    query = (
        select(Product)
        .where(_has_store_subquery())
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.stores),
            selectinload(Product.stores),
        )
    )

    if sort_by == "price_asc":
        query = query.order_by(Product.lowest_price_ever.asc().nulls_last())
    elif sort_by == "price_desc":
        query = query.order_by(Product.lowest_price_ever.desc().nulls_last())
    elif sort_by == "newest":
        query = query.order_by(desc(Product.created_at))
    else:
        # Teknoloji kategorilerini önceliklendir, sonra alarm_count
        tech_case = (
            select(Category.slug)
            .where(Category.id == Product.category_id)
            .correlate(Product)
            .scalar_subquery()
        )
        from sqlalchemy import case
        is_tech = case(
            (tech_case.in_(tech_slugs), 0),
            else_=1,
        )
        query = query.order_by(is_tech, desc(Product.alarm_count), desc(Product.lowest_price_ever))

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    return result.scalars().all()


@router.get("/categories", response_model=list[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Tüm üst kategoriler — ürün sayısı ile birlikte (aktif mağazası olanlar)."""
    # Her kategori için aktif mağazası+fiyatı olan ürün sayısı
    store_exists = (
        exists()
        .where(
            ProductStore.product_id == Product.id,
            ProductStore.is_active == True,
            ProductStore.current_price > 0,
        )
    )
    count_subq = (
        select(func.count(Product.id))
        .where(Product.category_id == Category.id, store_exists)
        .correlate(Category)
        .scalar_subquery()
    )

    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Category, count_subq.label("product_count"))
        .where(Category.parent_id.is_(None))
        .options(selectinload(Category.children))
    )

    categories = []
    for row in result.all():
        cat = row[0]
        cat.product_count = row[1] or 0
        categories.append(cat)

    return categories


@router.get("/categories/{slug}/products", response_model=list[ProductResponse])
async def get_category_products(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    sort_by: str = Query("alarm_count", regex="^(price_asc|price_desc|alarm_count)$"),
    db: AsyncSession = Depends(get_db),
):
    """Kategori bazlı ürün listeleme. Mağazası olanlar önce gelir."""
    from fastapi import HTTPException
    from sqlalchemy.orm import selectinload
    from sqlalchemy import case

    cat_result = await db.execute(select(Category).where(Category.slug == slug))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Kategori bulunamadı")

    query = (
        select(Product)
        .where(Product.category_id == category.id, _has_store_subquery())
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.stores),
            selectinload(Product.stores),
        )
    )

    if sort_by == "price_asc":
        query = query.order_by(Product.lowest_price_ever.asc().nulls_last())
    elif sort_by == "price_desc":
        query = query.order_by(Product.lowest_price_ever.desc().nulls_last())
    else:
        query = query.order_by(desc(Product.alarm_count), desc(Product.lowest_price_ever))

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
