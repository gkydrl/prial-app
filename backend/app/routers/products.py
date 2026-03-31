import uuid
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.product import Product, ProductStore, ProductVariant
from app.models.alarm import Alarm, AlarmStatus
from app.models.price_history import PriceHistory
from app.models.category import Category
from app.models.prediction import PricePrediction
from app.services.prediction.batch_loader import attach_predictions
from app.schemas.product import (
    ProductResponse, ProductAddRequest, PriceHistoryPoint,
    ProductPreviewRequest, ProductPreviewResponse,
    ProductVariantResponse, MatchUrlRequest, MatchUrlResponse,
)
from app.schemas.alarm import AlarmResponse
from app.core.security import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/products", tags=["products"])

_optional_bearer = HTTPBearer(auto_error=False)


async def _optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Token varsa kullanıcıyı döndür, yoksa None."""
    if credentials is None:
        return None
    try:
        from app.core.security import decode_token
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            return None
        import uuid as _uuid
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        return user if user and user.is_active else None
    except Exception:
        return None


@router.get("/{product_id}/prediction")
async def get_product_prediction(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Bugünkü AI tahminini döner. Auth gerektirmez."""
    result = await db.execute(
        select(PricePrediction)
        .where(
            PricePrediction.product_id == product_id,
            PricePrediction.prediction_date == date.today(),
        )
        .order_by(PricePrediction.created_at.desc())
        .limit(1)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        return {"status": "no_prediction"}

    from app.services.prediction.batch_loader import _parse_reasoning
    summary, pros, cons = _parse_reasoning(pred.reasoning_text)
    return {
        "status": "ok",
        "recommendation": pred.recommendation.value,
        "confidence": float(pred.confidence),
        "reasoning_text": summary,
        "reasoning_pros": pros,
        "reasoning_cons": cons,
        "predicted_direction": pred.predicted_direction.value,
        "current_price": float(pred.current_price),
    }


@router.post("/preview", response_model=ProductPreviewResponse)
async def preview_product(
    payload: ProductPreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """
    URL'yi scrape eder ve ürün bilgisini döner. Veritabanına kaydetmez.
    """
    from app.services.scraper.dispatcher import scrape_url

    try:
        scraped = await scrape_url(payload.url)
    except Exception:
        raise HTTPException(status_code=422, detail="Ürün bilgileri alınamadı. Linki kontrol et.")

    if not scraped.current_price:
        raise HTTPException(status_code=422, detail="Ürün fiyatı bulunamadı.")

    return ProductPreviewResponse(
        title=scraped.title,
        current_price=scraped.current_price,
        image_url=scraped.image_url,
    )


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
        # Kullanıcının bu ürüne zaten aktif/paused talebi var mı?
        existing_result = await db.execute(
            select(Alarm).where(
                Alarm.user_id == current_user.id,
                Alarm.product_id == product_store.product_id,
                Alarm.status.in_([AlarmStatus.ACTIVE, AlarmStatus.PAUSED]),
            )
        )
        existing_alarm = existing_result.scalar_one_or_none()
        if existing_alarm:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ALARM_EXISTS",
                    "alarm_id": str(existing_alarm.id),
                    "target_price": float(existing_alarm.target_price),
                },
            )

        # Ürün zaten var, direkt alarm kur
        alarm = Alarm(
            user_id=current_user.id,
            product_id=product_store.product_id,
            variant_id=product_store.variant_id,
            product_store_id=product_store.id,
            target_price=payload.target_price,
            status=AlarmStatus.ACTIVE,
        )
        db.add(alarm)
        await db.flush()

        # Ürünün ve variant'ın alarm sayısını artır
        product = await db.get(Product, product_store.product_id)
        product.alarm_count += 1
        if product_store.variant_id:
            variant_obj = await db.get(ProductVariant, product_store.variant_id)
            if variant_obj:
                variant_obj.alarm_count += 1
                db.add(variant_obj)

        return {"message": "Alarm kuruldu", "alarm_id": str(alarm.id)}

    # Yeni ürün — arka planda scrape et ve alarm kur
    background_tasks.add_task(
        scrape_and_save_product,
        url=str(payload.url),
        user_id=current_user.id,
        target_price=payload.target_price,
    )

    return {"message": "Ürün ekleniyor, kısa süre içinde alarm kurulacak"}


