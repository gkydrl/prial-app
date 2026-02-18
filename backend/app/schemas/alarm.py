import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.alarm import AlarmStatus
from app.schemas.product import ProductResponse, ProductStoreResponse


class AlarmCreate(BaseModel):
    product_id: uuid.UUID
    target_price: Decimal = Field(gt=0)
    product_store_id: uuid.UUID | None = None  # Belirli bir mağaza için


class AlarmResponse(BaseModel):
    id: uuid.UUID
    target_price: Decimal
    status: AlarmStatus
    triggered_price: Decimal | None
    triggered_at: datetime | None
    created_at: datetime
    product: ProductResponse
    product_store: ProductStoreResponse | None

    model_config = {"from_attributes": True}


class AlarmUpdate(BaseModel):
    target_price: Decimal | None = Field(None, gt=0)
    status: AlarmStatus | None = None
