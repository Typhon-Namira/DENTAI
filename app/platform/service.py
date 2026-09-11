import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import sys
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from cryptography.fernet import Fernet
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import (
    AccessRequest,
    ClinicRegistry,
    PlatformAdminAudit,
    PlatformCommercialConfig,
    PlatformEmailLog,
    SubscriptionTerm,
)
from app.database.models import Branch, Role, User, UserBranchScope

PLAN_NAME = "Teta2 Care"
SUBSCRIPTION_DAYS = 30
settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(UTC)


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")[:52]
    return slug or "clinic"


def _safe_database_name(slug: str) -> str:
    base = re.sub(r"[^a-z0-9_]", "_", slug.casefold().replace("-", "_"))[:40]
    prefix = re.sub(r"[^a-z0-9_]", "_", settings.platform_tenant_database_prefix.casefold())
    return f"{prefix}{base}_{secrets.token_hex(3)}"


def _username(contact_name: str, clinic_name: str) -> str:
    first = re.sub(r"[^a-z0-9]", "", contact_name.casefold().split(" ")[0])[:20]
    clinic = re.sub(r"[^a-z0-9]", "", clinic_name.casefold())[:18]
    stem = first or clinic or "clinic"
    return f"{stem}{secrets.randbelow(9000) + 1000}"[:40]


def _temporary_password() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(16))


