import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import app.database.control_models  # noqa: F401
import app.database.models  # noqa: F401
from app.database.base import Base


def metadata():
    plane = os.getenv("MIGRATION_PLANE", "clinic")
    tables = {
        k: v
        for k, v in Base.metadata.tables.items()
        if (k == "clinic_registry") == (plane == "control")
    }
    from sqlalchemy import MetaData

    m = MetaData()
    for table in tables.values():
        table.to_metadata(m)
    return m


async def run():
    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        await conn.run_sync(
            lambda c: context.configure(connection=c, target_metadata=metadata(), compare_type=True)
        )
        await conn.run_sync(lambda _: context.run_migrations())
    await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=os.environ["DATABASE_URL"], target_metadata=metadata(), literal_binds=True
    )
    context.run_migrations()
else:
    asyncio.run(run())
