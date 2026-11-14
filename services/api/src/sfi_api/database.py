from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sfi_api.config import get_settings

settings = get_settings()
_engine = None
_session_factory = None


def _async_database_url(value: str):
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode
    query.pop("channel_binding", None)
    return url.set(query=query)


if settings.database_url:
    _engine = create_async_engine(
        _async_database_url(settings.database_url),
        pool_pre_ping=True,
        pool_recycle=300,
    )
    _session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("SFI_DATABASE_URL não foi configurada.")
    async with _session_factory() as session:
        yield session


async def check_database() -> bool:
    if _engine is None:
        return False
    async with _engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True


async def dispose_database() -> None:
    if _engine is not None:
        await _engine.dispose()
