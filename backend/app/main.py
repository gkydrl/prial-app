from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.routers import auth, users, products, alarms, home, discover

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fiyat takip zamanlayıcısı
    from app.services.price_tracker import check_all_prices

    scheduler.add_job(
        check_all_prices,
        trigger="interval",
        minutes=settings.scrape_interval_minutes,
        id="price_check",
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/debug/db")
async def debug_db():
    import traceback
    from sqlalchemy import text
    from app.database import engine
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            row = result.fetchone()
            # Tablo listesini de al
            tables = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            ))
            return {
                "status": "ok",
                "pg_version": str(row[0]),
                "tables": [r[0] for r in tables.fetchall()],
            }
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()[-2000:]}

