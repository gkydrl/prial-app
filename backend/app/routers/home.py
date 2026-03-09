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


def _price_before_subquery(since: datetime):
    """
    Her product_store için 'since' öncesindeki en son fiyatı döner.
    Bu referans fiyat, dönem başlamadan önceki son kayıttır.
    Day-over-day karşılaştırma için kullanılır (max/min yanılgısı yok).
    """
    rn_inner = (
        select(
            PriceHistory.product_store_id,
            PriceHistory.price,
            func.row_number().over(
                partition_by=PriceHistory.product_store_id,
                order_by=desc(PriceHistory.recorded_at),
            ).label("rn"),
        )
        .where(PriceHistory.recorded_at < since)
        .where(PriceHistory.price > 0)
        .subquery()
    )
    return (
        select(
            rn_inner.c.product_store_id,
            rn_inner.c.price.label("price_before"),
        )
        .where(rn_inner.c.rn == 1)
        .subquery()
    )


def _price_history_rows(db_result):
    """
    row[0] = ProductStore
    row[1] = price_before (dönem başlamadan önceki son fiyat — referans)

    Karşılaştırma: price_before → store.current_price (gerçek anlık DB değeri)
    """
    rows = []
    for row in db_result:
        store: ProductStore = row[0]
        price_before = float(row[1])
        current = float(store.current_price) if store.current_price else 0

        if price_before <= 0 or current <= 0 or current >= price_before:
            continue

        drop_pct = (price_before - current) / price_before * 100

        # Sanity check: %65+ düşüş → muhtemelen hatalı scrape
        if drop_pct > 65:
            continue

        # store='other' güvenilmez kaynak (alibaba, turkcell, vb.)
        if store.store.value == "other":
            continue

        product_id = str(store.product.id)
        entry = {
            "product": {
                "id": product_id,
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
                "original_price": price_before,
                "currency": store.currency,
                "discount_percent": store.discount_percent,
                "in_stock": store.in_stock,
                "last_checked_at": store.last_checked_at.isoformat() if store.last_checked_at else None,
            },
            "price_24h_ago": price_before,
            "price_now": current,
            "drop_amount": price_before - current,
            "drop_percent": round(drop_pct, 1),
        }
        rows.append(entry)

    # Aynı ürün birden fazla store ile çıkabilir — en düşük fiyatlı olanı tut
    seen: dict[str, dict] = {}
    for r in rows:
        pid = r["product"]["id"]
        if pid not in seen or r["price_now"] < seen[pid]["price_now"]:
            seen[pid] = r
    return list(seen.values())


def _discount_fallback_rows(stores: list[ProductStore]) -> list[dict]:
    """original_price > current_price olan mağazaları TopDropResponse formatında döndürür."""
    rows = []
    for s in stores:
        if not s.current_price or not s.original_price:
            continue
        cur = float(s.current_price)
        orig = float(s.original_price)
        if orig <= cur or cur <= 0:
            continue
        drop_pct = (orig - cur) / orig * 100
        # Sanity: %65+ düşüş → hatalı veri
        if drop_pct > 65:
            continue
        # store='other' güvenilmez kaynak
        if s.store.value == "other":
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
            "drop_percent": round(drop_pct, 1),
        })

    # Aynı ürün birden fazla store ile çıkabilir — en düşük fiyatlı olanı tut
    seen: dict[str, dict] = {}
    for r in rows:
        pid = r["product"]["id"]
        if pid not in seen or r["price_now"] < seen[pid]["price_now"]:
            seen[pid] = r
    return list(seen.values())


@router.get("/daily-deals")
async def daily_deals(
    limit: int = 20,
    period: str = Query(default="1d"),
    db: AsyncSession = Depends(get_db),
):
    """Fiyat düşen ürünler. 1d → 7d → indirimli ürünler kademeli fallback."""
    for fallback_period in [period, "7d"]:
        since = _since(fallback_period)
        before_subq = _price_before_subquery(since)
        result = await db.execute(
            select(ProductStore, before_subq.c.price_before)
            .join(before_subq, ProductStore.id == before_subq.c.product_store_id)
            .options(selectinload(ProductStore.product))
            .where(
                before_subq.c.price_before > ProductStore.current_price,
                ProductStore.in_stock == True,
                ProductStore.is_active == True,
                ProductStore.current_price > 0,
            )
            .order_by(desc(
                (before_subq.c.price_before - ProductStore.current_price) / before_subq.c.price_before
            ))
            .limit(limit)
        )
        rows = _price_history_rows(result.all())
        if len(rows) >= 3:
            return rows

    # Son çare: scraper'ın tespit ettiği anlık indirimler
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
    return _discount_fallback_rows(fb_result.scalars().all())


@router.get("/top-drops")
async def top_drops(
    limit: int = 20,
    period: str = Query(default="1d"),
    db: AsyncSession = Depends(get_db),
):
    """En çok ₺ düşen ürünler. 1d → 7d → indirimli ürünler kademeli fallback."""
    for fallback_period in [period, "7d"]:
        since = _since(fallback_period)
        before_subq = _price_before_subquery(since)
        result = await db.execute(
            select(ProductStore, before_subq.c.price_before)
            .join(before_subq, ProductStore.id == before_subq.c.product_store_id)
            .options(selectinload(ProductStore.product))
            .where(
                before_subq.c.price_before > ProductStore.current_price,
                ProductStore.in_stock == True,
                ProductStore.is_active == True,
                ProductStore.current_price > 0,
            )
            .order_by(desc(before_subq.c.price_before - ProductStore.current_price))
            .limit(limit)
        )
        rows = _price_history_rows(result.all())
        if len(rows) >= 3:
            return rows

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
    return _discount_fallback_rows(fb_result.scalars().all())


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
