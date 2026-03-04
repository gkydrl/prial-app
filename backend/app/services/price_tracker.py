"""
Öncelik kuyruğuna göre fiyat kontrolü ve alarm tetikleme servisi.
APScheduler ile her 15 dakikada bir çalışır, sadece zamanı gelen store'ları işler.

Öncelik seviyeleri:
  1 = HIGH   — aktif alarmı var  → her 2 saatte bir kontrol
  2 = MEDIUM — geçmişte alarm aldı → her 8 saatte bir kontrol
  3 = LOW    — hiç alarm yok     → her 24 saatte bir kontrol
"""
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.product import ProductStore
from app.models.price_history import PriceHistory
from app.models.alarm import Alarm, AlarmStatus
from app.services.scraper.dispatcher import scrape_url
from app.services.notification_service import send_alarm_notifications

PRIORITY_INTERVALS = {
    1: timedelta(hours=2),   # HIGH  — aktif alarmı var
    2: timedelta(hours=8),   # MEDIUM — geçmişte alarm aldı
    3: timedelta(hours=24),  # LOW   — hiç alarm yok
}


def next_check_delta(priority: int) -> timedelta:
    return PRIORITY_INTERVALS.get(priority, timedelta(hours=24))


async def refresh_store_priority(db: AsyncSession, store: ProductStore) -> None:
    """Bir store'un aktif alarm durumuna göre önceliğini ve next_check_at'ini günceller."""
    result = await db.execute(
        select(Alarm).where(
            Alarm.product_store_id == store.id,
            Alarm.status == AlarmStatus.ACTIVE,
        ).limit(1)
    )
    has_active_alarm = result.scalar_one_or_none() is not None

    if has_active_alarm:
        store.check_priority = 1
    elif store.check_priority > 2:
        # Geçmişte en az 1 alarm vardı (alarm_count > 0 veya dışarıdan set edildi)
        pass  # priority 2 dışarıdan set edilir (alarm silinince)
    # priority 3 zaten default


async def check_due_prices() -> None:
    """
    next_check_at'i geçmiş olan (veya hiç set edilmemiş) store'ları scrape eder.
    """
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProductStore).where(
                ProductStore.is_active == True,
                (ProductStore.next_check_at == None) | (ProductStore.next_check_at <= now),
            )
        )
        stores: list[ProductStore] = result.scalars().all()

    if not stores:
        print("[price_tracker] Kontrol edilecek store yok.")
        return

    print(f"[price_tracker] {len(stores)} store kontrol ediliyor...")

    semaphore = asyncio.Semaphore(settings.scrape_concurrency)

    async def process(store: ProductStore) -> None:
        async with semaphore:
            try:
                await check_product_price(store.id)
            except Exception as e:
                print(f"[price_tracker] Hata (store_id={store.id}): {e}")

    await asyncio.gather(*[process(s) for s in stores])


async def check_product_price(product_store_id) -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        store = await db.get(ProductStore, product_store_id)
        if not store:
            return

        try:
            scraped = await scrape_url(store.url)
        except Exception as e:
            print(f"[price_tracker] Scraping hatası ({store.url}): {e}")
            # Hata olsa bile next_check_at güncelle (sonsuz döngüden kaçın)
            store.next_check_at = now + next_check_delta(store.check_priority)
            store.last_checked_at = now
            await db.commit()
            return

        new_price = scraped.current_price
        old_price = store.current_price
        price_changed = old_price != new_price

        if price_changed:
            store.current_price = new_price
            store.original_price = scraped.original_price
            store.discount_percent = scraped.discount_percent
            store.in_stock = scraped.in_stock

            history = PriceHistory(
                product_store_id=store.id,
                price=new_price,
                original_price=scraped.original_price,
                in_stock=scraped.in_stock,
            )
            db.add(history)

            from app.models.product import Product
            product = await db.get(Product, store.product_id)
            if product:
                if product.lowest_price_ever is None or new_price < product.lowest_price_ever:
                    product.lowest_price_ever = new_price
                db.add(product)

        # Önceliği yenile ve bir sonraki kontrol zamanını ayarla
        await refresh_store_priority(db, store)
        store.last_checked_at = now
        store.next_check_at = now + next_check_delta(store.check_priority)
        db.add(store)

        if price_changed:
            await db.flush()
            await _check_alarms(db, store, new_price)

        await db.commit()

        if price_changed:
            print(f"[price_tracker] Fiyat değişti: {store.url} | {old_price} → {new_price}")


async def _check_alarms(
    db: AsyncSession,
    store: ProductStore,
    new_price: Decimal,
) -> None:
    """Fiyat düştüğünde ilgili aktif alarmları tetikle."""
    result = await db.execute(
        select(Alarm).where(
            Alarm.product_store_id == store.id,
            Alarm.status == AlarmStatus.ACTIVE,
            Alarm.target_price >= new_price,
        )
    )
    triggered_alarms: list[Alarm] = result.scalars().all()

    for alarm in triggered_alarms:
        alarm.status = AlarmStatus.TRIGGERED
        alarm.triggered_price = new_price
        alarm.triggered_at = datetime.now(timezone.utc)
        db.add(alarm)

    if triggered_alarms:
        await db.flush()
        await send_alarm_notifications(triggered_alarms, store, new_price)
