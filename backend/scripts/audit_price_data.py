"""
Fiyat verisi denetim scripti.
Supabase DB'ye bağlanıp son 6 aylık price_history verisini analiz eder.

Kullanım:
    python -m scripts.audit_price_data

Kontroller:
1. Spike'lar: Ardışık kayıtlar arasında %200+ fiyat artışı
2. Düşüşler: Ardışık kayıtlar arasında %80+ ani düşüş
3. Sabit fiyatlar: 30+ gün boyunca aynı fiyat
4. Sahte fiyatlar: 11111, 22222, 99999 gibi placeholder değerler
5. Veri boşlukları: 14+ gündür yeni kayıt olmayan aktif store'lar
6. Fiyat tutarsızlığı: Aynı ürünün mağazaları arasında 5x+ fark
7. Genel istatistikler
"""
from __future__ import annotations

import asyncio
import sys
import os

# Proje kökünü path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import Product, ProductStore
from app.models.price_history import PriceHistory


# Placeholder fiyat kalıpları
_PLACEHOLDER_PRICES = {
    Decimal("11111"), Decimal("22222"), Decimal("33333"), Decimal("44444"),
    Decimal("55555"), Decimal("66666"), Decimal("77777"), Decimal("88888"),
    Decimal("99999"), Decimal("11111.11"), Decimal("99999.99"),
    Decimal("0.01"), Decimal("0.1"), Decimal("1"),
}


def _is_placeholder(price: Decimal) -> bool:
    """Tekrarlayan rakam veya bilinen placeholder mı?"""
    if price in _PLACEHOLDER_PRICES:
        return True
    s = str(int(price))
    if len(s) >= 4 and len(set(s)) == 1:
        return True
    return False


