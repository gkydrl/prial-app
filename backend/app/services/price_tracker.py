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
from app.services.notification_service import send_alarm_notifications, notify_price_drop

PRIORITY_INTERVALS = {
    1: timedelta(hours=2),   # HIGH  — aktif alarmı var
    2: timedelta(hours=8),   # MEDIUM — geçmişte alarm aldı
    3: timedelta(hours=24),  # LOW   — hiç alarm yok
}


def next_check_delta(priority: int) -> timedelta:
    return PRIORITY_INTERVALS.get(priority, timedelta(hours=24))


async def refresh_store_priority(db: AsyncSession, store: ProductStore) -> None:
    """Bir store'un aktif alarm durumuna göre önceliğini ve next_check_at'ini günceller."""
    # Direkt store'a bağlı alarm var mı?
    store_alarm_result = await db.execute(
        select(Alarm).where(
            Alarm.product_store_id == store.id,
            Alarm.status == AlarmStatus.ACTIVE,
        ).limit(1)
    )
    has_active_alarm = store_alarm_result.scalar_one_or_none() is not None

    # Store'un variant'ına bağlı alarm var mı?
    if not has_active_alarm and store.variant_id is not None:
        variant_alarm_result = await db.execute(
            select(Alarm).where(
                Alarm.variant_id == store.variant_id,
                Alarm.status == AlarmStatus.ACTIVE,
            ).limit(1)
        )
        has_active_alarm = variant_alarm_result.scalar_one_or_none() is not None

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
        # 0 veya None fiyat → scrape başarısız, kaydetme
        if not new_price or new_price <= 0:
            store.next_check_at = now + next_check_delta(store.check_priority)
            store.last_checked_at = now
            await db.commit()
            return

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

            from app.models.product import Product, ProductVariant
            product = await db.get(Product, store.product_id)
            if product:
                if product.lowest_price_ever is None or new_price < product.lowest_price_ever:
                    product.lowest_price_ever = new_price
                db.add(product)

            if store.variant_id:
                variant = await db.get(ProductVariant, store.variant_id)
                if variant:
                    if variant.lowest_price_ever is None or new_price < variant.lowest_price_ever:
                        variant.lowest_price_ever = new_price
                    db.add(variant)

        # Önceliği yenile ve bir sonraki kontrol zamanını ayarla
        await refresh_store_priority(db, store)
        store.last_checked_at = now
        store.next_check_at = now + next_check_delta(store.check_priority)
        db.add(store)

        if price_changed:
            await db.flush()
            await _check_alarms(db, store, new_price)

            # Fiyat dususu bildirimi (%10 / %20)
            if old_price and old_price > 0 and new_price < old_price:
                drop_pct = float((old_price - new_price) / old_price * 100)
                if drop_pct >= 10:
                    await _notify_price_drop_users(
                        db, store, new_price, int(drop_pct)
                    )

        await db.commit()

        if price_changed:
            print(f"[price_tracker] Fiyat değişti: {store.url} | {old_price} → {new_price}")


async def _check_alarms(
    db: AsyncSession,
    store: ProductStore,
    new_price: Decimal,
) -> None:
    """Fiyat düştüğünde ilgili aktif alarmları tetikle.

    Hem store bazlı hem de variant bazlı alarmları kontrol eder.
    Variant bazlı alarm: alarmın variant_id'si bu store'un variant_id'siyle eşleşiyorsa
    ve alarmın hedef fiyatı yeni fiyatın üzerindeyse tetiklenir.
    """
    from sqlalchemy import or_

    conditions = [
        Alarm.product_store_id == store.id,
    ]
    if store.variant_id is not None:
        conditions.append(Alarm.variant_id == store.variant_id)

    result = await db.execute(
        select(Alarm).where(
            or_(*conditions),
            Alarm.status == AlarmStatus.ACTIVE,
            Alarm.target_price >= new_price,
        )
    )
    # Deduplicate in case alarm matches both store and variant conditions
    seen = set()
    triggered_alarms: list[Alarm] = []
    for alarm in result.scalars().all():
        if alarm.id not in seen:
            seen.add(alarm.id)
            triggered_alarms.append(alarm)

    for alarm in triggered_alarms:
        alarm.status = AlarmStatus.TRIGGERED
        alarm.triggered_price = new_price
        alarm.triggered_at = datetime.now(timezone.utc)
        db.add(alarm)

    if triggered_alarms:
        await db.flush()

        # Kampanya kodu atama
        from app.services.promo_assignment import assign_promo_for_alarm
        for alarm in triggered_alarms:
            try:
                assigned_code = await assign_promo_for_alarm(db, alarm, store, new_price)
                alarm._promo_code = assigned_code  # transient attribute for notification
            except Exception as e:
                print(f"[price_tracker] Promo atama hatası (alarm={alarm.id}): {e}")
                alarm._promo_code = None

        await send_alarm_notifications(triggered_alarms, store, new_price)


async def _notify_price_drop_users(
    db: AsyncSession,
    store: ProductStore,
    new_price: Decimal,
    drop_percent: int,
) -> None:
    """Fiyat %10+ dustugunde bu urunu takip eden tum kullanicilara bildirim gonder."""
    from app.models.user import User
    from app.models.product import Product

    product = await db.get(Product, store.product_id)
    if not product:
        return

    # Bu urunu aktif olarak takip eden kullanicilari bul
    result = await db.execute(
        select(Alarm.user_id).where(
            Alarm.product_id == store.product_id,
            Alarm.status == AlarmStatus.ACTIVE,
        ).distinct()
    )
    user_ids = [row[0] for row in result.all()]
    if not user_ids:
        return

    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = users_result.scalars().all()

    # Gosterilecek dusus yuzdesi: %10 veya %20 (esik degerleri)
    display_percent = 20 if drop_percent >= 20 else 10

    for user in users:
        try:
            await notify_price_drop(
                db=db,
                user=user,
                product=product,
                store=store,
                drop_percent=display_percent,
                new_price=new_price,
            )
        except Exception as e:
            print(f"[price_tracker] Price drop bildirim hatasi (user={user.id}): {e}")
