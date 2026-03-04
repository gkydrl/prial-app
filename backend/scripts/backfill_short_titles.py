"""
Mevcut ürünlere short_title ekler.
Tek seferlik çalıştır: python -m scripts.backfill_short_titles

Railway'de çalıştırmak için:
  railway run python -m scripts.backfill_short_titles
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.product import Product
from app.services.short_title_generator import generate_short_title


async def backfill():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product).where(Product.short_title.is_(None))
        )
        products = result.scalars().all()

    print(f"[backfill] {len(products)} ürün işlenecek...")
    updated = 0

    for product in products:
        short = await generate_short_title(product.brand, product.title)
        async with AsyncSessionLocal() as db:
            p = await db.get(Product, product.id)
            if p:
                p.short_title = short
                db.add(p)
                await db.commit()
        updated += 1
        print(f"  [{updated}/{len(products)}] {product.title[:50]} → {short}")
        # Rate limit için küçük bekleme
        await asyncio.sleep(0.2)

    print(f"[backfill] Tamamlandı. {updated} ürün güncellendi.")


if __name__ == "__main__":
    asyncio.run(backfill())
