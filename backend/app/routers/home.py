from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory
from app.models.alarm import Alarm, AlarmStatus
from app.schemas.product import ProductResponse, ProductStoreResponse

router = APIRouter(prefix="/home", tags=["home"])

PERIOD_HOURS: dict[str, int] = {
    "1d": 24,
    "7d": 24 * 7,
    "30d": 24 * 30,
    "90d": 24 * 90,
    "365d": 24 * 365,
}


def _since(period: str) -> datetime:
    hours = PERIOD_HOURS.get(period, 24)
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _price_history_rows(db_result):
    """Shared serializer for price-history-based endpoints.

    row[0] = ProductStore (with .current_price = gerçek anlık fiyat)
    row[1] = min_price (dönemdeki en düşük)
    row[2] = max_price (dönemdeki en yüksek)
    """
    rows = []
    for row in db_result:
        store: ProductStore = row[0]
        min_price = float(row[1])
        max_price = float(row[2])
        # Gerçek anlık fiyat — tarihsel min değil
        current = float(store.current_price) if store.current_price else min_price
        # Fiyat geri çıkmışsa (şu an tarihsel maksimuma yakınsa) listeye alma
        if max_price > 0 and current >= max_price * 0.95:
            continue
        rows.append({
            "product": {
                "id": str(store.product.id),
                "title": store.product.title,
                "brand": store.product.brand,
                "description": None,
                "image_url": store.product.image_url,
                "lowest_price_ever": float(store.product.lowest_price_ever) if store.product.lowest_price_ever else None,
                "alarm_count": store.product.alarm_count,
                "stores": [],
                "created_at": store.product.created_at.isoformat(),
            },
            "store": {
                "id": str(store.id),
                "store": store.store.value,
                "url": store.url,
                "current_price": current,
                "original_price": max_price,
                "currency": store.currency,
                "discount_percent": store.discount_percent,
                "in_stock": store.in_stock,
                "last_checked_at": store.last_checked_at.isoformat() if store.last_checked_at else None,
            },
            "price_24h_ago": max_price,
            "price_now": current,
            "drop_amount": max_price - current,
            "drop_percent": round((max_price - current) / max_price * 100, 1),
        })
    return rows


def _price_history_subquery(since: datetime):
    return (
        select(
            PriceHistory.product_store_id,
            func.min(PriceHistory.price).label("min_price"),
            func.max(PriceHistory.price).label("max_price"),
        )
        .where(PriceHistory.recorded_at >= since)
        .where(PriceHistory.price > 0)  # 0 fiyatlı bozuk kayıtları dışla
        .group_by(PriceHistory.product_store_id)
        .subquery()
    )


def _discount_fallback_rows(stores: list[ProductStore]) -> list[dict]:
    """original_price > current_price olan mağazaları TopDropResponse formatında döndürür."""
    rows = []
    for s in stores:
        if not s.current_price or not s.original_price:
            continue
        cur = float(s.current_price)
        orig = float(s.original_price)
        if orig <= cur:
            continue
        rows.append({
            "product": {
                "id": str(s.product.id),
                "title": s.product.title,
                "brand": s.product.brand,
                "description": None,
                "image_url": s.product.image_url,
                "lowest_price_ever": float(s.product.lowest_price_ever) if s.product.lowest_price_ever else None,
                "alarm_count": s.product.alarm_count,
                "stores": [],
                "created_at": s.product.created_at.isoformat(),
            },
            "store": {
                "id": str(s.id),
                "store": s.store.value,
                "url": s.url,
                "current_price": cur,
                "original_price": orig,
                "currency": s.currency,
                "discount_percent": s.discount_percent,
                "in_stock": s.in_stock,
                "last_checked_at": s.last_checked_at.isoformat() if s.last_checked_at else None,
            },
            "price_24h_ago": orig,
            "price_now": cur,
            "drop_amount": orig - cur,
            "drop_percent": round((orig - cur) / orig * 100, 1),
        })
    return rows


