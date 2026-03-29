"""
Gunluk tahmin runner — tum urunler icin AL/BEKLE tahmini uretir.
Scheduler'dan cagrilir.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory
from app.models.prediction import PricePrediction
from app.services.prediction.analyzer import compute_features, PricePoint
from app.services.prediction.predictor import predict_and_save


async def run_daily_predictions() -> dict:
    """
    Tum aktif urunler icin gunluk tahmin uret.
    Returns: {"total": N, "predicted": N, "skipped": N}
    """
    stats = {"total": 0, "predicted": 0, "skipped": 0, "errors": 0}

    async with AsyncSessionLocal() as db:
        # Aktif fiyati olan urunleri getir
        result = await db.execute(
            select(Product)
            .where(
                Product.id.in_(
                    select(ProductStore.product_id)
                    .where(
                        ProductStore.is_active == True,  # noqa: E712
                        ProductStore.current_price.isnot(None),
                    )
                    .distinct()
                )
            )
        )
        products = result.scalars().all()

        print(f"[prediction/runner] {len(products)} ürün için tahmin üretilecek", flush=True)

        for product in products:
            stats["total"] += 1
            try:
                predicted = await predict_for_product(product, db)
                if predicted:
                    stats["predicted"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"[prediction/runner] Hata ({product.title[:40]}): {e}", flush=True)

        await db.commit()

    print(f"[prediction/runner] Tamamlandı: {stats}", flush=True)
    return stats


async def predict_for_product(product: Product, db: AsyncSession) -> PricePrediction | None:
    """
    Tek bir urun icin tahmin uret.
    Returns: PricePrediction or None (yeterli veri yoksa)
    """
    today = date.today()

    # Bugun zaten tahmin var mi?
    existing = await db.execute(
        select(PricePrediction.id).where(
            PricePrediction.product_id == product.id,
            PricePrediction.prediction_date == today,
        )
    )
    if existing.scalar_one_or_none():
        return None

    # Mevcut en dusuk fiyati bul
    price_result = await db.execute(
        select(func.min(ProductStore.current_price))
        .where(
            ProductStore.product_id == product.id,
            ProductStore.is_active == True,  # noqa: E712
            ProductStore.in_stock == True,   # noqa: E712
            ProductStore.current_price.isnot(None),
        )
    )
    current_price = price_result.scalar_one_or_none()
    if not current_price:
        return None

    # Fiyat gecmisini getir (son 1 yil)
    one_year_ago = today - timedelta(days=365)

    # product_store_id'leri bul
    store_ids_result = await db.execute(
        select(ProductStore.id).where(ProductStore.product_id == product.id)
    )
    store_ids = [row[0] for row in store_ids_result.all()]

    if not store_ids:
        return None

    history_result = await db.execute(
        select(PriceHistory.recorded_at, PriceHistory.price)
        .where(
            PriceHistory.product_store_id.in_(store_ids),
            PriceHistory.recorded_at >= one_year_ago,
        )
        .order_by(PriceHistory.recorded_at.asc())
    )
    history_rows = history_result.all()

    # Minimum 5 data point gerekli
    if len(history_rows) < 5:
        return None

    price_history = [
        PricePoint(date=row.recorded_at.date(), price=float(row.price))
        for row in history_rows
    ]

    # Feature hesapla
    features = compute_features(
        current_price=float(current_price),
        price_history=price_history,
        l1y_min=float(product.l1y_lowest_price) if product.l1y_lowest_price else None,
        l1y_max=float(product.l1y_highest_price) if product.l1y_highest_price else None,
    )

    # Tahmin uret ve kaydet
    prediction = await predict_and_save(
        product_id=product.id,
        current_price=float(current_price),
        features=features,
        db=db,
    )

    return prediction
