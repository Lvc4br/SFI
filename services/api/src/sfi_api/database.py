from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sfi_api.config import get_settings

settings = get_settings()
_engine = None
_session_factory = None

if settings.database_url:
    url = settings.database_url.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )
    _engine = create_async_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("DATABASE_URL não foi configurada.")

    async with _session_factory() as session:
        yield session


async def check_database() -> bool:
    if _engine is None:
        return False

    from sqlalchemy import text

    async with _engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return True


async def dispose_database() -> None:
    if _engine is not None:
        await _engine.dispose()
