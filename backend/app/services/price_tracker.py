"""
Periyodik fiyat kontrolü ve alarm tetikleme servisi.
APScheduler ile her N dakikada bir çalışır.
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.product import ProductStore
from app.models.price_history import PriceHistory
from app.models.alarm import Alarm, AlarmStatus
from app.services.scraper.dispatcher import scrape_url
from app.services.notification_service import send_alarm_notifications


async def check_all_prices() -> None:
    """Aktif tüm ProductStore kayıtlarının fiyatını günceller."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ProductStore).where(ProductStore.is_active == True)
        )
        stores: list[ProductStore] = result.scalars().all()

    for store in stores:
        try:
            await check_product_price(store.id)
        except Exception as e:
            print(f"Fiyat kontrol hatası (store_id={store.id}): {e}")


async def check_product_price(product_store_id) -> None:
    async with AsyncSessionLocal() as db:
        store = await db.get(ProductStore, product_store_id)
        if not store:
            return

        try:
            scraped = await scrape_url(store.url)
        except Exception as e:
            print(f"Scraping hatası: {e}")
            return

        new_price = scraped.current_price
        old_price = store.current_price

        # Fiyat değişti mi?
        if old_price != new_price:
            store.current_price = new_price
            store.original_price = scraped.original_price
            store.discount_percent = scraped.discount_percent
            store.in_stock = scraped.in_stock
            store.last_checked_at = datetime.now(timezone.utc)

            # Fiyat geçmişi kaydet
            history = PriceHistory(
                product_store_id=store.id,
                price=new_price,
                original_price=scraped.original_price,
                in_stock=scraped.in_stock,
            )
            db.add(history)

            # Ürünün en düşük fiyatını güncelle
            from app.models.product import Product
            product = await db.get(Product, store.product_id)
            if product:
                if product.lowest_price_ever is None or new_price < product.lowest_price_ever:
                    product.lowest_price_ever = new_price
                db.add(product)

            db.add(store)
            await db.flush()

        # Aktif alarmları kontrol et
        if old_price != new_price:
            await _check_alarms(db, store, new_price)

        await db.commit()


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
