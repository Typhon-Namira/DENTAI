import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.models import CareConversation, CareConversationMessage, CarePlanItem
from app.clinic_resolution.service import resolver
from app.core.errors import AppError
from app.database.control_models import (
    AccessRequest,
    ClinicRegistry,
    PlatformAdminAudit,
    PlatformEmailLog,
    PlatformVisit,
)
from app.database.models import AIAnalysis, FollowUp, Patient, XRay
from app.database.sessions import control_session
from app.platform.api import require_platform_admin
from app.platform.market_api import market_code

router = APIRouter(prefix="/platform/admin-control", tags=["platform-admin-control"])

PUBLIC_PAGE_PATHS = (
    "/",
    "/product",
    "/how-it-works",
    "/pricing",
    "/clinical-safety",
    "/about",
    "/register",
    "/request-access",
    "/login",
)


class ClinicEdit(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None
    subscription_state: str | None = Field(default=None, max_length=40)
    expires_at: datetime | None = None


class GiftGrant(BaseModel):
    months: int = Field(ge=1, le=24)
    note: str | None = Field(default=None, max_length=2000)


class ArchiveClinic(BaseModel):
    confirm_slug: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=2000)


class RequestEdit(BaseModel):
    clinic_name: str | None = Field(default=None, min_length=2, max_length=200)
    country: str | None = Field(default=None, min_length=2, max_length=80)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    website: str | None = Field(default=None, max_length=300)
    contact_name: str | None = Field(default=None, min_length=2, max_length=160)
    contact_role: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, min_length=6, max_length=50)
    admin_note: str | None = Field(default=None, max_length=4000)


