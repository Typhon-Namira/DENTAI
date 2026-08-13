import uuid
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import ClinicRegistry
from app.database.sessions import make_engine


@dataclass(frozen=True)
class ResolvedClinic:
    id: uuid.UUID
    slug: str
    name: str
    database_url: str
    allowed_origins: list[str]


class ClinicResolver:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._engines: dict[uuid.UUID, AsyncEngine] = {}

    def _decrypt(self, value: str) -> str:
        if value.startswith("plain:") and self.settings.app_env in {"development", "test"}:
            return value[6:]
        if not self.settings.tenant_dsn_encryption_key:
            raise RuntimeError("TENANT_DSN_ENCRYPTION_KEY is required")
        try:
            return (
                Fernet(self.settings.tenant_dsn_encryption_key.encode())
                .decrypt(value.encode())
                .decode()
            )
        except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
            raise AppError("CLINIC_CONFIGURATION_INVALID", "Clinic is unavailable.", 503) from exc

    async def by_slug(self, db: AsyncSession, slug: str) -> ResolvedClinic:
        row = await db.scalar(
            select(ClinicRegistry).where(
                ClinicRegistry.slug == slug.lower(), ClinicRegistry.is_active.is_(True)
            )
        )
        if not row:
            raise AppError("CLINIC_NOT_FOUND", "Clinic is unavailable.", 404)
        return ResolvedClinic(
            row.id,
            row.slug,
            row.name,
            self._decrypt(row.encrypted_database_url),
            row.allowed_origins,
        )

    async def by_id(self, db: AsyncSession, clinic_id: uuid.UUID) -> ResolvedClinic:
        row = await db.get(ClinicRegistry, clinic_id)
        if not row or not row.is_active:
            raise AppError("CLINIC_NOT_FOUND", "Clinic is unavailable.", 401)
        return ResolvedClinic(
            row.id,
            row.slug,
            row.name,
            self._decrypt(row.encrypted_database_url),
            row.allowed_origins,
        )

    def session_factory(self, clinic: ResolvedClinic) -> async_sessionmaker[AsyncSession]:
        engine = self._engines.get(clinic.id)
        if not engine:
            if len(self._engines) >= self.settings.max_tenant_engines:
                raise AppError(
                    "TENANT_CAPACITY_REACHED", "Clinic database capacity is unavailable.", 503
                )
            engine = self._engines[clinic.id] = make_engine(clinic.database_url)
        return async_sessionmaker(engine, expire_on_commit=False)

    async def dispose_all(self) -> None:
        engines = list(self._engines.values())
        self._engines.clear()
        for engine in engines:
            await engine.dispose()


resolver = ClinicResolver()
