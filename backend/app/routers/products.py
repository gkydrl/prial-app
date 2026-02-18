import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.product import Product, ProductStore
from app.models.alarm import Alarm, AlarmStatus
from app.models.price_history import PriceHistory
from app.schemas.product import ProductResponse, ProductAddRequest, PriceHistoryPoint
from app.schemas.alarm import AlarmResponse
from app.core.security import get_current_user

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/add", response_model=dict)
async def add_product_by_url(
    payload: ProductAddRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    URL'den ürün bilgisini çeker, veritabanına kaydeder ve alarm oluşturur.
    Scraping işlemi arka planda yapılır.
    """
    from app.services.scraper import scrape_and_save_product

    # URL daha önce eklenmiş mi?
    result = await db.execute(select(ProductStore).where(ProductStore.url == str(payload.url)))
    product_store = result.scalar_one_or_none()

    if product_store:
        # Ürün zaten var, direkt alarm kur
        alarm = Alarm(
            user_id=current_user.id,
            product_id=product_store.product_id,
            product_store_id=product_store.id,
            target_price=payload.target_price,
            status=AlarmStatus.ACTIVE,
        )
        db.add(alarm)
        await db.flush()

        # Ürünün alarm sayısını artır
        product = await db.get(Product, product_store.product_id)
        product.alarm_count += 1

        return {"message": "Alarm kuruldu", "alarm_id": str(alarm.id)}

    # Yeni ürün — arka planda scrape et ve alarm kur
    background_tasks.add_task(
        scrape_and_save_product,
        url=str(payload.url),
        user_id=current_user.id,
        target_price=payload.target_price,
    )

    return {"message": "Ürün ekleniyor, kısa süre içinde alarm kurulacak"}


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    return product


@router.get("/{product_id}/price-history", response_model=list[PriceHistoryPoint])
async def get_price_history(
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(PriceHistory)
        .join(ProductStore)
        .where(ProductStore.product_id == product_id)
        .order_by(PriceHistory.recorded_at.desc())
    )
    if store_id:
        query = query.where(PriceHistory.product_store_id == store_id)

    result = await db.execute(query.limit(90))  # Son 90 kayıt
    return result.scalars().all()
