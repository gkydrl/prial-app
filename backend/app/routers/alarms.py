import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.alarm import Alarm, AlarmStatus
from app.models.product import Product, ProductStore, ProductVariant
from app.schemas.alarm import AlarmCreate, AlarmResponse, AlarmUpdate
from app.core.security import get_current_user
from app.services.price_tracker import refresh_store_priority, next_check_delta
from app.services.notification_service import notify_community_milestone
from datetime import datetime, timezone

MILESTONES = [100, 500, 1000, 5000]

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

    # Variant belirtilmemişse product_id'ye ait ilk variant'ı seç
    variant_id = payload.variant_id
    if not variant_id:
        vr = await db.execute(
            select(ProductVariant)
            .where(ProductVariant.product_id == payload.product_id)
            .limit(1)
        )
        variant = vr.scalar_one_or_none()
        if variant:
            variant_id = variant.id

    # Mağaza belirtilmemişse variant'a ait en ucuz mağazayı seç
    store_id = payload.product_store_id
    if not store_id:
        stores_query = (
            select(ProductStore)
            .where(ProductStore.product_id == payload.product_id, ProductStore.in_stock == True)
        )
        if variant_id:
            stores_query = stores_query.where(ProductStore.variant_id == variant_id)
        stores_query = stores_query.order_by(ProductStore.current_price.asc()).limit(1)
        sr = await db.execute(stores_query)
        store = sr.scalar_one_or_none()
        if store:
            store_id = store.id

    alarm = Alarm(
        user_id=current_user.id,
        product_id=payload.product_id,
        variant_id=variant_id,
        product_store_id=store_id,
        target_price=payload.target_price,
        status=AlarmStatus.ACTIVE,
    )
    db.add(alarm)
    product.alarm_count += 1

    # Milestone kontrolu — arka planda gonder
    if product.alarm_count in MILESTONES:
        import asyncio
        asyncio.ensure_future(notify_community_milestone(product, product.alarm_count))

    # variant alarm_count güncelle
    if variant_id:
        variant_obj = await db.get(ProductVariant, variant_id)
        if variant_obj:
            variant_obj.alarm_count += 1
            db.add(variant_obj)

    await db.flush()

    # Aktif alarm var → variant'a bağlı tüm store'ları HIGH önceliğe al
    if variant_id:
        vs_result = await db.execute(
            select(ProductStore).where(
                ProductStore.variant_id == variant_id,
                ProductStore.is_active == True,
            )
        )
        variant_stores = vs_result.scalars().all()
        for vs in variant_stores:
            vs.check_priority = 1
            vs.next_check_at = datetime.now(timezone.utc)
            db.add(vs)
    elif store_id:
        target_store = await db.get(ProductStore, store_id)
        if target_store:
            target_store.check_priority = 1
            target_store.next_check_at = datetime.now(timezone.utc)
            db.add(target_store)

    # İlişkileriyle birlikte döndür
    res = await db.execute(
        select(Alarm)
        .options(
            selectinload(Alarm.product).selectinload(Product.stores),
            selectinload(Alarm.product).selectinload(Product.variants).selectinload(ProductVariant.stores),
            selectinload(Alarm.product_store),
            selectinload(Alarm.variant),
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
            selectinload(Alarm.product).selectinload(Product.variants).selectinload(ProductVariant.stores),
            selectinload(Alarm.product_store),
            selectinload(Alarm.variant),
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
        old_status = alarm.status
        alarm.status = payload.status
        # Aktif → pause/delete geçişinde önceliği düşür
        if old_status == AlarmStatus.ACTIVE and payload.status != AlarmStatus.ACTIVE:
            if alarm.product_store_id:
                store = await db.get(ProductStore, alarm.product_store_id)
                if store:
                    store.check_priority = 2
                    store.next_check_at = datetime.now(timezone.utc) + next_check_delta(2)
                    db.add(store)

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

    # Variant alarm sayısını azalt
    if alarm.variant_id:
        variant_obj = await db.get(ProductVariant, alarm.variant_id)
        if variant_obj and variant_obj.alarm_count > 0:
            variant_obj.alarm_count -= 1
            db.add(variant_obj)

    # Store önceliğini MEDIUM'a düşür (geçmişte alarm aldı)
    if alarm.product_store_id:
        store = await db.get(ProductStore, alarm.product_store_id)
        if store:
            store.check_priority = 2
            store.next_check_at = datetime.now(timezone.utc) + next_check_delta(2)
            db.add(store)

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
