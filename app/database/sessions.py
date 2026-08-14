from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()


def make_engine(url: str) -> AsyncEngine:
    options: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        # SQLite is a local/test fallback. Avoid retaining aiosqlite worker
        # threads across request or event-loop lifetimes.
        options["poolclass"] = NullPool
    else:
        options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
        )
    return create_async_engine(url, **options)


control_engine = make_engine(settings.control_database_url)
ControlSession = async_sessionmaker(control_engine, expire_on_commit=False)


async def control_session() -> AsyncIterator[AsyncSession]:
    async with ControlSession() as session:
        yield session


async def dispose_control_engine() -> None:
    await control_engine.dispose()
