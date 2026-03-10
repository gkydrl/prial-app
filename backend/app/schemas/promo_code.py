import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.promo_code import DiscountType
from app.models.product import StoreName


class PromoCodeResponse(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    discount_type: DiscountType
    discount_value: Decimal
    store: StoreName | None
    min_price: Decimal | None
    starts_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class PromoCodeCreate(BaseModel):
    code: str = Field(max_length=50)
    title: str = Field(max_length=200)
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0)
    store: StoreName | None = None
    min_price: Decimal | None = None
    starts_at: datetime
    expires_at: datetime
    is_active: bool = True
    product_ids: list[uuid.UUID] = Field(default_factory=list)


class PromoCodeUpdate(BaseModel):
    code: str | None = None
    title: str | None = None
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = None
    store: StoreName | None = None
    min_price: Decimal | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None
    product_ids: list[uuid.UUID] | None = None
