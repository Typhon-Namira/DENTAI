import asyncio
import os
import re
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.care.models import CareAppointment
from app.clinic_resolution.service import resolver
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import (
    ClinicRegistry,
    PlatformAccessRequest,
    PlatformAdminEvent,
    PlatformBillingSettings,
)
from app.database.models import AIAnalysis, Branch, Patient, Role, User, UserBranchScope, Visit, XRay

SUBSCRIPTION_DAYS = 30
PLAN_CODE = "TETA2_CARE"
PLAN_NAME = "Teta2 Care"
ACTIVE_SUBSCRIPTION = "ACTIVE"

_migration_lock = asyncio.Lock()


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) < 3 or len(slug) > 80:
        raise AppError("INVALID_CLINIC_SLUG", "Clinic slug must be 3 to 80 characters.", 422)
    return slug


def subscription_expired(clinic: ClinicRegistry, now: datetime | None = None) -> bool:
    if clinic.subscription_status != ACTIVE_SUBSCRIPTION:
        return True
    if clinic.subscription_ends_at is None:
        return False
    end = clinic.subscription_ends_at
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    return end <= (now or datetime.now(UTC))


def next_subscription_window(clinic: ClinicRegistry | None = None) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    if clinic and clinic.subscription_ends_at:
        current_end = clinic.subscription_ends_at
        if current_end.tzinfo is None:
            current_end = current_end.replace(tzinfo=UTC)
        start = max(now, current_end)
    else:
        start = now
    return start, start + timedelta(days=SUBSCRIPTION_DAYS)


async def billing_settings(session: AsyncSession) -> PlatformBillingSettings:
    row = await session.get(PlatformBillingSettings, 1)
    if row is None:
        row = PlatformBillingSettings(
            id=1,
            plan_name=PLAN_NAME,
            price=Decimal("0"),
            currency="AMD",
            bank_name="",
            cardholder_name="",
            card_number="",
            payment_note="",
            support_email="",
            login_url="https://www.teta2.com",
        )
        session.add(row)
        await session.flush()
    return row


async def admin_event(
    session: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None,
    details: dict | None = None,
) -> None:
    session.add(
        PlatformAdminEvent(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )


def generate_temporary_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%+-_"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(ch.islower() for ch in value)
            and any(ch.isupper() for ch in value)
            and any(ch.isdigit() for ch in value)
            and any(not ch.isalnum() for ch in value)
        ):
            return value


def default_username(request: PlatformAccessRequest) -> str:
    base = normalize_slug(request.requested_slug).replace("-", ".")
    return f"director.{base}"[:80]


def _upgrade_tenant_sync(database_url: str) -> None:
    previous_url = os.environ.get("DATABASE_URL")
    previous_plane = os.environ.get("MIGRATION_PLANE")
    try:
        os.environ["DATABASE_URL"] = database_url
        os.environ["MIGRATION_PLANE"] = "clinic"
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


async def migrate_tenant_database(database_url: str) -> None:
    async with _migration_lock:
        try:
            await asyncio.to_thread(_upgrade_tenant_sync, database_url)
        except Exception as exc:
            raise AppError(
                "TENANT_PROVISIONING_FAILED",
                "Tenant database could not be migrated. Check the database URL and availability.",
                422,
            ) from exc


def encrypt_database_url(database_url: str) -> str:
    settings = get_settings()
    if settings.app_env in {"development", "test"} and not settings.tenant_dsn_encryption_key:
        return f"plain:{database_url}"
    if not settings.tenant_dsn_encryption_key:
        raise AppError(
            "TENANT_ENCRYPTION_NOT_CONFIGURED",
            "Tenant database encryption is not configured.",
            503,
        )
    return Fernet(settings.tenant_dsn_encryption_key.encode()).encrypt(database_url.encode()).decode()


