import asyncio
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinic_resolution.service import resolver
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
from app.database.models import AIAnalysis, Patient, User, Visit
from app.database.sessions import control_session
from app.platform.service import (
    PLAN_NAME,
    SUBSCRIPTION_DAYS,
    activate_or_renew,
    audit,
    commercial_config,
    issue_admin_token,
    send_payment_request,
    utcnow,
    validate_admin_token,
    verify_admin_credentials,
)

router = APIRouter(prefix="/platform", tags=["platform"])
settings = get_settings()


class AccessRequestCreate(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=200)
    legal_name: str | None = Field(default=None, max_length=240)
    country: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=1000)
    website: HttpUrl | None = None
    contact_name: str = Field(min_length=2, max_length=200)
    contact_role: str | None = Field(default=None, max_length=160)
    contact_email: EmailStr
    contact_phone: str = Field(min_length=5, max_length=50)
    dentist_count: int | None = Field(default=None, ge=1, le=10000)
    monthly_patient_volume: int | None = Field(default=None, ge=0, le=10_000_000)
    preferred_language: str = Field(default="en", pattern="^(en|hy|ru|fa|tr)$")
    notes: str | None = Field(default=None, max_length=5000)


class AdminLogin(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=500)


class CommercialUpdate(BaseModel):
    price_amount: float = Field(gt=0, le=100_000_000)
    currency: str = Field(min_length=2, max_length=12)
    bank_name: str | None = Field(default=None, max_length=160)
    card_holder: str | None = Field(default=None, max_length=200)
    card_number: str | None = Field(default=None, max_length=64)
    payment_instructions: str | None = Field(default=None, max_length=5000)
    support_email: EmailStr | None = None
    sender_name: str = Field(default="Teta2 Care", min_length=2, max_length=120)


class RequestNote(BaseModel):
    note: str | None = Field(default=None, max_length=5000)
    receipt_reference: str | None = Field(default=None, max_length=500)


