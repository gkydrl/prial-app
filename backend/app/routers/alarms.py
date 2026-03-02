import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.alarm import Alarm, AlarmStatus
from app.models.product import Product, ProductStore
from app.schemas.alarm import AlarmCreate, AlarmResponse, AlarmUpdate
from app.core.security import get_current_user

router = APIRouter(prefix="/alarms", tags=["alarms"])


@router.post("/", response_model=AlarmResponse, status_code=201)
async def create_alarm(
    payload: AlarmCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ürün var mı?
    product = await db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    # Aynı ürün için aktif/paused alarm zaten var mı?
    dup = await db.execute(
        select(Alarm).where(
            Alarm.user_id == current_user.id,
            Alarm.product_id == payload.product_id,
            Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.PAUSED]),
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu ürün için zaten aktif bir talebiniz var")

    # Mağaza belirtilmemişse en ucuz mağazayı seç
    store_id = payload.product_store_id
    if not store_id:
        sr = await db.execute(
            select(ProductStore)
            .where(ProductStore.product_id == payload.product_id, ProductStore.in_stock == True)
            .order_by(ProductStore.current_price.asc())
            .limit(1)
        )
        store = sr.scalar_one_or_none()
        if store:
            store_id = store.id

    alarm = Alarm(
        user_id=current_user.id,
        product_id=payload.product_id,
        product_store_id=store_id,
        target_price=payload.target_price,
        status=AlarmStatus.ACTIVE,
    )
    db.add(alarm)
    product.alarm_count += 1
    await db.flush()

    # İlişkileriyle birlikte döndür
    res = await db.execute(
        select(Alarm)
        .options(
            selectinload(Alarm.product).selectinload(Product.stores),
            selectinload(Alarm.product_store),
        )
        .where(Alarm.id == alarm.id)
    )
    return res.scalar_one()


@router.get("/", response_model=list[AlarmResponse])
async def list_alarms(
    status: AlarmStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Alarm)
        .options(
            selectinload(Alarm.product).selectinload(Product.stores),
            selectinload(Alarm.product_store),
        )
        .where(Alarm.user_id == current_user.id)
    )
    if status:
        query = query.where(Alarm.status == status)
    query = query.order_by(Alarm.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{alarm_id}", response_model=AlarmResponse)
async def update_alarm(
    alarm_id: uuid.UUID,
    payload: AlarmUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alarm = await _get_user_alarm(alarm_id, current_user.id, db)

    if payload.target_price is not None:
        alarm.target_price = payload.target_price
    if payload.status is not None:
        alarm.status = payload.status

    db.add(alarm)
    return alarm


@router.delete("/{alarm_id}", status_code=204)
async def delete_alarm(
    alarm_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alarm = await _get_user_alarm(alarm_id, current_user.id, db)
    alarm.status = AlarmStatus.DELETED

    # Ürünün alarm sayısını azalt
    product = await db.get(Product, alarm.product_id)
    if product and product.alarm_count > 0:
        product.alarm_count -= 1

    db.add(alarm)


async def _get_user_alarm(
    alarm_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Alarm:
    result = await db.execute(
        select(Alarm).where(Alarm.id == alarm_id, Alarm.user_id == user_id)
    )
    alarm = result.scalar_one_or_none()
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm bulunamadı")
    return alarm
