from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.routers import auth, users, products, alarms, home, discover, admin, store_panel

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tablolar alembic migration ile oluşturuluyor (start.sh → alembic upgrade head)
    import app.models  # noqa: F401 — modelleri register et

    from app.services.price_tracker import check_due_prices
    from app.services.catalog_crawler import crawl_all_variants
    from app.services.summary_service import send_daily_summaries, send_weekly_summaries
    from app.services.product_discovery import discover_daily
    from app.services.akakce.importer import bulk_import as akakce_bulk_import, daily_enrichment_full as akakce_daily_enrichment_full
    from app.services.review_enrichment import enrich_reviews_daily
    from app.services.prediction.runner import run_daily_predictions
    from app.services.prediction.evaluator import evaluate_predictions
    from app.services.exchange_rate import fetch_and_store_rates
    from app.services.pipeline_monitor import run_monitored
    from app.services.data_quality import run_data_quality_check

    # ── Yüksek frekanslı job'lar (monitörlenmez, çok sık) ──

    scheduler.add_job(
        check_due_prices,
        trigger="interval",
        minutes=15,
        id="price_check",
        replace_existing=True,
    )

    scheduler.add_job(
        fetch_and_store_rates,
        trigger="interval",
        hours=1,
        id="exchange_rate_update",
        replace_existing=True,
    )

    # ── Gece pipeline'ı (monitörlü) ──

    # 02:00 — Akakce yeni ürün import
    async def _akakce_bulk():
        await run_monitored("akakce_bulk_import", akakce_bulk_import(batch_size=50, only_new=True))

    scheduler.add_job(
        _akakce_bulk,
        trigger="cron",
        hour=2, minute=0,
        id="akakce_bulk_import",
        replace_existing=True,
    )

    # 03:00 — Full enrichment (tüm ürünler, ~90dk)
    async def _enrichment_full():
        await run_monitored("akakce_enrichment_full", akakce_daily_enrichment_full())

    scheduler.add_job(
        _enrichment_full,
        trigger="cron",
        hour=3, minute=0,
        id="akakce_daily_enrichment_full",
        replace_existing=True,
    )

    # 04:00 — Ürün keşfi
    async def _discover():
        await run_monitored("product_discovery", discover_daily())

    scheduler.add_job(
        _discover,
        trigger="cron",
        hour=4, minute=0,
        id="product_discovery",
        replace_existing=True,
    )

    # 04:30 — Katalog crawl (mağazasız ürünler için store ara — her gün)
    async def _daily_crawl():
        await run_monitored("daily_catalog_crawl", crawl_all_variants(new_only=True))

    scheduler.add_job(
        _daily_crawl,
        trigger="cron",
        hour=4, minute=30,
        id="daily_catalog_crawl",
        replace_existing=True,
    )

    # 05:00 — Review enrichment (500 ürün/gün — Haiku'yu besler)
    async def _review():
        await run_monitored("review_enrichment", enrich_reviews_daily(batch_size=500))

    scheduler.add_job(
        _review,
        trigger="cron",
        hour=5, minute=0,
        id="review_enrichment",
        replace_existing=True,
    )

    # 06:00 — AI tahminleri
    async def _predictions():
        await run_monitored("daily_predictions", run_daily_predictions())

    scheduler.add_job(
        _predictions,
        trigger="cron",
        hour=6, minute=0,
        id="daily_predictions",
        replace_existing=True,
    )

    # 07:00 — Tahmin değerlendirme
    async def _evaluate():
        await run_monitored("prediction_evaluation", evaluate_predictions())

    scheduler.add_job(
        _evaluate,
        trigger="cron",
        hour=7, minute=0,
        id="prediction_evaluation",
        replace_existing=True,
    )

    # 08:00 — Veri kalitesi kontrolü (tüm gece pipeline'ı bittikten sonra)
    async def _quality():
        await run_monitored("data_quality_check", run_data_quality_check())

    scheduler.add_job(
        _quality,
        trigger="cron",
        hour=8, minute=0,
        id="data_quality_check",
        replace_existing=True,
    )

    # 10:00 — Günlük özet bildirimi
    async def _daily_summary():
        await run_monitored("daily_summary", send_daily_summaries())

    scheduler.add_job(
        _daily_summary,
        trigger="cron",
        hour=10, minute=0,
        id="daily_summary",
        replace_existing=True,
    )

    # Haftalık — Pazar 03:00 katalog taraması
    async def _catalog_crawl():
        await run_monitored("catalog_crawl", crawl_all_variants(new_only=True))

    scheduler.add_job(
        _catalog_crawl,
        trigger="cron",
        day_of_week="sun",
        hour=3, minute=0,
        id="catalog_crawl",
        replace_existing=True,
    )

    # Haftalık — Pazartesi 10:00 haftalık özet
    async def _weekly_summary():
        await run_monitored("weekly_summary", send_weekly_summaries())

    scheduler.add_job(
        _weekly_summary,
        trigger="cron",
        day_of_week="mon",
        hour=10, minute=0,
        id="weekly_summary",
        replace_existing=True,
    )

    scheduler.start()

    yield

    # Uygulama kapanırken
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(alarms.router, prefix="/api/v1")
app.include_router(home.router, prefix="/api/v1")
app.include_router(discover.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(store_panel.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/health/deep")
async def health_deep():
    """Tum kritik endpoint'leri ve DB baglantisini kontrol eder."""
    import time
    from sqlalchemy import text
    from app.database import AsyncSessionLocal

    results = {}
    all_ok = True
    start = time.time()

    # 1. DB baglantisi
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        results["database"] = "ok"
    except Exception as e:
        results["database"] = f"FAIL: {str(e)[:100]}"
        all_ok = False

    # 2. Kritik endpoint'leri internal olarak test et
    from starlette.testclient import TestClient
    import httpx

    checks = [
        ("discover_categories", "/api/v1/discover/categories"),
        ("discover_products", "/api/v1/discover/products?page=1&page_size=1"),
        ("home_daily_deals", "/api/v1/home/daily-deals?limit=1"),
        ("home_top_drops", "/api/v1/home/top-drops?limit=1"),
        ("home_most_alarmed", "/api/v1/home/most-alarmed?limit=1"),
        ("products_list", "/api/v1/products?limit=1"),
    ]

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        for name, path in checks:
            try:
                resp = await client.get(path)
                if resp.status_code == 200:
                    results[name] = "ok"
                else:
                    results[name] = f"FAIL: HTTP {resp.status_code}"
                    all_ok = False
            except Exception as e:
                results[name] = f"FAIL: {str(e)[:100]}"
                all_ok = False

    elapsed = round((time.time() - start) * 1000)

    return {
        "status": "ok" if all_ok else "degraded",
        "version": settings.app_version,
        "checks": results,
        "elapsed_ms": elapsed,
    }
