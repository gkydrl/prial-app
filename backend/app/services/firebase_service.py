import firebase_admin
from firebase_admin import credentials, messaging
from app.config import settings

_app = None


def _get_firebase_app():
    global _app
    if _app is None:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _app = firebase_admin.initialize_app(cred)
    return _app


async def send_push_notification(
    token: str,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> str:
    """Firebase Cloud Messaging ile push notification gönderir. Message ID döner."""
    _get_firebase_app()

    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        token=token,
        android=messaging.AndroidConfig(priority="high"),
        apns=messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(sound="default", badge=1)
            )
        ),
    )

    # firebase-admin SDK senkron çalışır, thread pool'da çalıştır
    import asyncio
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: messaging.send(message))
    return response
