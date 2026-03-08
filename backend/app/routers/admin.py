"""
Admin endpoints — ürün kataloğu yönetimi.
X-Admin-Key header ile korunur.
"""
import uuid
from decimal import Decimal
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.product import Product, ProductStore, ProductVariant
from app.models.user import User
from app.models.category import Category
from app.schemas.admin import AdminProductCreate, AdminProductResponse

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> None:
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Yetkisiz")


@router.post("/products", response_model=AdminProductResponse, status_code=201)
async def seed_product(
    payload: AdminProductCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """
    Ürünü store URL'siz kataloga ekler.
    Crawler günlük olarak mağaza bağlantılarını otomatik kurar.
    """
    # Kategori bul
    category_id: uuid.UUID | None = None
    if payload.category_slug:
        res = await db.execute(
            select(Category).where(Category.slug == payload.category_slug)
        )
        cat = res.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail=f"Kategori bulunamadı: {payload.category_slug}")
        category_id = cat.id

    # Aynı brand+title zaten var mı?
    dup_q = select(Product).where(Product.title == payload.title)
    if payload.brand:
        dup_q = dup_q.where(Product.brand == payload.brand)
    dup = (await db.execute(dup_q)).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status_code=409,
            detail={"code": "PRODUCT_EXISTS", "product_id": str(dup.id)},
        )

    # Ürünü oluştur
    product = Product(
        title=payload.title,
        brand=payload.brand,
        description=payload.description,
        image_url=payload.image_url,
        category_id=category_id,
        alarm_count=0,
    )
    db.add(product)
    await db.flush()

    # Variantları oluştur
    variant_inputs = payload.variants or [{"title": None, "attributes": {}, "image_url": None}]
    for vi in variant_inputs:
        attrs = vi.attributes if isinstance(vi, dict) else vi.attributes
        title = vi.title if isinstance(vi, dict) else vi.title
        img = vi.image_url if isinstance(vi, dict) else vi.image_url

        variant = ProductVariant(
            product_id=product.id,
            title=title,
            attributes=attrs or {},
            image_url=img or payload.image_url,
        )
        db.add(variant)

    await db.commit()

    return AdminProductResponse(
        id=product.id,
        title=product.title,
        brand=product.brand,
        variant_count=len(variant_inputs),
    )


@router.post("/products/{product_id}/variants", status_code=201)
async def add_variant(
    product_id: uuid.UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Mevcut ürüne yeni variant ekler."""
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")

    variant = ProductVariant(
        product_id=product_id,
        title=payload.get("title"),
        attributes=payload.get("attributes", {}),
        image_url=payload.get("image_url"),
    )
    db.add(variant)
    await db.commit()
    return {"variant_id": str(variant.id)}


@router.get("/products", response_model=list[AdminProductResponse])
async def list_products(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Katalogdaki tüm ürünleri listeler (variant sayısıyla birlikte)."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Product).options(selectinload(Product.variants)).order_by(Product.created_at.desc())
    )
    products = result.scalars().all()
    return [
        AdminProductResponse(
            id=p.id,
            title=p.title,
            brand=p.brand,
            variant_count=len(p.variants),
        )
        for p in products
    ]


@router.get("/debug/config")
async def debug_config(_: None = Depends(require_admin)):
    """Railway'deki config değerlerini kontrol eder (key'ler maskelenir)."""
    key = settings.scraper_api_key
    anthropic = settings.anthropic_api_key
    return {
        "scraper_api_key": f"{key[:6]}...{key[-4:]}" if len(key) > 10 else f"({len(key)} karakter — ÇOK KISA)",
        "anthropic_api_key_set": bool(anthropic),
        "admin_api_key": f"{settings.admin_api_key[:4]}...",
        "crawler_search_concurrency": settings.crawler_search_concurrency,
        "crawler_results_per_store": settings.crawler_results_per_store,
    }



@router.post("/crawl/trigger")
async def trigger_crawl(
    background_tasks: BackgroundTasks,
    new_only: bool = False,
    _: None = Depends(require_admin),
):
    """Katalog crawler'ını manuel tetikler. new_only=true → sadece mağazasız variant'ları işler."""
    from app.services.catalog_crawler import crawl_all_variants

    async def _run():
        await crawl_all_variants(new_only=new_only)

    background_tasks.add_task(_run)
    mode = "sadece yeni variant'lar" if new_only else "tüm variant'lar"
    return {"message": f"Crawler başlatıldı ({mode}, arka planda çalışıyor)"}


# ─── Push Notification Test Endpoints ────────────────────────────────────────


@router.post("/test-notifications/target-reached")
async def test_target_reached(
    user_email: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Senaryo 1: Hedef fiyata ulaşıldı bildirimi test eder."""
    from app.services.notification_service import _send_push
    from app.models.notification import NotificationCategory

    user = await _get_test_user(db, user_email)
    await _send_push(
        user=user,
        title="🎯 Hedefine ulaştın!",
        body="iPhone 16 Pro Max artık 44.799 ₺. Hemen al!",
        category=NotificationCategory.TARGET_REACHED,
        data={"test": "true"},
        db=db,
    )
    await db.commit()
    return {"status": "sent", "scenario": "target_reached"}


