import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.database.control_models import (
    AccessRequest,
    ClinicRegistry,
    PlatformAdminAudit,
    PlatformEmailLog,
)
from app.database.sessions import control_session
from app.platform.admin_control_service import (
    aggregate_clinic_stats,
    payment_payload,
    serialize_clinic,
    tenant_stats,
    traffic_payload,
)
from app.platform.api import require_platform_admin

router = APIRouter(prefix="/platform/admin-control", tags=["platform-admin-control"])


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


async def audit(
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
        clinic_rows.append(serialize_clinic(clinic, await tenant_stats(session, clinic)))

    categories, states, totals = aggregate_clinic_stats(clinic_rows)
    clinics_by_id = {clinic.id: clinic for clinic in clinics}
    payments = await payment_payload(session, clinics_by_id)
    traffic = await traffic_payload(session)
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
                select(PlatformAdminAudit).order_by(PlatformAdminAudit.created_at.desc()).limit(40)
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
            **totals,
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
        "clinic": serialize_clinic(clinic, await tenant_stats(session, clinic)),
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
    await audit(
        session,
        action="CLINIC_EDITED",
        target_type="CLINIC",
        target_id=str(clinic.id),
        details={"changes": {key: str(value) for key, value in changes.items()}},
    )
    await session.commit()
    return serialize_clinic(clinic, await tenant_stats(session, clinic))


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
    await audit(
        session,
        action="GIFT_PREMIUM_GRANTED",
        target_type="CLINIC",
        target_id=str(clinic.id),
        details={"months": body.months, "expires_at": expires.isoformat(), "note": body.note},
    )
    await session.commit()
    return serialize_clinic(clinic, await tenant_stats(session, clinic))


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
    await audit(
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
    await audit(
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
    await audit(
        session,
        action="ACCESS_REQUEST_DELETED",
        target_type="ACCESS_REQUEST",
        target_id=str(row.id),
        details={"clinic_name": row.clinic_name, "email": row.email},
    )
    await session.delete(row)
    await session.commit()
    return {"deleted": True, "request_id": str(request_id)}
