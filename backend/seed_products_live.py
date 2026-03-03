"""
Gerçek Trendyol ürünlerini scrape ederek veritabanına ekler.
App modüllerine bağımlı değil — tamamen bağımsız çalışır.

Kullanım:
    cd backend
    python3 seed_products_live.py
"""

import asyncio
import os
import re
import sys
import uuid
import json
from decimal import Decimal

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

# asyncpg/psycopg prefix'ini temizle → psycopg2-style URL
DB_URL = re.sub(r"^postgresql\+asyncpg://", "postgresql://", RAW_DB_URL)
DB_URL = re.sub(r"^postgresql\+psycopg://", "postgresql://", DB_URL)

# ─── Ürün URL listesi ─────────────────────────────────────────────────────────

URLS = [
    # iPhone 16 Serisi
    ("Telefon", "https://www.trendyol.com/apple/iphone-16-pro-max-256-gb-col-titanyum-ithalatci-garantili-p-872473711"),
    ("Telefon", "https://www.trendyol.com/apple/iphone-16-pro-max-512gb-naturel-titanyum-p-857296112"),
    ("Telefon", "https://www.trendyol.com/apple/iphone-16-pro-max-256gb-beyaz-titanyum-p-857296102"),
    ("Telefon", "https://www.trendyol.com/apple/iphone-16-pro-256gb-col-titanyum-p-857296087"),
    # Samsung Galaxy S25
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-s25-ultra-512-gb-titanyum-gri-samsung-turkiye-garantili-p-889950713"),
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-s25-ultra-12gb-ram-512gb-titanyum-gece-siyahi-p-925936926"),
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-s25-ultra-512-gb-titanyum-gumus-samsung-turkiye-garantili-p-889950711"),
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-s25-ultra-1-tb-titanyum-siyah-samsung-turkiye-garantili-p-889950717"),
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-s25-ultra-256gb-titanium-gray-p-897458120"),
    # Samsung S24 Ultra
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-s24-ultra-512-gb-titanyum-siyah-samsung-turkiye-garantili-p-792557587"),
    # Samsung Z Serisi
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-z-fold6-1-tb-pembe-cep-telefonu-samsung-turkiye-garantili-p-838658388"),
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-z-fold6-512-gb-gumus-cep-telefonu-samsung-turkiye-garantili-p-838658387"),
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-z-flip6-256-gb-mavi-cep-telefonu-samsung-turkiye-garantili-p-838658399"),
    ("Telefon", "https://www.trendyol.com/samsung/galaxy-z-flip6-256-gb-mint-yesili-cep-telefonu-samsung-turkiye-garantili-p-838658396"),
    # MacBook
    ("Bilgisayar", "https://www.trendyol.com/apple/macbook-air-m3-16gb-256gb-ssd-macos-13-tasinabilir-bilgisayar-uzay-grisi-mc8g4tu-a-p-871069133"),
    # iPad
    ("Tablet", "https://www.trendyol.com/apple/ipad-air-6-nesil-m2-wi-fi-11-inc-128gb-mor-muwf3tu-a-p-828871818"),
    # Apple Watch
    ("Akilli Saat", "https://www.trendyol.com/apple/watch-series-10-46mm-natural-titanyum-kasa-siyah-naylon-kordon-akilli-saat-mqdy3tu-a-p-880069401"),
    # Sony Kulaklık
    ("Kulaklik", "https://www.trendyol.com/sony/wh-1000xm5-tamamen-kablosuz-gurultu-engelleme-ozellikli-kulaklik-siyah-p-312097758"),
    ("Kulaklik", "https://www.trendyol.com/sony/wh-1000xm5-tamamen-kablosuz-gurultu-engelleme-ozellikli-kulaklik-gumus-p-312102332"),
    ("Kulaklik", "https://www.trendyol.com/sony/wf-1000xm5-kablosuz-gurultu-onleyici-kulak-ici-bluetooth-kulaklik-siyah-p-879878726"),
    # Samsung Watch
    ("Akilli Saat", "https://www.trendyol.com/samsung/galaxy-watch7-gumus-44mm-p-838640814"),
    ("Akilli Saat", "https://www.trendyol.com/samsung/galaxy-watch7-yesil-44mm-p-838640813"),
    ("Akilli Saat", "https://www.trendyol.com/samsung/galaxy-watch-ultra-lte-47mm-titanyum-akilli-saat-p-861548711"),
    ("Akilli Saat", "https://www.trendyol.com/samsung/galaxy-watch-ultra-47mm-e-sim-titanyum-gri-akilli-saat-p-851389269"),
    ("Akilli Saat", "https://www.trendyol.com/samsung/galaxy-watch-ultra-akilli-saat-samsung-turkiye-garantili-p-882669414"),
    # Samsung TV
    ("Televizyon", "https://www.trendyol.com/samsung/65q70d-65-qled-4k-tizen-os-smart-tv-2024-p-862742117"),
    ("Televizyon", "https://www.trendyol.com/samsung/65qn90d-65-neo-qled-4k-tizen-os-smart-tv-2024-p-828113455"),
    ("Televizyon", "https://www.trendyol.com/samsung/65-qled-4k-q80d-tizen-os-smart-tv-2024-p-837776135"),
    ("Televizyon", "https://www.trendyol.com/samsung/65-inc-neo-qled-4k-qn85d-tizen-os-smart-televizyon-p-828852418"),
    ("Televizyon", "https://www.trendyol.com/samsung/65q60d-4k-ultra-hd-65-165-ekran-uydu-alicili-smart-qled-tv-p-833690927"),
    ("Televizyon", "https://www.trendyol.com/samsung/75qn90d-75-neo-qled-4k-tizen-os-akilli-tv-2024-p-828105799"),
    # Dyson
    ("Ev Aleti", "https://www.trendyol.com/dyson/v15-detect-absolute-kablosuz-supurge-p-757252727"),
    ("Ev Aleti", "https://www.trendyol.com/dyson/v15-detect-total-clean-kablosuz-supurge-p-776885643"),
    ("Ev Aleti", "https://www.trendyol.com/dyson/v15-detect-absolute-kablosuz-supurge-sarjli-369535-01-p-143679407"),
    ("Ev Aleti", "https://www.trendyol.com/dyson/v15s-detect-submarine-islak-ve-kuru-temizleme-ozellikli-kablosuz-supurge-p-804140693"),
    # PlayStation 5
    ("Oyun Konsolu", "https://www.trendyol.com/sony/playstation-5-slim-digital-ithalatci-garantili-2-dualsense-sarj-istasyonu-p-800623487"),
    ("Oyun Konsolu", "https://www.trendyol.com/sony/playstation-5-slim-digital-1-tb-p-796044855"),
    # Kamera
    ("Kamera", "https://www.trendyol.com/sony/a7-iii-full-frame-govde-alpha-a7m3-p-3000206"),
]

