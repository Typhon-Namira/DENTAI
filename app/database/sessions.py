from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()


def make_engine(url: str) -> AsyncEngine:
    options: dict[str, object] = {"pool_pre_ping": True}
    if not url.startswith("sqlite"):
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
