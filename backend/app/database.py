from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


def _build_url(url: str) -> str:
    """
    Railway / Heroku tarzı postgres:// URL'lerini asyncpg formatına çevirir.
    sslmode query param'ını korur — asyncpg bunu connect_args üzerinden değil
    URL'de desteklemez, bu yüzden tamamen kaldırıyoruz ve SSL'i devre dışı bırakıyoruz.
    Railway internal network'te SSL gerekmez.
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # asyncpg sslmode URL param'ını desteklemez — kaldır
    for param in ("?sslmode=require", "&sslmode=require", "?sslmode=disable", "&sslmode=disable"):
        url = url.replace(param, "")
    return url


engine = create_async_engine(
    _build_url(settings.database_url),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
    # Railway pgbouncer transaction-mode ile uyumluluk için prepared statement cache'i kapat
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
