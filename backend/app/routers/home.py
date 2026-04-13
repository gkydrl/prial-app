from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, case, cast, Integer, literal
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory
from app.models.alarm import Alarm, AlarmStatus
from app.models.user import User
from app.models.prediction import PricePrediction, Recommendation
from app.schemas.product import ProductResponse, ProductStoreResponse
from app.services.prediction.batch_loader import attach_predictions

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


def _review_count_expr():
    """Total review count from review_summary JSONB (sum of all stores' count)."""
    return func.coalesce(
        cast(Product.review_summary["trendyol"]["count"].astext, Integer), literal(0)
    ) + func.coalesce(
        cast(Product.review_summary["hepsiburada"]["count"].astext, Integer), literal(0)
    )


def _price_before_subquery(since: datetime):
    """
    Her ürün için 'since' öncesindeki en son kaydedilen fiyatı döner.
    Mağaza farkı gözetmez — her mağazanın son fiyatından en düşüğünü alır.
    Lookback penceresi en az 7 gün: kısa kesintilere dayanıklı.
    """
    period_len = datetime.now(timezone.utc) - since
    lookback_hours = max(period_len.total_seconds() / 3600 * 3, 24 * 7)
    lookback = since - timedelta(hours=lookback_hours)

    # Her product_store için since öncesindeki en son kayıt zamanı
    latest_per_store = (
        select(
            PriceHistory.product_store_id,
            func.max(PriceHistory.recorded_at).label("latest_at"),
        )
        .where(PriceHistory.recorded_at < since)
        .where(PriceHistory.recorded_at >= lookback)
        .where(PriceHistory.price > 0)
        .group_by(PriceHistory.product_store_id)
        .subquery()
    )

    # O zamandaki fiyatı al ve ürün bazında en düşüğünü bul
    return (
        select(
            ProductStore.product_id,
            func.min(PriceHistory.price).label("price_before"),
        )
        .join(ProductStore, PriceHistory.product_store_id == ProductStore.id)
        .join(
            latest_per_store,
            (PriceHistory.product_store_id == latest_per_store.c.product_store_id)
            & (PriceHistory.recorded_at == latest_per_store.c.latest_at),
        )
        .where(PriceHistory.price > 0)
        .where(ProductStore.is_active == True)
        .group_by(ProductStore.product_id)
        .subquery()
    )


def _price_history_rows(db_result):
    """
    row[0] = Product
    row[1] = price_before (dönem öncesindeki tüm mağazalardaki min fiyat)
    row[2] = price_now (şu anki tüm mağazalardaki min fiyat)
    row[3] = best_store (en düşük fiyatlı store — link için)
    """
    rows = []
    for row in db_result:
        product: Product = row[0]
        price_before = float(row[1])
        price_now = float(row[2])
        best_store: ProductStore = row[3]

        if price_before <= 0 or price_now <= 0 or price_now >= price_before:
            continue

        drop_pct = (price_before - price_now) / price_before * 100

        # Sanity check: %50+ düşüş → muhtemelen hatalı scrape
        if drop_pct > 50:
            continue

        product_id = str(product.id)
        entry = {
            "product": {
                "id": product_id,
                "title": product.title,
                "brand": product.brand,
                "description": None,
                "image_url": product.image_url,
                "lowest_price_ever": float(product.lowest_price_ever) if product.lowest_price_ever else None,
                "alarm_count": product.alarm_count,
                "stores": [],
                "created_at": product.created_at.isoformat(),
            },
            "store": {
                "id": str(best_store.id),
                "store": best_store.store.value,
                "url": best_store.url,
                "current_price": price_now,
                "original_price": price_before,
                "currency": best_store.currency,
                "discount_percent": best_store.discount_percent,
                "in_stock": best_store.in_stock,
                "last_checked_at": best_store.last_checked_at.isoformat() if best_store.last_checked_at else None,
            },
            "price_24h_ago": price_before,
            "price_now": price_now,
            "drop_amount": price_before - price_now,
            "drop_percent": round(drop_pct, 1),
        }
        rows.append(entry)

    return rows


def _current_min_subquery():
    """Her ürün için tüm aktif mağazalardaki şu anki en düşük fiyatı döner."""
    return (
        select(
            ProductStore.product_id,
            func.min(ProductStore.current_price).label("price_now"),
        )
        .where(
            ProductStore.in_stock == True,
            ProductStore.is_active == True,
            ProductStore.current_price > 0,
        )
        .group_by(ProductStore.product_id)
        .subquery()
    )


