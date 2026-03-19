import hashlib
import random
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserRegister, UserLogin, TokenResponse, UserResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest, ResendVerificationRequest,
)
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)


def _generate_verification_code() -> str:
    return f"{random.randint(100000, 999999)}"

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu e-posta adresi zaten kayıtlı")

    code = _generate_verification_code()
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        verification_code=code,
        verification_code_expires=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(user)
    await db.flush()

    # Send verification email
    from app.services.email_service import send_verification_email
    try:
        await send_verification_email(user.email, code)
        print(f"[auth] Doğrulama kodu gönderildi: {user.email}")
    except Exception as e:
        print(f"[auth] Doğrulama e-postası gönderilemedi ({user.email}): {e}")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(
    payload: VerifyEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """6 haneli doğrulama kodunu kontrol eder ve hesabı doğrular."""
    if current_user.is_verified:
        return  # Zaten doğrulanmış

    now = datetime.now(timezone.utc)
    if (
        not current_user.verification_code
        or not current_user.verification_code_expires
        or current_user.verification_code_expires < now
    ):
        raise HTTPException(status_code=400, detail="Doğrulama kodunun süresi dolmuş. Yeni kod gönderin.")

    if current_user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Geçersiz doğrulama kodu")

    current_user.is_verified = True
    current_user.verification_code = None
    current_user.verification_code_expires = None
    db.add(current_user)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Yeni doğrulama kodu gönderir."""
    if current_user.is_verified:
        return

    code = _generate_verification_code()
    current_user.verification_code = code
    current_user.verification_code_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.add(current_user)
    await db.flush()

    from app.services.email_service import send_verification_email
    try:
        await send_verification_email(current_user.email, code)
        print(f"[auth] Doğrulama kodu yeniden gönderildi: {current_user.email}")
    except Exception as e:
        print(f"[auth] Doğrulama e-postası gönderilemedi ({current_user.email}): {e}")
        raise HTTPException(status_code=500, detail="E-posta gönderilemedi, lütfen tekrar deneyin")


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hesap devre dışı")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Geçersiz refresh token")

    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Şifre sıfırlama e-postası gönderir.
    Kullanıcı bulunamasa bile 204 döner — email enumeration'a karşı.
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )

        user.reset_token_hash = token_hash
        user.reset_token_expires = expires
        db.add(user)
        await db.commit()

        from app.services.email_service import send_password_reset_email
        try:
            await send_password_reset_email(user.email, raw_token)
            print(f"[auth] Şifre sıfırlama e-postası gönderildi: {user.email}")
        except Exception as e:
            print(f"[auth] Şifre sıfırlama e-postası gönderilemedi ({user.email}): {e}")


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(User).where(
            User.reset_token_hash == token_hash,
            User.reset_token_expires > now,
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş bağlantı")

    user.password_hash = hash_password(payload.new_password)
    user.reset_token_hash = None
    user.reset_token_expires = None
    db.add(user)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hesabı kalıcı olarak devre dışı bırakır ve kişisel verileri temizler.
    Apple App Store Review Guidelines 5.1.1 gereği in-app hesap silme.
    """
    from app.models.alarm import Alarm, AlarmStatus

    # Alarmları iptal et
    result = await db.execute(
        select(Alarm).where(Alarm.user_id == current_user.id, Alarm.status == AlarmStatus.ACTIVE)
    )
    for alarm in result.scalars().all():
        alarm.status = AlarmStatus.DELETED
        db.add(alarm)

    # Kişisel verileri temizle
    current_user.is_active = False
    current_user.full_name = None
    current_user.email = f"deleted_{current_user.id}@deleted.prial.app"
    current_user.firebase_token = None
    current_user.avatar_url = None
    current_user.reset_token_hash = None
    current_user.reset_token_expires = None
    db.add(current_user)
    await db.commit()
