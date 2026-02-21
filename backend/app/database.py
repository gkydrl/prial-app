from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


def _build_url(url: str) -> str:
    """
    Railway / Heroku tarzı postgres:// URL'lerini psycopg3 async formatına çevirir.
    psycopg3 (postgresql+psycopg) Railway pgbouncer transaction mode ile uyumludur.
    """
    # asyncpg URL'i varsa da psycopg'ye çevir
    url = url.replace("postgresql+asyncpg://", "postgresql+psycopg://")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # sslmode query param'larını temizle (connect_args ile yönetilir)
    for param in ("?sslmode=require", "&sslmode=require", "?sslmode=disable", "&sslmode=disable"):
        url = url.replace(param, "")
    return url


engine = create_async_engine(
    _build_url(settings.database_url),
    echo=settings.debug,
    # Railway pgbouncer (transaction mode) uyumluluğu:
    # - NullPool: pgbouncer zaten pooling yapıyor, SQLAlchemy pool'u gereksiz
    # - prepare_threshold=None: psycopg3 server-side prepared statement kullanmaz
    poolclass=NullPool,
    connect_args={"prepare_threshold": None},
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