async def _audit(
    session: AsyncSession,
    *,
    action: str,
    target_type: str,
    target_id: str | None,
    details: dict,
) -> None:
    session.add(
        PlatformAdminAudit(
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _clinic_category(clinic: ClinicRegistry) -> str:
    source = (clinic.subscription_source or "").upper()
    plan = (clinic.subscription_plan or "").upper()
    if source == "GIFT":
        return "GIFT"
    if plan == "FREE" or source == "FREE":
        return "FREE"
    if plan in {"PREMIUM", "TETA2_CARE"}:
        return "PAID" if source != "GIFT" else "GIFT"
    return "LEGACY"


def _clinic_operational_state(clinic: ClinicRegistry) -> str:
    now = datetime.now(UTC)
    expiry = _aware(clinic.subscription_expires_at)
    if not clinic.is_active:
        return "ARCHIVED"
    if clinic.subscription_state == "PAYMENT_REVIEW":
        return "PAYMENT_REVIEW"
    if expiry is not None and expiry <= now:
        return "EXPIRED"
    return clinic.subscription_state or "ACTIVE"


async def _count(session: AsyncSession, model, *where) -> int:
    statement = select(func.count()).select_from(model)
    if where:
        statement = statement.where(*where)
    return int(await session.scalar(statement) or 0)


async def _tenant_stats(control: AsyncSession, clinic: ClinicRegistry) -> dict:
    empty = {
        "patients": 0,
        "opgs": 0,
        "ai_analyses": 0,
        "followups_total": 0,
        "followups_completed": 0,
        "followups_pending": 0,
        "care_items_total": 0,
        "care_items_completed": 0,
        "care_items_pending": 0,
        "ai_conversations": 0,
        "conversation_messages": 0,
        "database_status": "UNAVAILABLE",
    }
    try:
        resolved = await resolver.by_id(control, clinic.id)
        factory = resolver.session_factory(resolved)
        async with factory() as tenant:
            patients = await _count(tenant, Patient)
            opgs = await _count(tenant, XRay)
            ai_analyses = await _count(tenant, AIAnalysis)
            followups_total = await _count(tenant, FollowUp)
            followups_completed = await _count(
                tenant,
                FollowUp,
                or_(
                    FollowUp.completed_at.is_not(None),
                    func.upper(FollowUp.status).in_(["COMPLETED", "DONE", "TREATED"]),
                ),
            )
            care_items_total = await _count(tenant, CarePlanItem)
            care_items_completed = await _count(
                tenant,
                CarePlanItem,
                or_(
                    CarePlanItem.outcome_at.is_not(None),
                    func.upper(CarePlanItem.status).in_(["COMPLETED", "DONE", "TREATED"]),
                ),
            )
            conversations = await _count(tenant, CareConversation)
            messages = await _count(tenant, CareConversationMessage)
        return {
            "patients": patients,
            "opgs": opgs,
            "ai_analyses": ai_analyses,
            "followups_total": followups_total,
            "followups_completed": followups_completed,
            "followups_pending": max(0, followups_total - followups_completed),
            "care_items_total": care_items_total,
            "care_items_completed": care_items_completed,
            "care_items_pending": max(0, care_items_total - care_items_completed),
            "ai_conversations": conversations,
            "conversation_messages": messages,
            "database_status": "ONLINE",
        }
    except Exception:
        return empty


def _serialize_clinic(clinic: ClinicRegistry, stats: dict) -> dict:
    expiry = _aware(clinic.subscription_expires_at)
    now = datetime.now(UTC)
    days_remaining = None
    if expiry is not None:
        days_remaining = max(0, (expiry - now).days)
    return {
        "id": str(clinic.id),
        "slug": clinic.slug,
        "name": clinic.name,
        "registry_active": clinic.is_active,
        "subscription_plan": clinic.subscription_plan or "LEGACY",
        "subscription_state": clinic.subscription_state or "ACTIVE",
        "subscription_source": clinic.subscription_source or "LEGACY",
        "category": _clinic_category(clinic),
        "operational_state": _clinic_operational_state(clinic),
        "subscription_starts_at": clinic.subscription_starts_at,
        "subscription_expires_at": expiry,
        "days_remaining": days_remaining,
        "free_trial_started_at": clinic.free_trial_started_at,
        "upgrade_requested_at": clinic.upgrade_requested_at,
        "gift_granted_at": clinic.gift_granted_at,
        "gift_note": clinic.gift_note,
        "created_at": clinic.created_at,
        "updated_at": clinic.updated_at,
        "stats": stats,
    }


async def _traffic_payload(session: AsyncSession) -> dict:
    now = datetime.now(UTC)
    day = now - timedelta(hours=24)
    month = now - timedelta(days=30)

    totals = dict(
        (
            await session.execute(
                select(PlatformVisit.path, func.count())
                .where(PlatformVisit.path.in_(PUBLIC_PAGE_PATHS))
                .group_by(PlatformVisit.path)
            )
        ).all()
    )
    last_24h = dict(
        (
            await session.execute(
                select(PlatformVisit.path, func.count())
                .where(
                    PlatformVisit.path.in_(PUBLIC_PAGE_PATHS),
                    PlatformVisit.created_at >= day,
                )
                .group_by(PlatformVisit.path)
            )
        ).all()
    )
    last_30d = dict(
        (
            await session.execute(
                select(PlatformVisit.path, func.count())
                .where(
                    PlatformVisit.path.in_(PUBLIC_PAGE_PATHS),
                    PlatformVisit.created_at >= month,
                )
                .group_by(PlatformVisit.path)
            )
        ).all()
    )
    unique_30d = dict(
        (
            await session.execute(
                select(
                    PlatformVisit.path,
                    func.count(func.distinct(PlatformVisit.visitor_hash)),
                )
                .where(
                    PlatformVisit.path.in_(PUBLIC_PAGE_PATHS),
                    PlatformVisit.created_at >= month,
                )
                .group_by(PlatformVisit.path)
            )
        ).all()
    )
    pages = [
        {
            "path": path,
            "visits_total": int(totals.get(path, 0)),
            "visits_24h": int(last_24h.get(path, 0)),
            "visits_30d": int(last_30d.get(path, 0)),
            "unique_30d": int(unique_30d.get(path, 0)),
        }
        for path in PUBLIC_PAGE_PATHS
    ]
    return {
        "pages": pages,
        "totals": {
            "visits_total": sum(item["visits_total"] for item in pages),
            "visits_24h": sum(item["visits_24h"] for item in pages),
            "visits_30d": sum(item["visits_30d"] for item in pages),
        },
    }


async def _payment_payload(session: AsyncSession, clinics_by_id: dict[uuid.UUID, ClinicRegistry]) -> dict:
    rows = list(
        (
            await session.scalars(
                select(AccessRequest)
                .where(AccessRequest.payment_verified_at.is_not(None))
                .order_by(AccessRequest.payment_verified_at.desc())
            )
        ).all()
    )
    payments = []
    revenue = defaultdict(int)
    accounted = 0
    for row in rows:
        clinic = clinics_by_id.get(row.activated_clinic_id) if row.activated_clinic_id else None
        if clinic is not None and _clinic_category(clinic) == "GIFT":
            continue
        amount = row.payment_amount
        currency = row.payment_currency
        is_accounted = amount is not None and bool(currency)
        if is_accounted:
            revenue[str(currency)] += int(amount or 0)
            accounted += 1
        payments.append(
            {
                "id": str(row.id),
                "clinic_id": str(row.activated_clinic_id) if row.activated_clinic_id else None,
                "clinic_name": clinic.name if clinic else row.clinic_name,
                "market": market_code(row.country, row.city, row.address),
                "amount": amount,
                "currency": currency,
                "accounted": is_accounted,
                "reference": row.payment_reference,
                "proof_note": row.payment_proof_note,
                "verified_at": row.payment_verified_at,
                "created_at": row.created_at,
            }
        )
    return {
        "items": payments,
        "verified_count": len(payments),
        "accounted_count": accounted,
        "unpriced_legacy_count": len(payments) - accounted,
        "revenue_by_currency": dict(revenue),
    }


@router.get("/dashboard", dependencies=[Depends(require_platform_admin)])
async def admin_control_dashboard(
    session: Annotated[AsyncSession, Depends(control_session)],
):
    clinics = list(
        (
            await session.scalars(select(ClinicRegistry).order_by(ClinicRegistry.created_at.desc()))
        ).all()
    )
    clinic_rows = []
    for clinic in clinics:
        clinic_rows.append(_serialize_clinic(clinic, await _tenant_stats(session, clinic)))

    categories = Counter(row["category"] for row in clinic_rows)
    states = Counter(row["operational_state"] for row in clinic_rows)
    totals = defaultdict(int)
    for row in clinic_rows:
        for key, value in row["stats"].items():
            if isinstance(value, int):
                totals[key] += value

    clinics_by_id = {clinic.id: clinic for clinic in clinics}
    payments = await _payment_payload(session, clinics_by_id)
    traffic = await _traffic_payload(session)
    pending_requests = int(
        await session.scalar(
            select(func.count())
            .select_from(AccessRequest)
            .where(AccessRequest.status.in_(["SUBMITTED", "PAYMENT_REQUESTED", "PAYMENT_REVIEW"]))
        )
        or 0
    )
    failed_emails = int(
        await session.scalar(
            select(func.count())
            .select_from(PlatformEmailLog)
            .where(PlatformEmailLog.status == "FAILED")
        )
        or 0
    )
    recent_audit = list(
        (
            await session.scalars(
                select(PlatformAdminAudit)
                .order_by(PlatformAdminAudit.created_at.desc())
                .limit(40)
            )
        ).all()
    )

    return {
        "generated_at": datetime.now(UTC),
        "clinics": clinic_rows,
        "summary": {
            "clinics_total": len(clinic_rows),
            "clinics_free": categories["FREE"],
            "clinics_paid": categories["PAID"],
            "clinics_gifted": categories["GIFT"],
            "clinics_legacy": categories["LEGACY"],
            "clinics_archived": states["ARCHIVED"],
            "clinics_payment_review": states["PAYMENT_REVIEW"],
            "pending_requests": pending_requests,
            "failed_emails": failed_emails,
            **dict(totals),
            "payments_verified": payments["verified_count"],
        },
        "payments": payments,
        "traffic": traffic,
        "recent_audit": [
            {
                "id": str(row.id),
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "details": row.details,
                "created_at": row.created_at,
            }
            for row in recent_audit
        ],
    }


@router.get("/clinics/{clinic_id}", dependencies=[Depends(require_platform_admin)])
async def admin_control_clinic(
    clinic_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await session.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    request = await session.scalar(
        select(AccessRequest)
        .where(AccessRequest.activated_clinic_id == clinic.id)
        .order_by(AccessRequest.created_at.desc())
        .limit(1)
    )
    return {
        "clinic": _serialize_clinic(clinic, await _tenant_stats(session, clinic)),
        "access_request": (
            {
                "id": str(request.id),
                "clinic_name": request.clinic_name,
                "contact_name": request.contact_name,
                "email": request.email,
                "phone": request.phone,
                "country": request.country,
                "city": request.city,
                "status": request.status,
                "payment_reference": request.payment_reference,
                "payment_amount": request.payment_amount,
                "payment_currency": request.payment_currency,
                "payment_verified_at": request.payment_verified_at,
                "created_at": request.created_at,
            }
            if request
            else None
        ),
    }


@router.patch("/clinics/{clinic_id}", dependencies=[Depends(require_platform_admin)])
async def edit_clinic(
    clinic_id: uuid.UUID,
    body: ClinicEdit,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await session.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes:
        clinic.name = str(changes["name"]).strip()
    if "is_active" in changes:
        clinic.is_active = bool(changes["is_active"])
    if "subscription_state" in changes and changes["subscription_state"] is not None:
        clinic.subscription_state = str(changes["subscription_state"]).upper()
    if "expires_at" in changes:
        clinic.subscription_expires_at = changes["expires_at"]
    clinic.updated_at = datetime.now(UTC)
    await _audit(
        session,
        action="CLINIC_EDITED",
        target_type="CLINIC",
        target_id=str(clinic.id),
        details={"changes": {key: str(value) for key, value in changes.items()}},
    )
    await session.commit()
    return _serialize_clinic(clinic, await _tenant_stats(session, clinic))


@router.post("/clinics/{clinic_id}/gift", dependencies=[Depends(require_platform_admin)])
async def grant_gift(
    clinic_id: uuid.UUID,
    body: GiftGrant,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await session.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    now = datetime.now(UTC)
    expires = now + timedelta(days=30 * body.months)
    clinic.subscription_plan = "PREMIUM"
    clinic.subscription_state = "ACTIVE"
    clinic.subscription_source = "GIFT"
    clinic.subscription_starts_at = now
    clinic.subscription_expires_at = expires
    clinic.gift_granted_at = now
    clinic.gift_note = body.note.strip() if body.note else None
    clinic.upgrade_requested_at = None
    clinic.is_active = True
    clinic.updated_at = now
    await _audit(
        session,
        action="GIFT_PREMIUM_GRANTED",
        target_type="CLINIC",
        target_id=str(clinic.id),
        details={"months": body.months, "expires_at": expires.isoformat(), "note": body.note},
    )
    await session.commit()
    return _serialize_clinic(clinic, await _tenant_stats(session, clinic))


@router.post("/clinics/{clinic_id}/archive", dependencies=[Depends(require_platform_admin)])
async def archive_clinic(
    clinic_id: uuid.UUID,
    body: ArchiveClinic,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await session.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    if body.confirm_slug.strip().casefold() != clinic.slug.casefold():
        raise AppError(
            "CLINIC_CONFIRMATION_MISMATCH",
            "Type the exact clinic slug to archive access.",
            409,
        )
    clinic.is_active = False
    clinic.subscription_state = "ARCHIVED"
    clinic.updated_at = datetime.now(UTC)
    await _audit(
        session,
        action="CLINIC_ARCHIVED",
        target_type="CLINIC",
        target_id=str(clinic.id),
        details={"slug": clinic.slug, "note": body.note},
    )
    await session.commit()
    return {"archived": True, "clinic_id": str(clinic.id), "data_preserved": True}


@router.patch("/access-requests/{request_id}", dependencies=[Depends(require_platform_admin)])
async def edit_access_request(
    request_id: uuid.UUID,
    body: RequestEdit,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(row, field, value)
    row.updated_at = datetime.now(UTC)
    await _audit(
        session,
        action="ACCESS_REQUEST_EDITED",
        target_type="ACCESS_REQUEST",
        target_id=str(row.id),
        details={"fields": list(changes)},
    )
    await session.commit()
    return {"id": str(row.id), "updated": True}


@router.delete("/access-requests/{request_id}", dependencies=[Depends(require_platform_admin)])
async def delete_access_request(
    request_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.activated_clinic_id:
        raise AppError(
            "ACCESS_REQUEST_LINKED_TO_CLINIC",
            "Activated clinic requests cannot be deleted. Archive the clinic instead so its history is preserved.",
            409,
        )
    await _audit(
        session,
        action="ACCESS_REQUEST_DELETED",
        target_type="ACCESS_REQUEST",
        target_id=str(row.id),
        details={"clinic_name": row.clinic_name, "email": row.email},
    )
    await session.delete(row)
    await session.commit()
    return {"deleted": True, "request_id": str(request_id)}
