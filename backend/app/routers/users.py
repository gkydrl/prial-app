from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdatePreferences, UserUpdateFirebaseToken, UserChangePassword
from app.core.security import get_current_user, verify_password, hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_preferences(
    payload: UserUpdatePreferences,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.add(current_user)
    return current_user


@router.patch("/me/password")
async def change_password(
    payload: UserChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.auth_provider and not current_user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="Sosyal giriş ile kayıt olduğunuz için şifre değiştiremezsiniz",
        )
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mevcut şifre hatalı")
    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    return {"message": "Şifre güncellendi"}


@router.post("/me/firebase-token", response_model=UserResponse)
async def update_firebase_token(
    payload: UserUpdateFirebaseToken,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.firebase_token = payload.firebase_token
    db.add(current_user)
    return current_user
