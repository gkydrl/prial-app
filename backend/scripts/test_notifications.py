"""
Push notification test script.
Kullanim:
    python scripts/test_notifications.py --email kullanici@example.com
    python scripts/test_notifications.py --email kullanici@example.com --scenario all
    python scripts/test_notifications.py --email kullanici@example.com --scenario price_drop

Senaryo secenekleri:
    target_reached  — Hedef fiyat ulasildi
    price_drop_10   — Fiyat %10 dustu
    price_drop_20   — Fiyat %20 dustu
    milestone        — 500 kisi takip ediyor
    daily_summary    — Gunluk ozet
    weekly_summary   — Haftalik ozet
    all              — Tum senaryolar (varsayilan)
"""
import argparse
import asyncio
import sys
import os

# Backend app'i icin path ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.notification import NotificationCategory
from app.services.notification_service import _send_push, notify_daily_summary, notify_weekly_summary


SCENARIOS = {
    "target_reached": {
        "title": "Hedef fiyata ulasildi! iPhone 16 Pro",
        "body": "Hedef fiyat 45.000 TL'ye ulasildi! Su an: 44.799 TL",
        "category": NotificationCategory.TARGET_REACHED,
    },
    "price_drop_10": {
        "title": "%10 fiyat dususu! AirPods Pro 2",
        "body": "Fiyat %10 dustu, su an 6.299 TL",
        "category": NotificationCategory.PRICE_DROP,
    },
    "price_drop_20": {
        "title": "%20 fiyat dususu! Samsung Galaxy S24",
        "body": "Fiyat %20 dustu, su an 29.999 TL",
        "category": NotificationCategory.PRICE_DROP,
    },
    "milestone": {
        "title": "500 kisi takip ediyor!",
        "body": "MacBook Air M3 artik 500 kisi tarafindan takip ediliyor",
        "category": NotificationCategory.MILESTONE,
    },
}


async def get_user(email: str) -> User:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"HATA: Kullanici bulunamadi: {email}")
            sys.exit(1)
        if not user.firebase_token:
            print(f"HATA: Kullanicinin push token'i yok: {email}")
            sys.exit(1)
        print(f"Kullanici bulundu: {user.full_name or user.email}")
        print(f"Push token: {user.firebase_token[:30]}...")
        return user


async def send_scenario(user: User, name: str) -> None:
    if name in SCENARIOS:
        s = SCENARIOS[name]
        async with AsyncSessionLocal() as db:
            await _send_push(
                user=user,
                title=s["title"],
                body=s["body"],
                category=s["category"],
                data={"test": "true"},
                db=db,
            )
            await db.commit()
        print(f"  [OK] {name}")

    elif name == "daily_summary":
        async with AsyncSessionLocal() as db:
            await notify_daily_summary(user=user, drop_count=5, db=db)
            await db.commit()
        print(f"  [OK] {name}")

    elif name == "weekly_summary":
        async with AsyncSessionLocal() as db:
            await notify_weekly_summary(
                user=user,
                top_product_name="iPad Air M2 256GB",
                drop_percent=22,
                db=db,
            )
            await db.commit()
        print(f"  [OK] {name}")

    else:
        print(f"  [HATA] Bilinmeyen senaryo: {name}")


async def main():
    parser = argparse.ArgumentParser(description="Push notification test script")
    parser.add_argument("--email", required=True, help="Test kullanicisinin e-posta adresi")
    parser.add_argument(
        "--scenario",
        default="all",
        help="Senaryo adi (all, target_reached, price_drop_10, price_drop_20, milestone, daily_summary, weekly_summary)",
    )
    args = parser.parse_args()

    user = await get_user(args.email)

    if args.scenario == "all":
        scenarios = list(SCENARIOS.keys()) + ["daily_summary", "weekly_summary"]
    else:
        scenarios = [args.scenario]

    print(f"\n{len(scenarios)} senaryo gonderiliyor...\n")

    for name in scenarios:
        try:
            await send_scenario(user, name)
        except Exception as e:
            print(f"  [HATA] {name}: {e}")

        # Bildirimler arasi 2 saniye bekle (ust uste gelmesin)
        if len(scenarios) > 1:
            await asyncio.sleep(2)

    print(f"\nTamamlandi!")


if __name__ == "__main__":
    asyncio.run(main())
