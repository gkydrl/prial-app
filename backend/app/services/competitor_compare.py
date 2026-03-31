"""
Rakip karşılaştırma servisi — aynı kategorideki ürünlerle fiyat/değer kıyası.
Mevcut DB'deki Product + ProductStore üzerinden hesaplanır.
"""
import logging
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductStore

logger = logging.getLogger(__name__)


async def get_category_comparison(product_id, db: AsyncSession) -> dict:
    """
    Ürünün kategori içindeki fiyat pozisyonunu detaylı hesaplar.

    Returns: {
        rank, total_in_category, cheaper_count, more_expensive_count,
        avg_category_price, price_vs_avg_pct, min_price, max_price,
        similar_priced, same_brand_alternatives, percentile,
    }
    """
    # 1. Hedef ürünü al
    target = await db.get(Product, product_id)
    if not target:
        return {"error": "product_not_found"}

    if not target.category_id:
        return {"error": "no_category", "product_title": target.title}

    # 2. Hedef ürünün en düşük aktif fiyatını bul
    target_price_row = await db.execute(
        select(func.min(ProductStore.current_price))
        .where(
            and_(
                ProductStore.product_id == product_id,
                ProductStore.is_active.is_(True),
                ProductStore.in_stock.is_(True),
                ProductStore.current_price.isnot(None),
            )
        )
    )
    target_price = target_price_row.scalar_one_or_none()
    if not target_price:
        return {
            "error": "no_active_price",
            "product_title": target.title,
        }

    # 3. Aynı kategorideki tüm ürünlerin minimum fiyatlarını çek
    category_prices_q = (
        select(
            Product.id,
            Product.title,
            Product.brand,
            func.min(ProductStore.current_price).label("min_price"),
        )
        .join(ProductStore, ProductStore.product_id == Product.id)
        .where(
            and_(
                Product.category_id == target.category_id,
                ProductStore.is_active.is_(True),
                ProductStore.in_stock.is_(True),
                ProductStore.current_price.isnot(None),
            )
        )
        .group_by(Product.id, Product.title, Product.brand)
        .order_by(func.min(ProductStore.current_price))
    )
    rows = (await db.execute(category_prices_q)).all()

    if not rows:
        return {"error": "empty_category", "product_title": target.title}

    # 4. Hesaplamalar
    prices = [float(r.min_price) for r in rows]
    total = len(prices)
    avg_price = sum(prices) / total
    target_price_f = float(target_price)

    # Rank (ucuzdan pahalıya, 1-indexed)
    rank = next((i + 1 for i, r in enumerate(rows) if r.id == product_id), total)
    cheaper_count = rank - 1
    more_expensive_count = total - rank
    percentile = round((rank - 1) / total, 2) if total > 1 else 0.0
    price_vs_avg_pct = round((target_price_f - avg_price) / avg_price * 100, 1) if avg_price > 0 else 0

    # Min/max
    min_row = rows[0]
    max_row = rows[-1]

    # Benzer fiyatlılar (±%15 aralığında, kendisi hariç, max 5)
    lower = target_price_f * 0.85
    upper = target_price_f * 1.15
    similar_priced = [
        {"title": r.title, "brand": r.brand, "price": float(r.min_price)}
        for r in rows
        if r.id != product_id and lower <= float(r.min_price) <= upper
    ][:5]

    # Aynı marka alternatifleri (kendisi hariç, max 5)
    same_brand = [
        {"title": r.title, "price": float(r.min_price)}
        for r in rows
        if r.id != product_id and r.brand and target.brand and r.brand == target.brand
    ][:5]

    return {
        "product_title": target.title,
        "product_brand": target.brand,
        "product_price": target_price_f,
        "category_id": str(target.category_id),
        "rank": rank,
        "total_in_category": total,
        "cheaper_count": cheaper_count,
        "more_expensive_count": more_expensive_count,
        "avg_category_price": round(avg_price, 2),
        "price_vs_avg_pct": price_vs_avg_pct,
        "min_price": {
            "title": min_row.title,
            "brand": min_row.brand,
            "price": float(min_row.min_price),
        },
        "max_price": {
            "title": max_row.title,
            "brand": max_row.brand,
            "price": float(max_row.min_price),
        },
        "similar_priced": similar_priced,
        "same_brand_alternatives": same_brand,
        "percentile": percentile,
    }