CATEGORY_SLUG = {
    "Telefon":       "telefon",
    "Bilgisayar":    "bilgisayar",
    "Tablet":        "tablet",
    "Televizyon":    "televizyon",
    "Ev Aleti":      "ev-aleti",
    "Akilli Saat":   "akilli-saat",
    "Oyun Konsolu":  "oyun-konsolu",
    "Kamera":        "kamera",
    "Kulaklik":      "kulaklik",
}

# ─── Trendyol Scraper (app'e bağımsız) ───────────────────────────────────────

async def scrape_trendyol(url: str) -> dict:
    """ld+json'dan ürün bilgisi parse eder."""
    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Referer": "https://www.trendyol.com/",
    }

    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    matches = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL
    )

    product_data = {}
    webpage_data = {}
    for raw in matches:
        try:
            d = json.loads(raw.strip())
            if d.get("@type") in ("ProductGroup", "Product"):
                product_data = d
                break
            if d.get("@type") == "WebPage" and not webpage_data:
                webpage_data = d
        except Exception:
            continue

    # WebPage fallback: fiyatı JS state'den çek
    if not product_data and webpage_data:
        # discountedPrice: {"value": 26999, ...}
        price_m = re.search(r'"discountedPrice"\s*:\s*\{"value"\s*:\s*(\d+)', html)
        orig_m = re.search(r'"originalPrice"\s*:\s*\{"value"\s*:\s*(\d+)', html)
        image_m = webpage_data.get("primaryImageOfPage", "")
        if price_m:
            title = webpage_data.get("name", "").strip()
            brand = None
            image_url = image_m if isinstance(image_m, str) else None
            current_price = Decimal(price_m.group(1))
            original_price = Decimal(orig_m.group(1)) if orig_m else None
            if original_price and original_price <= current_price:
                original_price = None
            discount_pct = None
            if original_price and current_price and original_price > current_price:
                discount_pct = round((1 - float(current_price) / float(original_price)) * 100)
            in_stock = True
            m = re.search(r"-p-(\d+)", url)
            store_product_id = m.group(1) if m else None
            return {
                "title": title,
                "brand": brand,
                "image_url": image_url,
                "current_price": current_price,
                "original_price": original_price,
                "discount_percent": discount_pct,
                "in_stock": in_stock,
                "store_product_id": store_product_id,
            }
        raise ValueError("ld+json bulunamadı (WebPage - fiyat yok)")

    if not product_data:
        raise ValueError("ld+json bulunamadı")

    title = product_data.get("name", "").strip()
    brand = (product_data.get("manufacturer") or
             (product_data.get("brand") or {}).get("name"))

    # Görsel
    image_raw = product_data.get("image", {})
    image_url = None
    if isinstance(image_raw, dict):
        content_urls = image_raw.get("contentUrl", [])
        image_url = content_urls[0] if content_urls else None
    elif isinstance(image_raw, str):
        image_url = image_raw

    # Fiyat
    offers = product_data.get("offers", {})
    current_price = Decimal(str(offers.get("price", 0) or 0))
    original_price = None
    high_price = offers.get("highPrice")
    if high_price and Decimal(str(high_price)) > current_price:
        original_price = Decimal(str(high_price))

    # İndirim %
    discount_pct = None
    if original_price and current_price and original_price > current_price:
        discount_pct = round((1 - float(current_price) / float(original_price)) * 100)

    # Stok
    availability = offers.get("availability", "")
    in_stock = "OutOfStock" not in availability

    # Store product ID
    m = re.search(r"-p-(\d+)", url)
    store_product_id = m.group(1) if m else None

    return {
        "title": title,
        "brand": brand,
        "image_url": image_url,
        "current_price": current_price,
        "original_price": original_price,
        "discount_percent": discount_pct,
        "in_stock": in_stock,
        "store_product_id": store_product_id,
    }

