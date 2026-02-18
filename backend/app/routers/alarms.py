import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.alarm import Alarm, AlarmStatus
from app.models.product import Product
from app.schemas.alarm import AlarmResponse, AlarmUpdate
from app.core.security import get_current_user

router = APIRouter(prefix="/alarms", tags=["alarms"])


@router.get("/", response_model=list[AlarmResponse])
async def list_alarms(
    status: AlarmStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Alarm).where(Alarm.user_id == current_user.id)
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
