"""
Tek seferlik fiyat outlier temizlik scripti.
Her product_store_id grubu için IQR hesaplar, outlier kayıtları siler,
lowest_price_ever ve l1y istatistiklerini yeniden hesaplar.

Kullanım:
    python -m scripts.cleanup_price_outliers --dry-run   # Sadece raporla
    python -m scripts.cleanup_price_outliers              # Gerçek silme
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory


async def run_cleanup(dry_run: bool = True):
    """Ana temizlik fonksiyonu."""
    print(f"{'[DRY-RUN] ' if dry_run else ''}Fiyat outlier temizliği başlatılıyor...")

    total_deleted = 0
    total_groups = 0
    groups_with_outliers = 0

    async with AsyncSessionLocal() as db:
        # Tüm product_store_id'leri al
        store_ids_result = await db.execute(
            select(func.distinct(PriceHistory.product_store_id))
        )
        store_ids = [row[0] for row in store_ids_result.all()]
        total_groups = len(store_ids)
        print(f"Toplam {total_groups} product_store grubu incelenecek")

        for idx, ps_id in enumerate(store_ids):
            # Bu store'un tüm fiyat kayıtlarını çek
            records_result = await db.execute(
                select(PriceHistory.id, PriceHistory.price)
                .where(
                    PriceHistory.product_store_id == ps_id,
                    PriceHistory.price > 0,
                )
                .order_by(PriceHistory.recorded_at)
            )
            records = records_result.all()

            if len(records) < 4:
                continue

            prices = sorted([float(r[1]) for r in records])
            q1 = prices[len(prices) // 4]
            q3 = prices[3 * len(prices) // 4]
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            outlier_ids = [r[0] for r in records if not (lower <= float(r[1]) <= upper)]

            if not outlier_ids:
                continue

            groups_with_outliers += 1
            total_deleted += len(outlier_ids)

            if len(outlier_ids) <= 5:
                outlier_prices = [float(r[1]) for r in records if r[0] in set(outlier_ids)]
                print(f"  [{str(ps_id)[:8]}] {len(outlier_ids)} outlier (range: {lower:.0f}-{upper:.0f}) fiyatlar: {outlier_prices}")

            if not dry_run:
                await db.execute(
                    delete(PriceHistory).where(PriceHistory.id.in_(outlier_ids))
                )

            if (idx + 1) % 500 == 0:
                if not dry_run:
                    await db.commit()
                print(f"  İlerleme: {idx + 1}/{total_groups} — {total_deleted} outlier bulundu")

        if not dry_run:
            await db.commit()

        print(f"\n{'[DRY-RUN] ' if dry_run else ''}Outlier temizliği tamamlandı:")
        print(f"  Toplam grup: {total_groups}")
        print(f"  Outlier içeren grup: {groups_with_outliers}")
        print(f"  {'Silinecek' if dry_run else 'Silinen'} kayıt: {total_deleted}")

        # l1y istatistiklerini yeniden hesapla
        if not dry_run:
            print("\nl1y istatistikleri yeniden hesaplanıyor...")
            await _recalculate_stats(db)


async def _recalculate_stats(db: AsyncSession):
    """Her ürünün lowest_price_ever ve l1y istatistiklerini yeniden hesapla."""
    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)

    products_result = await db.execute(select(Product.id))
    product_ids = [row[0] for row in products_result.all()]

    updated = 0
    for pid in product_ids:
        # Bu ürünün tüm store'larından fiyat geçmişi
        store_ids_result = await db.execute(
            select(ProductStore.id).where(ProductStore.product_id == pid)
        )
        ps_ids = [row[0] for row in store_ids_result.all()]

        if not ps_ids:
            continue

        # l1y fiyatları
        l1y_result = await db.execute(
            select(PriceHistory.price)
            .where(
                PriceHistory.product_store_id.in_(ps_ids),
                PriceHistory.recorded_at >= one_year_ago,
                PriceHistory.price > 0,
            )
        )
        l1y_prices = sorted([float(row[0]) for row in l1y_result.all()])

        product = await db.get(Product, pid)
        if not product:
            continue

        if l1y_prices:
            # IQR filtreli
            if len(l1y_prices) >= 4:
                q1 = l1y_prices[len(l1y_prices) // 4]
                q3 = l1y_prices[3 * len(l1y_prices) // 4]
                iqr = q3 - q1
                clean = [p for p in l1y_prices if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr]
                if not clean:
                    clean = l1y_prices
            else:
                clean = l1y_prices

            product.l1y_lowest_price = Decimal(str(min(clean)))
            product.l1y_highest_price = Decimal(str(max(clean)))
            updated += 1

    await db.commit()
    print(f"  {updated} ürünün l1y istatistikleri güncellendi")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fiyat outlier temizliği")
    parser.add_argument("--dry-run", action="store_true", help="Sadece raporla, silme")
    args = parser.parse_args()

    asyncio.run(run_cleanup(dry_run=args.dry_run))
