"""
Push notification senaryolari:
  1. Hedef fiyat ulasildi (target_reached)
  2. Fiyat %10 dustu (price_drop)
  3. Fiyat %20 dustu (price_drop)
  4. Topluluk milestone (milestone)
  5. Gunluk ozet (daily_summary)
  6. Haftalik ozet (weekly_summary)
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.alarm import Alarm, AlarmStatus
from app.models.notification import (
    Notification,
    NotificationType,
    NotificationStatus,
    NotificationCategory,
)
from app.models.product import Product, ProductStore
from app.models.user import User
from app.services.push_service import send_expo_push
from app.services.email_service import send_alarm_email


# --- Ortak helper -----------------------------------------------------------


async def _send_push(
    user: User,
    title: str,
    body: str,
    category: NotificationCategory,
    data: dict | None = None,
    alarm_id=None,
    product_id=None,
    db: AsyncSession | None = None,
) -> None:
    """Expo Push API ile bildirim gonderir ve Notification kaydi olusturur."""
    if not user.push_notifications_enabled or not user.firebase_token:
        return

    status = NotificationStatus.PENDING
    error_msg = None
    try:
        await send_expo_push(
            token=user.firebase_token,
            title=title,
            body=body,
            data=data,
        )
        status = NotificationStatus.SENT
    except Exception as e:
        status = NotificationStatus.FAILED
        error_msg = str(e)[:500]

    notif = Notification(
        user_id=user.id,
        alarm_id=alarm_id,
        product_id=product_id,
        type=NotificationType.PUSH,
        category=category,
        status=status,
        title=title,
        body=body,
        error_message=error_msg,
        sent_at=datetime.now(timezone.utc) if status == NotificationStatus.SENT else None,
    )

    if db:
        db.add(notif)
    else:
        async with AsyncSessionLocal() as session:
            session.add(notif)
            await session.commit()


async def _was_recently_sent(
    db: AsyncSession,
    user_id,
    product_id,
    category: NotificationCategory,
    hours: int = 24,
) -> bool:
    """Ayni user+product+category icin son N saat icinde bildirim gonderilmis mi?"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(Notification.id).where(
            and_(
                Notification.user_id == user_id,
                Notification.product_id == product_id,
                Notification.category == category,
                Notification.status == NotificationStatus.SENT,
                Notification.created_at >= cutoff,
            )
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


# --- Senaryo 1: Hedef fiyat ulasildi ----------------------------------------