async def get_quick_position(product_id, db: AsyncSession) -> dict:
    """Hızlı: rank, total, percentile, avg farkı."""
    target = await db.get(Product, product_id)
    if not target or not target.category_id:
        return {"error": "product_not_found_or_no_category"}

    # Ürünün min fiyatı
    target_price_row = await db.execute(
        select(func.min(ProductStore.current_price))
        .where(
            and_(
                ProductStore.product_id == product_id,
                ProductStore.is_active.is_(True),
                ProductStore.in_stock.is_(True),
                ProductStore.current_price.isnot(None),
            )
        )
    )
    target_price = target_price_row.scalar_one_or_none()
    if not target_price:
        return {"error": "no_active_price"}

    # Kategori istatistikleri (tek sorguda)
    stats_row = await db.execute(
        select(
            func.count(func.distinct(Product.id)).label("total"),
            func.avg(func.min(ProductStore.current_price)).over().label("avg_price"),
        )
        .select_from(Product)
        .join(ProductStore, ProductStore.product_id == Product.id)
        .where(
            and_(
                Product.category_id == target.category_id,
                ProductStore.is_active.is_(True),
                ProductStore.in_stock.is_(True),
                ProductStore.current_price.isnot(None),
            )
        )
    )

    # Daha basit yaklaşım: toplam ve ortalamayı ayrı çek
    total_row = await db.execute(
        select(func.count(func.distinct(Product.id)))
        .select_from(ProductStore)
        .join(Product, Product.id == ProductStore.product_id)
        .where(
            and_(
                Product.category_id == target.category_id,
                ProductStore.is_active.is_(True),
                ProductStore.in_stock.is_(True),
                ProductStore.current_price.isnot(None),
            )
        )
    )
    total = total_row.scalar() or 0

    # Daha ucuz ürün sayısı
    cheaper_subq = (
        select(func.count(func.distinct(Product.id)))
        .select_from(ProductStore)
        .join(Product, Product.id == ProductStore.product_id)
        .where(
            and_(
                Product.category_id == target.category_id,
                ProductStore.is_active.is_(True),
                ProductStore.in_stock.is_(True),
                ProductStore.current_price.isnot(None),
                ProductStore.current_price < target_price,
            )
        )
    )
    cheaper_count = (await db.execute(cheaper_subq)).scalar() or 0

    rank = cheaper_count + 1
    percentile = round((rank - 1) / total, 2) if total > 1 else 0.0

    # Ortalama fiyat (her ürünün min fiyatının ortalaması)
    avg_row = await db.execute(
        select(func.avg(func.min(ProductStore.current_price)))
        .select_from(ProductStore)
        .join(Product, Product.id == ProductStore.product_id)
        .where(
            and_(
                Product.category_id == target.category_id,
                ProductStore.is_active.is_(True),
                ProductStore.in_stock.is_(True),
                ProductStore.current_price.isnot(None),
            )
        )
        .group_by(Product.id)
    )
    # Manuel hesaplama — avg of group-by results
    min_prices = [float(r[0]) for r in avg_row if r[0]]
    avg_price = sum(min_prices) / len(min_prices) if min_prices else 0

    target_price_f = float(target_price)
    price_vs_avg_pct = round((target_price_f - avg_price) / avg_price * 100, 1) if avg_price > 0 else 0

    return {
        "product_title": target.title,
        "product_price": target_price_f,
        "rank": rank,
        "total_in_category": total,
        "percentile": percentile,
        "avg_category_price": round(avg_price, 2),
        "price_vs_avg_pct": price_vs_avg_pct,
    }
