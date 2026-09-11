import hashlib
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import (
    AccessRequest,
    ClinicRegistry,
    PlatformEmailLog,
    PlatformSettings,
    PlatformVisit,
)
from app.database.sessions import control_session
from app.platform.admin_auth import (
    ADMIN_SESSION_HOURS,
    authenticate_platform_admin,
    verify_platform_admin_session,
)
from app.platform.service import (
    activation_email_body,
    payment_email_body,
    platform_settings,
    provision_clinic,
    renew_clinic,
    send_logged_email,
)

router = APIRouter(prefix="/platform", tags=["platform"])


class AccessRequestCreate(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=200)
    country: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    website: HttpUrl | None = None
    contact_name: str = Field(min_length=2, max_length=160)
    contact_role: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=50)
    dentists_count: int = Field(default=1, ge=1, le=500)
    branches_count: int = Field(default=1, ge=1, le=100)
    notes: str | None = Field(default=None, max_length=4000)


class AdminLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)


class AdminDecision(BaseModel):
    note: str | None = Field(default=None, max_length=4000)


class PaymentVerification(BaseModel):
    reference: str | None = Field(default=None, max_length=200)
    proof_note: str | None = Field(default=None, max_length=4000)


class SettingsUpdate(BaseModel):
    price_amount: int = Field(ge=0, le=1_000_000_000)
    price_currency: str = Field(min_length=2, max_length=12)
    payment_recipient: str = Field(min_length=1, max_length=200)
    payment_card: str = Field(max_length=100)
    payment_bank_details: str = Field(max_length=4000)
    payment_email_subject: str = Field(min_length=1, max_length=240)
    payment_email_intro: str = Field(min_length=1, max_length=5000)
    activation_email_subject: str = Field(min_length=1, max_length=240)
    activation_email_intro: str = Field(min_length=1, max_length=5000)


class RenewRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)


