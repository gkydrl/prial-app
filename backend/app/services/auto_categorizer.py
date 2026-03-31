"""
Kategorisiz ürünlere başlığa göre otomatik kategori atar.
"""
from __future__ import annotations

import re
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.category import Category

# Başlık keyword → kategori slug eşleştirmesi (öncelik sırasına göre)
KEYWORD_MAP: list[tuple[list[str], str]] = [
    # Telefon
    (["iphone", "galaxy s2", "galaxy s1", "galaxy a", "pixel", "xiaomi redmi", "poco"], "akilli-telefon"),
    # Laptop
    (["laptop", "notebook", "dizüstü", "macbook", "predator", "helios", "vivobook",
      "thinkpad", "zenbook", "yoga slim", "ideapad", "matebook", "swift"], "laptop"),
    # Tablet
    (["ipad", "galaxy tab", "tablet", "mediapad"], "tablet"),
    # Akıllı Saat
    (["apple watch", "galaxy watch", "huawei watch", "akıllı saat", "garmin", "fitbit"], "akilli-saat"),
    # Kulaklık
    (["airpods", "kulaklık", "earbuds", "headphone", "buds"], "kulaklik"),
    # TV
    (["televizyon", "smart tv", "oled tv", "qled", "neo qled"], "televizyon"),
    # Kamera / Fotoğraf
    (["alpha a7", "lumix", "eos r", "fotoğraf", "kamera", "mirrorless", "dslr"], "kamera"),
    # Oyun Konsolu
    (["playstation", "ps5", "xbox", "nintendo", "switch", "steam deck"], "oyun-konsolu"),
    # Monitör
    (["monitör", "monitor"], "monitor"),
    # Hoparlör
    (["hoparlör", "speaker", "soundbar", "homepod"], "hoparlor"),
    # Depolama
    (["ssd", "hdd", "hard disk", "flash bellek", "t7 shield", "t9"], "depolama"),
    # Beyaz Eşya
    (["buzdolabı", "çamaşır", "bulaşık", "ankastre", "fırın", "ocak", "beko"], "beyaz-esya"),
    # Ev Aleti
    (["robot süpürge", "süpürge", "hava temizleyici", "klima", "elektrikli", "dreame", "roborock"], "ev-aleti"),
    # Projeksiyon
    (["projeksiyon", "projektör", "projector", "lümen", "optoma", "viewsonic", "valerion"], "televizyon"),
    # Spor & Fitness
    (["rowerg", "concept2", "koşu bandı", "bisiklet", "fitness", "spor aleti"], "spor-fitness"),
    # Ağ Cihazı
    (["router", "modem", "mesh", "access point"], "ag-cihazi"),
    # Akıllı Ev
    (["akıllı ev", "smart home", "google nest", "echo"], "akilli-ev"),
    # Güvenlik
    (["güvenlik kamerası", "ip kamera"], "guvenlik"),
    # Kişisel Bakım
    (["tıraş", "epilatör", "saç kurutma", "diş fırçası"], "kisisel-bakim"),
    # Sneaker
    (["sneaker", "spor ayakkabı", "jordan", "air max", "new balance"], "sneaker"),
    # E-mobilite
    (["scooter", "e-bisiklet", "elektrikli kaykay"], "e-mobilite"),
]


def guess_category_slug(title: str) -> str | None:
    """Ürün başlığından kategori slug'ı tahmin et."""
    title_lower = title.lower()
    for keywords, slug in KEYWORD_MAP:
        for kw in keywords:
            if kw.lower() in title_lower:
                return slug
    return None


async def auto_categorize_products(db: AsyncSession) -> dict:
    """Kategorisiz tüm ürünlere otomatik kategori ata."""
    stats = {"total": 0, "categorized": 0, "unknown": 0}

    # Kategorisiz ürünleri getir
    result = await db.execute(
        select(Product).where(Product.category_id.is_(None))
    )
    products = result.scalars().all()
    stats["total"] = len(products)

    if not products:
        return stats

    # Kategori slug → id map
    cat_result = await db.execute(select(Category))
    categories = cat_result.scalars().all()
    cat_map = {c.slug: c.id for c in categories}

    unknown_titles = []
    for product in products:
        slug = guess_category_slug(product.title)
        if slug and slug in cat_map:
            product.category_id = cat_map[slug]
            stats["categorized"] += 1
        else:
            stats["unknown"] += 1
            unknown_titles.append(product.title[:60])

    await db.commit()

    if unknown_titles:
        print(f"[auto_categorizer] Kategorilenemeyenler:", flush=True)
        for t in unknown_titles[:20]:
            print(f"  - {t}", flush=True)

    return stats
