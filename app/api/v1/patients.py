import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.care.models import CareAppointment, CareConversation, CarePlan
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import (
    AIAnalysis,
    AuditLog,
    Branch,
    CareTimelineItem,
    DentalFinding,
    FollowUp,
    FutureRiskProfile,
    Patient,
    PatientDoctorAssignment,
    Role,
    Visit,
    XRay,
)
from app.outreach.whatsapp_client import normalize_phone

router = APIRouter(prefix="/patients", tags=["patients"])


class PatientCreate(BaseModel):
    patient_number: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    branch_id: uuid.UUID
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=40)
    whatsapp_phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None


class TransferRequest(BaseModel):
    destination_branch_id: uuid.UUID


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=40)
    whatsapp_phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None


def _normalized_phone(value: str | None, field_name: str) -> str | None:
    if value is None or not value.strip():
        return None
    try:
        return normalize_phone(value)
    except ValueError as exc:
        raise AppError(
            "INVALID_PHONE",
            f"{field_name} must use international format, for example +374XXXXXXXX.",
            422,
        ) from exc


@router.get("")
async def list_patients(
    ctx: Annotated[AuthContext, Depends(current_context)],
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    status: str | None = "ACTIVE",
    branch_id: uuid.UUID | None = None,
):
    page_size = min(max(page_size, 1), 100)
    q = select(Patient)
    if ctx.user.role != Role.DIRECTOR:
        q = q.where(Patient.branch_id.in_(ctx.branch_ids))
    if ctx.user.role == Role.DOCTOR:
        q = q.join(PatientDoctorAssignment, PatientDoctorAssignment.patient_id == Patient.id).where(
            PatientDoctorAssignment.doctor_id == ctx.user.id,
            PatientDoctorAssignment.active.is_(True),
        )
    if branch_id:
        if ctx.user.role != Role.DIRECTOR and branch_id not in ctx.branch_ids:
            raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
        q = q.where(Patient.branch_id == branch_id)
    if status:
        normalized_status = status.upper()
        if normalized_status not in {"ACTIVE", "ARCHIVED", "ALL"}:
            raise AppError("INVALID_PATIENT_STATUS", "Patient status is invalid.", 422)
        if normalized_status != "ALL":
            q = q.where(Patient.status == normalized_status)
    if search and search.strip():
        value = f"%{search.strip()}%"
        q = q.where(
            or_(
                Patient.patient_number.ilike(value),
                Patient.first_name.ilike(value),
                Patient.last_name.ilike(value),
                Patient.email.ilike(value),
                Patient.phone.ilike(value),
                Patient.whatsapp_phone.ilike(value),
            )
        )
    q = q.order_by(Patient.created_at.desc())
    total = await ctx.session.scalar(select(func.count()).select_from(q.order_by(None).subquery()))
    rows = (
        await ctx.session.scalars(q.offset((max(page, 1) - 1) * page_size).limit(page_size))
    ).all()
    return {
        "items": [model_dict(x) for x in rows],
        "page": page,
        "page_size": page_size,
        "total": total or 0,
    }


