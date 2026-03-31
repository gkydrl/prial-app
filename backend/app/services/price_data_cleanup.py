"""
Fiyat verisi temizliği — outlier price_history kayıtlarını sil,
l1y_lowest / l1y_highest değerlerini yeniden hesapla.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory


async def run_price_cleanup() -> dict:
    """
    Tüm ürünler için:
    1. Negatif / sıfır fiyatları sil
    2. Outlier fiyatları sil (medyandan %90+ sapma)
    3. l1y değerlerini temiz veriden yeniden hesapla
    """
    stats = {
        "products_processed": 0,
        "negative_deleted": 0,
        "outliers_deleted": 0,
        "l1y_recalculated": 0,
        "l1y_cleared": 0,
    }

    try:
        # Phase 1: Negatif ve sıfır fiyatları global sil
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(PriceHistory).where(PriceHistory.price <= 0).returning(PriceHistory.id)
            )
            negative_rows = result.all()
            stats["negative_deleted"] = len(negative_rows)
            await db.commit()
            print(f"[cleanup] {stats['negative_deleted']} negatif/sıfır kayıt silindi", flush=True)

        # Phase 2: Ürün bazında outlier temizliği + l1y recalculation
        async with AsyncSessionLocal() as db:
            products = (await db.execute(select(Product))).scalars().all()

        for product in products:
            async with AsyncSessionLocal() as db:
                db_product = await db.get(Product, product.id)
                if not db_product:
                    continue

                outliers_removed = await _clean_product_outliers(db_product, db)
                stats["outliers_deleted"] += outliers_removed

                recalculated = await _recalculate_l1y(db_product, db)
                if recalculated == "recalculated":
                    stats["l1y_recalculated"] += 1
                elif recalculated == "cleared":
                    stats["l1y_cleared"] += 1

                await db.commit()
                stats["products_processed"] += 1

        print(f"[cleanup] Tamamlandı: {stats}", flush=True)

    except Exception as e:
        print(f"[cleanup] HATA: {e}", flush=True)
        import traceback
        traceback.print_exc()

    return stats


async def _clean_product_outliers(product: Product, db: AsyncSession) -> int:
    """
    Ürünün price_history'sindeki outlier'ları sil.
    Medyandan %90+ sapan değerler outlier kabul edilir.
    """
    # Ürünün tüm store'larını bul
    stores_result = await db.execute(
        select(ProductStore.id).where(ProductStore.product_id == product.id)
    )
    store_ids = [row[0] for row in stores_result.all()]
    if not store_ids:
        return 0

    # Tüm fiyatları çek
    prices_result = await db.execute(
        select(PriceHistory.id, PriceHistory.price)
        .where(PriceHistory.product_store_id.in_(store_ids))
        .where(PriceHistory.price > 0)
    )
    rows = prices_result.all()
    if len(rows) < 5:
        return 0  # Yeterli veri yok, outlier tespiti yapma

    prices = sorted([float(r[1]) for r in rows])
    median = prices[len(prices) // 2]

    if median <= 0:
        return 0

    # Outlier sınırları: medyanın %10'undan az veya 3 katından fazla
    lower_bound = median * 0.1
    upper_bound = median * 3.0

    # Outlier ID'leri bul
    outlier_ids = [
        r[0] for r in rows
        if float(r[1]) < lower_bound or float(r[1]) > upper_bound
    ]

    if not outlier_ids:
        return 0

    # Sil
    await db.execute(
        delete(PriceHistory).where(PriceHistory.id.in_(outlier_ids))
    )

    product_label = f"{product.brand or ''} {product.title[:40]}".strip()
    print(
        f"[cleanup] {product_label}: {len(outlier_ids)} outlier silindi "
        f"(median={median:,.0f}, bounds={lower_bound:,.0f}-{upper_bound:,.0f})",
        flush=True,
    )
    return len(outlier_ids)


async def _recalculate_l1y(product: Product, db: AsyncSession) -> str:
    """
    Ürünün l1y_lowest ve l1y_highest değerlerini
    temizlenmiş price_history'den yeniden hesapla.
    """
    # Ürünün store'larını bul
    stores_result = await db.execute(
        select(ProductStore.id).where(ProductStore.product_id == product.id)
    )
    store_ids = [row[0] for row in stores_result.all()]
    if not store_ids:
        product.l1y_lowest_price = None
        product.l1y_highest_price = None
        return "cleared"

    # Son 1 yılın fiyatlarını çek
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)

    result = await db.execute(
        select(
            func.min(PriceHistory.price),
            func.max(PriceHistory.price),
        )
        .where(
            PriceHistory.product_store_id.in_(store_ids),
            PriceHistory.price > 0,
            PriceHistory.recorded_at >= one_year_ago,
        )
    )
    row = result.one()
    min_price, max_price = row[0], row[1]

    if min_price is None or max_price is None:
        # Son 1 yılda veri yok, tüm zamanları dene
        result2 = await db.execute(
            select(
                func.min(PriceHistory.price),
                func.max(PriceHistory.price),
            )
            .where(
                PriceHistory.product_store_id.in_(store_ids),
                PriceHistory.price > 0,
            )
        )
        row2 = result2.one()
        min_price, max_price = row2[0], row2[1]

    if min_price is None:
        product.l1y_lowest_price = None
        product.l1y_highest_price = None
        return "cleared"

    # Mevcut fiyatla sanity check
    current_price = await _get_current_price(product, db)
    if current_price and min_price < current_price * Decimal("0.1"):
        # Hâlâ outlier var, mevcut fiyatın %30'unu minimum olarak kullan
        min_price = max(min_price, current_price * Decimal("0.3"))

    product.l1y_lowest_price = min_price
    product.l1y_highest_price = max_price
    return "recalculated"


async def _get_current_price(product: Product, db: AsyncSession) -> Decimal | None:
    """Ürünün en düşük aktif fiyatını döner."""
    result = await db.execute(
        select(func.min(ProductStore.current_price))
        .where(
            ProductStore.product_id == product.id,
            ProductStore.is_active == True,  # noqa: E712
            ProductStore.in_stock == True,    # noqa: E712
        )
    )
    return result.scalar_one_or_none()
