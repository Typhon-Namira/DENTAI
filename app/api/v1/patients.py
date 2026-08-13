import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import (
    AIAnalysis,
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

router = APIRouter(prefix="/patients", tags=["patients"])


class PatientCreate(BaseModel):
    patient_number: str = Field(min_length=1, max_length=80)
    first_name: str
    last_name: str
    branch_id: uuid.UUID


class TransferRequest(BaseModel):
    destination_branch_id: uuid.UUID


@router.get("")
async def list_patients(
    ctx: Annotated[AuthContext, Depends(current_context)], page: int = 1, page_size: int = 25
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
    rows = (
        await ctx.session.scalars(q.offset((max(page, 1) - 1) * page_size).limit(page_size))
    ).all()
    return {"items": [model_dict(x) for x in rows], "page": page, "page_size": page_size}


@router.post("", status_code=201)
async def create_patient(
    body: PatientCreate, ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))]
):
    if ctx.user.role == Role.MANAGER and body.branch_id not in ctx.branch_ids:
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    patient = Patient(**body.model_dump())
    ctx.session.add(patient)
    await ctx.session.flush()
    await audit(ctx.session, ctx.user, "PATIENT_CREATED", "Patient", patient.id, patient.branch_id)
    await ctx.session.commit()
    return model_dict(patient)


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
