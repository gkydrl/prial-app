"""
Ürün başlığından variant özelliklerini çıkarır ve variant oluşturur/bulur.
"""
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# --- Regex patterns ---
_STORAGE_PATTERN = re.compile(
    r"\b(16|32|64|128|256|512)\s*GB\b"
    r"|\b[12]\s*TB\b",
    re.IGNORECASE,
)
_RAM_PATTERN = re.compile(
    r"\b(4|6|8|12|16|32)\s*GB\s*RAM\b",
    re.IGNORECASE,
)
_COLOR_KEYWORDS = [
    "Siyah", "Beyaz", "Mavi", "Kırmızı", "Gümüş", "Altın",
    "Yeşil", "Mor", "Sarı", "Gri", "Pembe", "Turuncu", "Lacivert",
    "Bronz", "Titan", "Midnight", "Starlight",
]
_COLOR_PATTERN = re.compile(
    r"\b(" + "|".join(_COLOR_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def extract_attributes(title: str) -> dict[str, Any]:
    """
    Ürün başlığından storage, ram ve color bilgisini çıkarır.
    Örnek: "Samsung Galaxy S25 256GB Mavi" → {"storage": "256GB", "color": "Mavi"}
    """
    attrs: dict[str, Any] = {}

    storage_match = _STORAGE_PATTERN.search(title)
    if storage_match:
        raw = storage_match.group(0).replace(" ", "").upper()
        attrs["storage"] = raw

    ram_match = _RAM_PATTERN.search(title)
    if ram_match:
        raw = ram_match.group(0).replace(" ", "").upper()
        # Normalise: "8GBRAM" → "8GB RAM"
        raw = re.sub(r"(\d+GB)(RAM)", r"\1 \2", raw, flags=re.IGNORECASE).upper()
        attrs["ram"] = raw

    color_match = _COLOR_PATTERN.search(title)
    if color_match:
        attrs["color"] = color_match.group(0).capitalize()

    return attrs


def _variant_title(attributes: dict[str, Any]) -> str | None:
    """Attribute dict'inden okunabilir başlık üretir: "256GB Mavi" """
    parts = []
    if "storage" in attributes:
        parts.append(attributes["storage"])
    if "ram" in attributes:
        parts.append(attributes["ram"])
    if "color" in attributes:
        parts.append(attributes["color"])
    return " ".join(parts) if parts else None


async def find_or_create_variant(
    db: AsyncSession,
    product_id: uuid.UUID,
    attributes: dict[str, Any],
    image_url: str | None = None,
) -> "ProductVariant":  # noqa: F821
    """
    Verilen product_id + attributes kombinasyonu için mevcut variant'ı döner,
    yoksa yeni oluşturur.
    """
    from app.models.product import ProductVariant
    from sqlalchemy.dialects.postgresql import JSONB

    # attributes eşleşmesini JSONB @> operatörüyle yap
    result = await db.execute(
        select(ProductVariant).where(
            ProductVariant.product_id == product_id,
            ProductVariant.attributes.op("@>")(attributes),
            ProductVariant.attributes.op("<@")(attributes),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    title = _variant_title(attributes)
    variant = ProductVariant(
        product_id=product_id,
        title=title,
        attributes=attributes if attributes else None,
        image_url=image_url,
    )
    db.add(variant)
    await db.flush()
    return variant