def _discount_fallback_rows(stores: list[ProductStore]) -> list[dict]:
    """original_price > current_price olan mağazaları TopDropResponse formatında döndürür.
    Bu veriler gerçek fiyat geçmişi değil, mağazanın kendi indirim bilgisi.
    Bu yüzden daha sıkı filtreleme uygulanır.
    """
    rows = []
    for s in stores:
        if not s.current_price or not s.original_price:
            continue
        cur = float(s.current_price)
        orig = float(s.original_price)
        if orig <= cur or cur <= 0:
            continue
        drop_pct = (orig - cur) / orig * 100
        # Mağaza indirimlerinde %35+ → güvenilmez veya kalıcı kampanya
        if drop_pct > 35:
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


async def _product_drop_query(db, since, order_by, limit):
    """
    Ürün bazlı fiyat düşüşü sorgusu.
    price_before = dönem öncesinde tüm mağazalardaki min fiyat
    price_now = şu anki tüm mağazalardaki min fiyat
    """
    from sqlalchemy.orm import aliased

    before_subq = _price_before_subquery(since)
    now_subq = _current_min_subquery()

    # En düşük fiyatlı store'u bulmak için (link göstermek amaçlı)
    best_store_subq = (
        select(
            ProductStore.product_id,
            func.min(ProductStore.id).label("best_store_id"),
        )
        .where(
            ProductStore.in_stock == True,
            ProductStore.is_active == True,
            ProductStore.current_price > 0,
        )
        # current_price = min fiyat olan store'u bul
        .group_by(ProductStore.product_id)
        .subquery()
    )

    BestStore = aliased(ProductStore)

    result = await db.execute(
        select(Product, before_subq.c.price_before, now_subq.c.price_now, BestStore)
        .join(before_subq, Product.id == before_subq.c.product_id)
        .join(now_subq, Product.id == now_subq.c.product_id)
        .join(BestStore, (BestStore.product_id == Product.id) & (BestStore.current_price == now_subq.c.price_now) & (BestStore.in_stock == True) & (BestStore.is_active == True))
        .where(
            before_subq.c.price_before > now_subq.c.price_now,
            before_subq.c.price_before > 0,  # division by zero koruması
        )
        .order_by(order_by(before_subq, now_subq))
        .limit(limit * 2)  # duplicate olabilir, fazla çek
    )

    # Aynı ürün birden fazla store ile gelebilir — ilkini tut
    seen = set()
    unique_rows = []
    for row in result.all():
        pid = row[0].id
        if pid in seen:
            continue
        seen.add(pid)
        unique_rows.append(row)
        if len(unique_rows) >= limit:
            break

    return _price_history_rows(unique_rows)


