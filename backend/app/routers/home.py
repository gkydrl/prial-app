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
    """Shared serializer for price-history-based endpoints."""
    return [
        {
            "product": {
                "id": str(row[0].product.id),
                "title": row[0].product.title,
                "brand": row[0].product.brand,
                "description": None,
                "image_url": row[0].product.image_url,
                "lowest_price_ever": float(row[0].product.lowest_price_ever) if row[0].product.lowest_price_ever else None,
                "alarm_count": row[0].product.alarm_count,
                "stores": [],
                "created_at": row[0].product.created_at.isoformat(),
            },
            "store": {
                "id": str(row[0].id),
                "store": row[0].store.value,
                "url": row[0].url,
                "current_price": float(row[1]),
                "original_price": float(row[2]),
                "currency": row[0].currency,
                "discount_percent": row[0].discount_percent,
                "in_stock": row[0].in_stock,
                "last_checked_at": row[0].last_checked_at.isoformat() if row[0].last_checked_at else None,
            },
            "price_24h_ago": float(row[2]),
            "price_now": float(row[1]),
            "drop_amount": float(row[2] - row[1]),
            "drop_percent": round(float((row[2] - row[1]) / row[2] * 100), 1),
        }
        for row in db_result
    ]


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


@router.get("/daily-deals")
async def daily_deals(
    limit: int = 20,
    period: str = Query(default="1d"),
    db: AsyncSession = Depends(get_db),
):
    """Son dönemde en çok oransal düşen ürünler (Bugünün Fırsatları)."""
    since = _since(period)
    subquery = _price_history_subquery(since)

    result = await db.execute(
        select(ProductStore, subquery.c.min_price, subquery.c.max_price)
        .join(subquery, ProductStore.id == subquery.c.product_store_id)
        .options(selectinload(ProductStore.product))
        .where(subquery.c.max_price > subquery.c.min_price)
        .order_by(desc((subquery.c.max_price - subquery.c.min_price) / subquery.c.max_price))
        .limit(limit)
    )
    return _price_history_rows(result.all())


@router.get("/top-drops")
async def top_drops(
    limit: int = 20,
    period: str = Query(default="1d"),
    db: AsyncSession = Depends(get_db),
):
    """Son dönemde en çok fiyat düşen ürünler (₺ bazında)."""
    since = _since(period)
    subquery = _price_history_subquery(since)

    result = await db.execute(
        select(ProductStore, subquery.c.min_price, subquery.c.max_price)
        .join(subquery, ProductStore.id == subquery.c.product_store_id)
        .options(selectinload(ProductStore.product))
        .where(subquery.c.max_price > subquery.c.min_price)
        .order_by(desc(subquery.c.max_price - subquery.c.min_price))
        .limit(limit)
    )
    return _price_history_rows(result.all())


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
