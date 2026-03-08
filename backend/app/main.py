from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.routers import auth, users, products, alarms, home, discover, admin

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tüm tabloları oluştur (henüz yoksa)
    from app.database import engine, Base
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Öncelik kuyruğuna göre fiyat takip zamanlayıcısı
    # Her 15 dakikada çalışır; sadece next_check_at'i geçmiş store'ları işler.
    from app.services.price_tracker import check_due_prices
    from app.services.catalog_crawler import crawl_all_variants
    from app.services.summary_service import send_daily_summaries, send_weekly_summaries

    scheduler.add_job(
        check_due_prices,
        trigger="interval",
        minutes=15,
        id="price_check",
        replace_existing=True,
    )

    # Günlük katalog taraması — her gece 03:00'da
    scheduler.add_job(
        crawl_all_variants,
        trigger="cron",
        hour=3,
        minute=0,
        id="catalog_crawl",
        replace_existing=True,
    )

    # Günlük özet bildirimi — her gün 09:00
    scheduler.add_job(
        send_daily_summaries,
        trigger="cron",
        hour=9,
        minute=0,
        id="daily_summary",
        replace_existing=True,
    )

    # Haftalık özet bildirimi — her Pazartesi 10:00
    scheduler.add_job(
        send_weekly_summaries,
        trigger="cron",
        day_of_week="mon",
        hour=10,
        minute=0,
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
