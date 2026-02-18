from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory
from app.schemas.product import ProductResponse, ProductStoreResponse

router = APIRouter(prefix="/home", tags=["home"])


@router.get("/daily-deals")
async def daily_deals(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Bugünün indirimleri — discount_percent'e göre sıralı."""
    result = await db.execute(
        select(ProductStore)
        .where(ProductStore.discount_percent.isnot(None))
        .where(ProductStore.in_stock == True)
        .order_by(desc(ProductStore.discount_percent))
        .limit(limit)
    )
    stores = result.scalars().all()
    return stores


@router.get("/top-drops")
async def top_drops(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Son 24 saatte en çok düşen ürünler."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    # Son 24 saatteki fiyat kayıtlarından en büyük düşüşü bul
    subquery = (
        select(
            PriceHistory.product_store_id,
            func.min(PriceHistory.price).label("min_price"),
            func.max(PriceHistory.price).label("max_price"),
        )
        .where(PriceHistory.recorded_at >= since)
        .group_by(PriceHistory.product_store_id)
        .subquery()
    )

    result = await db.execute(
        select(ProductStore, subquery.c.min_price, subquery.c.max_price)
        .join(subquery, ProductStore.id == subquery.c.product_store_id)
        .where(subquery.c.max_price > subquery.c.min_price)
        .order_by(desc(subquery.c.max_price - subquery.c.min_price))
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "store": row[0],
            "price_24h_ago": row[2],
            "price_now": row[1],
            "drop_amount": row[2] - row[1],
            "drop_percent": round((row[2] - row[1]) / row[2] * 100, 1),
        }
        for row in rows
    ]


@router.get("/most-alarmed")
async def most_alarmed(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """En çok alarm kurulan ürünler."""
    result = await db.execute(
        select(Product)
        .order_by(desc(Product.alarm_count))
        .limit(limit)
    )
    return result.scalars().all()
