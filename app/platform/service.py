import asyncio
import os
import re
import secrets
import smtplib
import string
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import (
    AccessRequest,
    ClinicRegistry,
    PlatformEmailLog,
    PlatformSettings,
)
from app.database.models import Branch, Role, User, UserBranchScope


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug[:60] or f"clinic-{secrets.token_hex(3)}"


def random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def platform_settings(session: AsyncSession) -> PlatformSettings:
    row = await session.get(PlatformSettings, 1)
    if row:
        return row
    row = PlatformSettings(id=1)
    session.add(row)
    await session.flush()
    return row


def _send_smtp(recipient: str, subject: str, body: str) -> str | None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)
    return message.get("Message-ID")


async def send_logged_email(
    session: AsyncSession,
    *,
    recipient: str,
    subject: str,
    body: str,
    kind: str,
    access_request_id: uuid.UUID | None = None,
    clinic_id: uuid.UUID | None = None,
) -> PlatformEmailLog:
    log = PlatformEmailLog(
        access_request_id=access_request_id,
        clinic_id=clinic_id,
        kind=kind,
        recipient=recipient,
        subject=subject,
        status="SENDING",
    )
    session.add(log)
    await session.flush()
    try:
        provider_message_id = await asyncio.to_thread(_send_smtp, recipient, subject, body)
        log.status = "SENT"
        log.provider_message_id = provider_message_id
    except Exception as exc:
        log.status = "FAILED"
        log.error = f"{type(exc).__name__}: {exc}"[:2000]
        raise AppError("EMAIL_SEND_FAILED", "The email could not be sent.", 502) from exc
    return log


def payment_email_body(request: AccessRequest, settings: PlatformSettings) -> str:
    card = settings.payment_card.strip() or "Not configured"
    bank = settings.payment_bank_details.strip() or "Not configured"
    return (
        f"Hello {request.contact_name},\n\n"
        f"{settings.payment_email_intro}\n\n"
        f"Plan: {settings.plan_name}\n"
        f"Access period: {settings.subscription_days} days\n"
        f"Price: {settings.price_amount:,} {settings.price_currency}\n"
        f"Recipient: {settings.payment_recipient}\n"
        f"Card / payment number: {card}\n"
        f"Bank details: {bank}\n\n"
        "After payment, reply to this email with the payment receipt. "
        "Your clinic will only be activated after an administrator verifies the payment.\n\n"
        "Teta2 Care"
    )


def activation_email_body(
    request: AccessRequest,
    settings: PlatformSettings,
    *,
    slug: str,
    username: str,
    password: str,
    expires_at: datetime,
) -> str:
    public_url = get_settings().platform_public_url.rstrip("/")
    return (
        f"Hello {request.contact_name},\n\n"
        f"{settings.activation_email_intro}\n\n"
        f"Clinic: {request.clinic_name}\n"
        f"Plan: {settings.plan_name}\n"
        f"Access expires: {expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"Login URL: {public_url}/login\n"
        f"Clinic slug: {slug}\n"
        f"Username: {username}\n"
        f"Temporary password: {password}\n\n"
        "Please store these credentials securely. Your clinic data is retained when the subscription expires; "
        "renewal reactivates the same dashboard without deleting historical data.\n\n"
        "Teta2 Care"
    )


def _migrate_tenant_sync(database_url: str) -> None:
    previous_url = os.environ.get("DATABASE_URL")
    previous_plane = os.environ.get("MIGRATION_PLANE")
    try:
        os.environ["DATABASE_URL"] = database_url
        os.environ["MIGRATION_PLANE"] = "clinic"
        command.upgrade(Config(str(Path("alembic.ini"))), "head")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        if previous_plane is None:
            os.environ.pop("MIGRATION_PLANE", None)
        else:
            os.environ["MIGRATION_PLANE"] = previous_plane


async def _ensure_database(database_url: str) -> None:
    settings = get_settings()
    url = make_url(database_url)
    if url.get_backend_name().startswith("sqlite"):
        return
    if url.get_backend_name() != "postgresql":
        return
    admin_url = settings.tenant_database_admin_url
    if not admin_url:
        raise AppError(
            "TENANT_DATABASE_ADMIN_URL_REQUIRED",
            "Automatic clinic provisioning requires TENANT_DATABASE_ADMIN_URL.",
            409,
        )
    database = url.database
    if not database or not re.fullmatch(r"[A-Za-z0-9_\-]+", database):
        raise AppError("TENANT_DATABASE_NAME_INVALID", "Tenant database name is invalid.", 409)
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database}
            )
            if not exists:
                escaped = database.replace('"', '""')
                await connection.execute(text(f'CREATE DATABASE "{escaped}"'))
    finally:
        await engine.dispose()


