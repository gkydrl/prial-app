import uuid
from typing import Any
from pydantic import BaseModel, Field


class VariantInput(BaseModel):
    title: str | None = None          # "256GB Kırmızı" — yoksa attributes'tan türetilir
    attributes: dict[str, Any] = Field(default_factory=dict)  # {"storage": "256GB", "color": "Kırmızı"}
    image_url: str | None = None


class AdminProductCreate(BaseModel):
    title: str = Field(description="Ürün adı — SKU seviyesinde (ör. 'iPhone 16 Pro')")
    brand: str | None = None
    category_slug: str | None = None
    description: str | None = None
    image_url: str | None = None
    variants: list[VariantInput] = Field(
        default_factory=list,
        description="Boş bırakılırsa attributes={} olan 1 default variant oluşturulur",
    )


class AdminProductResponse(BaseModel):
    id: uuid.UUID
    title: str
    brand: str | None
    variant_count: int