@router.post("", status_code=201)
async def create_patient(
    body: PatientCreate,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    if ctx.user.role != Role.DIRECTOR and body.branch_id not in ctx.branch_ids:
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    payload = body.model_dump()
    payload["phone"] = _normalized_phone(body.phone, "Phone")
    payload["whatsapp_phone"] = _normalized_phone(body.whatsapp_phone, "WhatsApp number")
    payload["email"] = str(body.email) if body.email else None
    duplicate = await ctx.session.scalar(
        select(Patient.id).where(Patient.patient_number == body.patient_number)
    )
    if duplicate:
        raise AppError(
            "PATIENT_NUMBER_EXISTS", "A patient with this record number already exists.", 409
        )
    patient = Patient(**payload)
    ctx.session.add(patient)
    await ctx.session.flush()
    if ctx.user.role == Role.DOCTOR:
        ctx.session.add(
            PatientDoctorAssignment(
                patient_id=patient.id,
                doctor_id=ctx.user.id,
                branch_id=patient.branch_id,
                assigned_by=ctx.user.id,
            )
        )
        await ctx.session.flush()
    await audit(ctx.session, ctx.user, "PATIENT_CREATED", "Patient", patient.id, patient.branch_id)
    await ctx.session.commit()
    return model_dict(patient)


@router.patch("/{patient_id}")
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    patient = await authorized_patient(ctx, patient_id)
    changes = body.model_dump(exclude_unset=True)
    for field in ("phone", "whatsapp_phone"):
        if field in changes:
            changes[field] = _normalized_phone(changes[field], field.replace("_", " ").title())
    if "email" in changes:
        changes["email"] = str(changes["email"]) if changes["email"] else None
    for key, value in changes.items():
        setattr(patient, key, value)
    await audit(
        ctx.session,
        ctx.user,
        "PATIENT_UPDATED",
        "Patient",
        patient.id,
        patient.branch_id,
        {"fields": sorted(changes)},
    )
    await ctx.session.commit()
    return model_dict(patient)


async def _set_patient_status(patient_id: uuid.UUID, status: str, ctx: AuthContext):
    patient = await authorized_patient(ctx, patient_id)
    if patient.status == status:
        return model_dict(patient)
    patient.status = status
    await audit(
        ctx.session, ctx.user, f"PATIENT_{status}", "Patient", patient.id, patient.branch_id
    )
    await ctx.session.commit()
    return model_dict(patient)


@router.post("/{patient_id}/archive")
async def archive_patient(
    patient_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    return await _set_patient_status(patient_id, "ARCHIVED", ctx)


@router.post("/{patient_id}/restore")
async def restore_patient(
    patient_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    return await _set_patient_status(patient_id, "ACTIVE", ctx)


@router.get("/{patient_id}/profile")
async def profile(patient_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]):
    patient = await authorized_patient(ctx, patient_id)

    async def rows(model):
        return [
            model_dict(x)
            for x in (
                await ctx.session.scalars(select(model).where(model.patient_id == patient.id))
            ).all()
        ]

    return {
        "patient": model_dict(patient),
        "assignments": await rows(PatientDoctorAssignment),
        "visits": await rows(Visit),
        "xrays": await rows(XRay),
        "ai_analyses": await rows(AIAnalysis),
        "findings": await rows(DentalFinding),
        "future_risk": await rows(FutureRiskProfile),
        "future_care": await rows(CareTimelineItem),
        "followups": await rows(FollowUp),
        "care_plans": await rows(CarePlan),
        "conversations": await rows(CareConversation),
        "appointments": await rows(CareAppointment),
        "audit_history": [
            model_dict(item)
            for item in (
                await ctx.session.scalars(
                    select(AuditLog)
                    .where(AuditLog.entity_id == str(patient.id))
                    .order_by(AuditLog.created_at.desc())
                    .limit(200)
                )
            ).all()
        ],
    }


@router.post("/{patient_id}/transfer")
async def transfer(
    patient_id: uuid.UUID,
    body: TransferRequest,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    patient = await authorized_patient(ctx, patient_id)
    destination = await ctx.session.get(Branch, body.destination_branch_id)
    if not destination or not destination.is_active:
        raise AppError("DESTINATION_BRANCH_INVALID", "Destination branch is invalid.", 422)
    if ctx.user.role == Role.MANAGER and body.destination_branch_id not in ctx.branch_ids:
        raise AppError("BRANCH_NOT_AUTHORIZED", "Destination is outside your scope.", 403)
    old = patient.branch_id
    patient.branch_id = destination.id
    assignments = (
        await ctx.session.scalars(
            select(PatientDoctorAssignment).where(
                PatientDoctorAssignment.patient_id == patient.id,
                PatientDoctorAssignment.active.is_(True),
            )
        )
    ).all()
    for a in assignments:
        a.active = False
    await audit(
        ctx.session,
        ctx.user,
        "PATIENT_TRANSFERRED",
        "Patient",
        patient.id,
        destination.id,
        {"from": str(old), "to": str(destination.id)},
    )
    await ctx.session.commit()
    return model_dict(patient)
