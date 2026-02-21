import ssl

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


def _clean_url(url: str) -> str:
    """
    Railway / Heroku tarzı postgres:// URL'lerini asyncpg formatına çevirir
    ve sslmode query param'ını kaldırır (SSL connect_args ile yönetilir).
    """
    # postgres:// → postgresql+asyncpg://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # sslmode query param'larını temizle
    for param in ("?sslmode=require", "&sslmode=require", "?sslmode=disable", "&sslmode=disable"):
        url = url.replace(param, "")
    return url


def _make_ssl_context() -> ssl.SSLContext:
    """Railway gibi self-signed cert kullanan DB'ler için: şifreli ama cert doğrulamasız."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


engine = create_async_engine(
    _clean_url(settings.database_url),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
    connect_args={"ssl": _make_ssl_context()},
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
