"""
update_images.py — Trendyol ürün sayfalarından gerçek CDN image URL'lerini çeker
ve Supabase'deki products tablosunu günceller.

Kullanım:
    cd backend && pip install requests beautifulsoup4 && python update_images.py
"""

import os
import re
import sys
import time
import uuid

def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

load_env()

try:
    import requests
except ImportError:
    print("Eksik: pip install requests")
    sys.exit(1)

try:
    import psycopg
except ImportError:
    print("Eksik: pip install psycopg[binary]")
    sys.exit(1)

raw_url = os.environ.get("DATABASE_URL", "")
if not raw_url:
    print("ERROR: DATABASE_URL yok")
    sys.exit(1)

db_url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)
db_url = re.sub(r"^postgresql\+psycopg://", "postgresql://", db_url)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Ürün adı → Trendyol URL eşlemesi
PRODUCTS = [
    ("iPhone 15 Pro 128 GB Siyah Titanyum", "https://www.trendyol.com/apple/iphone-15-pro-128-gb-siyah-titanyum-p-762254849"),
    ("iPhone 15 Pro Max 256 GB Siyah Titanyum", "https://www.trendyol.com/apple/iphone-15-pro-max-256-gb-siyah-titanyum-p-762254852"),
    ("Samsung Galaxy S24 128 GB", "https://www.trendyol.com/samsung/galaxy-s24-128-gb-cep-telefonu-siyah-p-806345791"),
    ("Samsung Galaxy S24 Ultra 256 GB", "https://www.trendyol.com/samsung/galaxy-s24-ultra-256-gb-siyah-p-806345798"),
    ("MacBook Air M2 8GB 256GB", "https://www.trendyol.com/apple/macbook-air-m2-cip-8gb-256gb-ssd-uzay-grisi-p-680576633"),
    ("MacBook Pro M3 14 inç", "https://www.trendyol.com/apple/macbook-pro-m3-14-inc-8gb-1tb-ssd-uzay-siyahi-p-791893654"),
    ("iPad Pro 11 inç M4 256GB", "https://www.trendyol.com/apple/ipad-pro-11-inc-m4-256gb-wifi-uzay-siyahi-p-889284958"),
    ("iPad Air M2 11 inç 128GB", "https://www.trendyol.com/apple/ipad-air-m2-11-inc-128gb-wifi-mavi-p-889284960"),
    ("Apple Watch Series 9 45mm", "https://www.trendyol.com/apple/watch-series-9-gps-45mm-pembe-aluminyum-kasa-p-791893645"),
    ("Apple Watch Ultra 2", "https://www.trendyol.com/apple/watch-ultra-2-49-mm-titanyum-p-791893647"),
    ("AirPods Pro 2. Nesil", "https://www.trendyol.com/apple/airpods-pro-2-nesil-p-124853508"),
    ("AirPods Max", "https://www.trendyol.com/apple/airpods-max-uzay-grisi-p-124853509"),
    ("Sony WH-1000XM5 Kulaklik", "https://www.trendyol.com/sony/wh-1000xm5-kulakustu-bluetooth-kulaklik-siyah-p-377014944"),
    ("Samsung Galaxy Watch 6 Classic 47mm", "https://www.trendyol.com/samsung/galaxy-watch6-classic-47mm-akilli-saat-siyah-p-726367553"),
    ("Sony PlayStation 5 Slim", "https://www.trendyol.com/sony/playstation-5-slim-p-795202574"),
    ("Xbox Series X", "https://www.trendyol.com/microsoft/xbox-series-x-p-63502679"),
    ("Nintendo Switch OLED", "https://www.trendyol.com/nintendo/switch-oled-model-beyaz-p-92286761"),
    ("Samsung 55 QLED 4K TV", "https://www.trendyol.com/samsung/55-q60d-qled-4k-smart-tv-p-871218685"),
    ("LG OLED 55 C3 TV", "https://www.trendyol.com/lg/55-c3-oled-evo-4k-smart-tv-p-726367550"),
    ("Samsung 65 Neo QLED TV", "https://www.trendyol.com/samsung/65-qn85d-neo-qled-4k-smart-tv-p-871218690"),
    ("Dyson V15 Detect Supurge", "https://www.trendyol.com/dyson/v15-detect-absolute-sarjli-supurge-p-457606241"),
    ("Dyson V12 Detect Slim", "https://www.trendyol.com/dyson/v12-detect-slim-absolute-sarjli-supurge-p-457606239"),
    ("Xiaomi Robot Supurge X10+", "https://www.trendyol.com/xiaomi/robot-supurge-x10-p-599789877"),
    ("iRobot Roomba j7+", "https://www.trendyol.com/irobot/roomba-j7-plus-robot-supurge-p-377014946"),
    ("DeLonghi Dedica Espresso Makinesi", "https://www.trendyol.com/delonghi/dedica-style-ec885m-espresso-makinesi-p-116853408"),
    ("Nespresso Vertuo Next", "https://www.trendyol.com/nespresso/vertuo-next-kahve-makinesi-p-116853409"),
    ("Philips Airfryer 3000 Series XL", "https://www.trendyol.com/philips/airfryer-3000-series-xl-hd9270-90-p-233891584"),
    ("Tefal Easy Fry XXL Airfryer", "https://www.trendyol.com/tefal/easy-fry-xxl-ey801d-airfryer-p-233891586"),
    ("Bosch Serie 6 Camasir Makinesi 9kg", "https://www.trendyol.com/bosch/serie-6-9-kg-1400-devir-camasir-makinesi-p-116853410"),
    ("Samsung WW90T Camasir Makinesi", "https://www.trendyol.com/samsung/ww90t-camasir-makinesi-p-116853411"),
    ("Mitsubishi Electric 12000 BTU Klima", "https://www.trendyol.com/mitsubishi-electric/12000-btu-klima-p-116853412"),
    ("Daikin 12000 BTU Klima", "https://www.trendyol.com/daikin/12000-btu-a-enerji-sinifi-inverter-klima-p-116853413"),
    ("Samsung Cift Kapili No Frost Buzdolabi", "https://www.trendyol.com/samsung/rt50k6340bs-no-frost-buzdolabi-p-116853414"),
    ("Bosch Bulasik Makinesi Serie 4", "https://www.trendyol.com/bosch/serie-4-smi4hvs41e-bulasik-makinesi-p-116853415"),
    ("Asus ROG Strix G16 Gaming Laptop", "https://www.trendyol.com/asus/rog-strix-g16-g614ji-n3220-gaming-laptop-p-726367555"),
    ("Lenovo ThinkPad X1 Carbon", "https://www.trendyol.com/lenovo/thinkpad-x1-carbon-gen-12-laptop-p-726367556"),
    ("HP Spectre x360 14", "https://www.trendyol.com/hp/spectre-x360-14-ef2013dx-laptop-p-726367557"),
    ("Dell XPS 15 OLED", "https://www.trendyol.com/dell/xps-15-9530-laptop-p-726367558"),
    ("Xiaomi 14 256GB", "https://www.trendyol.com/xiaomi/14-256gb-siyah-cep-telefonu-p-806345800"),
    ("Google Pixel 9 Pro", "https://www.trendyol.com/google/pixel-9-pro-256gb-obsidyan-p-889284962"),
    ("Samsung Galaxy Z Fold 5", "https://www.trendyol.com/samsung/galaxy-z-fold5-256gb-siyah-p-726367560"),
    ("Samsung Galaxy Z Flip 5", "https://www.trendyol.com/samsung/galaxy-z-flip5-256gb-mint-p-726367561"),
    ("OnePlus 12 256GB", "https://www.trendyol.com/oneplus/12-256gb-siyah-p-806345802"),
    ("Sony Xperia 1 V", "https://www.trendyol.com/sony/xperia-1-v-256gb-siyah-p-726367562"),
    ("DJI Mini 4 Pro Drone", "https://www.trendyol.com/dji/mini-4-pro-drone-p-791893649"),
    ("DJI Air 3 Drone", "https://www.trendyol.com/dji/air-3-drone-p-791893650"),
    ("Sony A7 IV Ayinasiz Fotograf Makinesi", "https://www.trendyol.com/sony/a7-iv-body-aynasiz-fotograf-makinesi-p-377014948"),
    ("Canon EOS R50 Kit", "https://www.trendyol.com/canon/eos-r50-18-45mm-kit-aynasiz-fotograf-makinesi-p-599789879"),
    ("GoPro Hero 12 Black", "https://www.trendyol.com/gopro/hero12-black-aksiyon-kamerasi-p-726367563"),
    ("Samsung Galaxy Tab S9 FE", "https://www.trendyol.com/samsung/galaxy-tab-s9-fe-128gb-wifi-p-791893651"),
    ("Samsung Galaxy Tab S9 Ultra", "https://www.trendyol.com/samsung/galaxy-tab-s9-ultra-256gb-wifi-p-726367565"),
    ("Microsoft Surface Pro 9", "https://www.trendyol.com/microsoft/surface-pro-9-i5-8gb-256gb-p-599789881"),
    ("Beats Studio Pro Kulaklik", "https://www.trendyol.com/beats/studio-pro-kulaklik-siyah-p-599789882"),
    ("Bose QuietComfort 45", "https://www.trendyol.com/bose/quietcomfort-45-kulaklik-siyah-p-377014950"),
    ("JBL Charge 5 Bluetooth Hoparlor", "https://www.trendyol.com/jbl/charge-5-tasinabilir-bluetooth-hoparlor-p-233891590"),
    ("Sonos Era 100", "https://www.trendyol.com/sonos/era-100-akilli-hoparlor-p-599789884"),
    ("Xiaomi Mi Band 8 Pro", "https://www.trendyol.com/xiaomi/mi-band-8-pro-akilli-bileklik-p-791893652"),
    ("Garmin Forerunner 265", "https://www.trendyol.com/garmin/forerunner-265-gps-akilli-saat-p-726367567"),
    ("Amazfit GTR 4", "https://www.trendyol.com/amazfit/gtr-4-akilli-saat-p-599789886"),
    ("Asus ROG Ally Oyun Konsolu", "https://www.trendyol.com/asus/rog-ally-rc71l-z1-extreme-oyun-konsolu-p-791893653"),
    ("Steam Deck OLED 512GB", "https://www.trendyol.com/valve/steam-deck-oled-512gb-p-791893654"),
    ("LG 27 UltraGear 4K Gaming Monitor", "https://www.trendyol.com/lg/27gp950-b-27-4k-nano-ips-144hz-gaming-monitor-p-377014952"),
    ("Samsung 32 Odyssey G7 Monitor", "https://www.trendyol.com/samsung/32-odyssey-g7-ls32bg700exuf-monitor-p-599789888"),
    ("Logitech MX Master 3S Mouse", "https://www.trendyol.com/logitech/mx-master-3s-kablosuz-mouse-p-599789889"),
    ("Apple Magic Keyboard", "https://www.trendyol.com/apple/magic-keyboard-turkce-q-p-116853420"),
    ("Philips Lumea IPL Epilasyon Cihazi", "https://www.trendyol.com/philips/lumea-ipl-8000-serisi-bri945-00-p-377014954"),
    ("Dyson Airwrap Sac Sekillendirici", "https://www.trendyol.com/dyson/airwrap-multi-styler-complete-long-p-457606243"),
    ("Dyson Supersonic Sac Kurutma Makinesi", "https://www.trendyol.com/dyson/supersonic-sac-kurutma-makinesi-p-116853422"),
    ("Oral-B iO Series 9 Dis Fircasi", "https://www.trendyol.com/oral-b/io-series-9-siyah-onyx-elektrikli-dis-fircasi-p-233891594"),
    ("Philips OneBlade Pro Tiras Makinesi", "https://www.trendyol.com/philips/oneblade-pro-qp6550-15-tiras-makinesi-p-233891595"),
    ("Bosch TDS4080 Buharlı Utu", "https://www.trendyol.com/bosch/tds4080-sensixx-x-da80-3100w-buharli-utu-p-116853424"),
    ("Tefal Ingenio Unlimited Tencere Seti", "https://www.trendyol.com/tefal/ingenio-unlimited-tencere-seti-p-233891597"),
    ("Xiaomi Mi 4K Laser Projektor", "https://www.trendyol.com/xiaomi/mi-smart-projector-2-pro-4k-lazer-projektor-p-457606245"),
    ("Epson EH-TW7000 Projeksiyon", "https://www.trendyol.com/epson/eh-tw7000-3lcd-4k-pro-uhd-projeksiyon-cihazi-p-457606246"),
    ("Samsung The Frame 55 TV", "https://www.trendyol.com/samsung/55-the-frame-ls55a-4k-art-mode-tv-p-233891599"),
    ("LG 65 OLED evo C4 TV", "https://www.trendyol.com/lg/65-c4-oled-evo-4k-smart-tv-p-889284964"),
    ("Philips 65 Ambilight TV", "https://www.trendyol.com/philips/65pus8349-65-4k-ambilight-smart-tv-p-871218692"),
    ("Asus ZenBook 14 OLED", "https://www.trendyol.com/asus/zenbook-14-oled-um3402ya-laptop-p-726367568"),
    ("Lenovo IdeaPad Slim 5 16", "https://www.trendyol.com/lenovo/ideapad-slim-5-16irl8-laptop-p-791893655"),
    ("MSI Raider GE78 Gaming Laptop", "https://www.trendyol.com/msi/raider-ge78-hx-13vi-gaming-laptop-p-791893656"),
    ("Huawei MateBook X Pro", "https://www.trendyol.com/huawei/matebook-x-pro-2024-laptop-p-889284966"),
    ("Anker 737 Tasinabilir Sarj Cihazi", "https://www.trendyol.com/anker/737-power-bank-24000mah-p-457606247"),
    ("Belkin BoostCharge Pro 3u1 Arada", "https://www.trendyol.com/belkin/boostcharge-pro-3u1-arada-kablosuz-sarj-p-599789891"),
    ("Samsung 2TB T9 Tasinabilir SSD", "https://www.trendyol.com/samsung/t9-2tb-tasinabilir-ssd-siyah-p-791893657"),
    ("WD My Passport 4TB", "https://www.trendyol.com/wd/my-passport-4tb-tasinabilir-disk-siyah-p-377014956"),
    ("Xiaomi 14T Pro 256GB", "https://www.trendyol.com/xiaomi/14t-pro-256gb-siyah-p-889284968"),
    ("Huawei Pura 70 Pro", "https://www.trendyol.com/huawei/pura-70-pro-256gb-siyah-p-889284969"),
    ("Nothing Phone 2a Plus", "https://www.trendyol.com/nothing/phone-2a-plus-256gb-siyah-p-889284970"),
    ("Garmin Fenix 7X Pro", "https://www.trendyol.com/garmin/fenix-7x-pro-solar-gps-akilli-saat-p-791893658"),
    ("Samsung Galaxy Ring", "https://www.trendyol.com/samsung/galaxy-ring-size-7-p-889284971"),
    ("TP-Link Deco XE75 Pro Mesh WiFi", "https://www.trendyol.com/tp-link/deco-xe75-pro-ax5400-mesh-wifi-6e-3lu-p-726367570"),
    ("Netgear Orbi RBK863S Mesh WiFi", "https://www.trendyol.com/netgear/orbi-960-rbk963s-wifi-6e-mesh-p-726367571"),
    ("Arlo Pro 5S Guvenlik Kamerasi", "https://www.trendyol.com/arlo/pro-5s-2k-guvenlik-kamerasi-p-726367572"),
    ("Philips Hue Starter Kit", "https://www.trendyol.com/philips/hue-white-color-ambiance-starter-kit-p-233891602"),
    ("Amazon Echo Show 10", "https://www.trendyol.com/amazon/echo-show-10-3-nesil-p-233891603"),
    ("Apple HomePod 2. Nesil", "https://www.trendyol.com/apple/homepod-2-nesil-gece-yarisi-p-599789894"),
    ("Xiaomi Smart Band 8 Active", "https://www.trendyol.com/xiaomi/smart-band-8-active-akilli-bileklik-p-791893660"),
    ("Fitbit Charge 6", "https://www.trendyol.com/fitbit/charge-6-akilli-bileklik-obsidyan-p-791893661"),
    ("DJI OM 6 Gimbal", "https://www.trendyol.com/dji/om-6-gimbal-p-599789896"),
    ("Insta360 X4 360 Derece Kamera", "https://www.trendyol.com/insta360/x4-360-derece-aksiyon-kamerasi-p-889284973"),
]


