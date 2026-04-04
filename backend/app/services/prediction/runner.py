"""
Gunluk tahmin runner — tum urunler icin AL/BEKLE tahmini uretir.
Scheduler'dan cagrilir.

V3: Concurrent execution (asyncio.Semaphore), timeout koruması,
    Railway restart'a dayanıklı batch commit.
"""
from __future__ import annotations

import asyncio
import re
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

# Concurrent Haiku çağrıları — API rate limit'e dikkat
CONCURRENCY = 15
# Tek ürün için max süre (Haiku timeout dahil)
PER_PRODUCT_TIMEOUT = 45


async def run_daily_predictions() -> dict:
    """
    Tum aktif urunler icin gunluk tahmin uret.
    Returns: {"total": N, "predicted": N, "skipped": N}
    """
    stats = {
        "total": 0, "predicted": 0, "skipped": 0,
        "errors": 0, "haiku_skipped": 0, "timeout": 0,
    }

    async with AsyncSessionLocal() as db:
        # Store'u olan tüm ürünleri getir
        result = await db.execute(
            select(Product.id)
            .where(
                Product.id.in_(
                    select(ProductStore.product_id).distinct()
                )
            )
        )
        product_ids = [row[0] for row in result.all()]

    total = len(product_ids)
    stats["total"] = total
    print(f"[prediction/runner] {total} ürün için tahmin üretilecek (concurrency={CONCURRENCY})", flush=True)

    semaphore = asyncio.Semaphore(CONCURRENCY)
    progress = {"done": 0}

    async def _process_one(product_id):
        async with semaphore:
            try:
                result = await asyncio.wait_for(
                    _predict_one(product_id, stats),
                    timeout=PER_PRODUCT_TIMEOUT,
                )
            except asyncio.TimeoutError:
                stats["timeout"] += 1
            except Exception as e:
                stats["errors"] += 1
                if stats["errors"] <= 10:
                    print(f"[prediction/runner] Hata: {e}", flush=True)
            finally:
                progress["done"] += 1
                done = progress["done"]
                if done % 200 == 0 or done == total:
                    print(
                        f"[prediction/runner] {done}/{total} — "
                        f"predicted={stats['predicted']} skip={stats['skipped']} "
                        f"err={stats['errors']} timeout={stats['timeout']} "
                        f"haiku_skip={stats['haiku_skipped']}",
                        flush=True,
                    )

    # Concurrent execution
    tasks = [_process_one(pid) for pid in product_ids]
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"[prediction/runner] Tamamlandı: {stats}", flush=True)
    return stats


async def _predict_one(product_id, stats: dict) -> None:
    """Tek ürün için tahmin — kendi session'ında."""
    try:
        async with AsyncSessionLocal() as db:
            product = await db.get(Product, product_id, options=[selectinload(Product.category)])
            if not product:
                stats["skipped"] += 1
                return
            result = await predict_for_product(product, db)
            if result is None:
                stats["skipped"] += 1
            else:
                predicted, haiku_skipped = result
                stats["predicted"] += 1
                if haiku_skipped:
                    stats["haiku_skipped"] += 1
                await db.commit()
    except Exception as e:
        stats["errors"] += 1
        if stats["errors"] <= 10:
            print(f"[prediction/runner] _predict_one hata ({product_id}): {type(e).__name__}: {e}", flush=True)


