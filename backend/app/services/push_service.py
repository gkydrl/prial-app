"""
Expo Push Notification API client.

Expo push token'ları (ExponentPushToken[xxx]) ile bildirim gönderir.
Firebase SDK yerine Expo Push API kullanır — mobile zaten Expo token üretiyor.

Docs: https://docs.expo.dev/push-notifications/sending-notifications/
"""
import httpx

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
BATCH_SIZE = 100


async def send_expo_push(
    token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> dict:
    """Tek bir Expo push token'a bildirim gönderir."""
    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "priority": "high",
    }
    if data:
        payload["data"] = data

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            EXPO_PUSH_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result = resp.json()

    # Expo API hata döndüyse raise et
    ticket = result.get("data", {})
    if ticket.get("status") == "error":
        raise RuntimeError(
            f"Expo push error: {ticket.get('message', 'unknown')}"
        )
    return result


async def send_expo_push_batch(
    messages: list[dict],
) -> list[dict]:
    """Birden fazla bildirim gönderir (100'lük batch'ler halinde).

    Her message dict'i: {"to", "title", "body", "data"?}
    """
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        for i in range(0, len(messages), BATCH_SIZE):
            batch = messages[i : i + BATCH_SIZE]
            # Expo formatına dönüştür
            payloads = []
            for msg in batch:
                p = {
                    "to": msg["to"],
                    "title": msg["title"],
                    "body": msg["body"],
                    "sound": "default",
                    "priority": "high",
                }
                if msg.get("data"):
                    p["data"] = msg["data"]
                payloads.append(p)

            resp = await client.post(
                EXPO_PUSH_URL,
                json=payloads,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()
            results.extend(result.get("data", []))

    return results