SEARCH_API = "https://public.trendyol.com/discovery-web-searchgw-service/api/filter/v2"


def get_image_url_via_api(product_title: str):
    """Trendyol arama API'si üzerinden ürün görselini bulur."""
    try:
        resp = requests.get(
            SEARCH_API,
            params={"q": product_title, "pi": 1, "psize": 3},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        products = (
            data.get("result", {}).get("products", [])
            or data.get("products", [])
            or []
        )
        for p in products:
            imgs = p.get("images", []) or []
            if imgs:
                url = imgs[0]
                if not url.startswith("http"):
                    url = "https://cdn.dsmcdn.com" + url
                return url
            img = p.get("imageUrl", "") or p.get("image", "")
            if img:
                if not img.startswith("http"):
                    img = "https://cdn.dsmcdn.com" + img
                return img
    except Exception as e:
        print(f"  API hata: {e}")
    return None


def get_image_url_via_page(product_url: str):
    """Yedek: Trendyol ürün sayfasından og:image çeker."""
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        # og:image meta tag
        match = re.search(r'og:image["\s]+content="(https://cdn\.dsmcdn\.com/[^"]+)"', resp.text)
        if match:
            return match.group(1)

        # ty.../org_zoom.jpg pattern in HTML/JSON
        match = re.search(
            r'https://cdn\.dsmcdn\.com/ty\d+/[^"\'\\<>\s]+_org_zoom\.jpg',
            resp.text,
        )
        if match:
            return match.group(0)

    except Exception as e:
        print(f"  Sayfa hata: {e}")
    return None


def main():
    print("Veritabanına bağlanılıyor...")
    conn = psycopg.connect(db_url)
    print(f"Bağlandı. {len(PRODUCTS)} ürün işlenecek.\n")

    updated = 0
    failed = 0

    with conn:
        with conn.cursor() as cur:
            for i, (title, trendyol_url) in enumerate(PRODUCTS, 1):
                print(f"[{i:03d}/{len(PRODUCTS)}] {title[:45]}")

                # Önce arama API'si, başarısız olursa ürün sayfası
                image_url = get_image_url_via_api(title) or get_image_url_via_page(trendyol_url)
                if image_url:
                    cur.execute(
                        "UPDATE products SET image_url = %s WHERE title = %s",
                        (image_url, title)
                    )
                    rows = cur.rowcount
                    if rows > 0:
                        print(f"  ✓ Güncellendi: {image_url[:70]}")
                        updated += 1
                    else:
                        print(f"  ⚠ Ürün DB'de bulunamadı")
                        failed += 1
                else:
                    print(f"  ✗ Görsel URL bulunamadı")
                    failed += 1

                # Rate limit'e takılmamak için kısa bekleme
                time.sleep(0.5)

    print(f"\n=== Tamamlandı: {updated} güncellendi, {failed} atlandı ===")
    conn.close()


if __name__ == "__main__":
    main()
