"""
Gunluk ve haftalik fiyat ozeti bildirimleri.
APScheduler cron job'lari tarafindan cagrilir.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.alarm import Alarm, AlarmStatus
from app.models.price_history import PriceHistory
from app.models.product import Product, ProductStore
from app.models.user import User
from app.services.notification_service import notify_daily_summary, notify_weekly_summary


async def send_daily_summaries() -> None:
    """Her gun 10:00 — takip edilen urunlerdeki son 24 saatteki fiyat dususlerini ozetle.
    Pazartesi gunleri calistirilmaz (haftalik ozet gider)."""
    now = datetime.now(timezone.utc)
    if now.weekday() == 0:  # 0 = Pazartesi
        print("[daily_summary] Pazartesi — haftalik ozet gidecek, gunluk atlanıyor.")
        return
    cutoff = now - timedelta(hours=24)

    async with AsyncSessionLocal() as db:
        # Aktif alarmi olan kullanicilari bul
        user_result = await db.execute(
            select(Alarm.user_id).where(
                Alarm.status == AlarmStatus.ACTIVE,
            ).distinct()
        )
        user_ids = [row[0] for row in user_result.all()]

        if not user_ids:
            print("[daily_summary] Aktif alarmi olan kullanici yok.")
            return

        for user_id in user_ids:
            user_row = await db.execute(select(User).where(User.id == user_id))
            user = user_row.scalar_one_or_none()
            if not user or not user.push_notifications_enabled or not user.firebase_token:
                continue

            # Kullanicinin takip ettigi urunlerin store'larini bul
            alarm_result = await db.execute(
                select(Alarm.product_id).where(
                    Alarm.user_id == user_id,
                    Alarm.status == AlarmStatus.ACTIVE,
                ).distinct()
            )
            product_ids = [row[0] for row in alarm_result.all()]
            if not product_ids:
                continue

            # Bu urunlerin store'larinda son 24 saatte fiyat dususu olan urun sayisi
            store_result = await db.execute(
                select(ProductStore.product_id).where(
                    ProductStore.product_id.in_(product_ids),
                    ProductStore.is_active == True,
                ).distinct()
            )
            tracked_product_ids = [row[0] for row in store_result.all()]
            if not tracked_product_ids:
                continue

            # Son 24 saatteki fiyat kayitlarini kontrol et — fiyat dusen urunleri say
            drop_count = 0
            for pid in tracked_product_ids:
                stores = await db.execute(
                    select(ProductStore).where(
                        ProductStore.product_id == pid,
                        ProductStore.is_active == True,
                    )
                )
                for store in stores.scalars().all():
                    # Son 24 saatteki en eski ve en yeni fiyati karsilastir
                    history = await db.execute(
                        select(PriceHistory.price).where(
                            PriceHistory.product_store_id == store.id,
                            PriceHistory.recorded_at >= cutoff,
                        ).order_by(PriceHistory.recorded_at.asc())
                    )
                    prices = [row[0] for row in history.all()]
                    if len(prices) >= 2 and prices[-1] < prices[0]:
                        drop_count += 1
                        break  # Bu urun icin bir store yeter

            if drop_count > 0:
                await notify_daily_summary(user=user, drop_count=drop_count, db=db)

        await db.commit()

    print(f"[daily_summary] Gunluk ozet bildirimleri gonderildi.")


async def send_weekly_summaries() -> None:
    """Her Pazartesi 10:00 — haftanin en cok dusen urununu bildir."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    async with AsyncSessionLocal() as db:
        # Aktif alarmi olan kullanicilari bul
        user_result = await db.execute(
            select(Alarm.user_id).where(
                Alarm.status == AlarmStatus.ACTIVE,
            ).distinct()
        )
        user_ids = [row[0] for row in user_result.all()]

        if not user_ids:
            print("[weekly_summary] Aktif alarmi olan kullanici yok.")
            return

        for user_id in user_ids:
            user_row = await db.execute(select(User).where(User.id == user_id))
            user = user_row.scalar_one_or_none()
            if not user or not user.push_notifications_enabled or not user.firebase_token:
                continue

            # Kullanicinin takip ettigi urunler
            alarm_result = await db.execute(
                select(Alarm.product_id).where(
                    Alarm.user_id == user_id,
                    Alarm.status == AlarmStatus.ACTIVE,
                ).distinct()
            )
            product_ids = [row[0] for row in alarm_result.all()]
            if not product_ids:
                continue

            # Her urun icin son 7 gundeki en buyuk dususu bul
            best_drop_percent = 0
            best_product_name = ""

            for pid in product_ids:
                product = await db.get(Product, pid)
                if not product:
                    continue

                stores = await db.execute(
                    select(ProductStore).where(
                        ProductStore.product_id == pid,
                        ProductStore.is_active == True,
                    )
                )
                for store in stores.scalars().all():
                    # Son 7 gundeki ilk ve son fiyat
                    history = await db.execute(
                        select(PriceHistory.price).where(
                            PriceHistory.product_store_id == store.id,
                            PriceHistory.recorded_at >= cutoff,
                        ).order_by(PriceHistory.recorded_at.asc())
                    )
                    prices = [row[0] for row in history.all()]
                    if len(prices) >= 2 and prices[0] > 0:
                        drop = float((prices[0] - prices[-1]) / prices[0] * 100)
                        if drop > best_drop_percent:
                            best_drop_percent = drop
                            best_product_name = product.short_title or product.title[:38]

            if best_drop_percent > 0 and best_product_name:
                await notify_weekly_summary(
                    user=user,
                    top_product_name=best_product_name,
                    drop_percent=int(best_drop_percent),
                    db=db,
                )

        await db.commit()

    print(f"[weekly_summary] Haftalik ozet bildirimleri gonderildi.")