def _tenant_url_for_slug(slug: str) -> str:
    template = get_settings().tenant_database_url_template
    if not template:
        raise AppError(
            "TENANT_DATABASE_TEMPLATE_REQUIRED",
            "Automatic clinic provisioning requires TENANT_DATABASE_URL_TEMPLATE.",
            409,
        )
    database = "teta2_" + re.sub(r"[^a-z0-9]+", "_", slug.casefold()).strip("_")
    return template.format(slug=slug, database=database)


async def _unique_slug(session: AsyncSession, clinic_name: str) -> str:
    base = slugify(clinic_name)
    candidate = base
    suffix = 2
    while await session.scalar(select(ClinicRegistry.id).where(ClinicRegistry.slug == candidate)):
        candidate = f"{base[:52]}-{suffix}"
        suffix += 1
    return candidate


async def provision_clinic(
    control_session: AsyncSession,
    *,
    request: AccessRequest,
    settings: PlatformSettings,
) -> tuple[ClinicRegistry, str, str, datetime]:
    if request.activated_clinic_id:
        existing = await control_session.get(ClinicRegistry, request.activated_clinic_id)
        if existing:
            raise AppError("CLINIC_ALREADY_ACTIVATED", "This request is already activated.", 409)

    slug = await _unique_slug(control_session, request.clinic_name)
    database_url = _tenant_url_for_slug(slug)
    await _ensure_database(database_url)
    await asyncio.to_thread(_migrate_tenant_sync, database_url)

    username_base = re.sub(r"[^a-z0-9]", "", request.contact_name.casefold().replace(" ", "."))
    username = (username_base or "director")[:50]
    password = random_password()
    tenant_engine = create_async_engine(database_url)
    try:
        async with (
            async_sessionmaker(tenant_engine, expire_on_commit=False)() as tenant,
            tenant.begin(),
        ):
            existing_username = await tenant.scalar(
                select(User.id).where(User.username == username)
            )
            if existing_username:
                username = f"{username}.{secrets.token_hex(2)}"
            branch = Branch(
                name=f"{request.clinic_name} Main",
                code="MAIN",
                address=request.address,
                phone=request.phone,
            )
            tenant.add(branch)
            await tenant.flush()
            user = User(
                username=username,
                email=request.email.casefold(),
                password_hash=hash_password(password),
                role=Role.DIRECTOR,
                first_name=request.contact_name.split()[0],
                last_name=" ".join(request.contact_name.split()[1:]) or "Director",
            )
            tenant.add(user)
            await tenant.flush()
            tenant.add(UserBranchScope(user_id=user.id, branch_id=branch.id))
    finally:
        await tenant_engine.dispose()

    key = get_settings().tenant_dsn_encryption_key
    if not key:
        if get_settings().app_env in {"development", "test"}:
            encrypted = f"plain:{database_url}"
        else:
            raise AppError(
                "TENANT_ENCRYPTION_KEY_REQUIRED", "Tenant encryption is unavailable.", 503
            )
    else:
        encrypted = Fernet(key.encode()).encrypt(database_url.encode()).decode()

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.subscription_days)
    clinic = ClinicRegistry(
        slug=slug,
        name=request.clinic_name,
        is_active=True,
        encrypted_database_url=encrypted,
        allowed_origins=[get_settings().platform_public_url],
        feature_flags={"teta2_care": True},
        subscription_plan="TETA2_CARE",
        subscription_starts_at=now,
        subscription_expires_at=expires_at,
    )
    control_session.add(clinic)
    await control_session.flush()
    request.activated_clinic_id = clinic.id
    request.payment_verified_at = request.payment_verified_at or now
    request.status = "ACTIVE"
    request.updated_at = now
    return clinic, username, password, expires_at


async def renew_clinic(
    clinic: ClinicRegistry, settings: PlatformSettings, *, days: int | None = None
) -> datetime:
    now = datetime.now(UTC)
    duration = timedelta(days=days or settings.subscription_days)
    base = (
        clinic.subscription_expires_at
        if clinic.subscription_expires_at and clinic.subscription_expires_at > now
        else now
    )
    clinic.subscription_plan = "TETA2_CARE"
    clinic.subscription_starts_at = clinic.subscription_starts_at or now
    clinic.subscription_expires_at = base + duration
    clinic.is_active = True
    clinic.updated_at = now
    return clinic.subscription_expires_at