@router.get("", response_model=list[ProductResponse])
async def list_products(
    limit: int = Query(default=50, le=200),
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Tüm ürünleri listeler (Keşfet ekranı için). category slug ile filtrelenebilir."""
    query = select(Product).options(
        selectinload(Product.variants).selectinload(ProductVariant.stores),
        selectinload(Product.stores),
    )
    if category:
        cat_sq = select(Category.id).where(Category.slug == category).scalar_subquery()
        query = query.where(Product.category_id == cat_sq)
    result = await db.execute(
        query.order_by(Product.alarm_count.desc(), Product.created_at.desc()).limit(limit)
    )
    products = result.scalars().all()
    await attach_predictions(products, db)
    return products


@router.get("/by-id-short/{short_id}", response_model=ProductResponse)
async def get_product_by_short_id(
    short_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Short ID (ilk 8 hex karakter) ile ürün getir — SEO-friendly URL'ler için."""
    if len(short_id) < 8:
        raise HTTPException(status_code=400, detail="Short ID en az 8 karakter olmalı")

    # Short ID'den UUID prefix oluştur (8 hex → UUID format: xxxxxxxx-...)
    sid = short_id[:8].lower()
    # Tüm ürünleri getirmek yerine text cast ile filtrele
    from sqlalchemy import text
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.stores),
            selectinload(Product.stores),
        )
        .where(text(f"CAST(id AS TEXT) LIKE :prefix"))
        .params(prefix=f"{sid}%")
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    await attach_predictions([product], db)
    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(_optional_user),
):
    from datetime import datetime, timezone
    from app.models.promo_code import PromoCode, promo_code_products

    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.stores),
            selectinload(Product.stores),
        )
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    # Fetch active promo codes for this product
    now = datetime.now(timezone.utc)
    promo_result = await db.execute(
        select(PromoCode).where(
            PromoCode.is_active == True,
            PromoCode.starts_at <= now,
            PromoCode.expires_at > now,
        )
    )
    all_promos = promo_result.scalars().all()

    # Kullanıcıya atanmış kampanya kodlarını çek
    assigned_promos = []
    if current_user:
        from app.models.campaign import UserPromoAssignment, Campaign
        assign_result = await db.execute(
            select(UserPromoAssignment, Campaign)
            .join(Campaign, UserPromoAssignment.campaign_id == Campaign.id)
            .where(
                UserPromoAssignment.user_id == current_user.id,
                UserPromoAssignment.product_id == product_id,
            )
        )
        for assignment, campaign in assign_result.all():
            assigned_promos.append({
                "campaign_id": campaign.id,
                "campaign_title": campaign.title,
                "code": assignment.code,
                "discount_type": campaign.discount_type,
                "discount_value": campaign.discount_value,
                "assigned_at": assignment.assigned_at,
            })

    # Attach today's prediction
    await attach_predictions([product], db)

    # For each store, find applicable promo codes + assigned promos
    for store in product.stores:
        store.promo_codes = [
            p for p in all_promos
            if (p.store is None or p.store == store.store)
            and (len(p.products) == 0 or product_id in [pr.id for pr in p.products])
        ]
        store.assigned_promos = assigned_promos
    for variant in product.variants:
        for store in variant.stores:
            store.promo_codes = [
                p for p in all_promos
                if (p.store is None or p.store == store.store)
                and (len(p.products) == 0 or product_id in [pr.id for pr in p.products])
            ]
            store.assigned_promos = assigned_promos

    return product


@router.post("/match-url", response_model=MatchUrlResponse)
async def match_url(
    payload: MatchUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Kullanıcı dışarıdan (Trendyol, Hepsiburada, vb.) URL paylaştığında
    kataloğumuzda eşleşen ürün+variant'ı bulur.

    Eşleşme bulunamazsa 404 döner: kullanıcıya "Katalogumuzda yok" mesajı gösterilir.
    """
    from app.services.scraper.dispatcher import scrape_url
    from app.services.catalog_matcher import find_best_match
    from app.services.variant_extractor import extract_attributes

    # 1. URL'yi scrape et
    try:
        scraped = await scrape_url(str(payload.url))
    except Exception:
        raise HTTPException(status_code=422, detail="Ürün bilgileri alınamadı. Linki kontrol et.")

    # 2. Bu URL zaten sistemde mi?
    existing_store = (await db.execute(
        select(ProductStore).where(ProductStore.url == scraped.url)
    )).scalar_one_or_none()

    if existing_store:
        # Direkt eşleşme — ProductStore var
        product = await db.get(Product, existing_store.product_id)
        variant = await db.get(ProductVariant, existing_store.variant_id) if existing_store.variant_id else None
        if product and variant:
            product_full = (await db.execute(
                select(Product)
                .options(
                    selectinload(Product.variants).selectinload(ProductVariant.stores),
                    selectinload(Product.stores),
                )
                .where(Product.id == product.id)
            )).scalar_one()
            variant_full = next((v for v in product_full.variants if v.id == variant.id), None)
            if variant_full:
                return MatchUrlResponse(
                    product_id=product.id,
                    variant_id=variant.id,
                    product=product_full,
                    variant=variant_full,
                    matched_store_url=scraped.url,
                    already_tracked=True,
                )

    # 3. Katalogda brand + attribute eşleşmesi ara
    scraped_attrs = extract_attributes(scraped.title)

    # Brand filtresiyle aday ürünleri çek
    brand_filter = scraped.brand or ""
    candidates_q = (
        select(Product, ProductVariant)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .options(selectinload(Product.variants), selectinload(Product.stores))
    )
    if brand_filter:
        candidates_q = candidates_q.where(
            Product.brand.ilike(f"%{brand_filter}%")
        )
    candidates_result = await db.execute(candidates_q.limit(50))
    candidates = [(row[0], row[1]) for row in candidates_result.all()]

    match = await find_best_match(
        scraped_title=scraped.title,
        scraped_brand=scraped.brand,
        candidates=candidates,
    )

    if not match:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_IN_CATALOG",
                "message": "Bu ürün henüz katalogumuzda yok.",
            },
        )

    matched_product, matched_variant = match

    # Tam ürün verisini yükle
    product_full = (await db.execute(
        select(Product)
        .options(
            selectinload(Product.variants).selectinload(ProductVariant.stores),
            selectinload(Product.stores),
        )
        .where(Product.id == matched_product.id)
    )).scalar_one()
    variant_full = next((v for v in product_full.variants if v.id == matched_variant.id), matched_variant)

    return MatchUrlResponse(
        product_id=matched_product.id,
        variant_id=matched_variant.id,
        product=product_full,
        variant=variant_full,
        matched_store_url=scraped.url,
        already_tracked=False,
    )


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

    result = await db.execute(query.limit(365))  # Son 1 yıl
    return result.scalars().all()
