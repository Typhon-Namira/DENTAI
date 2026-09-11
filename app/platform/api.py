import asyncio
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.serialization import model_dict
from app.core.errors import AppError
from app.core.rate_limit import sensitive_limit
from app.database.control_models import (
    ClinicRegistry,
    PlatformAccessRequest,
    PlatformAdminEvent,
    PlatformBillingSettings,
)
from app.database.sessions import control_session
from app.platform.emailer import (
    credentials_email,
    deliver_email,
    payment_instructions_email,
    renewal_email,
    smtp_configured,
)
from app.platform.security import (
    authenticate_platform_admin,
    platform_admin_configured,
    require_platform_admin,
)
from app.platform.service import (
    PLAN_CODE,
    PLAN_NAME,
    SUBSCRIPTION_DAYS,
    admin_event,
    billing_settings,
    default_username,
    normalize_slug,
    provision_new_clinic,
    renew_clinic_subscription,
    subscription_expired,
    tenant_operational_snapshot,
)

router = APIRouter(prefix="/platform", tags=["platform"])


class AccessRequestCreate(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=200)
    requested_slug: str = Field(min_length=3, max_length=80)
    country: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    website: HttpUrl | None = None
    director_name: str = Field(min_length=2, max_length=200)
    work_email: EmailStr
    phone: str = Field(min_length=5, max_length=80)
    branch_count: int = Field(default=1, ge=1, le=100)
    dentist_count: int = Field(default=1, ge=1, le=1000)
    notes: str | None = Field(default=None, max_length=4000)


class AdminLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class BillingSettingsPatch(BaseModel):
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=12)
    bank_name: str = Field(default="", max_length=200)
    cardholder_name: str = Field(default="", max_length=200)
    card_number: str = Field(default="", max_length=100)
    payment_note: str = Field(default="", max_length=2000)
    support_email: EmailStr | None = None
    login_url: HttpUrl


class RequestPatch(BaseModel):
    clinic_name: str | None = Field(default=None, min_length=2, max_length=200)
    requested_slug: str | None = Field(default=None, min_length=3, max_length=80)
    country: str | None = Field(default=None, min_length=2, max_length=120)
    city: str | None = Field(default=None, min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    website: HttpUrl | None = None
    director_name: str | None = Field(default=None, min_length=2, max_length=200)
    work_email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=5, max_length=80)
    branch_count: int | None = Field(default=None, ge=1, le=100)
    dentist_count: int | None = Field(default=None, ge=1, le=1000)
    notes: str | None = Field(default=None, max_length=4000)
    admin_note: str | None = Field(default=None, max_length=4000)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=2000)


class PaymentVerification(BaseModel):
    payment_reference: str = Field(min_length=1, max_length=300)
    note: str | None = Field(default=None, max_length=4000)


class ActivateRequest(BaseModel):
    tenant_database_url: str = Field(min_length=10, max_length=2000)
    username: str | None = Field(default=None, min_length=3, max_length=80)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    branch_name: str = Field(default="Main Clinic", min_length=2, max_length=160)
    branch_code: str = Field(default="MAIN", min_length=2, max_length=40)


class SubscriptionAction(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


def _request_dict(row: PlatformAccessRequest) -> dict:
    data = model_dict(row)
    data["plan_name"] = PLAN_NAME
    data["subscription_days"] = SUBSCRIPTION_DAYS
    return data


def _clinic_dict(row: ClinicRegistry) -> dict:
    data = model_dict(row)
    data.pop("encrypted_database_url", None)
    data["subscription_expired"] = subscription_expired(row)
    data["plan_name"] = PLAN_NAME
    data["subscription_days"] = SUBSCRIPTION_DAYS
    return data


@router.get("/plan")
async def public_plan(control: Annotated[AsyncSession, Depends(control_session)]):
    settings = await billing_settings(control)
    await control.commit()
    return {
        "code": PLAN_CODE,
        "name": PLAN_NAME,
        "price": str(settings.price),
        "currency": settings.currency,
        "subscription_days": SUBSCRIPTION_DAYS,
    }


@router.post(
    "/access-requests",
    status_code=201,
    dependencies=[Depends(sensitive_limit("platform-access-request", 5, 3600))],
)
async def create_access_request(
    body: AccessRequestCreate,
    control: Annotated[AsyncSession, Depends(control_session)],
):
    slug = normalize_slug(body.requested_slug)
    email = str(body.work_email).lower()
    existing_clinic = await control.scalar(select(ClinicRegistry.id).where(ClinicRegistry.slug == slug))
    if existing_clinic:
        raise AppError("CLINIC_SLUG_EXISTS", "This clinic identifier is already registered.", 409)
    duplicate = await control.scalar(
        select(PlatformAccessRequest.id).where(
            PlatformAccessRequest.work_email == email,
            PlatformAccessRequest.status.in_(
                ["SUBMITTED", "PAYMENT_PENDING", "PAYMENT_VERIFIED", "PROVISIONING"]
            ),
        )
    )
    if duplicate:
        raise AppError(
            "ACCESS_REQUEST_EXISTS",
            "An active access request already exists for this email address.",
            409,
        )
    row = PlatformAccessRequest(
        clinic_name=body.clinic_name.strip(),
        requested_slug=slug,
        country=body.country.strip(),
        city=body.city.strip(),
        address=body.address.strip() if body.address else None,
        website=str(body.website) if body.website else None,
        director_name=body.director_name.strip(),
        work_email=email,
        phone=body.phone.strip(),
        branch_count=body.branch_count,
        dentist_count=body.dentist_count,
        notes=body.notes.strip() if body.notes else None,
        plan=PLAN_CODE,
        status="SUBMITTED",
    )
    control.add(row)
    await control.flush()
    await admin_event(
        control,
        action="ACCESS_REQUEST_SUBMITTED",
        entity_type="PlatformAccessRequest",
        entity_id=str(row.id),
        details={"clinic_name": row.clinic_name, "slug": row.requested_slug},
    )
    await control.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "plan": PLAN_NAME,
        "subscription_days": SUBSCRIPTION_DAYS,
        "message": "Your Teta2 Care access request was submitted for review.",
    }


