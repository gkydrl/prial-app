"""
Her ürüne rastgele 50-150 arası alarm_count ekler.
Gerçek alarm kaydı oluşturmaz — sadece sayacı günceller.

Kullanım:
    cd backend
    python3 seed_alarm_counts.py
"""

import os
import re
import sys
import random

# ─── .env yükle ───────────────────────────────────────────────────────────────

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

RAW_DB_URL = os.environ.get("DATABASE_URL", "")
if not RAW_DB_URL:
    print("ERROR: DATABASE_URL .env'de tanımlı değil.")
    sys.exit(1)

DB_URL = re.sub(r"^postgresql\+asyncpg://", "postgresql://", RAW_DB_URL)
DB_URL = re.sub(r"^postgresql\+psycopg://", "postgresql://", DB_URL)

# ─── Ana fonksiyon ────────────────────────────────────────────────────────────

def main():
    try:
        import psycopg
    except ImportError:
        try:
            import psycopg2 as psycopg
        except ImportError:
            print("ERROR: psycopg veya psycopg2 yüklü değil.")
            sys.exit(1)

    conn = psycopg.connect(DB_URL)

    with conn.cursor() as cur:
        cur.execute("SELECT id, title, alarm_count FROM products ORDER BY created_at")
        products = cur.fetchall()

    print(f"{len(products)} ürün bulundu.\n")

    updated = 0
    for product_id, title, current_count in products:
        new_count = random.randint(50, 150)
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET alarm_count = %s WHERE id = %s",
                (new_count, product_id)
            )
        updated += 1
        print(f"  ✓ {title[:50]:50s}  {current_count:>4d} → {new_count}")

    conn.commit()
    conn.close()
    print(f"\n{'='*50}")
    print(f"Tamamlandı! {updated} ürün güncellendi.")


if __name__ == "__main__":
    main()
