"""
URL'ye göre doğru scraper'ı seçer ve ürünü veritabanına kaydeder.
"""
import uuid
from decimal import Decimal

from app.services.scraper.base import BaseScraper, ScrapedProduct
from app.services.scraper.trendyol import TrendyolScraper
from app.services.scraper.hepsiburada import HepsiburadaScraper
# Amazon devre dışı — fiyat/stok verileri güvenilmez (USD karışıklığı)
# from app.services.scraper.amazon import AmazonScraper
from app.services.scraper.n11 import N11Scraper
from app.services.scraper.mediamarkt import MediaMarktScraper
# Vatan devre dışı — taksit fiyatı scrape ediyor (7.50 TL Samsung Watch gibi)
# from app.services.scraper.vatan import VatanScraper
from app.services.scraper.universal_scraper import UniversalScraper

# Bilinen siteler — sırayla denenir
SCRAPERS: list[BaseScraper] = [
    TrendyolScraper(),
    HepsiburadaScraper(),
    N11Scraper(),
    MediaMarktScraper(),
]

_universal = UniversalScraper()


def get_scraper(url: str) -> BaseScraper:
    """Bilinen siteler için özel scraper, bilinmeyenler için UniversalScraper döner."""
    for scraper in SCRAPERS:
        if scraper.can_handle(url):
            return scraper
    return _universal


async def scrape_url(url: str) -> ScrapedProduct:
    scraper = get_scraper(url)
    return await scraper.scrape(url)


async def _trigger_initial_prediction(product_id: uuid.UUID) -> None:
    """
    Yeni eklenen ürün için hemen tahmin üret.
    predict_for_product 2+ fiyat noktası istiyor — yeni ürünlerde 1 tane var.
    Burada tek fiyat noktasıyla basit bir tahmin yapıp kaydediyoruz.
    """
    from app.database import AsyncSessionLocal
    from app.models.product import Product, ProductStore
    from app.models.price_history import PriceHistory
    from app.models.prediction import PricePrediction
    from app.services.prediction.analyzer import compute_features, PricePoint
    from app.services.prediction.predictor import predict_and_save
    from app.services.prediction.reasoning_generator import generate_reasoning_text
    from sqlalchemy import select, func
    from sqlalchemy.orm import selectinload
    from datetime import date, timedelta

    async with AsyncSessionLocal() as db:
        product = await db.get(Product, product_id, options=[selectinload(Product.category)])
        if not product:
            return

        # Mevcut en düşük fiyat
        price_result = await db.execute(
            select(func.min(ProductStore.current_price))
            .where(
                ProductStore.product_id == product_id,
                ProductStore.is_active == True,  # noqa: E712
                ProductStore.current_price.isnot(None),
            )
        )
        current_price = price_result.scalar_one_or_none()
        if not current_price:
            return

        # Fiyat geçmişi — yeni üründe 1 nokta olabilir, 2. noktayı oluştur
        store_ids_result = await db.execute(
            select(ProductStore.id).where(ProductStore.product_id == product_id)
        )
        store_ids = [row[0] for row in store_ids_result.all()]

        history_result = await db.execute(
            select(PriceHistory.recorded_at, PriceHistory.price)
            .where(
                PriceHistory.product_store_id.in_(store_ids),
                PriceHistory.price > 0,
            )
            .order_by(PriceHistory.recorded_at.asc())
        )
        history_rows = history_result.all()

        # Minimum 1 nokta gerekli — 2. noktayı aynı fiyatla bir gün önce sentetik ekle
        today = date.today()
        if len(history_rows) == 1:
            price_history = [
                PricePoint(date=today - timedelta(days=1), price=float(history_rows[0].price)),
                PricePoint(date=today, price=float(current_price)),
            ]
        elif len(history_rows) >= 2:
            price_history = [
                PricePoint(date=row.recorded_at.date(), price=float(row.price))
                for row in history_rows
            ]
        else:
            return

        cat_name = product.category.name if product.category else None
        features = compute_features(
            current_price=float(current_price),
            price_history=price_history,
            l1y_min=float(product.l1y_lowest_price) if product.l1y_lowest_price else None,
            l1y_max=float(product.l1y_highest_price) if product.l1y_highest_price else None,
            category_slug=cat_name,
        )

        prediction = await predict_and_save(
            product_id=product_id,
            current_price=float(current_price),
            features=features,
            db=db,
            category_id=product.category_id,
        )

        # Reasoning text üret (V3 JSON — summary + pros + cons)
        wait_days = getattr(prediction, '_wait_days', None)
        expected_price = getattr(prediction, '_expected_price', None)

        try:
            reasoning_text = await generate_reasoning_text(
                product_title=product.title,
                recommendation=prediction.recommendation.value,
                confidence=float(prediction.confidence),
                current_price=float(current_price),
                reasoning=prediction.reasoning or {},
                l1y_lowest=float(product.l1y_lowest_price) if product.l1y_lowest_price else None,
                l1y_highest=float(product.l1y_highest_price) if product.l1y_highest_price else None,
                predicted_direction=prediction.predicted_direction.value,
                review_summary=product.review_summary,
                wait_days=wait_days,
                expected_price=expected_price,
                event_details=features.event_details,
            )
            prediction.reasoning_text = reasoning_text
        except Exception as e:
            print(f"[dispatcher] Reasoning hatası: {e}")

        await db.commit()
        print(f"[dispatcher] Yeni ürün tahmini oluşturuldu: {product.title[:50]} → {prediction.recommendation.value}")


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
            from app.services.variant_extractor import extract_attributes, find_or_create_variant
            from app.services.short_title_generator import generate_short_title

            short_title = await generate_short_title(scraped.brand, scraped.title)

            # Ürün oluştur
            product = Product(
                title=scraped.title,
                short_title=short_title,
                brand=scraped.brand,
                description=scraped.description,
                image_url=scraped.image_url,
                lowest_price_ever=scraped.current_price,
                alarm_count=1,
            )
            db.add(product)
            await db.flush()

            # Variant oluştur / bul
            attributes = extract_attributes(scraped.title)
            variant = await find_or_create_variant(
                db,
                product_id=product.id,
                attributes=attributes,
                image_url=scraped.image_url,
            )
            variant.alarm_count += 1
            variant.lowest_price_ever = scraped.current_price
            db.add(variant)
            await db.flush()

            # Mağaza kaydı
            store_enum = StoreName(scraped.store)
            product_store = ProductStore(
                product_id=product.id,
                variant_id=variant.id,
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
                variant_id=variant.id,
                product_store_id=product_store.id,
                target_price=target_price,
                status=AlarmStatus.ACTIVE,
            )
            db.add(alarm)

            await db.commit()

            # On-demand prediction: yeni ürün için hemen AI analizi üret
            # Arka planda çalışır, başarısız olursa ertesi gün run_daily_predictions yakalar
            try:
                await _trigger_initial_prediction(product.id)
            except Exception as pred_err:
                print(f"[dispatcher] İlk tahmin hatası ({product.title[:40]}): {pred_err}")

        except Exception as e:
            await db.rollback()
            print(f"Veritabanı kayıt hatası: {e}")