@router.get("/daily-deals")
async def daily_deals(
    limit: int = 20,
    period: str = Query(default="30d"),
    db: AsyncSession = Depends(get_db),
):
    """Son dönemde en çok oransal düşen ürünler. Yeterli history yoksa indirimli ürünler gösterilir."""
    since = _since(period)
    subquery = _price_history_subquery(since)

    result = await db.execute(
        select(ProductStore, subquery.c.min_price, subquery.c.max_price)
        .join(subquery, ProductStore.id == subquery.c.product_store_id)
        .options(selectinload(ProductStore.product))
        .where(
            subquery.c.max_price > subquery.c.min_price,
            ProductStore.in_stock == True,
            ProductStore.is_active == True,
        )
        .order_by(desc((subquery.c.max_price - subquery.c.min_price) / subquery.c.max_price))
        .limit(limit)
    )
    rows = _price_history_rows(result.all())

    if len(rows) < 5:
        fb_result = await db.execute(
            select(ProductStore)
            .options(selectinload(ProductStore.product))
            .where(
                ProductStore.is_active == True,
                ProductStore.in_stock == True,
                ProductStore.original_price > ProductStore.current_price,
                ProductStore.current_price > 0,
            )
            .order_by(desc(
                (ProductStore.original_price - ProductStore.current_price) / ProductStore.original_price
            ))
            .limit(limit)
        )
        rows = _discount_fallback_rows(fb_result.scalars().all())

    return rows


@router.get("/top-drops")
async def top_drops(
    limit: int = 20,
    period: str = Query(default="30d"),
    db: AsyncSession = Depends(get_db),
):
    """Son dönemde en çok ₺ düşen ürünler. Yeterli history yoksa indirimli ürünler gösterilir."""
    since = _since(period)
    subquery = _price_history_subquery(since)

    result = await db.execute(
        select(ProductStore, subquery.c.min_price, subquery.c.max_price)
        .join(subquery, ProductStore.id == subquery.c.product_store_id)
        .options(selectinload(ProductStore.product))
        .where(
            subquery.c.max_price > subquery.c.min_price,
            ProductStore.in_stock == True,
            ProductStore.is_active == True,
        )
        .order_by(desc(subquery.c.max_price - subquery.c.min_price))
        .limit(limit)
    )
    rows = _price_history_rows(result.all())

    if len(rows) < 5:
        fb_result = await db.execute(
            select(ProductStore)
            .options(selectinload(ProductStore.product))
            .where(
                ProductStore.is_active == True,
                ProductStore.in_stock == True,
                ProductStore.original_price > ProductStore.current_price,
                ProductStore.current_price > 0,
            )
            .order_by(desc(ProductStore.original_price - ProductStore.current_price))
            .limit(limit)
        )
        rows = _discount_fallback_rows(fb_result.scalars().all())

    return rows


@router.get("/most-alarmed")
async def most_alarmed(
    limit: int = 20,
    period: str = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """En çok alarm kurulan ürünler. period verilirse o dönemde oluşturulan alarmlara göre sıralar."""
    if period and period in PERIOD_HOURS:
        since = _since(period)
        subq = (
            select(
                Alarm.product_id,
                func.count(Alarm.id).label("period_count"),
            )
            .where(Alarm.created_at >= since)
            .where(Alarm.status != AlarmStatus.DELETED)
            .group_by(Alarm.product_id)
            .subquery()
        )
        result = await db.execute(
            select(Product)
            .join(subq, Product.id == subq.c.product_id)
            .options(selectinload(Product.stores))
            .order_by(desc(subq.c.period_count))
            .limit(limit)
        )
    else:
        result = await db.execute(
            select(Product)
            .options(selectinload(Product.stores))
            .order_by(desc(Product.alarm_count), desc(Product.created_at))
            .limit(limit)
        )
    return result.scalars().all()
