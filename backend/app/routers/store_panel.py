"""
Mağaza paneli API'si — B2B kampanya yönetimi.
Ayrı JWT auth (user JWT'den bağımsız).
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.database import get_db
from app.core.security import hash_password, verify_password, decode_token
from app.models.campaign import (
    StoreAccount,
    Campaign,
    campaign_products,
    CodePool,
    UserPromoAssignment,
)
from app.models.product import Product
from app.schemas.campaign import (
    StoreAccountCreate,
    StoreAccountLogin,
    StoreAccountResponse,
    StoreTokenResponse,
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignStats,
    CodePoolUpload,
    CodePoolItemResponse,
)

from jose import jwt as jose_jwt

router = APIRouter(prefix="/store", tags=["store-panel"])
store_bearer = HTTPBearer()


# ─── Store JWT helpers ─────────────────────────────────────────────────────────

def _create_store_token(store_account_id: uuid.UUID) -> str:
    from datetime import timedelta
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {"sub": str(store_account_id), "exp": expire, "type": "store"}
    return jose_jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


async def get_current_store(
    credentials: HTTPAuthorizationCredentials = Depends(store_bearer),
    db: AsyncSession = Depends(get_db),
) -> StoreAccount:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "store":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token tipi")
    store_id = payload.get("sub")
    result = await db.execute(select(StoreAccount).where(StoreAccount.id == uuid.UUID(store_id)))
    account = result.scalar_one_or_none()
    if not account or not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mağaza hesabı bulunamadı")
    return account


# ─── Auth ──────────────────────────────────────────────────────────────────────

@router.post("/auth/register", response_model=StoreAccountResponse, status_code=201)
async def register_store(payload: StoreAccountCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(StoreAccount).where(StoreAccount.contact_email == payload.contact_email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")

    account = StoreAccount(
        store=payload.store,
        company_name=payload.company_name,
        contact_email=payload.contact_email,
        password_hash=hash_password(payload.password),
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.post("/auth/login", response_model=StoreTokenResponse)
async def login_store(payload: StoreAccountLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StoreAccount).where(StoreAccount.contact_email == payload.contact_email)
    )
    account = result.scalar_one_or_none()
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı")
    if not account.is_active:
        raise HTTPException(status_code=403, detail="Hesap devre dışı")

    return StoreTokenResponse(access_token=_create_store_token(account.id))


# ─── Campaigns ─────────────────────────────────────────────────────────────────

@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    store: StoreAccount = Depends(get_current_store),
):
    result = await db.execute(
        select(Campaign).where(Campaign.store_account_id == store.id).order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()
    out = []
    for c in campaigns:
        resp = CampaignResponse.model_validate(c)
        resp.product_ids = [p.id for p in c.products]
        out.append(resp)
    return out


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    store: StoreAccount = Depends(get_current_store),
):
    if not payload.is_unique_codes and not payload.fixed_code:
        raise HTTPException(status_code=422, detail="Sabit kod kampanyası için fixed_code gerekli")

    campaign = Campaign(
        store_account_id=store.id,
        title=payload.title,
        discount_type=payload.discount_type,
        discount_value=payload.discount_value,
        target_price_min=payload.target_price_min,
        target_price_max=payload.target_price_max,
        is_unique_codes=payload.is_unique_codes,
        fixed_code=payload.fixed_code,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
    )
    db.add(campaign)
    await db.flush()

    # Ürün bağlantıları
    if payload.product_ids:
        for pid in payload.product_ids:
            product = await db.get(Product, pid)
            if product:
                await db.execute(
                    campaign_products.insert().values(campaign_id=campaign.id, product_id=pid)
                )

    # İlk kodları yükle
    if payload.codes and payload.is_unique_codes:
        for code_str in payload.codes:
            db.add(CodePool(campaign_id=campaign.id, code=code_str.strip()))

    await db.flush()
    await db.refresh(campaign)

    resp = CampaignResponse.model_validate(campaign)
    resp.product_ids = payload.product_ids
    return resp


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    store: StoreAccount = Depends(get_current_store),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.store_account_id == store.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")

    # Stats
    total = (await db.execute(
        select(func.count()).select_from(CodePool).where(CodePool.campaign_id == campaign.id)
    )).scalar() or 0
    assigned = (await db.execute(
        select(func.count()).select_from(CodePool).where(
            CodePool.campaign_id == campaign.id,
            CodePool.assigned_to != None,
        )
    )).scalar() or 0

    resp = CampaignDetailResponse.model_validate(campaign)
    resp.product_ids = [p.id for p in campaign.products]
    resp.stats = CampaignStats(
        total_codes=total,
        assigned_count=assigned,
        remaining_count=total - assigned,
    )
    return resp


@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    store: StoreAccount = Depends(get_current_store),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.store_account_id == store.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")

    update_data = payload.model_dump(exclude_unset=True)
    product_ids = update_data.pop("product_ids", None)

    for field, value in update_data.items():
        setattr(campaign, field, value)

    if product_ids is not None:
        # Mevcut bağlantıları sil ve yeniden ekle
        await db.execute(campaign_products.delete().where(campaign_products.c.campaign_id == campaign.id))
        for pid in product_ids:
            await db.execute(campaign_products.insert().values(campaign_id=campaign.id, product_id=pid))

    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)

    resp = CampaignResponse.model_validate(campaign)
    resp.product_ids = [p.id for p in campaign.products]
    return resp


@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    store: StoreAccount = Depends(get_current_store),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.store_account_id == store.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")

    await db.delete(campaign)


# ─── Code Pool ─────────────────────────────────────────────────────────────────

@router.post("/campaigns/{campaign_id}/codes", status_code=201)
async def upload_codes(
    campaign_id: uuid.UUID,
    payload: CodePoolUpload,
    db: AsyncSession = Depends(get_db),
    store: StoreAccount = Depends(get_current_store),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.store_account_id == store.id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")
    if not campaign.is_unique_codes:
        raise HTTPException(status_code=422, detail="Sabit kod kampanyasına havuz kodu eklenemez")

    added = 0
    for code_str in payload.codes:
        code_str = code_str.strip()
        if not code_str:
            continue
        # Duplicate kontrolü
        existing = await db.execute(select(CodePool.id).where(CodePool.code == code_str).limit(1))
        if existing.scalar_one_or_none() is not None:
            continue
        db.add(CodePool(campaign_id=campaign.id, code=code_str))
        added += 1

    return {"added": added, "total_submitted": len(payload.codes)}


@router.get("/campaigns/{campaign_id}/codes", response_model=list[CodePoolItemResponse])
async def list_codes(
    campaign_id: uuid.UUID,
    assigned: bool | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    store: StoreAccount = Depends(get_current_store),
):
    # Kampanya sahiplik kontrolü
    result = await db.execute(
        select(Campaign.id).where(Campaign.id == campaign_id, Campaign.store_account_id == store.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")

    query = select(CodePool).where(CodePool.campaign_id == campaign_id)
    if assigned is True:
        query = query.where(CodePool.assigned_to != None)
    elif assigned is False:
        query = query.where(CodePool.assigned_to == None)

    result = await db.execute(query.offset(offset).limit(limit))
    return result.scalars().all()


# ─── Product Search ────────────────────────────────────────────────────────────

@router.get("/products/search")
async def search_products(
    q: str = Query(min_length=2),
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
    _store: StoreAccount = Depends(get_current_store),
):
    result = await db.execute(
        select(Product)
        .where(Product.title.ilike(f"%{q}%"))
        .order_by(Product.alarm_count.desc())
        .limit(limit)
    )
    products = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "brand": p.brand,
            "image_url": p.image_url,
            "alarm_count": p.alarm_count,
        }
        for p in products
    ]
