"""
Katalog seed scripti — direkt psycopg3 kullanır (Python 3.9 uyumlu).

Çalıştırma (backend/ dizininden):
    python scripts/seed/run_seed.py

.env dosyasında DATABASE_URL tanımlı olmalı.
Idempotent: mevcut kategori/ürün/variantları atlar.
"""

import os
import sys
import re
import uuid
import json

# .env dosyasını oku
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
    print("ERROR: DATABASE_URL ortam değişkeni tanımlı değil.")
    print("Örnek: DATABASE_URL=postgresql://user:pass@host:5432/db python scripts/seed/run_seed.py")
    sys.exit(1)

# SQLAlchemy URL formatını psycopg3 native formatına çevir
db_url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)
db_url = re.sub(r"^postgresql\+psycopg://", "postgresql://", db_url)
for param in ("?sslmode=require", "&sslmode=require", "?sslmode=disable", "&sslmode=disable"):
    db_url = db_url.replace(param, "")

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg yüklü değil. Çalıştır: pip install psycopg[binary]")
    sys.exit(1)

# Seed verilerini import et
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_here)))

from scripts.seed.categories import CATEGORIES
from scripts.seed.data_technology import TECHNOLOGY_PRODUCTS
from scripts.seed.data_commission import COMMISSION_PRODUCTS
from scripts.seed.data_fashion import FASHION_PRODUCTS

ALL_PRODUCTS = TECHNOLOGY_PRODUCTS + COMMISSION_PRODUCTS + FASHION_PRODUCTS


def seed(conn):
    with conn.cursor() as cur:

        # ── 1. Kategoriler ────────────────────────────────────────────────────
        print("\nKategoriler oluşturuluyor...")
        cat_new = 0
        slug_to_id: dict[str, str] = {}

        for cat in CATEGORIES:
            # Mevcut mi?
            cur.execute("SELECT id FROM categories WHERE slug = %s", (cat["slug"],))
            row = cur.fetchone()
            if row:
                slug_to_id[cat["slug"]] = str(row[0])
            else:
                new_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO categories (id, name, slug) VALUES (%s, %s, %s)",
                    (new_id, cat["name"], cat["slug"]),
                )
                slug_to_id[cat["slug"]] = new_id
                cat_new += 1
                print(f"  [+] {cat['name']}")

        print(f"  {cat_new} yeni kategori, {len(CATEGORIES) - cat_new} mevcut (atlandı)")

        # ── 2. Ürünler & Variantlar ───────────────────────────────────────────
        print("\nÜrünler ve variantlar oluşturuluyor...")
        prod_new = 0
        prod_skip = 0
        var_new = 0
        var_skip = 0

        for product_data in ALL_PRODUCTS:
            title = product_data["title"]
            brand = product_data.get("brand")
            category_slug = product_data.get("category")
            variants_data = product_data.get("variants", [])
            category_id = slug_to_id.get(category_slug) if category_slug else None

            # Mevcut ürünü bul (title + brand üzerinden)
            if brand:
                cur.execute(
                    "SELECT id FROM products WHERE title = %s AND brand = %s",
                    (title, brand),
                )
            else:
                cur.execute(
                    "SELECT id FROM products WHERE title = %s AND brand IS NULL",
                    (title,),
                )
            row = cur.fetchone()

            if row:
                product_id = str(row[0])
                prod_skip += 1
            else:
                product_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO products (id, title, brand, category_id, alarm_count)
                    VALUES (%s, %s, %s, %s, 0)
                    """,
                    (product_id, title, brand, category_id),
                )
                prod_new += 1

            # Variantlar
            for vdata in variants_data:
                variant_title = vdata.get("title")
                attributes = vdata.get("attributes") or {}

                cur.execute(
                    "SELECT id FROM product_variants WHERE product_id = %s AND title = %s",
                    (product_id, variant_title),
                )
                if cur.fetchone():
                    var_skip += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO product_variants (id, product_id, title, attributes, alarm_count)
                    VALUES (%s, %s, %s, %s, 0)
                    """,
                    (
                        str(uuid.uuid4()),
                        product_id,
                        variant_title,
                        json.dumps(attributes) if attributes else None,
                    ),
                )
                var_new += 1

        print(f"  Ürün : {prod_new} yeni, {prod_skip} mevcut (atlandı)")
        print(f"  Variant: {var_new} yeni, {var_skip} mevcut (atlandı)")


def main():
    print("=" * 60)
    print("Prial Katalog Seed")
    print("=" * 60)

    total_prod = len(ALL_PRODUCTS)
    total_var = sum(len(p.get("variants", [])) for p in ALL_PRODUCTS)
    print(f"\nToplam veri: {total_prod} ürün, {total_var} variant, {len(CATEGORIES)} kategori")

    print(f"\nVeritabanına bağlanılıyor...")
    try:
        conn = psycopg.connect(db_url)
    except Exception as e:
        print(f"ERROR: Bağlantı kurulamadı: {e}")
        sys.exit(1)

    print("Bağlantı kuruldu.")

    try:
        with conn:
            seed(conn)
        print("\nSeed tamamlandı!")
    except Exception as e:
        print(f"\n[HATA] Seed başarısız: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
