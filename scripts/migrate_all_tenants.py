"""Upgrade the control database and every active tenant database to Alembic head."""

import asyncio
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.clinic_resolution.service import resolver
from app.database.control_models import ClinicRegistry
from app.database.sessions import ControlSession


def upgrade(url: str, plane: str) -> None:
    previous_url, previous_plane = os.environ.get("DATABASE_URL"), os.environ.get("MIGRATION_PLANE")
    try:
        os.environ["DATABASE_URL"] = url
        os.environ["MIGRATION_PLANE"] = plane
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        if previous_plane is None:
            os.environ.pop("MIGRATION_PLANE", None)
        else:
            os.environ["MIGRATION_PLANE"] = previous_plane


async def tenant_urls() -> list[tuple[str, str]]:
    async with ControlSession() as session:
        rows = (
            await session.scalars(select(ClinicRegistry).where(ClinicRegistry.is_active.is_(True)))
        ).all()
        return [(row.slug, resolver._decrypt(row.encrypted_database_url)) for row in rows]


def main() -> None:
    control_url = os.environ["CONTROL_DATABASE_URL"]
    upgrade(control_url, "control")
    for slug, database_url in asyncio.run(tenant_urls()):
        print(f"Migrating tenant {slug}", flush=True)
        upgrade(database_url, "clinic")


if __name__ == "__main__":
    main()
