from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdatePreferences, UserUpdateFirebaseToken
from app.core.security import get_current_user

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


@router.post("/me/firebase-token", response_model=UserResponse)
async def update_firebase_token(
    payload: UserUpdateFirebaseToken,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.firebase_token = payload.firebase_token
    db.add(current_user)
    return current_user