@router.post("/test-notifications/price-drop")
async def test_price_drop(
    user_email: str,
    drop_percent: int = 15,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Senaryo 2/3: Fiyat düşüşü bildirimi test eder."""
    from app.services.notification_service import _send_push
    from app.models.notification import NotificationCategory

    user = await _get_test_user(db, user_email)
    if drop_percent >= 20:
        title = "🔥 Büyük indirim!"
        body = "AirPods Pro 2 %20 düştü, şu an 5.299 ₺"
    else:
        title = "📉 AirPods Pro 2 %10 indi!"
        body = "Şu an 6.299 ₺ — hedefe yaklaşıyor"
    await _send_push(
        user=user,
        title=title,
        body=body,
        category=NotificationCategory.PRICE_DROP,
        data={"test": "true"},
        db=db,
    )
    await db.commit()
    return {"status": "sent", "scenario": "price_drop", "percent": drop_percent}


@router.post("/test-notifications/milestone")
async def test_milestone(
    user_email: str,
    milestone: int = 100,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Senaryo 4: Topluluk milestone bildirimi test eder."""
    from app.services.notification_service import _send_push
    from app.models.notification import NotificationCategory

    user = await _get_test_user(db, user_email)
    count_str = f"{milestone:,}".replace(",", ".")
    await _send_push(
        user=user,
        title="🚀 MacBook Air M3 trend oldu!",
        body=f"{count_str} kişi bu ürünü bekliyor, sen de katıl",
        category=NotificationCategory.MILESTONE,
        data={"test": "true"},
        db=db,
    )
    await db.commit()
    return {"status": "sent", "scenario": "milestone", "count": milestone}


@router.post("/test-notifications/daily-summary")
async def test_daily_summary(
    user_email: str,
    drop_count: int = 3,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Senaryo 5: Günlük özet bildirimi test eder."""
    from app.services.notification_service import notify_daily_summary

    user = await _get_test_user(db, user_email)
    await notify_daily_summary(user=user, drop_count=drop_count, db=db)
    await db.commit()
    return {"status": "sent", "scenario": "daily_summary", "drop_count": drop_count}


@router.post("/test-notifications/weekly-summary")
async def test_weekly_summary(
    user_email: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Senaryo 6: Haftalık özet bildirimi test eder."""
    from app.services.notification_service import notify_weekly_summary

    user = await _get_test_user(db, user_email)
    await notify_weekly_summary(
        user=user,
        top_product_name="iPhone 16 Pro Max 256GB",
        drop_percent=18,
        db=db,
    )
    await db.commit()
    return {"status": "sent", "scenario": "weekly_summary"}


@router.post("/test-notifications/all")
async def test_all_notifications(
    user_email: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Tüm 6 senaryoyu sırayla test eder."""
    from app.services.notification_service import (
        _send_push, notify_daily_summary, notify_weekly_summary,
    )
    from app.models.notification import NotificationCategory

    user = await _get_test_user(db, user_email)
    results = []

    # 1. Target reached
    await _send_push(
        user=user,
        title="🎯 Hedefine ulaştın!",
        body="iPhone 16 Pro Max artık 44.799 ₺. Hemen al!",
        category=NotificationCategory.TARGET_REACHED,
        data={"test": "true"},
        db=db,
    )
    results.append("target_reached")

    # 2. Price drop %10
    await _send_push(
        user=user,
        title="📉 AirPods Pro 2 %10 indi!",
        body="Şu an 6.299 ₺ — hedefe yaklaşıyor",
        category=NotificationCategory.PRICE_DROP,
        data={"test": "true"},
        db=db,
    )
    results.append("price_drop_10")

    # 3. Price drop %20
    await _send_push(
        user=user,
        title="🔥 Büyük indirim!",
        body="Samsung Galaxy S24 %20 düştü, şu an 29.999 ₺",
        category=NotificationCategory.PRICE_DROP,
        data={"test": "true"},
        db=db,
    )
    results.append("price_drop_20")

    # 4. Milestone
    await _send_push(
        user=user,
        title="🚀 MacBook Air M3 trend oldu!",
        body="500 kişi bu ürünü bekliyor, sen de katıl",
        category=NotificationCategory.MILESTONE,
        data={"test": "true"},
        db=db,
    )
    results.append("milestone")

    # 5. Daily summary
    await notify_daily_summary(user=user, drop_count=5, db=db)
    results.append("daily_summary")

    # 6. Weekly summary
    await notify_weekly_summary(
        user=user,
        top_product_name="iPad Air M2 256GB",
        drop_percent=22,
        db=db,
    )
    results.append("weekly_summary")

    await db.commit()
    return {"status": "all_sent", "scenarios": results}


async def _get_test_user(db: AsyncSession, email: str) -> User:
    """E-posta ile kullanıcıyı bulur, yoksa 404 döner."""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"Kullanıcı bulunamadı: {email}")
    if not user.firebase_token:
        raise HTTPException(status_code=400, detail="Kullanıcının push token'ı yok")
    return user