def _serialize_access(row: AccessRequest) -> dict:
    return {
        "id": str(row.id),
        "clinic_name": row.clinic_name,
        "country": row.country,
        "city": row.city,
        "address": row.address,
        "website": row.website,
        "contact_name": row.contact_name,
        "contact_role": row.contact_role,
        "email": row.email,
        "phone": row.phone,
        "dentists_count": row.dentists_count,
        "branches_count": row.branches_count,
        "notes": row.notes,
        "status": row.status,
        "admin_note": row.admin_note,
        "payment_reference": row.payment_reference,
        "payment_proof_note": row.payment_proof_note,
        "payment_instructions_sent_at": row.payment_instructions_sent_at,
        "payment_verified_at": row.payment_verified_at,
        "activated_clinic_id": (str(row.activated_clinic_id) if row.activated_clinic_id else None),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _serialize_clinic(row: ClinicRegistry) -> dict:
    now = datetime.now(UTC)
    expires = row.subscription_expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    active = row.is_active and (expires is None or expires > now)
    return {
        "id": str(row.id),
        "slug": row.slug,
        "name": row.name,
        "is_active": active,
        "registry_active": row.is_active,
        "subscription_plan": row.subscription_plan or "LEGACY",
        "subscription_starts_at": row.subscription_starts_at,
        "subscription_expires_at": expires,
        "days_remaining": max(0, (expires - now).days) if expires else None,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "feature_flags": row.feature_flags,
    }


def _serialize_settings(row: PlatformSettings) -> dict:
    return {
        "plan_name": "Teta2 Care",
        "subscription_days": 30,
        "price_amount": row.price_amount,
        "price_currency": row.price_currency,
        "payment_recipient": row.payment_recipient,
        "payment_card": row.payment_card,
        "payment_bank_details": row.payment_bank_details,
        "payment_email_subject": row.payment_email_subject,
        "payment_email_intro": row.payment_email_intro,
        "activation_email_subject": row.activation_email_subject,
        "activation_email_intro": row.activation_email_intro,
        "updated_at": row.updated_at,
    }


async def require_platform_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    verify_platform_admin_session(supplied)


@router.post("/admin/login")
async def platform_admin_login(body: AdminLogin):
    token = authenticate_platform_admin(str(body.email), body.password)
    return {
        "access_token": token,
        "expires_in": ADMIN_SESSION_HOURS * 60 * 60,
    }


@router.post("/access-requests", status_code=201)
async def create_access_request(
    body: AccessRequestCreate,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    recent_cutoff = datetime.now(UTC) - timedelta(hours=6)
    duplicate = await session.scalar(
        select(AccessRequest.id).where(
            AccessRequest.email == str(body.email).casefold(),
            AccessRequest.created_at >= recent_cutoff,
            AccessRequest.status.in_(["SUBMITTED", "PAYMENT_REQUESTED", "PAYMENT_REVIEW"]),
        )
    )
    if duplicate:
        raise AppError(
            "ACCESS_REQUEST_ALREADY_SUBMITTED",
            "A recent access request already exists for this email address.",
            409,
        )
    now = datetime.now(UTC)
    row = AccessRequest(
        clinic_name=body.clinic_name.strip(),
        country=body.country.strip(),
        city=body.city.strip(),
        address=body.address.strip() if body.address else None,
        website=str(body.website) if body.website else None,
        contact_name=body.contact_name.strip(),
        contact_role=body.contact_role.strip(),
        email=str(body.email).casefold(),
        phone=body.phone.strip(),
        dentists_count=body.dentists_count,
        branches_count=body.branches_count,
        notes=body.notes.strip() if body.notes else None,
        status="SUBMITTED",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "message": "Your Teta2 Care access request has been submitted for review.",
    }


@router.get("/public-plan")
async def public_plan(session: Annotated[AsyncSession, Depends(control_session)]):
    row = await platform_settings(session)
    await session.commit()
    return {
        "name": "Teta2 Care",
        "period_days": 30,
        "price_amount": row.price_amount,
        "price_currency": row.price_currency,
    }


@router.get("/admin/overview", dependencies=[Depends(require_platform_admin)])
async def admin_overview(session: Annotated[AsyncSession, Depends(control_session)]):
    now = datetime.now(UTC)
    day = now - timedelta(hours=24)
    month = now - timedelta(days=30)
    clinics = list(
        (
            await session.scalars(select(ClinicRegistry).order_by(ClinicRegistry.created_at.desc()))
        ).all()
    )
    requests = list(
        (
            await session.scalars(select(AccessRequest).order_by(AccessRequest.created_at.desc()))
        ).all()
    )
    emails = list(
        (
            await session.scalars(
                select(PlatformEmailLog).order_by(PlatformEmailLog.created_at.desc()).limit(100)
            )
        ).all()
    )
    visits_24h = int(
        await session.scalar(
            select(func.count()).select_from(PlatformVisit).where(PlatformVisit.created_at >= day)
        )
        or 0
    )
    visits_30d = int(
        await session.scalar(
            select(func.count()).select_from(PlatformVisit).where(PlatformVisit.created_at >= month)
        )
        or 0
    )
    unique_30d = int(
        await session.scalar(
            select(func.count(func.distinct(PlatformVisit.visitor_hash))).where(
                PlatformVisit.created_at >= month
            )
        )
        or 0
    )
    recent_visits = list(
        (
            await session.scalars(
                select(PlatformVisit).order_by(PlatformVisit.created_at.desc()).limit(500)
            )
        ).all()
    )
    route_counts = Counter(visit.path for visit in recent_visits)
    request_counts = Counter(access.status for access in requests)

    def subscription_active(clinic: ClinicRegistry) -> bool:
        expires = clinic.subscription_expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return clinic.is_active and (expires is None or expires > now)

    def expiring_soon(clinic: ClinicRegistry) -> bool:
        expires = clinic.subscription_expires_at
        if expires is None:
            return False
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return now < expires <= now + timedelta(days=7)

    active_clinics = sum(1 for clinic in clinics if subscription_active(clinic))
    expiring = sum(1 for clinic in clinics if expiring_soon(clinic))
    app_settings = get_settings()
    return {
        "health": {
            "api": "HEALTHY",
            "control_database": "HEALTHY",
            "smtp_configured": bool(app_settings.smtp_host and app_settings.smtp_from_email),
            "tenant_auto_provisioning_configured": bool(app_settings.tenant_database_url_template),
            "ai_provider": app_settings.ai_provider,
            "groq_configured": bool(app_settings.groq_api_key),
            "whatsapp_configured": bool(app_settings.whatsapp_service_url),
            "radar_enabled": app_settings.radar_enabled,
            "storage_provider": app_settings.object_storage_provider,
        },
        "metrics": {
            "clinics_total": len(clinics),
            "clinics_active": active_clinics,
            "clinics_expiring_7d": expiring,
            "requests_total": len(requests),
            "requests_pending": sum(
                request_counts[state]
                for state in ("SUBMITTED", "PAYMENT_REQUESTED", "PAYMENT_REVIEW")
            ),
            "visits_24h": visits_24h,
            "visits_30d": visits_30d,
            "unique_visitors_30d": unique_30d,
            "emails_failed_100": sum(1 for email in emails if email.status == "FAILED"),
        },
        "request_statuses": dict(request_counts),
        "top_routes": route_counts.most_common(15),
        "recent_emails": [
            {
                "id": str(email.id),
                "kind": email.kind,
                "recipient": email.recipient,
                "subject": email.subject,
                "status": email.status,
                "error": email.error,
                "created_at": email.created_at,
            }
            for email in emails[:30]
        ],
    }


@router.get("/admin/access-requests", dependencies=[Depends(require_platform_admin)])
async def admin_access_requests(
    session: Annotated[AsyncSession, Depends(control_session)],
):
    rows = (
        await session.scalars(select(AccessRequest).order_by(AccessRequest.created_at.desc()))
    ).all()
    return [_serialize_access(row) for row in rows]


@router.get("/admin/clinics", dependencies=[Depends(require_platform_admin)])
async def admin_clinics(session: Annotated[AsyncSession, Depends(control_session)]):
    rows = (
        await session.scalars(select(ClinicRegistry).order_by(ClinicRegistry.created_at.desc()))
    ).all()
    return [_serialize_clinic(row) for row in rows]


@router.get("/admin/settings", dependencies=[Depends(require_platform_admin)])
async def admin_settings(session: Annotated[AsyncSession, Depends(control_session)]):
    row = await platform_settings(session)
    await session.commit()
    return _serialize_settings(row)


@router.put("/admin/settings", dependencies=[Depends(require_platform_admin)])
async def update_admin_settings(
    body: SettingsUpdate,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await platform_settings(session)
    row.plan_name = "Teta2 Care"
    row.subscription_days = 30
    for field, value in body.model_dump().items():
        setattr(row, field, value.strip() if isinstance(value, str) else value)
    row.updated_at = datetime.now(UTC)
    await session.commit()
    return _serialize_settings(row)


@router.post(
    "/admin/access-requests/{request_id}/reject",
    dependencies=[Depends(require_platform_admin)],
)
async def reject_access_request(
    request_id: uuid.UUID,
    body: AdminDecision,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status == "ACTIVE":
        raise AppError(
            "ACCESS_REQUEST_ALREADY_ACTIVE",
            "An active clinic request cannot be rejected.",
            409,
        )
    row.status = "REJECTED"
    row.admin_note = body.note
    row.updated_at = datetime.now(UTC)
    await session.commit()
    return _serialize_access(row)


@router.post(
    "/admin/access-requests/{request_id}/send-payment",
    dependencies=[Depends(require_platform_admin)],
)
async def send_payment_instructions(
    request_id: uuid.UUID,
    body: AdminDecision,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status not in {"SUBMITTED", "PAYMENT_REQUESTED", "PAYMENT_REVIEW"}:
        raise AppError(
            "ACCESS_REQUEST_STATE_INVALID",
            "Payment instructions cannot be sent in this state.",
            409,
        )
    settings = await platform_settings(session)
    if not settings.payment_card.strip() and not settings.payment_bank_details.strip():
        raise AppError(
            "PAYMENT_DETAILS_REQUIRED",
            "Configure payment details before sending payment instructions.",
            409,
        )
    await send_logged_email(
        session,
        recipient=row.email,
        subject=settings.payment_email_subject,
        body=payment_email_body(row, settings),
        kind="PAYMENT_INSTRUCTIONS",
        access_request_id=row.id,
    )
    row.status = "PAYMENT_REQUESTED"
    row.admin_note = body.note or row.admin_note
    row.payment_instructions_sent_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    await session.commit()
    return _serialize_access(row)


@router.post(
    "/admin/access-requests/{request_id}/payment-received",
    dependencies=[Depends(require_platform_admin)],
)
async def payment_received(
    request_id: uuid.UUID,
    body: PaymentVerification,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status not in {"PAYMENT_REQUESTED", "PAYMENT_REVIEW"}:
        raise AppError(
            "ACCESS_REQUEST_STATE_INVALID", "Payment cannot be verified in this state.", 409
        )
    row.status = "PAYMENT_REVIEW"
    row.payment_reference = body.reference
    row.payment_proof_note = body.proof_note
    row.updated_at = datetime.now(UTC)
    await session.commit()
    return _serialize_access(row)


@router.post(
    "/admin/access-requests/{request_id}/activate",
    dependencies=[Depends(require_platform_admin)],
)
async def activate_access_request(
    request_id: uuid.UUID,
    body: PaymentVerification,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status not in {"PAYMENT_REQUESTED", "PAYMENT_REVIEW"}:
        raise AppError(
            "ACCESS_REQUEST_STATE_INVALID",
            "The request must reach payment review before activation.",
            409,
        )
    settings = await platform_settings(session)
    row.payment_reference = body.reference or row.payment_reference
    row.payment_proof_note = body.proof_note or row.payment_proof_note
    row.payment_verified_at = datetime.now(UTC)
    clinic, username, password, expires_at = await provision_clinic(
        session,
        request=row,
        settings=settings,
    )
    await send_logged_email(
        session,
        recipient=row.email,
        subject=settings.activation_email_subject,
        body=activation_email_body(
            row,
            settings,
            slug=clinic.slug,
            username=username,
            password=password,
            expires_at=expires_at,
        ),
        kind="ACTIVATION_CREDENTIALS",
        access_request_id=row.id,
        clinic_id=clinic.id,
    )
    await session.commit()
    return {
        "request": _serialize_access(row),
        "clinic": _serialize_clinic(clinic),
        "credentials_email_sent": True,
    }


@router.post(
    "/admin/clinics/{clinic_id}/renew",
    dependencies=[Depends(require_platform_admin)],
)
async def renew_subscription(
    clinic_id: uuid.UUID,
    body: RenewRequest,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await session.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    settings = await platform_settings(session)
    expires_at = await renew_clinic(clinic, settings, days=body.days)
    await session.commit()
    return {
        "clinic": _serialize_clinic(clinic),
        "subscription_expires_at": expires_at,
    }


async def record_platform_visit(request: Request, response_status: int) -> None:
    if request.url.path.startswith("/api/v1/platform/admin"):
        return
    try:
        async for session in control_session():
            secret = get_settings().app_secret.encode()
            forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            raw_identity = forwarded or (request.client.host if request.client else "")
            visitor_hash = (
                hashlib.sha256(secret + raw_identity.encode()).hexdigest()[:40]
                if raw_identity
                else None
            )
            session.add(
                PlatformVisit(
                    path=request.url.path[:300],
                    method=request.method[:12],
                    status_code=response_status,
                    visitor_hash=visitor_hash,
                    user_agent=request.headers.get("user-agent", "")[:500] or None,
                )
            )
            await session.commit()
            break
    except Exception:
        return
