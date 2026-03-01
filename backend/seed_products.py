"""
Seed script: 100 ürünü veritabanına ekler.
Kullanım:
    DATABASE_URL=postgresql://user:pass@host/db python seed_products.py
veya backend/.env içinde DATABASE_URL tanımlıysa doğrudan çalıştır.
"""

import os
import sys
import uuid
import re
from decimal import Decimal

# .env dosyasını oku (varsa)
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
    print("Örnek: DATABASE_URL=postgresql://user:pass@host:5432/db python seed_products.py")
    sys.exit(1)

# asyncpg / SQLAlchemy URL'sini psycopg3 formatına dönüştür
db_url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw_url)
db_url = re.sub(r"^postgresql\+psycopg://", "postgresql://", db_url)

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg yüklü değil. Çalıştır: pip install psycopg[binary]")
    sys.exit(1)

# ─── Ürün verisi ──────────────────────────────────────────────────────────────

PRODUCTS = [
    ("iPhone 15 Pro 128 GB Siyah Titanyum", "Apple", "Telefon", 72000, "https://www.trendyol.com/apple/iphone-15-pro-128-gb-siyah-titanyum-p-762254849", "https://cdn.dsmcdn.com/ty935/product/media/images/20230921/10/404428431/955217734/1/1_org_zoom.jpg"),
    ("iPhone 15 Pro Max 256 GB Siyah Titanyum", "Apple", "Telefon", 95000, "https://www.trendyol.com/apple/iphone-15-pro-max-256-gb-siyah-titanyum-p-762254852", "https://cdn.dsmcdn.com/ty935/product/media/images/20230921/10/404428433/955217736/1/1_org_zoom.jpg"),
    ("Samsung Galaxy S24 128 GB", "Samsung", "Telefon", 28000, "https://www.trendyol.com/samsung/galaxy-s24-128-gb-x-c103498", "https://cdn.dsmcdn.com/ty1132/product/media/images/prod/SPM/PIM/20240117/17/2b9e4b4b-8c8e-38f9-b12f-7f2de3b2b2f4/1_org_zoom.jpg"),
    ("Samsung Galaxy S24 Ultra 256 GB", "Samsung", "Telefon", 58000, "https://www.trendyol.com/samsung/galaxy-s24-ultra-256-gb-x-c103498", "https://cdn.dsmcdn.com/ty1132/product/media/images/prod/SPM/PIM/20240117/17/s24ultra.jpg"),
    ("MacBook Air M2 8GB 256GB", "Apple", "Bilgisayar", 42000, "https://www.trendyol.com/apple/macbook-air-m2-x-c104759", "https://cdn.dsmcdn.com/ty1012/product/media/images/20230601/macbookairm2.jpg"),
    ("MacBook Pro M3 14 inç", "Apple", "Bilgisayar", 85000, "https://www.trendyol.com/apple/macbook-pro-m3-14-x-c104759", "https://cdn.dsmcdn.com/macbookprom3.jpg"),
    ("iPad Pro 11 inç M4 256GB", "Apple", "Tablet", 45000, "https://www.trendyol.com/apple/ipad-pro-11-m4-x-c104760", "https://cdn.dsmcdn.com/ipadprom4.jpg"),
    ("iPad Air M2 11 inç 128GB", "Apple", "Tablet", 28000, "https://www.trendyol.com/apple/ipad-air-m2-x-c104760", "https://cdn.dsmcdn.com/ipadairm2.jpg"),
    ("Apple Watch Series 9 45mm", "Apple", "Akilli Saat", 18000, "https://www.trendyol.com/apple/watch-series-9-45mm-x-c104761", "https://cdn.dsmcdn.com/applewatchs9.jpg"),
    ("Apple Watch Ultra 2", "Apple", "Akilli Saat", 35000, "https://www.trendyol.com/apple/watch-ultra-2-x-c104761", "https://cdn.dsmcdn.com/applewatchultra2.jpg"),
    ("AirPods Pro 2. Nesil", "Apple", "Kulaklik", 9500, "https://www.trendyol.com/apple/airpods-pro-2-nesil-p-124853508", "https://cdn.dsmcdn.com/airpodspro2.jpg"),
    ("AirPods Max", "Apple", "Kulaklik", 22000, "https://www.trendyol.com/apple/airpods-max-x-c104762", "https://cdn.dsmcdn.com/airpodsmax.jpg"),
    ("Sony WH-1000XM5 Kulaklik", "Sony", "Kulaklik", 9000, "https://www.trendyol.com/sony/wh-1000xm5-x-c104762", "https://cdn.dsmcdn.com/sonywh1000xm5.jpg"),
    ("Samsung Galaxy Watch 6 Classic 47mm", "Samsung", "Akilli Saat", 12000, "https://www.trendyol.com/samsung/galaxy-watch-6-classic-47mm-x-c104761", "https://cdn.dsmcdn.com/galaxywatch6classic.jpg"),
    ("Sony PlayStation 5 Slim", "Sony", "Oyun Konsolu", 22000, "https://www.trendyol.com/sony/playstation-5-slim-x-c104763", "https://cdn.dsmcdn.com/ps5slim.jpg"),
    ("Xbox Series X", "Microsoft", "Oyun Konsolu", 18000, "https://www.trendyol.com/microsoft/xbox-series-x-x-c104763", "https://cdn.dsmcdn.com/xboxseriesx.jpg"),
    ("Nintendo Switch OLED", "Nintendo", "Oyun Konsolu", 14000, "https://www.trendyol.com/nintendo/switch-oled-x-c104763", "https://cdn.dsmcdn.com/nintendoswitcholed.jpg"),
    ("Samsung 55 QLED 4K TV", "Samsung", "Televizyon", 28000, "https://www.trendyol.com/samsung/55-qled-4k-tv-x-c104764", "https://cdn.dsmcdn.com/samsung55qled.jpg"),
    ("LG OLED 55 C3 TV", "LG", "Televizyon", 45000, "https://www.trendyol.com/lg/oled-55-c3-x-c104764", "https://cdn.dsmcdn.com/lgoled55c3.jpg"),
    ("Samsung 65 Neo QLED TV", "Samsung", "Televizyon", 55000, "https://www.trendyol.com/samsung/65-neo-qled-x-c104764", "https://cdn.dsmcdn.com/samsung65neoqled.jpg"),
    ("Dyson V15 Detect Supurge", "Dyson", "Ev Aleti", 22000, "https://www.trendyol.com/dyson/v15-detect-x-c104765", "https://cdn.dsmcdn.com/dysonv15.jpg"),
    ("Dyson V12 Detect Slim", "Dyson", "Ev Aleti", 16000, "https://www.trendyol.com/dyson/v12-detect-slim-x-c104765", "https://cdn.dsmcdn.com/dysonv12.jpg"),
    ("Xiaomi Robot Supurge X10+", "Xiaomi", "Ev Aleti", 14000, "https://www.trendyol.com/xiaomi/robot-supurge-x10-x-c104765", "https://cdn.dsmcdn.com/xiaomirobotx10.jpg"),
    ("iRobot Roomba j7+", "iRobot", "Ev Aleti", 18000, "https://www.trendyol.com/irobot/roomba-j7-x-c104765", "https://cdn.dsmcdn.com/irobotroombaj7.jpg"),
    ("DeLonghi Dedica Espresso Makinesi", "DeLonghi", "Ev Aleti", 8500, "https://www.trendyol.com/delonghi/dedica-espresso-x-c104766", "https://cdn.dsmcdn.com/delonghidedica.jpg"),
    ("Nespresso Vertuo Next", "Nespresso", "Ev Aleti", 7500, "https://www.trendyol.com/nespresso/vertuo-next-x-c104766", "https://cdn.dsmcdn.com/nespressovertuonext.jpg"),
    ("Philips Airfryer 3000 Series XL", "Philips", "Ev Aleti", 6500, "https://www.trendyol.com/philips/airfryer-3000-xl-x-c104766", "https://cdn.dsmcdn.com/philipsairfryer3000.jpg"),
    ("Tefal Easy Fry XXL Airfryer", "Tefal", "Ev Aleti", 5500, "https://www.trendyol.com/tefal/easy-fry-xxl-x-c104766", "https://cdn.dsmcdn.com/tefaleasyfrxxxl.jpg"),
    ("Bosch Serie 6 Camasir Makinesi 9kg", "Bosch", "Beyaz Esya", 22000, "https://www.trendyol.com/bosch/serie-6-camasir-makinesi-9kg-x-c104767", "https://cdn.dsmcdn.com/boschserie6.jpg"),
    ("Samsung WW90T Camasir Makinesi", "Samsung", "Beyaz Esya", 18000, "https://www.trendyol.com/samsung/ww90t-camasir-makinesi-x-c104767", "https://cdn.dsmcdn.com/samsungww90t.jpg"),
    ("Mitsubishi Electric 12000 BTU Klima", "Mitsubishi", "Beyaz Esya", 32000, "https://www.trendyol.com/mitsubishi/12000-btu-klima-x-c104768", "https://cdn.dsmcdn.com/mitsubishiklima.jpg"),
    ("Daikin 12000 BTU Klima", "Daikin", "Beyaz Esya", 28000, "https://www.trendyol.com/daikin/12000-btu-klima-x-c104768", "https://cdn.dsmcdn.com/daikinklima.jpg"),
    ("Samsung Cift Kapili No Frost Buzdolabi", "Samsung", "Beyaz Esya", 35000, "https://www.trendyol.com/samsung/cift-kapili-no-frost-x-c104769", "https://cdn.dsmcdn.com/samsungbuzdolabi.jpg"),
    ("Bosch Bulasik Makinesi Serie 4", "Bosch", "Beyaz Esya", 18000, "https://www.trendyol.com/bosch/bulasik-makinesi-serie4-x-c104769", "https://cdn.dsmcdn.com/boschbulasik.jpg"),
    ("Asus ROG Strix G16 Gaming Laptop", "Asus", "Bilgisayar", 45000, "https://www.trendyol.com/asus/rog-strix-g16-x-c104770", "https://cdn.dsmcdn.com/asusrogstrixg16.jpg"),
    ("Lenovo ThinkPad X1 Carbon", "Lenovo", "Bilgisayar", 55000, "https://www.trendyol.com/lenovo/thinkpad-x1-carbon-x-c104770", "https://cdn.dsmcdn.com/lenovothinkpadx1.jpg"),
    ("HP Spectre x360 14", "HP", "Bilgisayar", 48000, "https://www.trendyol.com/hp/spectre-x360-14-x-c104770", "https://cdn.dsmcdn.com/hpspectrex360.jpg"),
    ("Dell XPS 15 OLED", "Dell", "Bilgisayar", 65000, "https://www.trendyol.com/dell/xps-15-oled-x-c104770", "https://cdn.dsmcdn.com/dellxps15oled.jpg"),
    ("Xiaomi 14 256GB", "Xiaomi", "Telefon", 28000, "https://www.trendyol.com/xiaomi/14-256gb-x-c103498", "https://cdn.dsmcdn.com/xiaomi14.jpg"),
    ("Google Pixel 9 Pro", "Google", "Telefon", 45000, "https://www.trendyol.com/google/pixel-9-pro-x-c103498", "https://cdn.dsmcdn.com/googlepixel9pro.jpg"),
    ("Samsung Galaxy Z Fold 5", "Samsung", "Telefon", 65000, "https://www.trendyol.com/samsung/galaxy-z-fold-5-x-c103498", "https://cdn.dsmcdn.com/galaxyzfold5.jpg"),
    ("Samsung Galaxy Z Flip 5", "Samsung", "Telefon", 32000, "https://www.trendyol.com/samsung/galaxy-z-flip-5-x-c103498", "https://cdn.dsmcdn.com/galaxyzflip5.jpg"),
    ("OnePlus 12 256GB", "OnePlus", "Telefon", 22000, "https://www.trendyol.com/oneplus/12-256gb-x-c103498", "https://cdn.dsmcdn.com/oneplus12.jpg"),
    ("Sony Xperia 1 V", "Sony", "Telefon", 42000, "https://www.trendyol.com/sony/xperia-1-v-x-c103498", "https://cdn.dsmcdn.com/sonyxperia1v.jpg"),
    ("DJI Mini 4 Pro Drone", "DJI", "Kamera", 22000, "https://www.trendyol.com/dji/mini-4-pro-x-c104771", "https://cdn.dsmcdn.com/djimini4pro.jpg"),
    ("DJI Air 3 Drone", "DJI", "Kamera", 32000, "https://www.trendyol.com/dji/air-3-x-c104771", "https://cdn.dsmcdn.com/djiair3.jpg"),
    ("Sony A7 IV Ayinasiz Fotograf Makinesi", "Sony", "Kamera", 75000, "https://www.trendyol.com/sony/a7-iv-x-c104771", "https://cdn.dsmcdn.com/sonya7iv.jpg"),
    ("Canon EOS R50 Kit", "Canon", "Kamera", 28000, "https://www.trendyol.com/canon/eos-r50-kit-x-c104771", "https://cdn.dsmcdn.com/canoneposr50.jpg"),
    ("GoPro Hero 12 Black", "GoPro", "Kamera", 12000, "https://www.trendyol.com/gopro/hero-12-black-x-c104771", "https://cdn.dsmcdn.com/goprohero12.jpg"),
    ("Samsung Galaxy Tab S9 FE", "Samsung", "Tablet", 14000, "https://www.trendyol.com/samsung/galaxy-tab-s9-fe-x-c104760", "https://cdn.dsmcdn.com/galaxytabs9fe.jpg"),
    ("Samsung Galaxy Tab S9 Ultra", "Samsung", "Tablet", 45000, "https://www.trendyol.com/samsung/galaxy-tab-s9-ultra-x-c104760", "https://cdn.dsmcdn.com/galaxytabs9ultra.jpg"),
    ("Microsoft Surface Pro 9", "Microsoft", "Tablet", 48000, "https://www.trendyol.com/microsoft/surface-pro-9-x-c104760", "https://cdn.dsmcdn.com/microsoftsurfacepro9.jpg"),
    ("Beats Studio Pro Kulaklik", "Beats", "Kulaklik", 8500, "https://www.trendyol.com/beats/studio-pro-x-c104762", "https://cdn.dsmcdn.com/beatsstudiopro.jpg"),
    ("Bose QuietComfort 45", "Bose", "Kulaklik", 7500, "https://www.trendyol.com/bose/quietcomfort-45-x-c104762", "https://cdn.dsmcdn.com/bosequietcomfort45.jpg"),
    ("JBL Charge 5 Bluetooth Hoparlor", "JBL", "Hoparlor", 5500, "https://www.trendyol.com/jbl/charge-5-x-c104772", "https://cdn.dsmcdn.com/jblcharge5.jpg"),
    ("Sonos Era 100", "Sonos", "Hoparlor", 12000, "https://www.trendyol.com/sonos/era-100-x-c104772", "https://cdn.dsmcdn.com/sonosera100.jpg"),
    ("Xiaomi Mi Band 8 Pro", "Xiaomi", "Akilli Saat", 5500, "https://www.trendyol.com/xiaomi/mi-band-8-pro-x-c104761", "https://cdn.dsmcdn.com/xiaomimiband8pro.jpg"),
    ("Garmin Forerunner 265", "Garmin", "Akilli Saat", 18000, "https://www.trendyol.com/garmin/forerunner-265-x-c104761", "https://cdn.dsmcdn.com/garminforerunner265.jpg"),
    ("Amazfit GTR 4", "Amazfit", "Akilli Saat", 6500, "https://www.trendyol.com/amazfit/gtr-4-x-c104761", "https://cdn.dsmcdn.com/amazfitgtr4.jpg"),
    ("Asus ROG Ally Oyun Konsolu", "Asus", "Oyun Konsolu", 22000, "https://www.trendyol.com/asus/rog-ally-x-c104763", "https://cdn.dsmcdn.com/asusrogally.jpg"),
    ("Steam Deck OLED 512GB", "Valve", "Oyun Konsolu", 28000, "https://www.trendyol.com/valve/steam-deck-oled-512gb-x-c104763", "https://cdn.dsmcdn.com/steamdeckoled.jpg"),
    ("LG 27 UltraGear 4K Gaming Monitor", "LG", "Monitor", 18000, "https://www.trendyol.com/lg/27-ultragear-4k-gaming-x-c104773", "https://cdn.dsmcdn.com/lgultragear27.jpg"),
    ("Samsung 32 Odyssey G7 Monitor", "Samsung", "Monitor", 22000, "https://www.trendyol.com/samsung/32-odyssey-g7-x-c104773", "https://cdn.dsmcdn.com/samsungodysseyg7.jpg"),
    ("Logitech MX Master 3S Mouse", "Logitech", "Aksesuar", 3500, "https://www.trendyol.com/logitech/mx-master-3s-x-c104774", "https://cdn.dsmcdn.com/logitechmxmaster3s.jpg"),
    ("Apple Magic Keyboard", "Apple", "Aksesuar", 5500, "https://www.trendyol.com/apple/magic-keyboard-x-c104774", "https://cdn.dsmcdn.com/applemagickeyboard.jpg"),
    ("Philips Lumea IPL Epilasyon Cihazi", "Philips", "Kisisel Bakim", 12000, "https://www.trendyol.com/philips/lumea-ipl-x-c104775", "https://cdn.dsmcdn.com/philipslumea.jpg"),
    ("Dyson Airwrap Sac Sekillendirici", "Dyson", "Kisisel Bakim", 18000, "https://www.trendyol.com/dyson/airwrap-x-c104775", "https://cdn.dsmcdn.com/dysonairwrap.jpg"),
    ("Dyson Supersonic Sac Kurutma Makinesi", "Dyson", "Kisisel Bakim", 14000, "https://www.trendyol.com/dyson/supersonic-x-c104775", "https://cdn.dsmcdn.com/dysonsupersonic.jpg"),
    ("Oral-B iO Series 9 Dis Fircasi", "Oral-B", "Kisisel Bakim", 5500, "https://www.trendyol.com/oral-b/io-series-9-x-c104775", "https://cdn.dsmcdn.com/oralbioseires9.jpg"),
    ("Philips OneBlade Pro Tiras Makinesi", "Philips", "Kisisel Bakim", 3500, "https://www.trendyol.com/philips/oneblade-pro-x-c104775", "https://cdn.dsmcdn.com/philipsonebladepro.jpg"),
    ("Bosch TDS4080 Buharlı Utu", "Bosch", "Ev Aleti", 5500, "https://www.trendyol.com/bosch/tds4080-buharli-utu-x-c104766", "https://cdn.dsmcdn.com/boschtds4080.jpg"),
    ("Tefal Ingenio Unlimited Tencere Seti", "Tefal", "Ev Aleti", 6500, "https://www.trendyol.com/tefal/ingenio-unlimited-x-c104766", "https://cdn.dsmcdn.com/tefaingeniounlimited.jpg"),
    ("Xiaomi Mi 4K Laser Projektor", "Xiaomi", "Ev Aleti", 22000, "https://www.trendyol.com/xiaomi/mi-4k-laser-projector-x-c104776", "https://cdn.dsmcdn.com/xiaomiprojector.jpg"),
    ("Epson EH-TW7000 Projeksiyon", "Epson", "Ev Aleti", 28000, "https://www.trendyol.com/epson/eh-tw7000-x-c104776", "https://cdn.dsmcdn.com/epsoneh-tw7000.jpg"),
    ("Samsung The Frame 55 TV", "Samsung", "Televizyon", 42000, "https://www.trendyol.com/samsung/the-frame-55-x-c104764", "https://cdn.dsmcdn.com/samsungtheframe55.jpg"),
    ("LG 65 OLED evo C4 TV", "LG", "Televizyon", 75000, "https://www.trendyol.com/lg/65-oled-evo-c4-x-c104764", "https://cdn.dsmcdn.com/lgoled65c4.jpg"),
    ("Philips 65 Ambilight TV", "Philips", "Televizyon", 32000, "https://www.trendyol.com/philips/65-ambilight-x-c104764", "https://cdn.dsmcdn.com/philips65ambilight.jpg"),
    ("Asus ZenBook 14 OLED", "Asus", "Bilgisayar", 28000, "https://www.trendyol.com/asus/zenbook-14-oled-x-c104770", "https://cdn.dsmcdn.com/asuszenbook14oled.jpg"),
    ("Lenovo IdeaPad Slim 5 16", "Lenovo", "Bilgisayar", 22000, "https://www.trendyol.com/lenovo/ideapad-slim-5-16-x-c104770", "https://cdn.dsmcdn.com/lenovoideapadslim5.jpg"),
    ("MSI Raider GE78 Gaming Laptop", "MSI", "Bilgisayar", 75000, "https://www.trendyol.com/msi/raider-ge78-x-c104770", "https://cdn.dsmcdn.com/msiraiderge78.jpg"),
    ("Huawei MateBook X Pro", "Huawei", "Bilgisayar", 45000, "https://www.trendyol.com/huawei/matebook-x-pro-x-c104770", "https://cdn.dsmcdn.com/huaweimatebookxpro.jpg"),
    ("Anker 737 Tasinabilir Sarj Cihazi", "Anker", "Aksesuar", 5500, "https://www.trendyol.com/anker/737-x-c104774", "https://cdn.dsmcdn.com/anker737.jpg"),
    ("Belkin BoostCharge Pro 3u1 Arada", "Belkin", "Aksesuar", 3500, "https://www.trendyol.com/belkin/boostcharge-pro-3u1-x-c104774", "https://cdn.dsmcdn.com/belkinboostchargepro.jpg"),
    ("Samsung 2TB T9 Tasinabilir SSD", "Samsung", "Depolama", 5500, "https://www.trendyol.com/samsung/2tb-t9-portable-ssd-x-c104774", "https://cdn.dsmcdn.com/samsungt9ssd.jpg"),
    ("WD My Passport 4TB", "WD", "Depolama", 4500, "https://www.trendyol.com/wd/my-passport-4tb-x-c104774", "https://cdn.dsmcdn.com/wdmypassport4tb.jpg"),
    ("Xiaomi 14T Pro 256GB", "Xiaomi", "Telefon", 35000, "https://www.trendyol.com/xiaomi/14t-pro-256gb-x-c103498", "https://cdn.dsmcdn.com/xiaomi14tpro.jpg"),
    ("Huawei Pura 70 Pro", "Huawei", "Telefon", 42000, "https://www.trendyol.com/huawei/pura-70-pro-x-c103498", "https://cdn.dsmcdn.com/huaweipura70pro.jpg"),
    ("Nothing Phone 2a Plus", "Nothing", "Telefon", 18000, "https://www.trendyol.com/nothing/phone-2a-plus-x-c103498", "https://cdn.dsmcdn.com/nothingphone2a.jpg"),
    ("Garmin Fenix 7X Pro", "Garmin", "Akilli Saat", 28000, "https://www.trendyol.com/garmin/fenix-7x-pro-x-c104761", "https://cdn.dsmcdn.com/garminfenix7x.jpg"),
    ("Samsung Galaxy Ring", "Samsung", "Akilli Saat", 8500, "https://www.trendyol.com/samsung/galaxy-ring-x-c104761", "https://cdn.dsmcdn.com/samsunggalaxyring.jpg"),
    ("TP-Link Deco XE75 Pro Mesh WiFi", "TP-Link", "Ag Cihazi", 8500, "https://www.trendyol.com/tp-link/deco-xe75-pro-x-c104777", "https://cdn.dsmcdn.com/tplinkdecoxe75.jpg"),
    ("Netgear Orbi RBK863S Mesh WiFi", "Netgear", "Ag Cihazi", 14000, "https://www.trendyol.com/netgear/orbi-rbk863s-x-c104777", "https://cdn.dsmcdn.com/netgearorbi.jpg"),
    ("Arlo Pro 5S Guvenlik Kamerasi", "Arlo", "Guvenlik", 8500, "https://www.trendyol.com/arlo/pro-5s-x-c104778", "https://cdn.dsmcdn.com/arlopro5s.jpg"),
    ("Philips Hue Starter Kit", "Philips", "Akilli Ev", 5500, "https://www.trendyol.com/philips/hue-starter-kit-x-c104779", "https://cdn.dsmcdn.com/philipshuestarterkit.jpg"),
    ("Amazon Echo Show 10", "Amazon", "Akilli Ev", 8500, "https://www.trendyol.com/amazon/echo-show-10-x-c104779", "https://cdn.dsmcdn.com/amazonechoshow10.jpg"),
    ("Apple HomePod 2. Nesil", "Apple", "Akilli Ev", 12000, "https://www.trendyol.com/apple/homepod-2-nesil-x-c104779", "https://cdn.dsmcdn.com/applehomepod2.jpg"),
    ("Xiaomi Smart Band 8 Active", "Xiaomi", "Akilli Saat", 2500, "https://www.trendyol.com/xiaomi/smart-band-8-active-x-c104761", "https://cdn.dsmcdn.com/xiaomismartband8active.jpg"),
    ("Fitbit Charge 6", "Fitbit", "Akilli Saat", 6500, "https://www.trendyol.com/fitbit/charge-6-x-c104761", "https://cdn.dsmcdn.com/fitbitcharge6.jpg"),
    ("DJI OM 6 Gimbal", "DJI", "Aksesuar", 7500, "https://www.trendyol.com/dji/om-6-x-c104771", "https://cdn.dsmcdn.com/djiom6.jpg"),
    ("Insta360 X4 360 Derece Kamera", "Insta360", "Kamera", 18000, "https://www.trendyol.com/insta360/x4-x-c104771", "https://cdn.dsmcdn.com/insta360x4.jpg"),
]

