"""
Otomatik ürün keşfi için arama terimleri.

Kategoriler mevcut DB kategorileriyle uyumlu:
Telefon, Bilgisayar, Tablet, Televizyon, Ev Aleti,
Akıllı Saat, Oyun Konsolu, Kamera, Kulaklık, Beyaz Eşya,
Monitor, Hoparlör, Depolama, Ağ Cihazı, Kişisel Bakım
"""

DISCOVERY_TERMS: dict[str, list[str]] = {
    "telefon": [
        "iphone 16 pro max",
        "iphone 16 pro",
        "iphone 16",
        "iphone 15 pro max",
        "samsung galaxy s25 ultra",
        "samsung galaxy s25 plus",
        "samsung galaxy s25",
        "samsung galaxy z fold 6",
        "samsung galaxy z flip 6",
        "xiaomi 15 pro",
        "xiaomi 14 ultra",
        "google pixel 9 pro",
        "oneplus 13",
        "oppo find x8 pro",
        "honor magic 7 pro",
    ],
    "bilgisayar": [
        "macbook air m4",
        "macbook pro m4",
        "macbook pro m4 pro",
        "lenovo thinkpad x1 carbon",
        "lenovo ideapad slim 5",
        "asus zenbook 14",
        "asus rog strix laptop",
        "hp spectre x360",
        "dell xps 14",
        "dell inspiron 16",
        "monster abra laptop",
        "msi katana laptop",
    ],
    "tablet": [
        "ipad pro m4",
        "ipad air m2",
        "ipad 10. nesil",
        "samsung galaxy tab s10 ultra",
        "samsung galaxy tab s10 plus",
        "samsung galaxy tab s9 fe",
        "xiaomi pad 6s pro",
        "lenovo tab p12",
    ],
    "televizyon": [
        "samsung neo qled 4k tv",
        "lg oled evo c4 tv",
        "lg oled evo g4 tv",
        "sony bravia xr tv",
        "philips ambilight tv",
        "samsung the frame tv",
        "tcl qled tv 65 inç",
        "hisense u7 tv",
    ],
    "ev-aleti": [
        "dyson v15 detect",
        "dyson v12 detect slim",
        "dyson airwrap",
        "dyson supersonic",
        "irobot roomba",
        "roborock s8 pro",
        "philips airfryer xxl",
        "delonghi magnifica espresso",
        "nespresso vertuo",
    ],
    "beyaz-esya": [
        "samsung buzdolabı french door",
        "bosch bulaşık makinesi",
        "lg çamaşır makinesi",
        "arçelik kurutma makinesi",
        "beko ankastre fırın set",
    ],
    "akilli-saat": [
        "apple watch ultra 2",
        "apple watch series 10",
        "samsung galaxy watch 7 ultra",
        "samsung galaxy watch 7",
        "garmin fenix 8",
        "garmin venu 3",
        "huawei watch gt 5 pro",
    ],
    "oyun-konsolu": [
        "playstation 5 pro",
        "playstation 5 slim",
        "xbox series x",
        "nintendo switch oled",
        "steam deck oled",
        "playstation 5 dualsense",
        "meta quest 3",
    ],
    "kamera": [
        "sony alpha a7 iv",
        "sony alpha a7c ii",
        "canon eos r6 mark ii",
        "canon eos r50",
        "fujifilm x-t5",
        "nikon z6 iii",
        "gopro hero 13",
        "dji osmo pocket 3",
    ],
    "kulaklik": [
        "apple airpods pro 2",
        "apple airpods max",
        "sony wh-1000xm5",
        "sony wf-1000xm5",
        "samsung galaxy buds 3 pro",
        "bose quietcomfort ultra",
        "bose quietcomfort headphones",
        "sennheiser momentum 4",
        "jbl tour one m2",
    ],
    "monitor": [
        "lg ultragear oled monitor",
        "samsung odyssey oled g8",
        "dell ultrasharp 27 4k",
        "asus proart monitor",
        "benq mobiuz gaming monitor",
        "apple studio display",
    ],
    "hoparlor": [
        "sonos era 300",
        "sonos era 100",
        "marshall stanmore iii",
        "jbl charge 5",
        "jbl boombox 3",
        "bose soundlink max",
        "harman kardon aura studio 4",
    ],
}

# Tüm terimleri düz liste olarak al
def get_all_terms() -> list[tuple[str, str]]:
    """(kategori_slug, arama_terimi) tuple listesi döner."""
    result = []
    for category, terms in DISCOVERY_TERMS.items():
        for term in terms:
            result.append((category, term))
    return result
