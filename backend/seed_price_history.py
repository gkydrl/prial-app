"""
Seed script: Her product_store için son 24 saat içinde fiyat düşüşü simüle eder.
Kullanım:
    cd backend && python seed_price_history.py
"""

import os
import sys
import re
import uuid
from datetime import datetime, timedelta, timezone

def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

load_env()

raw_url = os.environ.get("DATABASE_URL", "")
if not raw_url:
    print("ERROR: DATABASE_URL tanımlı değil.")
    sys.exit(1)

db_url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)
db_url = re.sub(r"^postgresql\+psycopg://", "postgresql://", db_url)

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg yüklü değil. Çalıştır: pip install psycopg[binary]")
    sys.exit(1)

def main():
    print("Connecting to database...")
    try:
        conn = psycopg.connect(db_url)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("Connected. Seeding price history...")

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(hours=15)  # 15 saat önce

    with conn:
        with conn.cursor() as cur:
            # Tüm product_store kayıtlarını çek
            cur.execute(
                "SELECT id, current_price, original_price FROM product_stores WHERE is_active = true"
            )
            stores = cur.fetchall()
            print(f"Found {len(stores)} product stores.")

            inserted = 0
            skipped = 0
            for store_id, current_price, original_price in stores:
                # Zaten bu store için son 24 saatte kayıt var mı?
                cur.execute(
                    "SELECT COUNT(*) FROM price_history WHERE product_store_id = %s AND recorded_at >= %s",
                    (store_id, now - timedelta(hours=24)),
                )
                count = cur.fetchone()[0]
                if count >= 2:
                    skipped += 1
                    continue

                high_price = original_price if original_price else current_price * 120 / 100
                low_price = current_price

                # Eski fiyat (15 saat önce, yüksek)
                cur.execute(
                    """
                    INSERT INTO price_history (id, product_store_id, price, original_price, currency, in_stock, recorded_at)
                    VALUES (%s, %s, %s, %s, 'TRY', true, %s)
                    """,
                    (str(uuid.uuid4()), str(store_id), float(high_price), float(high_price), old_time),
                )

                # Güncel fiyat (1 saat önce, düşük)
                recent_time = now - timedelta(hours=1)
                cur.execute(
                    """
                    INSERT INTO price_history (id, product_store_id, price, original_price, currency, in_stock, recorded_at)
                    VALUES (%s, %s, %s, %s, 'TRY', true, %s)
                    """,
                    (str(uuid.uuid4()), str(store_id), float(low_price), float(high_price), recent_time),
                )
                inserted += 1

            print(f"\nDone! {inserted} store için fiyat geçmişi eklendi, {skipped} zaten vardı.")

    conn.close()


if __name__ == "__main__":
    main()