def _admin_signature(payload: str) -> str:
    return hmac.new(settings.app_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_admin_token(username: str) -> str:
    expires = int((utcnow() + timedelta(minutes=settings.platform_admin_token_minutes)).timestamp())
    payload = json.dumps({"sub": username, "exp": expires}, separators=(",", ":"))
    body = payload.encode().hex()
    return f"{body}.{_admin_signature(body)}"


def validate_admin_token(token: str) -> str:
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _admin_signature(body)):
            raise ValueError
        payload = json.loads(bytes.fromhex(body).decode())
        if int(payload["exp"]) <= int(utcnow().timestamp()):
            raise ValueError
        return str(payload["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AppError(
            "PLATFORM_ADMIN_AUTH_REQUIRED",
            "Platform admin authentication is required.",
            401,
        ) from exc


def verify_admin_credentials(username: str, password: str) -> bool:
    configured_user = settings.platform_admin_username or ""
    configured_password = settings.platform_admin_password or ""
    return (
        bool(configured_user and configured_password)
        and hmac.compare_digest(username, configured_user)
        and hmac.compare_digest(password, configured_password)
    )


async def commercial_config(session: AsyncSession) -> PlatformCommercialConfig:
    row = await session.get(PlatformCommercialConfig, 1)
    if row:
        return row
    row = PlatformCommercialConfig(id=1, plan_name=PLAN_NAME)
    session.add(row)
    await session.flush()
    return row


def payment_reference(request_id: uuid.UUID) -> str:
    return f"T2-{request_id.hex[:8].upper()}-{secrets.token_hex(2).upper()}"


def _payment_email_body(row: AccessRequest, config: PlatformCommercialConfig) -> str:
    amount = f"{row.quoted_price_amount or config.price_amount} {row.quoted_currency or config.currency}"
    lines = [
        f"Hello {row.contact_name},",
        "",
        f"Your request for {PLAN_NAME} has passed the first review stage.",
        f"Subscription term: {SUBSCRIPTION_DAYS} days.",
        f"Subscription price: {amount}.",
        f"Payment reference: {row.payment_reference}.",
        "",
        "Payment details:",
        f"Bank: {config.bank_name or '—'}",
        f"Card holder: {config.card_holder or '—'}",
        f"Card / account: {config.card_number or '—'}",
    ]
    if config.payment_instructions:
        lines.extend(["", config.payment_instructions.strip()])
    lines.extend(
        [
            "",
            "After payment, reply to this email with the transfer receipt and include the payment reference above.",
            "After payment verification, Teta2 will activate your clinic workspace for 30 days and send the login credentials.",
            "",
            PLAN_NAME,
        ]
    )
    return "\n".join(lines)


def _activation_email_body(
    row: AccessRequest,
    *,
    clinic_slug: str,
    username: str,
    password: str,
    expires_at: datetime,
) -> str:
    return "\n".join(
        [
            f"Hello {row.contact_name},",
            "",
            f"Your {PLAN_NAME} clinic workspace is now active.",
            f"Access period: {SUBSCRIPTION_DAYS} days.",
            f"Access expires: {expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"Sign-in page: {settings.platform_public_origin.rstrip('/')}/login",
            f"Clinic ID: {clinic_slug}",
            f"Username: {username}",
            f"Temporary password: {password}",
            "",
            "Your clinic data is preserved if access expires. Renewal extends dashboard access without deleting prior records.",
            "",
            PLAN_NAME,
        ]
    )


def _renewal_email_body(row: AccessRequest, expires_at: datetime) -> str:
    return "\n".join(
        [
            f"Hello {row.contact_name},",
            "",
            f"Your {PLAN_NAME} subscription has been renewed.",
            f"New access expiry: {expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            "Your existing clinic data, patient records, analyses, follow-ups and conversations remain unchanged.",
            "",
            PLAN_NAME,
        ]
    )


def _send_smtp_sync(recipient: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        if settings.app_env in {"development", "test"}:
            return
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)


async def send_logged_email(
    session: AsyncSession,
    *,
    kind: str,
    recipient: str,
    subject: str,
    body: str,
    request_id: uuid.UUID | None = None,
    clinic_id: uuid.UUID | None = None,
) -> PlatformEmailLog:
    log = PlatformEmailLog(
        access_request_id=request_id,
        clinic_id=clinic_id,
        kind=kind,
        recipient=recipient,
        subject=subject,
        status="QUEUED",
    )
    session.add(log)
    await session.flush()
    try:
        await asyncio.to_thread(_send_smtp_sync, recipient, subject, body)
        log.status = "SENT"
        log.sent_at = utcnow()
    except Exception as exc:
        log.status = "FAILED"
        log.safe_error = type(exc).__name__
        raise AppError("PLATFORM_EMAIL_FAILED", "The email could not be sent.", 503) from exc
    return log


async def send_payment_request(session: AsyncSession, row: AccessRequest) -> None:
    if row.status not in {"SUBMITTED", "PAYMENT_REQUEST_SENT"}:
        raise AppError(
            "ACCESS_REQUEST_STATE_INVALID",
            "This request cannot receive payment instructions now.",
            409,
        )
    config = await commercial_config(session)
    row.plan_name = PLAN_NAME
    row.quoted_price_amount = config.price_amount
    row.quoted_currency = config.currency
    row.payment_reference = row.payment_reference or payment_reference(row.id)
    await send_logged_email(
        session,
        kind="PAYMENT_REQUEST",
        recipient=row.contact_email,
        subject=f"Teta2 Care payment instructions · {row.payment_reference}",
        body=_payment_email_body(row, config),
        request_id=row.id,
        clinic_id=row.clinic_registry_id,
    )
    row.status = "PAYMENT_REQUEST_SENT"
    row.payment_email_sent_at = utcnow()
    row.updated_at = utcnow()


async def _create_postgres_database(database_name: str) -> None:
    admin_url = settings.platform_tenant_database_admin_url
    if not admin_url:
        raise AppError(
            "TENANT_PROVISIONING_NOT_CONFIGURED",
            "Automatic tenant database provisioning is not configured.",
            503,
        )
    if not re.fullmatch(r"[a-z0-9_]+", database_name):
        raise AppError("TENANT_DATABASE_NAME_INVALID", "Tenant database name is invalid.", 500)
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    finally:
        await engine.dispose()


def _tenant_url(database_name: str) -> str:
    template = settings.platform_tenant_database_url_template
    if template:
        return template.format(database=database_name)
    if settings.app_env in {"development", "test"}:
        return f"sqlite+aiosqlite:///./{database_name}.db"
    raise AppError(
        "TENANT_PROVISIONING_NOT_CONFIGURED",
        "Automatic tenant database provisioning is not configured.",
        503,
    )


async def _migrate_tenant(database_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["MIGRATION_PLANE"] = "clinic"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.communicate()
    if process.returncode != 0:
        raise AppError(
            "TENANT_MIGRATION_FAILED",
            "The clinic database could not be initialized.",
            503,
        )


async def provision_clinic(
    session: AsyncSession,
    *,
    row: AccessRequest,
) -> tuple[ClinicRegistry, str, str]:
    if row.clinic_registry_id:
        registry = await session.get(ClinicRegistry, row.clinic_registry_id)
        if registry:
            return registry, row.issued_username or "", ""

    slug_base = _safe_slug(row.clinic_name)
    slug = slug_base
    suffix = 1
    while await session.scalar(select(ClinicRegistry.id).where(ClinicRegistry.slug == slug)):
        suffix += 1
        slug = f"{slug_base[:46]}-{suffix}"

    database_name = _safe_database_name(slug)
    database_url = _tenant_url(database_name)
    if database_url.startswith("postgresql"):
        await _create_postgres_database(database_name)
    await _migrate_tenant(database_url)

    username = _username(row.contact_name, row.clinic_name)
    password = _temporary_password()
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as tenant, tenant.begin():
            branch = Branch(
                name=row.clinic_name,
                code="MAIN",
                address=row.address,
                phone=row.contact_phone,
            )
            tenant.add(branch)
            await tenant.flush()
            parts = row.contact_name.split(" ", 1)
            user = User(
                username=username,
                email=row.contact_email.lower(),
                password_hash=hash_password(password),
                role=Role.DIRECTOR,
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else "Admin",
            )
            tenant.add(user)
            await tenant.flush()
            tenant.add(UserBranchScope(user_id=user.id, branch_id=branch.id))
    finally:
        await engine.dispose()

    if settings.tenant_dsn_encryption_key:
        encrypted = (
            Fernet(settings.tenant_dsn_encryption_key.encode())
            .encrypt(database_url.encode())
            .decode()
        )
    elif settings.app_env in {"development", "test"}:
        encrypted = "plain:" + database_url
    else:
        raise AppError(
            "TENANT_ENCRYPTION_NOT_CONFIGURED",
            "Tenant encryption is unavailable.",
            503,
        )

    registry = ClinicRegistry(
        slug=slug,
        name=row.clinic_name,
        is_active=True,
        encrypted_database_url=encrypted,
        allowed_origins=[settings.platform_public_origin],
        feature_flags={"plan": PLAN_NAME},
        subscription_enforced=True,
    )
    session.add(registry)
    await session.flush()
    row.clinic_registry_id = registry.id
    row.issued_username = username
    return registry, username, password


async def activate_or_renew(
    session: AsyncSession,
    row: AccessRequest,
) -> tuple[ClinicRegistry, datetime]:
    if row.status != "PAYMENT_CONFIRMED":
        raise AppError(
            "ACCESS_REQUEST_STATE_INVALID",
            "Payment must be verified before activation.",
            409,
        )

    registry, username, password = await provision_clinic(session, row=row)
    now = utcnow()
    current_expiry = registry.access_expires_at
    if current_expiry is not None and current_expiry.tzinfo is None:
        current_expiry = current_expiry.replace(tzinfo=UTC)
    start = current_expiry if current_expiry and current_expiry > now else now
    end = start + timedelta(days=SUBSCRIPTION_DAYS)
    kind = "RENEWAL" if current_expiry else "INITIAL"

    registry.is_active = True
    registry.subscription_enforced = True
    registry.access_expires_at = end
    registry.updated_at = now
    session.add(
        SubscriptionTerm(
            clinic_id=registry.id,
            access_request_id=row.id,
            plan_name=PLAN_NAME,
            price_amount=row.quoted_price_amount,
            currency=row.quoted_currency,
            starts_at=start,
            ends_at=end,
            status="ACTIVE",
            kind=kind,
            payment_reference=row.payment_reference,
        )
    )

    if kind == "INITIAL":
        await send_logged_email(
            session,
            kind="ACCESS_ACTIVATED",
            recipient=row.contact_email,
            subject="Your Teta2 Care workspace is active",
            body=_activation_email_body(
                row,
                clinic_slug=registry.slug,
                username=username,
                password=password,
                expires_at=end,
            ),
            request_id=row.id,
            clinic_id=registry.id,
        )
    else:
        await send_logged_email(
            session,
            kind="SUBSCRIPTION_RENEWED",
            recipient=row.contact_email,
            subject="Your Teta2 Care subscription was renewed",
            body=_renewal_email_body(row, end),
            request_id=row.id,
            clinic_id=registry.id,
        )

    row.status = "ACTIVATED"
    row.activated_at = now
    row.updated_at = now
    return registry, end


def audit(
    session: AsyncSession,
    action: str,
    *,
    request_id: uuid.UUID | None = None,
    clinic_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> None:
    session.add(
        PlatformAdminAudit(
            action=action,
            access_request_id=request_id,
            clinic_id=clinic_id,
            metadata_json=metadata or {},
        )
    )
