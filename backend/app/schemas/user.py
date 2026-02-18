import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    full_name: str | None = Field(None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    push_notifications_enabled: bool
    email_notifications_enabled: bool
    notify_on_price_drop: bool
    notify_on_back_in_stock: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdatePreferences(BaseModel):
    full_name: str | None = Field(None, max_length=100)
    push_notifications_enabled: bool | None = None
    email_notifications_enabled: bool | None = None
    notify_on_price_drop: bool | None = None
    notify_on_back_in_stock: bool | None = None


class UserUpdateFirebaseToken(BaseModel):
    firebase_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