async def send_alarm_notifications(
    alarms: list[Alarm],
    store: ProductStore,
    new_price: Decimal,
) -> None:
    """Hedef fiyata ulastiginda alarm sahiplerine bildirim gonderir."""
    async with AsyncSessionLocal() as db:
        for alarm in alarms:
            user_result = await db.execute(select(User).where(User.id == alarm.user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            product = await db.get(Product, alarm.product_id)
            if not product:
                continue

            display_name = product.short_title or product.title[:38]
            price_str = f"{int(new_price):,}".replace(",", ".")
            title = "🎯 Hedefine ulaştın!"

            # Kampanya kodu varsa mesaja ekle
            promo_code = getattr(alarm, "_promo_code", None)
            if promo_code:
                body = f"{display_name} {price_str} ₺'ye düştü! {promo_code} koduyla ek indirim"
            else:
                body = f"{display_name} artık {price_str} ₺. Hemen al!"

            # Push
            await _send_push(
                user=user,
                title=title,
                body=body,
                category=NotificationCategory.TARGET_REACHED,
                data={"alarm_id": str(alarm.id), "product_url": store.url},
                alarm_id=alarm.id,
                product_id=product.id,
                db=db,
            )

            # E-posta
            if user.email_notifications_enabled:
                email_status = NotificationStatus.PENDING
                error_msg = None
                try:
                    await send_alarm_email(
                        to_email=user.email,
                        product_title=product.title,
                        product_url=store.url,
                        target_price=alarm.target_price,
                        current_price=new_price,
                        image_url=product.image_url,
                    )
                    email_status = NotificationStatus.SENT
                except Exception as e:
                    email_status = NotificationStatus.FAILED
                    error_msg = str(e)[:500]

                notif = Notification(
                    user_id=user.id,
                    alarm_id=alarm.id,
                    product_id=product.id,
                    type=NotificationType.EMAIL,
                    category=NotificationCategory.TARGET_REACHED,
                    status=email_status,
                    title=title,
                    body=body,
                    error_message=error_msg,
                    sent_at=datetime.now(timezone.utc) if email_status == NotificationStatus.SENT else None,
                )
                db.add(notif)

        await db.commit()


# --- Senaryo 2 & 3: Fiyat dususu (%10 / %20) -------------------------------


async def notify_price_drop(
    db: AsyncSession,
    user: User,
    product: Product,
    store: ProductStore,
    drop_percent: int,
    new_price: Decimal,
) -> None:
    """Fiyat belirli bir yuzde dustugunde kullaniciya bildirim gonderir."""
    # Spam onleme: son 24 saatte ayni urun icin price_drop bildirimi gittiyse gonderme
    if await _was_recently_sent(db, user.id, product.id, NotificationCategory.PRICE_DROP):
        return

    display_name = product.short_title or product.title[:38]
    price_str = f"{int(new_price):,}".replace(",", ".")
    if drop_percent >= 20:
        title = "🔥 Büyük indirim!"
        body = f"{display_name} %20 düştü, şu an {price_str} ₺"
    else:
        title = f"📉 {display_name} %10 indi!"
        body = f"Şu an {price_str} ₺ — hedefe yaklaşıyor"

    await _send_push(
        user=user,
        title=title,
        body=body,
        category=NotificationCategory.PRICE_DROP,
        data={"product_id": str(product.id), "product_url": store.url},
        product_id=product.id,
        db=db,
    )


# --- Senaryo 4: Topluluk milestone ------------------------------------------


async def notify_community_milestone(
    product: Product,
    milestone_count: int,
) -> None:
    """Urunun alarm sayisi bir milestone'a ulastiginda takipcilere bildirim gonderir."""
    async with AsyncSessionLocal() as db:
        # Bu urunu aktif olarak takip eden kullanicilari bul
        result = await db.execute(
            select(Alarm.user_id).where(
                Alarm.product_id == product.id,
                Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.PAUSED]),
            ).distinct()
        )
        user_ids = [row[0] for row in result.all()]

        if not user_ids:
            return

        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = users_result.scalars().all()

        display_name = product.short_title or product.title[:38]
        count_str = f"{milestone_count:,}".replace(",", ".")
        title = f"🚀 {display_name} trend oldu!"
        body = f"{count_str} kişi bu ürünü bekliyor, sen de katıl"

        for user in users:
            await _send_push(
                user=user,
                title=title,
                body=body,
                category=NotificationCategory.MILESTONE,
                data={"product_id": str(product.id)},
                product_id=product.id,
                db=db,
            )

        await db.commit()


# --- Senaryo 5: Gunluk ozet -------------------------------------------------


async def notify_daily_summary(
    user: User,
    drop_count: int,
    db: AsyncSession,
) -> None:
    """Kullaniciya gunluk fiyat dususu ozeti gonderir."""
    title = "☀️ Günaydın!"
    body = f"Bugün takip ettiğin {drop_count} üründe fiyat düşüşü var"

    await _send_push(
        user=user,
        title=title,
        body=body,
        category=NotificationCategory.DAILY_SUMMARY,
        db=db,
    )


# --- Senaryo 6: Haftalik ozet -----------------------------------------------


async def notify_weekly_summary(
    user: User,
    top_product_name: str,
    drop_percent: int,
    db: AsyncSession,
) -> None:
    """Kullaniciya haftalik en cok dusen urun bildirimini gonderir."""
    title = "📊 Haftalık özet"
    body = f"Bu hafta en çok düşen: {top_product_name} — %{drop_percent} indirim"

    await _send_push(
        user=user,
        title=title,
        body=body,
        category=NotificationCategory.WEEKLY_SUMMARY,
        db=db,
    )