# ─── Seed ────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    print(f"Connecting to database...")
    try:
        conn = psycopg.connect(db_url)
    except Exception as e:
        print(f"ERROR: Veritabanına bağlanılamadı: {e}")
        sys.exit(1)

    print("Connected. Seeding...")

    with conn:
        with conn.cursor() as cur:
            # 1. Kategorileri upsert et
            categories = list({p[2] for p in PRODUCTS})
            cat_map: dict[str, str] = {}

            for cat_name in categories:
                slug = slugify(cat_name)
                cat_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO categories (id, name, slug)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (cat_id, cat_name, slug),
                )
                row = cur.fetchone()
                cat_map[cat_name] = str(row[0])
                print(f"  Category: {cat_name} → {cat_map[cat_name]}")

            # 2. Ürünleri ve mağaza kayıtlarını ekle
            inserted = 0
            skipped = 0
            for title, brand, category, price, url, image_url in PRODUCTS:
                product_id = str(uuid.uuid4())
                cat_id = cat_map.get(category)
                original_price = round(price * 1.15)  # %15 indirimli gibi göster

                # Product upsert (title üzerinden çakışma kontrolü)
                cur.execute(
                    """
                    INSERT INTO products (id, title, brand, image_url, category_id, lowest_price_ever, alarm_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (product_id, title, brand, image_url, cat_id, price, 0),
                )
                row = cur.fetchone()
                if not row:
                    skipped += 1
                    continue

                actual_product_id = str(row[0])

                # ProductStore ekle
                cur.execute(
                    """
                    INSERT INTO product_stores
                        (id, product_id, store, url, current_price, original_price, currency, discount_percent, in_stock, is_active)
                    VALUES (%s, %s, 'TRENDYOL'::store_name_enum, %s, %s, %s, 'TRY', 15, true, true)
                    ON CONFLICT (url) DO NOTHING
                    """,
                    (str(uuid.uuid4()), actual_product_id, url, price, original_price),
                )
                inserted += 1
                print(f"  [{inserted}] {title}")

    print(f"\nDone! {inserted} ürün eklendi, {skipped} zaten vardı.")
    conn.close()


if __name__ == "__main__":
    main()
