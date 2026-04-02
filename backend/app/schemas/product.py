import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, HttpUrl, Field
from app.models.product import StoreName
from app.schemas.promo_code import PromoCodeResponse
from app.schemas.campaign import AssignedPromoResponse


class ProductStoreResponse(BaseModel):
    id: uuid.UUID
    store: StoreName
    url: str
    current_price: Decimal | None
    original_price: Decimal | None
    currency: str
    discount_percent: int | None
    in_stock: bool
    last_checked_at: datetime | None
    estimated_delivery_days: int | None = None
    delivery_text: str | None = None
    installment_text: str | None = None
    promo_codes: list[PromoCodeResponse] = []
    assigned_promos: list[AssignedPromoResponse] = []

    model_config = {"from_attributes": True}


class ProductVariantResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    attributes: dict[str, Any] | None
    image_url: str | None
    alarm_count: int
    lowest_price_ever: Decimal | None
    stores: list[ProductStoreResponse]

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    id: uuid.UUID
    title: str
    short_title: str | None = None
    brand: str | None
    description: str | None
    image_url: str | None
    lowest_price_ever: Decimal | None
    l1y_lowest_price: Decimal | None = None
    l1y_highest_price: Decimal | None = None
    akakce_url: str | None = None
    alarm_count: int
    recommendation: str | None = None
    reasoning_text: str | None = None
    reasoning_pros: list[str] | None = None
    reasoning_cons: list[str] | None = None
    predicted_direction: str | None = None
    prediction_confidence: float | None = None
    category_id: uuid.UUID | None = None
    category_slug: str | None = None
    variants: list[ProductVariantResponse]
    stores: list[ProductStoreResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductAddRequest(BaseModel):
    url: str = Field(description="E-ticaret ürün sayfası URL'i")
    target_price: Decimal = Field(gt=0, description="Alarm kurulacak hedef fiyat")


class ProductPreviewRequest(BaseModel):
    url: str = Field(description="E-ticaret ürün sayfası URL'i")


class ProductPreviewResponse(BaseModel):
    title: str
    current_price: Decimal
    image_url: str | None


class PriceHistoryPoint(BaseModel):
    price: Decimal
    recorded_at: datetime

    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    image_url: str | None
    product_count: int = 0
    children: list["CategoryResponse"] = []

    model_config = {"from_attributes": True}


class DailyDealResponse(BaseModel):
    product: ProductResponse
    store: ProductStoreResponse
    discount_percent: int
    price_drop_amount: Decimal


class TopDropResponse(BaseModel):
    product: ProductResponse
    store: ProductStoreResponse
    price_24h_ago: Decimal | None
    price_now: Decimal | None
    drop_percent: float | None


class MatchUrlRequest(BaseModel):
    url: str = Field(description="E-ticaret ürün sayfası URL'i (Trendyol, Hepsiburada, vb.)")


class MatchUrlResponse(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID
    product: ProductResponse
    variant: ProductVariantResponse
    matched_store_url: str   # Katalogda daha önce bu store'dan kayıt var mı?
    already_tracked: bool    # Bu URL zaten sistemde takip ediliyor mu?
