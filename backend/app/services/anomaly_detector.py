"""
Fiyat anomali tespiti.
Büyük fiyat değişimlerini tespit eder, gerçek indirim mi scrape hatası mı ayırır.
Gerçek büyük indirimde anlık bildirim gönderir (06:00'ı bekleme).

price_tracker.py'den check_product_price() içinde çağrılır.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductStore


# %30+ düşüş = anomali — incelenmeli
ANOMALY_DROP_THRESHOLD = 30

# %50+ düşüş ve tek mağaza = muhtemel scrape hatası
SUSPECT_DROP_THRESHOLD = 50


async def check_price_anomaly(
    db: AsyncSession,
    store: ProductStore,
    old_price: Decimal,
    new_price: Decimal,
) -> dict | None:
    """
    Fiyat değişiminde anomali kontrolü.
    Returns: anomaly dict veya None (normal değişim)

    Karar mantığı:
    - %30 altı düşüş → normal, None döner
    - %30-50 düşüş → "real_drop" (büyük indirim), bildirim tetikler
    - %50+ düşüş → diğer mağazaları kontrol et:
      - 2+ mağazada benzer düşüş → "confirmed_drop"
      - Tek mağazada → "suspect_error" (muhtemel scrape hatası)
    """
    if not old_price or old_price <= 0 or not new_price or new_price <= 0:
        return None

    if new_price >= old_price:
        return None  # Fiyat artışı — anomali değil

    drop_pct = float((old_price - new_price) / old_price * 100)

    if drop_pct < ANOMALY_DROP_THRESHOLD:
        return None  # Normal düşüş

    product = await db.get(Product, store.product_id)
    product_title = product.title[:80] if product else "?"

    # %50+ düşüş — çapraz doğrulama yap
    if drop_pct >= SUSPECT_DROP_THRESHOLD:
        # Aynı ürünün diğer mağazalarını kontrol et
        other_stores_result = await db.execute(
            select(ProductStore).where(
                ProductStore.product_id == store.product_id,
                ProductStore.id != store.id,
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.current_price.isnot(None),
                ProductStore.current_price > 0,
            )
        )
        other_stores = other_stores_result.scalars().all()

        # Diğer mağazalarda da yakın fiyat var mı?
        confirmed = False
        for other in other_stores:
            # Yeni fiyatla %20 içinde bir mağaza varsa gerçek
            if other.current_price and abs(float(other.current_price - new_price) / float(new_price)) < 0.20:
                confirmed = True
                break

        if not confirmed and other_stores:
            # Diğer mağazalar çok farklı fiyatta → muhtemel hata
            anomaly = {
                "type": "suspect_error",
                "product_title": product_title,
                "store": store.store.value,
                "old_price": float(old_price),
                "new_price": float(new_price),
                "drop_pct": round(drop_pct, 1),
                "other_store_prices": [
                    {"store": s.store.value, "price": float(s.current_price)}
                    for s in other_stores[:5]
                ],
            }
            print(
                f"[anomaly] ⚠️ ŞÜPHELI: {product_title} | {store.store.value} "
                f"| {old_price} → {new_price} (-%{drop_pct:.0f}%) "
                f"| Diğer mağazalar: {[float(s.current_price) for s in other_stores[:3]]}",
                flush=True,
            )
            return anomaly

    # Gerçek büyük indirim
    anomaly = {
        "type": "confirmed_drop" if drop_pct >= SUSPECT_DROP_THRESHOLD else "real_drop",
        "product_title": product_title,
        "store": store.store.value,
        "old_price": float(old_price),
        "new_price": float(new_price),
        "drop_pct": round(drop_pct, 1),
    }
    print(
        f"[anomaly] 🔥 BÜYÜK İNDİRİM: {product_title} | {store.store.value} "
        f"| {old_price} → {new_price} (-%{drop_pct:.0f}%)",
        flush=True,
    )
    return anomaly


async def should_skip_price_update(anomaly: dict | None) -> bool:
    """
    Suspect error durumunda fiyat güncellenmesini engeller.
    Gerçek indirimlerde güncelleme devam eder.
    """
    if anomaly and anomaly["type"] == "suspect_error":
        return True
    return False