@router.post(
    "/admin/login",
    dependencies=[Depends(sensitive_limit("platform-admin-login", 8, 300))],
)
async def platform_admin_login(body: AdminLogin):
    token = authenticate_platform_admin(str(body.email), body.password)
    from app.core.config import get_settings

    settings = get_settings()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.platform_admin_token_minutes * 60,
    }


@router.get("/admin/overview")
async def admin_overview(
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    clinics = (await control.scalars(select(ClinicRegistry).order_by(ClinicRegistry.created_at.desc()))).all()
    request_counts = dict(
        (
            await control.execute(
                select(PlatformAccessRequest.status, func.count())
                .group_by(PlatformAccessRequest.status)
            )
        ).all()
    )
    snapshots = await asyncio.gather(*(tenant_operational_snapshot(clinic) for clinic in clinics))
    totals = {
        key: sum(int(snapshot[key]) for snapshot in snapshots)
        for key in ("patients", "visits", "xrays", "analyses", "appointments")
    }
    active = sum(1 for clinic in clinics if not subscription_expired(clinic))
    expiring = 0
    now = datetime.now(UTC)
    for clinic in clinics:
        if not clinic.subscription_ends_at or subscription_expired(clinic):
            continue
        end = clinic.subscription_ends_at
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        if 0 <= (end - now).days <= 7:
            expiring += 1
    return {
        "plan": {"code": PLAN_CODE, "name": PLAN_NAME, "subscription_days": SUBSCRIPTION_DAYS},
        "clinics": {
            "total": len(clinics),
            "active": active,
            "expired_or_suspended": len(clinics) - active,
            "expiring_within_7_days": expiring,
        },
        "access_requests": request_counts,
        "platform_usage": totals,
        "tenant_health": {
            "healthy": sum(1 for item in snapshots if item["database"] == "healthy"),
            "unhealthy": sum(1 for item in snapshots if item["database"] != "healthy"),
        },
        "email_configured": smtp_configured(),
        "admin_configured": platform_admin_configured(),
    }


@router.get("/admin/health")
async def admin_health(
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    await control.execute(select(func.count()).select_from(ClinicRegistry))
    clinics = (await control.scalars(select(ClinicRegistry).order_by(ClinicRegistry.name.asc()))).all()
    snapshots = await asyncio.gather(*(tenant_operational_snapshot(clinic) for clinic in clinics))
    return {
        "control_database": "healthy",
        "smtp": "configured" if smtp_configured() else "not_configured",
        "tenant_databases": snapshots,
    }


@router.get("/admin/access-requests")
async def admin_access_requests(
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
    status: str | None = Query(default=None, max_length=40),
):
    query = select(PlatformAccessRequest).order_by(PlatformAccessRequest.created_at.desc())
    if status:
        query = query.where(PlatformAccessRequest.status == status.upper())
    rows = (await control.scalars(query.limit(500))).all()
    return [_request_dict(row) for row in rows]


@router.patch("/admin/access-requests/{request_id}")
async def edit_access_request(
    request_id: uuid.UUID,
    body: RequestPatch,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    row = await control.get(PlatformAccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    values = body.model_dump(exclude_unset=True)
    for field, value in values.items():
        if field == "requested_slug" and value is not None:
            value = normalize_slug(value)
        elif field == "work_email" and value is not None:
            value = str(value).lower()
        elif field == "website" and value is not None:
            value = str(value)
        setattr(row, field, value)
    row.updated_at = datetime.now(UTC)
    await admin_event(
        control,
        action="ACCESS_REQUEST_EDITED",
        entity_type="PlatformAccessRequest",
        entity_id=str(row.id),
    )
    await control.commit()
    return _request_dict(row)


@router.post("/admin/access-requests/{request_id}/approve")
async def approve_access_request(
    request_id: uuid.UUID,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    row = await control.get(PlatformAccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status not in {"SUBMITTED", "PAYMENT_PENDING"}:
        raise AppError("INVALID_ACCESS_REQUEST_STATE", "Request cannot enter payment review from its current state.", 409)
    settings = await billing_settings(control)
    subject, body = payment_instructions_email(
        clinic_name=row.clinic_name,
        director_name=row.director_name,
        price=str(settings.price),
        currency=settings.currency,
        bank_name=settings.bank_name,
        cardholder_name=settings.cardholder_name,
        card_number=settings.card_number,
        payment_note=settings.payment_note,
        request_id=str(row.id),
        support_email=settings.support_email,
    )
    delivery = await deliver_email(to=row.work_email, subject=subject, body=body)
    row.status = "PAYMENT_PENDING"
    row.updated_at = datetime.now(UTC)
    if delivery.sent:
        row.payment_instructions_sent_at = datetime.now(UTC)
    await admin_event(
        control,
        action="PAYMENT_INSTRUCTIONS_REQUESTED",
        entity_type="PlatformAccessRequest",
        entity_id=str(row.id),
        details={"email_sent": delivery.sent, "delivery": delivery.detail},
    )
    await control.commit()
    return {
        "request": _request_dict(row),
        "email_sent": delivery.sent,
        "email_delivery": delivery.detail,
        "email_preview": None if delivery.sent else {"subject": subject, "body": body},
    }


@router.post("/admin/access-requests/{request_id}/reject")
async def reject_access_request(
    request_id: uuid.UUID,
    body: RejectRequest,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    row = await control.get(PlatformAccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status == "ACTIVE":
        raise AppError("INVALID_ACCESS_REQUEST_STATE", "An active clinic request cannot be rejected.", 409)
    row.status = "REJECTED"
    row.admin_note = body.reason
    row.rejected_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    await admin_event(
        control,
        action="ACCESS_REQUEST_REJECTED",
        entity_type="PlatformAccessRequest",
        entity_id=str(row.id),
        details={"reason": body.reason},
    )
    await control.commit()
    return _request_dict(row)


@router.post("/admin/access-requests/{request_id}/verify-payment")
async def verify_payment(
    request_id: uuid.UUID,
    body: PaymentVerification,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    row = await control.get(PlatformAccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status != "PAYMENT_PENDING":
        raise AppError("INVALID_ACCESS_REQUEST_STATE", "Payment can only be verified after payment instructions are issued.", 409)
    row.status = "PAYMENT_VERIFIED"
    row.payment_reference = body.payment_reference
    row.payment_proof_note = body.note
    row.payment_reported_at = row.payment_reported_at or datetime.now(UTC)
    row.payment_verified_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    await admin_event(
        control,
        action="ACCESS_PAYMENT_VERIFIED",
        entity_type="PlatformAccessRequest",
        entity_id=str(row.id),
        details={"payment_reference": body.payment_reference},
    )
    await control.commit()
    return _request_dict(row)


@router.post("/admin/access-requests/{request_id}/activate")
async def activate_access_request(
    request_id: uuid.UUID,
    body: ActivateRequest,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    row = await control.get(PlatformAccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status != "PAYMENT_VERIFIED":
        raise AppError("PAYMENT_NOT_VERIFIED", "Payment must be verified before dashboard access is activated.", 409)
    if not re.match(r"^(postgresql|postgres|sqlite)(\+[^:]+)?://", body.tenant_database_url):
        raise AppError("INVALID_TENANT_DATABASE_URL", "Unsupported tenant database URL.", 422)
    row.status = "PROVISIONING"
    await control.flush()
    username = (body.username or default_username(row)).strip()
    clinic, temporary_password = await provision_new_clinic(
        control,
        request=row,
        database_url=body.tenant_database_url,
        username=username,
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        branch_name=body.branch_name.strip(),
        branch_code=body.branch_code.strip().upper(),
    )
    settings = await billing_settings(control)
    expires_at = clinic.subscription_ends_at
    assert expires_at is not None
    subject, email_body = credentials_email(
        clinic_name=clinic.name,
        clinic_slug=clinic.slug,
        username=username,
        temporary_password=temporary_password,
        login_url=settings.login_url,
        expires_at=expires_at.isoformat(),
    )
    delivery = await deliver_email(to=row.work_email, subject=subject, body=email_body)
    await admin_event(
        control,
        action="ACCESS_CREDENTIALS_EMAIL_REQUESTED",
        entity_type="ClinicRegistry",
        entity_id=str(clinic.id),
        details={"email_sent": delivery.sent, "delivery": delivery.detail},
    )
    await control.commit()
    return {
        "clinic": _clinic_dict(clinic),
        "email_sent": delivery.sent,
        "email_delivery": delivery.detail,
        "credentials_preview": None
        if delivery.sent
        else {
            "clinic_slug": clinic.slug,
            "username": username,
            "temporary_password": temporary_password,
            "login_url": settings.login_url,
        },
    }


@router.get("/admin/clinics")
async def admin_clinics(
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    rows = (await control.scalars(select(ClinicRegistry).order_by(ClinicRegistry.created_at.desc()))).all()
    snapshots = await asyncio.gather(*(tenant_operational_snapshot(row) for row in rows))
    by_id = {item["clinic_id"]: item for item in snapshots}
    return [{**_clinic_dict(row), "usage": by_id.get(str(row.id), {})} for row in rows]


@router.post("/admin/clinics/{clinic_id}/renew")
async def renew_clinic(
    clinic_id: uuid.UUID,
    body: SubscriptionAction,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    clinic = await control.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    _, end = await renew_clinic_subscription(control, clinic)
    request = await control.scalar(
        select(PlatformAccessRequest)
        .where(PlatformAccessRequest.clinic_id == clinic.id)
        .order_by(PlatformAccessRequest.created_at.desc())
        .limit(1)
    )
    settings = await billing_settings(control)
    email_sent = False
    email_delivery = "NO_CONTACT_EMAIL"
    if request:
        subject, email_body = renewal_email(
            clinic_name=clinic.name,
            login_url=settings.login_url,
            expires_at=end.isoformat(),
        )
        delivery = await deliver_email(to=request.work_email, subject=subject, body=email_body)
        email_sent = delivery.sent
        email_delivery = delivery.detail
    await control.commit()
    return {
        "clinic": _clinic_dict(clinic),
        "renewed_until": end.isoformat(),
        "email_sent": email_sent,
        "email_delivery": email_delivery,
    }


@router.post("/admin/clinics/{clinic_id}/suspend")
async def suspend_clinic(
    clinic_id: uuid.UUID,
    body: SubscriptionAction,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    clinic = await control.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    clinic.subscription_status = "SUSPENDED"
    clinic.updated_at = datetime.now(UTC)
    await admin_event(
        control,
        action="CLINIC_SUBSCRIPTION_SUSPENDED",
        entity_type="ClinicRegistry",
        entity_id=str(clinic.id),
        details={"note": body.note},
    )
    await control.commit()
    return _clinic_dict(clinic)


@router.get("/admin/billing-settings")
async def get_billing_settings(
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    row = await billing_settings(control)
    await control.commit()
    data = model_dict(row)
    data["price"] = str(row.price)
    data["plan_code"] = PLAN_CODE
    data["plan_name"] = PLAN_NAME
    data["subscription_days"] = SUBSCRIPTION_DAYS
    return data


@router.put("/admin/billing-settings")
async def update_billing_settings(
    body: BillingSettingsPatch,
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
):
    row = await billing_settings(control)
    row.plan_name = PLAN_NAME
    row.price = body.price
    row.currency = body.currency.strip().upper()
    row.bank_name = body.bank_name.strip()
    row.cardholder_name = body.cardholder_name.strip()
    row.card_number = body.card_number.strip()
    row.payment_note = body.payment_note.strip()
    row.support_email = str(body.support_email or "")
    row.login_url = str(body.login_url)
    row.updated_at = datetime.now(UTC)
    await admin_event(
        control,
        action="BILLING_SETTINGS_UPDATED",
        entity_type="PlatformBillingSettings",
        entity_id="1",
        details={"currency": row.currency, "price": str(row.price)},
    )
    await control.commit()
    return {
        **model_dict(row),
        "price": str(row.price),
        "plan_code": PLAN_CODE,
        "plan_name": PLAN_NAME,
        "subscription_days": SUBSCRIPTION_DAYS,
    }


@router.get("/admin/events")
async def admin_events(
    control: Annotated[AsyncSession, Depends(control_session)],
    _admin: Annotated[str, Depends(require_platform_admin)],
    limit: int = Query(default=100, ge=1, le=500),
):
    rows = (
        await control.scalars(
            select(PlatformAdminEvent).order_by(PlatformAdminEvent.created_at.desc()).limit(limit)
        )
    ).all()
    return [model_dict(row) for row in rows]