async def require_admin(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("PLATFORM_ADMIN_AUTH_REQUIRED", "Platform admin authentication is required.", 401)
    return validate_admin_token(authorization.removeprefix("Bearer ").strip())


def _request(row: AccessRequest) -> dict:
    return {
        "id": str(row.id), "status": row.status, "plan_name": PLAN_NAME,
        "clinic_name": row.clinic_name, "legal_name": row.legal_name,
        "country": row.country, "city": row.city, "address": row.address,
        "website": row.website, "contact_name": row.contact_name,
        "contact_role": row.contact_role, "contact_email": row.contact_email,
        "contact_phone": row.contact_phone, "dentist_count": row.dentist_count,
        "monthly_patient_volume": row.monthly_patient_volume,
        "preferred_language": row.preferred_language, "notes": row.notes,
        "quoted_price_amount": float(row.quoted_price_amount) if row.quoted_price_amount is not None else None,
        "quoted_currency": row.quoted_currency, "payment_reference": row.payment_reference,
        "payment_notes": row.payment_notes, "receipt_reference": row.receipt_reference,
        "review_note": row.review_note, "payment_email_sent_at": row.payment_email_sent_at,
        "payment_confirmed_at": row.payment_confirmed_at, "rejected_at": row.rejected_at,
        "activated_at": row.activated_at,
        "clinic_registry_id": str(row.clinic_registry_id) if row.clinic_registry_id else None,
        "issued_username": row.issued_username, "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _clinic(row: ClinicRegistry) -> dict:
    expiry = row.access_expires_at
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    active = bool(expiry and expiry > datetime.now(UTC))
    return {
        "id": str(row.id), "slug": row.slug, "name": row.name,
        "is_active": row.is_active, "plan_name": PLAN_NAME if row.subscription_enforced else "Legacy",
        "subscription_enforced": row.subscription_enforced, "access_expires_at": expiry,
        "access_status": "LEGACY" if not row.subscription_enforced else ("ACTIVE" if active else "EXPIRED"),
        "created_at": row.created_at, "updated_at": row.updated_at,
    }


def _config(row: PlatformCommercialConfig) -> dict:
    return {
        "plan_name": PLAN_NAME, "subscription_days": SUBSCRIPTION_DAYS,
        "price_amount": float(row.price_amount), "currency": row.currency,
        "bank_name": row.bank_name, "card_holder": row.card_holder,
        "card_number": row.card_number, "payment_instructions": row.payment_instructions,
        "support_email": row.support_email, "sender_name": row.sender_name,
        "updated_at": row.updated_at,
    }


@router.get("/commercial")
async def public_commercial(control: Annotated[AsyncSession, Depends(control_session)]):
    row = await commercial_config(control)
    await control.commit()
    return {k: v for k, v in _config(row).items() if k in {"plan_name", "subscription_days", "price_amount", "currency"}}


@router.post("/access-requests", status_code=201)
async def submit_access_request(body: AccessRequestCreate, control: Annotated[AsyncSession, Depends(control_session)]):
    row = AccessRequest(
        status="SUBMITTED", plan_name=PLAN_NAME, clinic_name=body.clinic_name.strip(),
        legal_name=body.legal_name.strip() if body.legal_name else None,
        country=body.country.strip(), city=body.city.strip(),
        address=body.address.strip() if body.address else None,
        website=str(body.website) if body.website else None,
        contact_name=body.contact_name.strip(),
        contact_role=body.contact_role.strip() if body.contact_role else None,
        contact_email=str(body.contact_email).lower(), contact_phone=body.contact_phone.strip(),
        dentist_count=body.dentist_count, monthly_patient_volume=body.monthly_patient_volume,
        preferred_language=body.preferred_language,
        notes=body.notes.strip() if body.notes else None,
    )
    control.add(row)
    await control.flush()
    audit(control, "ACCESS_REQUEST_SUBMITTED", request_id=row.id)
    await control.commit()
    return {"id": str(row.id), "status": row.status, "plan_name": PLAN_NAME}


@router.post("/admin/login")
async def admin_login(body: AdminLogin):
    if not verify_admin_credentials(body.username, body.password):
        await asyncio.sleep(0.15 + secrets.randbelow(100) / 1000)
        raise AppError("PLATFORM_ADMIN_LOGIN_FAILED", "Invalid platform admin credentials.", 401)
    return {"access_token": issue_admin_token(body.username), "token_type": "bearer", "expires_in": settings.platform_admin_token_minutes * 60}


@router.get("/admin/commercial", dependencies=[Depends(require_admin)])
async def get_commercial(control: Annotated[AsyncSession, Depends(control_session)]):
    row = await commercial_config(control)
    await control.commit()
    return _config(row)


@router.put("/admin/commercial", dependencies=[Depends(require_admin)])
async def save_commercial(body: CommercialUpdate, control: Annotated[AsyncSession, Depends(control_session)]):
    row = await commercial_config(control)
    row.plan_name = PLAN_NAME
    row.price_amount = body.price_amount
    row.currency = body.currency.upper().strip()
    row.bank_name = body.bank_name.strip() if body.bank_name else None
    row.card_holder = body.card_holder.strip() if body.card_holder else None
    row.card_number = body.card_number.strip() if body.card_number else None
    row.payment_instructions = body.payment_instructions.strip() if body.payment_instructions else None
    row.support_email = str(body.support_email).lower() if body.support_email else None
    row.sender_name = body.sender_name.strip()
    row.updated_at = utcnow()
    audit(control, "COMMERCIAL_CONFIG_UPDATED")
    await control.commit()
    return _config(row)


@router.get("/admin/access-requests", dependencies=[Depends(require_admin)])
async def access_requests(control: Annotated[AsyncSession, Depends(control_session)], status: str | None = Query(default=None), limit: int = Query(default=200, ge=1, le=500)):
    query = select(AccessRequest).order_by(AccessRequest.created_at.desc()).limit(limit)
    if status:
        query = query.where(AccessRequest.status == status.upper())
    return [_request(row) for row in (await control.scalars(query)).all()]


@router.get("/admin/access-requests/{request_id}", dependencies=[Depends(require_admin)])
async def access_request_detail(request_id: uuid.UUID, control: Annotated[AsyncSession, Depends(control_session)]):
    row = await control.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    result = _request(row)
    emails = (await control.scalars(select(PlatformEmailLog).where(PlatformEmailLog.access_request_id == request_id).order_by(PlatformEmailLog.created_at.desc()))).all()
    result["emails"] = [{"id": str(x.id), "kind": x.kind, "recipient": x.recipient, "subject": x.subject, "status": x.status, "safe_error": x.safe_error, "created_at": x.created_at, "sent_at": x.sent_at} for x in emails]
    return result


@router.post("/admin/access-requests/{request_id}/send-payment", dependencies=[Depends(require_admin)])
async def send_payment(request_id: uuid.UUID, control: Annotated[AsyncSession, Depends(control_session)]):
    row = await control.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    await send_payment_request(control, row)
    audit(control, "PAYMENT_INSTRUCTIONS_SENT", request_id=row.id)
    await control.commit()
    return _request(row)


@router.post("/admin/access-requests/{request_id}/payment-confirmed", dependencies=[Depends(require_admin)])
async def payment_confirmed(request_id: uuid.UUID, body: RequestNote, control: Annotated[AsyncSession, Depends(control_session)]):
    row = await control.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status not in {"PAYMENT_REQUEST_SENT", "PAYMENT_CONFIRMED"}:
        raise AppError("ACCESS_REQUEST_STATE_INVALID", "Payment cannot be confirmed in this state.", 409)
    row.status = "PAYMENT_CONFIRMED"
    row.payment_confirmed_at = utcnow()
    row.payment_notes = body.note.strip() if body.note else row.payment_notes
    row.receipt_reference = body.receipt_reference.strip() if body.receipt_reference else row.receipt_reference
    row.updated_at = utcnow()
    audit(control, "PAYMENT_CONFIRMED", request_id=row.id)
    await control.commit()
    return _request(row)


@router.post("/admin/access-requests/{request_id}/reject", dependencies=[Depends(require_admin)])
async def reject_request(request_id: uuid.UUID, body: RequestNote, control: Annotated[AsyncSession, Depends(control_session)]):
    row = await control.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status == "ACTIVATED":
        raise AppError("ACCESS_REQUEST_STATE_INVALID", "An activated request cannot be rejected.", 409)
    row.status = "REJECTED"
    row.review_note = body.note.strip() if body.note else None
    row.rejected_at = utcnow()
    row.updated_at = utcnow()
    audit(control, "ACCESS_REQUEST_REJECTED", request_id=row.id)
    await control.commit()
    return _request(row)


@router.post("/admin/access-requests/{request_id}/activate", dependencies=[Depends(require_admin)])
async def activate(request_id: uuid.UUID, control: Annotated[AsyncSession, Depends(control_session)]):
    row = await control.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    registry, expires_at = await activate_or_renew(control, row)
    audit(control, "CLINIC_ACCESS_ACTIVATED", request_id=row.id, clinic_id=registry.id, metadata={"expires_at": expires_at.isoformat()})
    await control.commit()
    return {"request": _request(row), "clinic": _clinic(registry), "expires_at": expires_at}


@router.post("/admin/clinics/{clinic_id}/renew", dependencies=[Depends(require_admin)])
async def renew(clinic_id: uuid.UUID, control: Annotated[AsyncSession, Depends(control_session)]):
    registry = await control.get(ClinicRegistry, clinic_id)
    if not registry:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    row = await control.scalar(select(AccessRequest).where(AccessRequest.clinic_registry_id == clinic_id).order_by(AccessRequest.created_at.desc()).limit(1))
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "No commercial request is linked to this clinic.", 404)
    row.status = "PAYMENT_CONFIRMED"
    row.payment_confirmed_at = utcnow()
    _, expires_at = await activate_or_renew(control, row)
    audit(control, "CLINIC_ACCESS_RENEWED", request_id=row.id, clinic_id=clinic_id, metadata={"expires_at": expires_at.isoformat()})
    await control.commit()
    return {"clinic": _clinic(registry), "expires_at": expires_at}


@router.get("/admin/clinics", dependencies=[Depends(require_admin)])
async def clinics(control: Annotated[AsyncSession, Depends(control_session)]):
    rows = (await control.scalars(select(ClinicRegistry).order_by(ClinicRegistry.created_at.desc()))).all()
    terms = (await control.scalars(select(SubscriptionTerm).order_by(SubscriptionTerm.created_at.desc()).limit(2000))).all()
    counts: dict[uuid.UUID, int] = {}
    for term in terms:
        counts[term.clinic_id] = counts.get(term.clinic_id, 0) + 1
    result = []
    for row in rows:
        item = _clinic(row)
        item["subscription_terms"] = counts.get(row.id, 0)
        result.append(item)
    return result


@router.get("/admin/overview", dependencies=[Depends(require_admin)])
async def overview(control: Annotated[AsyncSession, Depends(control_session)]):
    now = datetime.now(UTC)
    clinics = (await control.scalars(select(ClinicRegistry).order_by(ClinicRegistry.created_at.desc()))).all()
    request_counts = dict((await control.execute(select(AccessRequest.status, func.count(AccessRequest.id)).group_by(AccessRequest.status))).all())
    email_counts = dict((await control.execute(select(PlatformEmailLog.status, func.count(PlatformEmailLog.id)).group_by(PlatformEmailLog.status))).all())
    totals = {"patients": 0, "users": 0, "visits": 0, "analyses": 0}
    health: list[dict] = []
    recent_visits: list[dict] = []
    for registry in clinics:
        item = {"clinic_id": str(registry.id), "slug": registry.slug, "name": registry.name, "database": "inactive"}
        try:
            if registry.is_active:
                resolved = await resolver.by_id(control, registry.id, enforce_subscription=False)
                async with resolver.session_factory(resolved)() as tenant:
                    await tenant.execute(text("SELECT 1"))
                    counts = {
                        "patients": int(await tenant.scalar(select(func.count(Patient.id))) or 0),
                        "users": int(await tenant.scalar(select(func.count(User.id))) or 0),
                        "visits": int(await tenant.scalar(select(func.count(Visit.id))) or 0),
                        "analyses": int(await tenant.scalar(select(func.count(AIAnalysis.id))) or 0),
                    }
                    for key, value in counts.items():
                        totals[key] += value
                    item.update({"database": "healthy", **counts})
                    rows = (await tenant.scalars(select(Visit).order_by(Visit.visit_date.desc()).limit(10))).all()
                    recent_visits.extend({"clinic_id": str(registry.id), "clinic_name": registry.name, "visit_id": str(v.id), "patient_id": str(v.patient_id), "doctor_id": str(v.doctor_id), "branch_id": str(v.branch_id), "visit_date": v.visit_date, "summary": v.summary} for v in rows)
        except Exception as exc:
            item.update({"database": "unhealthy", "error": type(exc).__name__})
        health.append(item)
    recent_visits.sort(key=lambda x: x["visit_date"], reverse=True)
    def current_expiry(row: ClinicRegistry):
        value = row.access_expires_at
        return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value
    paid_active = sum(1 for row in clinics if row.subscription_enforced and current_expiry(row) and current_expiry(row) > now)
    return {
        "platform": {"plan_name": PLAN_NAME, "subscription_days": SUBSCRIPTION_DAYS, "api": "healthy", "control_database": "healthy", "generated_at": now},
        "clinics": {"total": len(clinics), "active_paid": paid_active, "expired_paid": sum(1 for x in clinics if x.subscription_enforced) - paid_active, "legacy": sum(1 for x in clinics if not x.subscription_enforced)},
        "requests": request_counts, "email_delivery": email_counts, "totals": totals,
        "health": health, "recent_visits": recent_visits[:100],
    }


@router.get("/admin/audit", dependencies=[Depends(require_admin)])
async def audit_log(control: Annotated[AsyncSession, Depends(control_session)], limit: int = Query(default=200, ge=1, le=500)):
    rows = (await control.scalars(select(PlatformAdminAudit).order_by(PlatformAdminAudit.created_at.desc()).limit(limit))).all()
    return [{"id": str(x.id), "action": x.action, "request_id": str(x.access_request_id) if x.access_request_id else None, "clinic_id": str(x.clinic_id) if x.clinic_id else None, "metadata": x.metadata_json, "created_at": x.created_at} for x in rows]
