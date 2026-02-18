"""
Alarm tetiklendiğinde push notification ve e-posta gönderir.
"""
from decimal import Decimal

from app.database import AsyncSessionLocal
from app.models.alarm import Alarm
from app.models.product import ProductStore
from app.models.notification import Notification, NotificationType, NotificationStatus
from app.services.firebase_service import send_push_notification
from app.services.email_service import send_alarm_email


async def send_alarm_notifications(
    alarms: list[Alarm],
    store: ProductStore,
    new_price: Decimal,
) -> None:
    async with AsyncSessionLocal() as db:
        for alarm in alarms:
            from sqlalchemy import select
            from app.models.user import User

            user_result = await db.execute(select(User).where(User.id == alarm.user_id))
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            from app.models.product import Product
            product = await db.get(Product, alarm.product_id)
            if not product:
                continue

            title = f"Fiyat Düştü! {product.title[:40]}..."
            body = (
                f"Hedef fiyatınız {alarm.target_price} TL'ye ulaşıldı. "
                f"Şu anki fiyat: {new_price} TL"
            )

            # Push Notification
            if user.push_notifications_enabled and user.firebase_token:
                push_status = NotificationStatus.PENDING
                error_msg = None
                try:
                    await send_push_notification(
                        token=user.firebase_token,
                        title=title,
                        body=body,
                        data={"alarm_id": str(alarm.id), "product_url": store.url},
                    )
                    push_status = NotificationStatus.SENT
                except Exception as e:
                    push_status = NotificationStatus.FAILED
                    error_msg = str(e)[:500]

                notif = Notification(
                    user_id=user.id,
                    alarm_id=alarm.id,
                    type=NotificationType.PUSH,
                    status=push_status,
                    title=title,
                    body=body,
                    error_message=error_msg,
                )
                db.add(notif)

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
                    type=NotificationType.EMAIL,
                    status=email_status,
                    title=title,
                    body=body,
                    error_message=error_msg,
                )
                db.add(notif)

        await db.commit()
