from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.routers import auth, users, products, alarms, home, discover

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tüm tabloları oluştur (henüz yoksa)
    from app.database import engine, Base
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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


@app.get("/debug/versions")
async def debug_versions():
    import importlib.metadata
    packages = ["bcrypt", "passlib", "psycopg", "asyncpg", "sqlalchemy"]
    versions = {}
    for pkg in packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            versions[pkg] = "not found"
    return versions


@app.post("/debug/register")
async def debug_register():
    """Register akışını test eder ve gerçek hatayı döndürür."""
    import traceback
    from app.database import AsyncSessionLocal
    from app.models.user import User
    from app.core.security import hash_password, create_access_token, create_refresh_token
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as session:
            existing = await session.execute(select(User).where(User.email == "debug@prial.app"))
            found = existing.scalar_one_or_none()
            if found:
                return {"status": "exists", "user_id": str(found.id)}

            user = User(
                email="debug@prial.app",
                password_hash=hash_password("Debug1234"),
                full_name="Debug User",
            )
            session.add(user)
            await session.flush()
            await session.commit()
            return {"status": "created", "user_id": str(user.id)}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()[-3000:]}

