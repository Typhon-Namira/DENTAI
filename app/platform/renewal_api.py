import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.database.control_models import AccessRequest, ClinicRegistry
from app.database.sessions import control_session
from app.platform.api import _request, require_admin
from app.platform.service import PLAN_NAME, audit, send_payment_request

router = APIRouter(prefix="/platform/admin", tags=["platform-renewal"])


@router.post("/clinics/{clinic_id}/renew", dependencies=[Depends(require_admin)])
async def reject_unsafe_direct_renewal(clinic_id: uuid.UUID):
    raise AppError(
        "RENEWAL_PAYMENT_REQUIRED",
        "Start a renewal payment request first; direct subscription extension is disabled.",
        409,
    )


@router.post("/clinics/{clinic_id}/start-renewal", dependencies=[Depends(require_admin)])
async def start_renewal(
    clinic_id: uuid.UUID,
    control: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await control.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    previous = await control.scalar(
        select(AccessRequest)
        .where(AccessRequest.clinic_registry_id == clinic_id)
        .order_by(AccessRequest.created_at.desc())
        .limit(1)
    )
    if not previous:
        raise AppError(
            "ACCESS_REQUEST_NOT_FOUND",
            "No commercial contact is linked to this clinic.",
            404,
        )
    pending = await control.scalar(
        select(AccessRequest)
        .where(
            AccessRequest.clinic_registry_id == clinic_id,
            AccessRequest.status.in_(["SUBMITTED", "PAYMENT_REQUEST_SENT", "PAYMENT_CONFIRMED"]),
        )
        .order_by(AccessRequest.created_at.desc())
        .limit(1)
    )
    if pending:
        raise AppError(
            "RENEWAL_ALREADY_PENDING",
            "A renewal payment workflow is already pending for this clinic.",
            409,
        )

    row = AccessRequest(
        status="SUBMITTED",
        plan_name=PLAN_NAME,
        clinic_name=clinic.name,
        legal_name=previous.legal_name,
        country=previous.country,
        city=previous.city,
        address=previous.address,
        website=previous.website,
        contact_name=previous.contact_name,
        contact_role=previous.contact_role,
        contact_email=previous.contact_email,
        contact_phone=previous.contact_phone,
        dentist_count=previous.dentist_count,
        monthly_patient_volume=previous.monthly_patient_volume,
        preferred_language=previous.preferred_language,
        notes="Subscription renewal",
        clinic_registry_id=clinic.id,
        issued_username=previous.issued_username,
    )
    control.add(row)
    await control.flush()
    await send_payment_request(control, row)
    audit(
        control,
        "RENEWAL_PAYMENT_REQUESTED",
        request_id=row.id,
        clinic_id=clinic.id,
    )
    await control.commit()
    return _request(row)