async def provision_new_clinic(
    control: AsyncSession,
    *,
    request: PlatformAccessRequest,
    database_url: str,
    username: str,
    first_name: str,
    last_name: str,
    branch_name: str,
    branch_code: str,
) -> tuple[ClinicRegistry, str]:
    existing = await control.scalar(select(ClinicRegistry).where(ClinicRegistry.slug == request.requested_slug))
    if existing:
        raise AppError("CLINIC_SLUG_EXISTS", "That clinic slug is already registered.", 409)

    await migrate_tenant_database(database_url)
    password = generate_temporary_password()
    tenant_engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with async_sessionmaker(tenant_engine, expire_on_commit=False)() as tenant, tenant.begin():
            duplicate = await tenant.scalar(
                select(User.id).where((User.username == username) | (User.email == request.work_email.lower()))
            )
            if duplicate:
                raise AppError(
                    "TENANT_ADMIN_EXISTS",
                    "The tenant database already contains the requested director account.",
                    409,
                )
            branch = Branch(name=branch_name, code=branch_code)
            tenant.add(branch)
            await tenant.flush()
            user = User(
                username=username,
                email=request.work_email.lower(),
                password_hash=hash_password(password),
                role=Role.DIRECTOR,
                first_name=first_name,
                last_name=last_name,
            )
            tenant.add(user)
            await tenant.flush()
            tenant.add(UserBranchScope(user_id=user.id, branch_id=branch.id))
    finally:
        await tenant_engine.dispose()

    starts_at, ends_at = next_subscription_window()
    clinic = ClinicRegistry(
        slug=request.requested_slug,
        name=request.clinic_name,
        is_active=True,
        encrypted_database_url=encrypt_database_url(database_url),
        allowed_origins=[],
        feature_flags={"teta2_care": True},
        subscription_plan=PLAN_CODE,
        subscription_status=ACTIVE_SUBSCRIPTION,
        subscription_started_at=starts_at,
        subscription_ends_at=ends_at,
        renewal_count=0,
    )
    control.add(clinic)
    await control.flush()
    request.clinic_id = clinic.id
    request.status = "ACTIVE"
    request.activated_at = datetime.now(UTC)
    request.updated_at = datetime.now(UTC)
    await admin_event(
        control,
        action="CLINIC_ACCESS_ACTIVATED",
        entity_type="ClinicRegistry",
        entity_id=str(clinic.id),
        details={"request_id": str(request.id), "plan": PLAN_CODE, "days": SUBSCRIPTION_DAYS},
    )
    return clinic, password


async def renew_clinic_subscription(
    session: AsyncSession, clinic: ClinicRegistry
) -> tuple[datetime, datetime]:
    start, end = next_subscription_window(clinic)
    clinic.subscription_plan = PLAN_CODE
    clinic.subscription_status = ACTIVE_SUBSCRIPTION
    clinic.is_active = True
    if clinic.subscription_started_at is None:
        clinic.subscription_started_at = start
    clinic.subscription_ends_at = end
    clinic.renewal_count = (clinic.renewal_count or 0) + 1
    clinic.updated_at = datetime.now(UTC)
    await admin_event(
        session,
        action="CLINIC_SUBSCRIPTION_RENEWED",
        entity_type="ClinicRegistry",
        entity_id=str(clinic.id),
        details={"new_expiry": end.isoformat(), "days": SUBSCRIPTION_DAYS},
    )
    return start, end


async def tenant_operational_snapshot(clinic: ClinicRegistry) -> dict:
    snapshot = {
        "clinic_id": str(clinic.id),
        "slug": clinic.slug,
        "name": clinic.name,
        "database": "unknown",
        "patients": 0,
        "visits": 0,
        "xrays": 0,
        "analyses": 0,
        "appointments": 0,
    }
    try:
        resolved = resolver.from_registry(clinic)
        factory = resolver.session_factory(resolved)
        async with factory() as db:
            counts = []
            for model in (Patient, Visit, XRay, AIAnalysis, CareAppointment):
                counts.append(int((await db.scalar(select(func.count()).select_from(model))) or 0))
        snapshot.update(
            {
                "database": "healthy",
                "patients": counts[0],
                "visits": counts[1],
                "xrays": counts[2],
                "analyses": counts[3],
                "appointments": counts[4],
            }
        )
    except Exception as exc:
        snapshot["database"] = "unhealthy"
        snapshot["error"] = type(exc).__name__
    return snapshot