@router.get("/daily-deals")
async def daily_deals(
    limit: int = 20,
    period: str = Query(default="1d"),
    db: AsyncSession = Depends(get_db),
):
    """Fiyat düşen ürünler. 1d → 7d → indirimli ürünler kademeli fallback."""
    try:
        for fallback_period in [period, "7d"]:
            since = _since(fallback_period)
            rows = await _product_drop_query(
                db, since,
                order_by=lambda b, n: desc((b.c.price_before - n.c.price_now) / b.c.price_before),
                limit=limit,
            )
            if len(rows) >= 3:
                return rows
    except Exception as e:
        print(f"[home/daily-deals] price_drop_query hatası: {e}", flush=True)

    # Son çare: scraper'ın tespit ettiği anlık indirimler
    fb_result = await db.execute(
        select(ProductStore)
        .options(selectinload(ProductStore.product))
        .where(
            ProductStore.is_active == True,
            ProductStore.in_stock == True,
            ProductStore.original_price > ProductStore.current_price,
            ProductStore.current_price > 0,
            ProductStore.original_price > 0,
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
        rows = await _product_drop_query(
            db, since,
            order_by=lambda b, n: desc(b.c.price_before - n.c.price_now),
            limit=limit,
        )
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
    products = result.scalars().all()
    await attach_predictions(products, db)
    return products


def _recent_review_filter():
    """Son 7 günde review_summary güncellenen ürünleri filtreler."""
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    return Product.review_summary["updated_at"].astext >= seven_days_ago


@router.get("/ai-picks", response_model=list[ProductResponse])
async def ai_picks(
    limit: int = Query(default=10, le=30),
    db: AsyncSession = Depends(get_db),
):
    """IYI_FIYAT tavsiyeleri — son 1 haftada review datası yakalanan ürünler, review sayısına göre sıralı."""
    from datetime import date as date_cls, timedelta as td

    today = date_cls.today()
    week_ago = today - td(days=7)

    total_reviews = _review_count_expr()
    products = []

    # 1) Son 1 haftada review datası olan + bugünkü/haftalık prediction
    for since_date in [today, week_ago]:
        result = await db.execute(
            select(Product)
            .join(
                PricePrediction,
                (PricePrediction.product_id == Product.id)
                & (PricePrediction.prediction_date >= since_date)
                & (PricePrediction.recommendation == Recommendation.IYI_FIYAT),
            )
            .options(
                selectinload(Product.stores),
                selectinload(Product.variants),
            )
            .where(Product.review_summary.isnot(None))
            .where(_recent_review_filter())
            .order_by(desc(total_reviews), desc(PricePrediction.confidence))
            .limit(limit)
        )
        products = result.scalars().all()
        if len(products) >= limit:
            break

    # 2) Yeterli değilse review filtresi olmadan doldur
    if len(products) < limit:
        seen_ids = {p.id for p in products}
        result = await db.execute(
            select(Product)
            .join(
                PricePrediction,
                (PricePrediction.product_id == Product.id)
                & (PricePrediction.prediction_date >= week_ago)
                & (PricePrediction.recommendation == Recommendation.IYI_FIYAT),
            )
            .options(
                selectinload(Product.stores),
                selectinload(Product.variants),
            )
            .order_by(desc(total_reviews), desc(PricePrediction.confidence))
            .limit(limit)
        )
        for p in result.scalars().all():
            if p.id not in seen_ids:
                products.append(p)
                seen_ids.add(p.id)
                if len(products) >= limit:
                    break

    await attach_predictions(products, db)
    return products


@router.get("/ai-wait-picks", response_model=list[ProductResponse])
async def ai_wait_picks(
    limit: int = Query(default=10, le=30),
    db: AsyncSession = Depends(get_db),
):
    """FIYAT_DUSEBILIR/FIYAT_YUKSELISTE tavsiyeleri — son 1 haftada review datası yakalanan ürünler, review sayısına göre sıralı."""
    from datetime import date as date_cls, timedelta as td

    today = date_cls.today()
    week_ago = today - td(days=7)

    total_reviews = _review_count_expr()
    recs = [Recommendation.FIYAT_DUSEBILIR, Recommendation.FIYAT_YUKSELISTE]
    products = []

    # 1) Son 1 haftada review datası olan + bugünkü/haftalık prediction
    for since_date in [today, week_ago]:
        result = await db.execute(
            select(Product)
            .join(
                PricePrediction,
                (PricePrediction.product_id == Product.id)
                & (PricePrediction.prediction_date >= since_date)
                & (PricePrediction.recommendation.in_(recs)),
            )
            .options(
                selectinload(Product.stores),
                selectinload(Product.variants),
            )
            .where(Product.review_summary.isnot(None))
            .where(_recent_review_filter())
            .order_by(desc(total_reviews), desc(PricePrediction.confidence))
            .limit(limit)
        )
        products = result.scalars().all()
        if len(products) >= limit:
            break

    # 2) Yeterli değilse review filtresi olmadan doldur
    if len(products) < limit:
        seen_ids = {p.id for p in products}
        result = await db.execute(
            select(Product)
            .join(
                PricePrediction,
                (PricePrediction.product_id == Product.id)
                & (PricePrediction.prediction_date >= week_ago)
                & (PricePrediction.recommendation.in_(recs)),
            )
            .options(
                selectinload(Product.stores),
                selectinload(Product.variants),
            )
            .order_by(desc(total_reviews), desc(PricePrediction.confidence))
            .limit(limit)
        )
        for p in result.scalars().all():
            if p.id not in seen_ids:
                products.append(p)
                seen_ids.add(p.id)
                if len(products) >= limit:
                    break

    await attach_predictions(products, db)
    return products


@router.get("/stats")
async def home_stats(db: AsyncSession = Depends(get_db)):
    """Ana sayfa istatistikleri: kullanıcı, aktif talep, gerçekleşen."""
    user_count = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_alarms = await db.execute(
        select(func.coalesce(func.sum(Product.alarm_count), 0))
    )
    triggered_count = await db.execute(
        select(func.count(Alarm.id)).where(Alarm.status == AlarmStatus.TRIGGERED)
    )
    # TODO: Gerçek kullanıcı sayısı yeterli olunca kaldır
    _USER_OFFSET = 1_847
    _TRIGGERED_OFFSET = 612

    return {
        "user_count": (user_count.scalar() or 0) + _USER_OFFSET,
        "active_alarm_count": int(active_alarms.scalar() or 0),
        "triggered_count": (triggered_count.scalar() or 0) + _TRIGGERED_OFFSET,
    }
