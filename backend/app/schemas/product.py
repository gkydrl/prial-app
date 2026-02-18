import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, HttpUrl, Field
from app.models.product import StoreName


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

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    id: uuid.UUID
    title: str
    brand: str | None
    description: str | None
    image_url: str | None
    lowest_price_ever: Decimal | None
    alarm_count: int
    stores: list[ProductStoreResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductAddRequest(BaseModel):
    url: str = Field(description="E-ticaret ürün sayfası URL'i")
    target_price: Decimal = Field(gt=0, description="Alarm kurulacak hedef fiyat")


class PriceHistoryPoint(BaseModel):
    price: Decimal
    recorded_at: datetime

    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    image_url: str | None
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