# ─── Ana seed fonksiyonu ───────────────────────────────────────────────────────

def main():
    try:
        import psycopg
    except ImportError:
        try:
            import psycopg2 as psycopg
        except ImportError:
            print("ERROR: psycopg veya psycopg2 yüklü değil.")
            print("Çalıştır: pip3 install psycopg2-binary")
            sys.exit(1)

    print(f"Veritabanına bağlanılıyor...")
    conn = psycopg.connect(DB_URL)
    print(f"Bağlandı. {len(URLS)} ürün eklenecek.\n")

    # Kategorileri oluştur
    cat_map = {}
    with conn.cursor() as cur:
        for cat_name, slug in CATEGORY_SLUG.items():
            cur.execute(
                "INSERT INTO categories (id, name, slug) VALUES (%s, %s, %s) "
                "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                (str(uuid.uuid4()), cat_name, slug)
            )
            row = cur.fetchone()
            cat_map[cat_name] = str(row[0])
    conn.commit()
    print(f"Kategoriler hazır: {list(CATEGORY_SLUG.keys())}\n")

    inserted = 0
    skipped = 0
    failed = 0

    for idx, (category, url) in enumerate(URLS, 1):
        print(f"[{idx}/{len(URLS)}] {url[-60:]}...")

        # Zaten var mı?
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM product_stores WHERE url = %s", (url,))
            if cur.fetchone():
                print(f"  ↷ Zaten var, atlandı.")
                skipped += 1
                continue

        # Scrape et
        try:
            data = asyncio.run(scrape_trendyol(url))
        except Exception as e:
            print(f"  ✗ Scraping hatası: {e}")
            failed += 1
            import time; time.sleep(3)
            continue

        if not data["current_price"] or data["current_price"] <= 0:
            print(f"  ✗ Fiyat alınamadı.")
            failed += 1
            continue

        # DB'ye kaydet
        try:
            with conn.cursor() as cur:
                product_id = str(uuid.uuid4())
                cat_id = cat_map.get(category)
                cur.execute(
                    "INSERT INTO products (id, title, brand, image_url, category_id, lowest_price_ever, alarm_count) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 0) RETURNING id",
                    (product_id, data["title"], data["brand"], data["image_url"],
                     cat_id, data["current_price"])
                )
                row = cur.fetchone()
                actual_id = str(row[0])

                store_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO product_stores "
                    "(id, product_id, store, store_product_id, url, current_price, original_price, "
                    "currency, discount_percent, in_stock, is_active) "
                    "VALUES (%s, %s, 'TRENDYOL'::store_name_enum, %s, %s, %s, %s, 'TRY', %s, %s, true) "
                    "ON CONFLICT (url) DO NOTHING",
                    (store_id, actual_id, data["store_product_id"], url,
                     data["current_price"], data["original_price"],
                     data["discount_percent"], data["in_stock"])
                )

                history_id = str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO price_history (id, product_store_id, price, original_price, in_stock, currency) "
                    "VALUES (%s, %s, %s, %s, %s, 'TRY')",
                    (history_id, store_id, data["current_price"],
                     data["original_price"], data["in_stock"])
                )
            conn.commit()
            inserted += 1
            price_str = f"{int(data['current_price']):,}".replace(",", ".") + " ₺"
            print(f"  ✓ {data['title'][:55]} — {price_str}")
        except Exception as e:
            conn.rollback()
            print(f"  ✗ DB hatası: {e}")
            failed += 1

        import time; time.sleep(2.5)

    conn.close()
    print(f"\n{'='*50}")
    print(f"Tamamlandı!")
    print(f"  ✓ Eklendi : {inserted}")
    print(f"  ↷ Atlandı : {skipped}")
    print(f"  ✗ Hata    : {failed}")


if __name__ == "__main__":
    main()
