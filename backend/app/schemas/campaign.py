import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr
from app.models.promo_code import DiscountType
from app.models.product import StoreName


# ─── Store Account ────────────────────────────────────────────────────────────

class StoreAccountCreate(BaseModel):
    store: StoreName
    company_name: str | None = None
    contact_email: EmailStr
    password: str = Field(min_length=8, max_length=64)


class StoreAccountLogin(BaseModel):
    contact_email: EmailStr
    password: str


class StoreAccountResponse(BaseModel):
    id: uuid.UUID
    store: StoreName
    company_name: str | None
    contact_email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Campaign ─────────────────────────────────────────────────────────────────

class CampaignCreate(BaseModel):
    title: str = Field(max_length=200)
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0)
    target_price_min: Decimal | None = None
    target_price_max: Decimal | None = None
    is_unique_codes: bool = True
    fixed_code: str | None = Field(default=None, max_length=50)
    starts_at: datetime
    expires_at: datetime
    product_ids: list[uuid.UUID] = Field(default_factory=list)
    codes: list[str] = Field(default_factory=list, description="İlk kod havuzu (opsiyonel)")


class CampaignUpdate(BaseModel):
    title: str | None = None
    discount_type: DiscountType | None = None
    discount_value: Decimal | None = None
    target_price_min: Decimal | None = None
    target_price_max: Decimal | None = None
    is_unique_codes: bool | None = None
    fixed_code: str | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None
    product_ids: list[uuid.UUID] | None = None


class CampaignResponse(BaseModel):
    id: uuid.UUID
    title: str
    discount_type: DiscountType
    discount_value: Decimal
    target_price_min: Decimal | None
    target_price_max: Decimal | None
    is_unique_codes: bool
    fixed_code: str | None
    starts_at: datetime
    expires_at: datetime
    is_active: bool
    created_at: datetime
    product_ids: list[uuid.UUID] = []

    model_config = {"from_attributes": True}


class CampaignStats(BaseModel):
    total_codes: int
    assigned_count: int
    remaining_count: int


class CampaignDetailResponse(CampaignResponse):
    stats: CampaignStats


# ─── Code Pool ─────────────────────────────────────────────────────────────────

class CodePoolUpload(BaseModel):
    codes: list[str] = Field(min_length=1)


class CodePoolItemResponse(BaseModel):
    id: uuid.UUID
    code: str
    assigned_to: uuid.UUID | None
    assigned_at: datetime | None
    is_used: bool

    model_config = {"from_attributes": True}


# ─── Assigned Promo (kullanıcıya özel) ────────────────────────────────────────

class AssignedPromoResponse(BaseModel):
    campaign_id: uuid.UUID
    campaign_title: str
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    assigned_at: datetime

    model_config = {"from_attributes": True}
