import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

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
    subscription_plan: str | None
    subscription_starts_at: datetime | None
    subscription_expires_at: datetime | None


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

    @staticmethod
    def _ensure_subscription(row: ClinicRegistry) -> None:
        if not row.is_active:
            raise AppError("CLINIC_NOT_FOUND", "Clinic is unavailable.", 404)
        expires_at = row.subscription_expires_at
        if expires_at is None:
            return
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise AppError(
                "SUBSCRIPTION_EXPIRED",
                "This Teta2 Care subscription has expired. Renew the clinic subscription to restore access; existing clinic data is preserved.",
                403,
            )

    async def by_slug(self, db: AsyncSession, slug: str) -> ResolvedClinic:
        row = await db.scalar(select(ClinicRegistry).where(ClinicRegistry.slug == slug.lower()))
        if not row:
            raise AppError("CLINIC_NOT_FOUND", "Clinic is unavailable.", 404)
        self._ensure_subscription(row)
        return ResolvedClinic(
            row.id,
            row.slug,
            row.name,
            self._decrypt(row.encrypted_database_url),
            row.allowed_origins,
            row.subscription_plan,
            row.subscription_starts_at,
            row.subscription_expires_at,
        )

    async def by_id(self, db: AsyncSession, clinic_id: uuid.UUID) -> ResolvedClinic:
        row = await db.get(ClinicRegistry, clinic_id)
        if not row:
            raise AppError("CLINIC_NOT_FOUND", "Clinic is unavailable.", 401)
        self._ensure_subscription(row)
        return ResolvedClinic(
            row.id,
            row.slug,
            row.name,
            self._decrypt(row.encrypted_database_url),
            row.allowed_origins,
            row.subscription_plan,
            row.subscription_starts_at,
            row.subscription_expires_at,
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
