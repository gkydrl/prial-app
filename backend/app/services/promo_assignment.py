"""
Alarm tetiklendiğinde kullanıcıya kampanya kodu atama servisi.

Akış:
1. Tetiklenen alarm'ın ürünü + mağazası için aktif kampanyaları bul
2. Fiyat bandı filtresi uygula
3. Zaten atanmış mı kontrol et
4. Unique kodlarsa havuzdan ata, fixed kodsa direkt kaydet
5. Kodu döndür (push bildiriminde kullanılacak)
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alarm import Alarm
from app.models.product import ProductStore
from app.models.campaign import (
    Campaign,
    campaign_products,
    CodePool,
    UserPromoAssignment,
)


async def assign_promo_for_alarm(
    db: AsyncSession,
    alarm: Alarm,
    store: ProductStore,
    new_price: Decimal,
) -> str | None:
    """
    Tetiklenen alarm için uygun kampanya var mı kontrol et.
    Varsa havuzdan kod ata ve user_promo_assignments'a kaydet.
    Kodu döndür (push bildiriminde kullanılacak).
    """
    now = datetime.now(timezone.utc)

    # 1. Bu ürün için aktif kampanyaları bul (kampanyanın mağazası, alarm'ın store'u ile eşleşmeli)
    # campaign_products üzerinden bu product_id'ye bağlı kampanyaları çek
    result = await db.execute(
        select(Campaign)
        .join(campaign_products, campaign_products.c.campaign_id == Campaign.id)
        .join(
            # Kampanyayı oluşturan mağaza hesabının store'u ile ürünün store'u eşleşmeli
            Campaign.store_account,
        )
        .where(
            campaign_products.c.product_id == alarm.product_id,
            Campaign.is_active == True,
            Campaign.starts_at <= now,
            Campaign.expires_at > now,
        )
    )
    campaigns = result.scalars().all()

    if not campaigns:
        return None

    for campaign in campaigns:
        # 2. Fiyat bandı filtresi: alarm.target_price bandın içinde mi?
        if campaign.target_price_min is not None and alarm.target_price < campaign.target_price_min:
            continue
        if campaign.target_price_max is not None and alarm.target_price > campaign.target_price_max:
            continue

        # 3. Bu user + product + campaign için zaten atanmış mı?
        existing = await db.execute(
            select(UserPromoAssignment.id).where(
                and_(
                    UserPromoAssignment.user_id == alarm.user_id,
                    UserPromoAssignment.campaign_id == campaign.id,
                    UserPromoAssignment.product_id == alarm.product_id,
                )
            ).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue

        code: str | None = None

        if campaign.is_unique_codes:
            # 4. Havuzdan atanmamış ilk kodu al
            pool_result = await db.execute(
                select(CodePool).where(
                    CodePool.campaign_id == campaign.id,
                    CodePool.assigned_to == None,
                ).limit(1).with_for_update(skip_locked=True)
            )
            pool_item = pool_result.scalar_one_or_none()
            if pool_item is None:
                continue  # Havuzda kod kalmamış

            pool_item.assigned_to = alarm.user_id
            pool_item.assigned_at = now
            db.add(pool_item)
            code = pool_item.code
        else:
            # 5. Fixed kod
            if not campaign.fixed_code:
                continue
            code = campaign.fixed_code

        # 6. user_promo_assignments'a kaydet
        assignment = UserPromoAssignment(
            user_id=alarm.user_id,
            campaign_id=campaign.id,
            product_id=alarm.product_id,
            code=code,
            assigned_at=now,
        )
        db.add(assignment)

        return code

    return None