async def predict_for_product(
    product: Product, db: AsyncSession
) -> tuple[PricePrediction, bool] | None:
    """
    Tek bir urun icin tahmin uret.
    Returns: (PricePrediction, haiku_skipped) or None (yeterli veri yoksa)
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

    # Minimum 2 data point gerekli (en az 2 fiyat noktası → trend hesaplanabilir)
    if len(history_rows) < 2:
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
    category_id = product.category_id

    # Feature hesapla
    features = compute_features(
        current_price=float(current_price),
        price_history=price_history,
        l1y_min=float(product.l1y_lowest_price) if product.l1y_lowest_price else None,
        l1y_max=float(product.l1y_highest_price) if product.l1y_highest_price else None,
        category_slug=cat_name,
    )

    # Tahmin uret ve kaydet (category_id ile hiyerarşik katsayı)
    prediction = await predict_and_save(
        product_id=product.id,
        current_price=float(current_price),
        features=features,
        db=db,
        category_id=category_id,
    )

    # Haiku çağrısı optimizasyonu: fiyat değişmemişse eski reasoning_text'i kullan
    haiku_skipped = False
    wait_days = getattr(prediction, '_wait_days', None)
    expected_price = getattr(prediction, '_expected_price', None)

    prev_reasoning = await _get_recent_reasoning(product.id, float(current_price), db)
    if prev_reasoning:
        # Gün sayısını countdown olarak güncelle
        prediction.reasoning_text = _patch_wait_days(prev_reasoning, wait_days)
        haiku_skipped = True
    else:
        # Shipping & installment info for reasoning
        shipping_info = []
        installment_info = []
        stores_result = await db.execute(
            select(ProductStore).where(
                ProductStore.product_id == product.id,
                ProductStore.is_active == True,  # noqa: E712
            )
        )
        for st in stores_result.scalars().all():
            if st.delivery_text or st.estimated_delivery_days:
                shipping_info.append({
                    "store": st.store.value.capitalize(),
                    "days": st.estimated_delivery_days,
                    "text": st.delivery_text,
                })
            if st.installment_text:
                installment_info.append({
                    "store": st.store.value.capitalize(),
                    "text": st.installment_text,
                })

        event_details = features.event_details

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
                review_summary=product.review_summary,
                shipping_info=shipping_info if shipping_info else None,
                installment_info=installment_info if installment_info else None,
                daily_lowest_price=float(product.daily_lowest_price) if product.daily_lowest_price else None,
                daily_lowest_store=product.daily_lowest_store,
                wait_days=wait_days,
                expected_price=expected_price,
                event_details=event_details,
            )
            prediction.reasoning_text = reasoning_text
        except Exception as e:
            print(f"[prediction/runner] Reasoning text hatası ({product.title[:40]}): {e}", flush=True)

    return prediction, haiku_skipped


async def _get_recent_reasoning(
    product_id, current_price: float, db: AsyncSession
) -> str | None:
    """
    Son 7 gün içinde reasoning_text varsa ve fiyat <%0.1 değişmişse eski text'i döner.
    Aksi halde None → yeni Haiku çağrısı gerekli.
    """
    seven_days_ago = date.today() - timedelta(days=7)

    result = await db.execute(
        select(PricePrediction.reasoning_text, PricePrediction.current_price)
        .where(
            PricePrediction.product_id == product_id,
            PricePrediction.prediction_date >= seven_days_ago,
            PricePrediction.reasoning_text.isnot(None),
        )
        .order_by(PricePrediction.prediction_date.desc())
        .limit(1)
    )
    row = result.first()
    if not row or not row.reasoning_text:
        return None

    prev_price = float(row.current_price)
    if prev_price <= 0:
        return None

    price_change_pct = abs(current_price - prev_price) / prev_price * 100
    if price_change_pct < 0.1:
        return row.reasoning_text

    return None


def _patch_wait_days(text: str, new_wait_days: int | None) -> str:
    """
    Reuse edilen reasoning_text'teki gün sayısını güncel countdown ile değiştir.
    Örnek: "7 gün beklemenizi" → "6 gün beklemenizi"
            "7 gün içinde"     → "6 gün içinde"
            "7 gün kaldı"      → "6 gün kaldı"
    """
    if new_wait_days is None or not text:
        return text

    # "X gün" kalıplarını bul ve güncelle
    # Yaygın kalıplar: "7 gün bekle", "7 gün içinde", "7 gün kaldı", "7 gün sonra"
    patched = re.sub(
        r'\b(\d{1,3})\s+gün\b',
        lambda m: f"{new_wait_days} gün",
        text,
    )
    return patched
