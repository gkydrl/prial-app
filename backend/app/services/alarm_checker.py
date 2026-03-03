"""
Her 30 dakikada bir tüm aktif talepleri kontrol eder.
Ürünün current_price <= kullanıcının target_price ise talebi kapatır ve bildirim gönderir.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.alarm import Alarm, AlarmStatus
from app.models.product import Product


async def check_alarm_triggers() -> None:
    """
    Aktif alarmları tara — current_price <= target_price olanları TRIGGERED yap.
    Fiyat takibinin yanında 30 dk'da bir ek güvenlik katmanı sağlar.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Alarm)
            .options(
                selectinload(Alarm.product_store),
                selectinload(Alarm.product).selectinload(Product.stores),
            )
            .where(Alarm.status == AlarmStatus.ACTIVE)
        )
        alarms = result.scalars().all()

        triggered_batch: list[tuple] = []

        for alarm in alarms:
            # Belirli bir mağaza hedefleniyorsa onu kullan
            if alarm.product_store and alarm.product_store.current_price is not None:
                store = alarm.product_store
                current_price = store.current_price
            elif alarm.product and alarm.product.stores:
                # Stokta olan en ucuz mağazayı bul
                in_stock = [
                    s for s in alarm.product.stores
                    if s.in_stock and s.current_price is not None
                ]
                if not in_stock:
                    continue
                store = min(in_stock, key=lambda s: s.current_price)
                current_price = store.current_price
            else:
                continue

            if current_price <= alarm.target_price:
                alarm.status = AlarmStatus.TRIGGERED
                alarm.triggered_price = current_price
                alarm.triggered_at = datetime.now(timezone.utc)
                triggered_batch.append((alarm, store, current_price))

        if triggered_batch:
            await db.commit()
            from app.services.notification_service import send_alarm_notifications
            for alarm, store, price in triggered_batch:
                try:
                    await send_alarm_notifications([alarm], store, price)
                except Exception as e:
                    print(f"[alarm_checker] Bildirim hatası (alarm={alarm.id}): {e}")

        print(
            f"[alarm_checker] {len(alarms)} aktif alarm kontrol edildi, "
            f"{len(triggered_batch)} tetiklendi."
        )
