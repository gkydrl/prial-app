"""
Bir arama sonucunun (SearchResult / ScrapedProduct) katalogdaki bir
ProductVariant ile eşleşip eşleşmediğini belirler.

Adım 1 — Regex/attribute karşılaştırma (hızlı, ücretsiz)
  • Brand kontrolü
  • Çıkarılan özellikler (storage, ram, color) karşılaştırması
  → Kesin eşleşme veya kesin red.
  → Belirsiz durum: Adım 2'ye geç.

Adım 2 — Fuzzy title karşılaştırma (Jaccard benzerliği)
  • LLM kullanmaz, kelime bazlı benzerlik hesaplar.
"""
from __future__ import annotations

from app.services.variant_extractor import extract_attributes


def _brands_compatible(brand_a: str | None, brand_b: str | None) -> bool:
    """İki brand birbiriyle uyumlu mu? (case-insensitive substring kontrolü)"""
    if not brand_a or not brand_b:
        return True  # Biri bilinmiyorsa reddetme
    a, b = brand_a.lower().strip(), brand_b.lower().strip()
    return a in b or b in a


def _attributes_compatible(variant_attrs: dict, scraped_attrs: dict) -> tuple[bool, bool]:
    """
    İki attribute dict karşılaştırır.
    Returns: (compatible: bool, confident: bool)
      compatible=False → kesin red
      compatible=True, confident=True → LLM'e gerek yok
      compatible=True, confident=False → LLM doğrulasın
    """
    if not variant_attrs:
        # Variant'ın attribute'u yoksa (ör. default variant) → attribute kontrolü atla
        return True, False

    mismatches = 0
    matches = 0

    for key, val in variant_attrs.items():
        if key not in scraped_attrs:
            # Scraped data'da bu attr yok → belirsiz, LLM karar versin
            continue

        v_str = str(val).lower().strip()
        s_str = scraped_attrs[key].lower().strip()

        if v_str == s_str:
            matches += 1
        elif key == "storage":
            # Storage için kesin eşleşme gerekir: 128GB ≠ 256GB
            mismatches += 1
        else:
            # Diğer attr'ler (color vs.) için substring kontrolü:
            # "Titan Siyah" ile "Siyah" → uyumlu (belirsiz)
            # "Mavi" ile "Kırmızı" → uyumsuz
            if v_str in s_str or s_str in v_str:
                # Kısmi eşleşme → belirsiz
                pass
            else:
                mismatches += 1

    if mismatches > 0:
        return False, True  # Kesin red

    confident = matches >= len(variant_attrs)  # Tüm attr'ler tam eşleştiyse emin
    return True, confident


async def is_match(
    product_brand: str | None,
    product_title: str,
    variant_title: str | None,
    variant_attrs: dict,
    scraped_title: str,
    scraped_brand: str | None,
) -> bool:
    """
    Bir SearchResult/ScrapedProduct ile katalog variantının eşleşip eşleşmediğini belirler.
    """
    # 1. Brand kontrolü
    if not _brands_compatible(product_brand, scraped_brand):
        return False

    # 2. Attribute karşılaştırması
    scraped_attrs = extract_attributes(scraped_title)
    compatible, confident = _attributes_compatible(variant_attrs, scraped_attrs)

    if not compatible:
        return False

    if confident:
        # Tüm attribute'lar eşleşti, product title da içeride mi kontrol et
        core = product_title.lower().split()
        title_lower = scraped_title.lower()
        # En az ürün adının önemli kelimelerinin %60'ı geçmeli
        meaningful = [w for w in core if len(w) > 3]
        if meaningful:
            hit = sum(1 for w in meaningful if w in title_lower)
            if hit / len(meaningful) < 0.6:
                return False
        return True

    # 3. Belirsiz durum → fuzzy title karşılaştırma (LLM yerine)
    return _fuzzy_title_match(
        catalog_label=f"{product_brand or ''} {product_title} {variant_title or ''}".strip(),
        scraped_title=scraped_title,
    )


def _normalize(text: str) -> set[str]:
    """Başlığı küçük harfe çevirip anlamlı kelimelere böler."""
    import re
    text = text.lower()
    # Parantez içindekiler dahil tüm kelimeleri al
    words = re.findall(r'[a-zçğıöşü0-9]+', text)
    # Çok kısa / anlamsız kelimeleri at
    stop = {"ve", "ile", "icin", "için", "the", "and", "for", "with", "in", "de", "da"}
    return {w for w in words if len(w) > 1 and w not in stop}


def _fuzzy_title_match(catalog_label: str, scraped_title: str) -> bool:
    """
    İki ürün başlığı arasında kelime bazlı Jaccard benzerliği hesaplar.
    Eşik: %40 — belirsiz durumlarda makul eşleşme için yeterli.
    """
    cat_words = _normalize(catalog_label)
    scr_words = _normalize(scraped_title)

    if not cat_words or not scr_words:
        return False

    intersection = cat_words & scr_words
    union = cat_words | scr_words

    similarity = len(intersection) / len(union)
    return similarity >= 0.40


async def find_best_match(
    scraped_title: str,
    scraped_brand: str | None,
    candidates: list,  # list of (Product, ProductVariant)
) -> tuple | None:
    """
    Birden fazla aday variant arasından en iyi eşleşmeyi bulur.
    candidates: [(Product, ProductVariant), ...]
    Returns: (Product, ProductVariant) veya None
    """
    for product, variant in candidates:
        matched = await is_match(
            product_brand=product.brand,
            product_title=product.title,
            variant_title=variant.title,
            variant_attrs=variant.attributes or {},
            scraped_title=scraped_title,
            scraped_brand=scraped_brand,
        )
        if matched:
            return product, variant
    return None
