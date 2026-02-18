"""
URL'ye göre doğru scraper'ı seçer ve ürünü veritabanına kaydeder.
"""
import uuid
from decimal import Decimal

from app.services.scraper.base import BaseScraper, ScrapedProduct
from app.services.scraper.trendyol import TrendyolScraper
from app.services.scraper.hepsiburada import HepsiburadaScraper
from app.services.scraper.amazon import AmazonScraper

SCRAPERS: list[BaseScraper] = [
    TrendyolScraper(),
    HepsiburadaScraper(),
    AmazonScraper(),
]


def get_scraper(url: str) -> BaseScraper:
    for scraper in SCRAPERS:
        if scraper.can_handle(url):
            return scraper
    raise ValueError(f"Desteklenmeyen mağaza URL'i: {url}")


async def scrape_url(url: str) -> ScrapedProduct:
    scraper = get_scraper(url)
    return await scraper.scrape(url)


async def scrape_and_save_product(
    url: str,
    user_id: uuid.UUID,
    target_price: Decimal,
) -> None:
    """Arka planda çalışır: scrape et, kaydet, alarm kur."""
    from app.database import AsyncSessionLocal
    from app.models.product import Product, ProductStore, StoreName
    from app.models.price_history import PriceHistory
    from app.models.alarm import Alarm, AlarmStatus

    try:
        scraped = await scrape_url(url)
    except Exception as e:
        # TODO: kullanıcıya hata bildirimi gönder
        print(f"Scraping hatası ({url}): {e}")
        return

    async with AsyncSessionLocal() as db:
        try:
            # Ürün oluştur
            product = Product(
                title=scraped.title,
                brand=scraped.brand,
                description=scraped.description,
                image_url=scraped.image_url,
                lowest_price_ever=scraped.current_price,
                alarm_count=1,
            )
            db.add(product)
            await db.flush()

            # Mağaza kaydı
            store_enum = StoreName(scraped.store)
            product_store = ProductStore(
                product_id=product.id,
                store=store_enum,
                store_product_id=scraped.store_product_id,
                url=scraped.url,
                current_price=scraped.current_price,
                original_price=scraped.original_price,
                discount_percent=scraped.discount_percent,
                in_stock=scraped.in_stock,
            )
            db.add(product_store)
            await db.flush()

            # Fiyat geçmişi
            history = PriceHistory(
                product_store_id=product_store.id,
                price=scraped.current_price,
                original_price=scraped.original_price,
                in_stock=scraped.in_stock,
            )
            db.add(history)

            # Alarm
            alarm = Alarm(
                user_id=user_id,
                product_id=product.id,
                product_store_id=product_store.id,
                target_price=target_price,
                status=AlarmStatus.ACTIVE,
            )
            db.add(alarm)

            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Veritabanı kayıt hatası: {e}")
