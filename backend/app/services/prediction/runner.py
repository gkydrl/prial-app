"""
Gunluk tahmin runner — tum urunler icin AL/BEKLE tahmini uretir.
Scheduler'dan cagrilir.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory
from app.models.prediction import PricePrediction
from app.services.prediction.analyzer import compute_features, PricePoint
from app.services.prediction.predictor import predict_and_save
from app.services.prediction.reasoning_generator import generate_reasoning_text


async def run_daily_predictions() -> dict:
    """
    Tum aktif urunler icin gunluk tahmin uret.
    Returns: {"total": N, "predicted": N, "skipped": N}
    """
    stats = {"total": 0, "predicted": 0, "skipped": 0, "errors": 0}

    async with AsyncSessionLocal() as db:
        # Store'u olan tüm ürünleri getir (current_price olmasına gerek yok,
        # fiyat geçmişinden alınabilir)
        result = await db.execute(
            select(Product)
            .options(selectinload(Product.category))
            .where(
                Product.id.in_(
                    select(ProductStore.product_id).distinct()
                )
            )
        )
        products = result.scalars().all()

        print(f"[prediction/runner] {len(products)} ürün için tahmin üretilecek", flush=True)

    # Her ürün için ayrı session — uzun transaction'ı önle
    for i, product in enumerate(products):
        stats["total"] += 1
        try:
            async with AsyncSessionLocal() as db:
                db_product = await db.get(Product, product.id, options=[selectinload(Product.category)])
                if not db_product:
                    stats["skipped"] += 1
                    continue
                predicted = await predict_for_product(db_product, db)
                if predicted:
                    stats["predicted"] += 1
                    await db.commit()
                else:
                    stats["skipped"] += 1
        except Exception as e:
            stats["errors"] += 1
            if stats["errors"] <= 10:  # İlk 10 hatayı logla
                print(f"[prediction/runner] Hata ({product.title[:40]}): {e}", flush=True)

        # Her 100 üründe progress logla
        if (i + 1) % 100 == 0:
            print(f"[prediction/runner] İlerleme: {i+1}/{len(products)} — {stats}", flush=True)

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

    # product_store_id'leri bul
    store_ids_result = await db.execute(
        select(ProductStore.id).where(ProductStore.product_id == product.id)
    )
    store_ids = [row[0] for row in store_ids_result.all()]

    if not store_ids:
        return None

    # Fiyat gecmisini getir (son 1 yil)
    one_year_ago = today - timedelta(days=365)

    history_result = await db.execute(
        select(PriceHistory.recorded_at, PriceHistory.price)
        .where(
            PriceHistory.product_store_id.in_(store_ids),
            PriceHistory.recorded_at >= one_year_ago,
            PriceHistory.price > 0,
        )
        .order_by(PriceHistory.recorded_at.asc())
    )
    history_rows = history_result.all()

    # Minimum 5 data point gerekli
    if len(history_rows) < 5:
        return None

    # Mevcut en dusuk fiyati bul (store'dan veya fiyat gecmisinin son kaydından)
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

    # Fallback: fiyat geçmişinin son kaydı
    if not current_price:
        current_price = history_rows[-1].price
    if not current_price:
        return None

    price_history = [
        PricePoint(date=row.recorded_at.date(), price=float(row.price))
        for row in history_rows
    ]

    # Kategori slug (ozel gun filtresi icin)
    cat_name = product.category.name if product.category else None

    # Feature hesapla
    features = compute_features(
        current_price=float(current_price),
        price_history=price_history,
        l1y_min=float(product.l1y_lowest_price) if product.l1y_lowest_price else None,
        l1y_max=float(product.l1y_highest_price) if product.l1y_highest_price else None,
        category_slug=cat_name,
    )

    # Tahmin uret ve kaydet
    prediction = await predict_and_save(
        product_id=product.id,
        current_price=float(current_price),
        features=features,
        db=db,
    )

    # İnsan-dostu açıklama üret
    try:
        reasoning_text = await generate_reasoning_text(
            product_title=product.title,
            recommendation=prediction.recommendation.value,
            confidence=float(prediction.confidence),
            current_price=float(current_price),
            reasoning=prediction.reasoning or {},
            l1y_lowest=float(product.l1y_lowest_price) if product.l1y_lowest_price else None,
            l1y_highest=float(product.l1y_highest_price) if product.l1y_highest_price else None,
            predicted_direction=prediction.predicted_direction.value,
        )
        prediction.reasoning_text = reasoning_text
    except Exception as e:
        print(f"[prediction/runner] Reasoning text hatası ({product.title[:40]}): {e}", flush=True)

    return prediction