async def run_audit():
    """Ana denetim fonksiyonu."""
    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

    async with AsyncSessionLocal() as db:
        print("=" * 70)
        print("  PRİAL FİYAT VERİSİ DENETİMİ")
        print("=" * 70)

        # ── 7. Genel istatistikler ──
        print("\n📊 GENEL İSTATİSTİKLER")
        print("-" * 40)

        total_records = (await db.execute(
            select(func.count(PriceHistory.id)).where(PriceHistory.recorded_at >= six_months_ago)
        )).scalar() or 0
        print(f"  Son 6 ay toplam kayıt: {total_records:,}")

        total_stores = (await db.execute(
            select(func.count(func.distinct(PriceHistory.product_store_id)))
            .where(PriceHistory.recorded_at >= six_months_ago)
        )).scalar() or 0
        print(f"  Kayıt olan store sayısı: {total_stores:,}")

        if total_stores > 0:
            print(f"  Store başına ortalama kayıt: {total_records / total_stores:.1f}")

        # Kaynak dağılımı
        source_result = await db.execute(
            select(PriceHistory.source, func.count())
            .where(PriceHistory.recorded_at >= six_months_ago)
            .group_by(PriceHistory.source)
        )
        print("  Kaynak dağılımı:")
        for source, count in source_result.all():
            print(f"    {source}: {count:,}")

        # ── 1. Spike'lar (%200+ artış) ──
        print("\n🔺 SPİKE TESPİTİ (%200+ fiyat artışı)")
        print("-" * 40)

        # Her product_store_id için ardışık kayıtları çek
        store_ids_result = await db.execute(
            select(func.distinct(PriceHistory.product_store_id))
            .where(PriceHistory.recorded_at >= six_months_ago)
        )
        store_ids = [row[0] for row in store_ids_result.all()]

        spike_count = 0
        spike_examples = []

        for ps_id in store_ids:
            records = (await db.execute(
                select(PriceHistory.price, PriceHistory.recorded_at, PriceHistory.source)
                .where(
                    PriceHistory.product_store_id == ps_id,
                    PriceHistory.recorded_at >= six_months_ago,
                    PriceHistory.price > 0,
                )
                .order_by(PriceHistory.recorded_at)
            )).all()

            for i in range(1, len(records)):
                old_price = records[i - 1][0]
                new_price = records[i][0]
                if old_price > 0 and new_price > old_price * 3:  # %200+ artış
                    spike_count += 1
                    if len(spike_examples) < 10:
                        spike_examples.append({
                            "store_id": str(ps_id)[:8],
                            "old": float(old_price),
                            "new": float(new_price),
                            "date": records[i][1].strftime("%Y-%m-%d"),
                            "source": records[i][2],
                            "ratio": f"{float(new_price / old_price):.1f}x",
                        })

        print(f"  Toplam spike: {spike_count}")
        for ex in spike_examples:
            print(f"    [{ex['store_id']}] {ex['old']:,.0f} → {ex['new']:,.0f} ({ex['ratio']}) @ {ex['date']} [{ex['source']}]")

        # ── 2. Ani düşüşler (%80+) ──
        print("\n🔻 ANİ DÜŞÜŞ TESPİTİ (%80+ fiyat düşüşü)")
        print("-" * 40)

        drop_count = 0
        drop_examples = []

        for ps_id in store_ids:
            records = (await db.execute(
                select(PriceHistory.price, PriceHistory.recorded_at, PriceHistory.source)
                .where(
                    PriceHistory.product_store_id == ps_id,
                    PriceHistory.recorded_at >= six_months_ago,
                    PriceHistory.price > 0,
                )
                .order_by(PriceHistory.recorded_at)
            )).all()

            for i in range(1, len(records)):
                old_price = records[i - 1][0]
                new_price = records[i][0]
                if old_price > 0 and new_price < old_price * Decimal("0.2"):  # %80+ düşüş
                    drop_count += 1
                    if len(drop_examples) < 10:
                        pct = float((old_price - new_price) / old_price * 100)
                        drop_examples.append({
                            "store_id": str(ps_id)[:8],
                            "old": float(old_price),
                            "new": float(new_price),
                            "date": records[i][1].strftime("%Y-%m-%d"),
                            "drop_pct": f"{pct:.0f}%",
                        })

        print(f"  Toplam ani düşüş: {drop_count}")
        for ex in drop_examples:
            print(f"    [{ex['store_id']}] {ex['old']:,.0f} → {ex['new']:,.0f} (-{ex['drop_pct']}) @ {ex['date']}")

        # ── 3. Sabit fiyatlar (30+ gün aynı) ──
        print("\n📏 SABİT FİYATLAR (30+ gün aynı fiyat)")
        print("-" * 40)

        stale_count = 0
        for ps_id in store_ids:
            records = (await db.execute(
                select(PriceHistory.price, PriceHistory.recorded_at)
                .where(
                    PriceHistory.product_store_id == ps_id,
                    PriceHistory.recorded_at >= six_months_ago,
                    PriceHistory.price > 0,
                )
                .order_by(PriceHistory.recorded_at)
            )).all()

            if len(records) < 2:
                continue

            # Ardışık aynı fiyat serileri bul
            streak_start = records[0][1]
            streak_price = records[0][0]

            for i in range(1, len(records)):
                if records[i][0] == streak_price:
                    duration = (records[i][1] - streak_start).days
                    if i == len(records) - 1 and duration >= 30:
                        stale_count += 1
                else:
                    duration = (records[i - 1][1] - streak_start).days
                    if duration >= 30:
                        stale_count += 1
                    streak_start = records[i][1]
                    streak_price = records[i][0]

        print(f"  Sabit fiyat serileri (30+ gün): {stale_count}")

        # ── 4. Placeholder fiyatlar ──
        print("\n🚫 PLACEHOLDER FİYATLAR")
        print("-" * 40)

        placeholder_count = 0
        placeholder_examples = []

        for ps_id in store_ids:
            records = (await db.execute(
                select(PriceHistory.price, PriceHistory.recorded_at)
                .where(
                    PriceHistory.product_store_id == ps_id,
                    PriceHistory.recorded_at >= six_months_ago,
                )
                .order_by(PriceHistory.recorded_at)
            )).all()

            for price, dt in records:
                if _is_placeholder(price):
                    placeholder_count += 1
                    if len(placeholder_examples) < 10:
                        placeholder_examples.append({
                            "store_id": str(ps_id)[:8],
                            "price": float(price),
                            "date": dt.strftime("%Y-%m-%d"),
                        })

        print(f"  Placeholder kayıt sayısı: {placeholder_count}")
        for ex in placeholder_examples:
            print(f"    [{ex['store_id']}] ₺{ex['price']:,.2f} @ {ex['date']}")

        # ── 5. Veri boşlukları (14+ gün) ──
        print("\n⏳ VERİ BOŞLUKLARI (14+ gün kayıt yok)")
        print("-" * 40)

        fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

        # Aktif store'lar ama 14+ gündür kayıt yok
        active_stores_result = await db.execute(
            select(ProductStore.id, ProductStore.store, ProductStore.product_id)
            .where(
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.current_price.isnot(None),
            )
        )
        active_stores = active_stores_result.all()

        gap_count = 0
        for ps_id, store_name, product_id in active_stores:
            latest = (await db.execute(
                select(func.max(PriceHistory.recorded_at))
                .where(PriceHistory.product_store_id == ps_id)
            )).scalar()

            if latest and latest < fourteen_days_ago:
                gap_count += 1

        print(f"  14+ gün kayıtsız aktif store: {gap_count}")

        # ── 6. Fiyat tutarsızlığı (5x+ fark) ──
        print("\n⚠️ FİYAT TUTARSIZLIĞI (aynı ürünün store'ları arasında 5x+ fark)")
        print("-" * 40)

        inconsistency_count = 0
        inconsistency_examples = []

        # Ürün başına aktif store'ların fiyatlarını grupla
        product_prices = defaultdict(list)
        stores_result = await db.execute(
            select(
                ProductStore.product_id,
                ProductStore.store,
                ProductStore.current_price,
            ).where(
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.current_price.isnot(None),
                ProductStore.current_price > 0,
            )
        )
        for product_id, store_name, price in stores_result.all():
            product_prices[product_id].append((store_name, price))

        for product_id, store_list in product_prices.items():
            if len(store_list) < 2:
                continue
            prices = [float(p) for _, p in store_list]
            min_p, max_p = min(prices), max(prices)
            if min_p > 0 and max_p / min_p >= 5:
                inconsistency_count += 1
                if len(inconsistency_examples) < 5:
                    inconsistency_examples.append({
                        "product_id": str(product_id)[:8],
                        "prices": [(s.value, float(p)) for s, p in store_list],
                    })

        print(f"  Tutarsız ürün sayısı: {inconsistency_count}")
        for ex in inconsistency_examples:
            stores_str = ", ".join(f"{s}: ₺{p:,.0f}" for s, p in ex["prices"])
            print(f"    [{ex['product_id']}] {stores_str}")

        # ── Özet ──
        print("\n" + "=" * 70)
        print("  ÖZET")
        print("=" * 70)
        print(f"  Spike'lar (%200+ artış):     {spike_count}")
        print(f"  Ani düşüşler (%80+):         {drop_count}")
        print(f"  Sabit fiyat serileri (30d+):  {stale_count}")
        print(f"  Placeholder fiyatlar:         {placeholder_count}")
        print(f"  Veri boşlukları (14d+):       {gap_count}")
        print(f"  Fiyat tutarsızlıkları (5x+):  {inconsistency_count}")
        print(f"  Toplam kayıt (6 ay):          {total_records:,}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_audit())
