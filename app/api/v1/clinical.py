import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import (
    CareTimelineItem,
    FollowUp,
    FutureRiskProfile,
    PatientDoctorAssignment,
    Role,
    User,
    UserBranchScope,
    Visit,
)

router = APIRouter(tags=["clinical"])


class AssignmentCreate(BaseModel):
    doctor_id: uuid.UUID


class VisitCreate(BaseModel):
    visit_date: datetime
    summary: str = Field(min_length=1, max_length=2000)
    clinical_notes: str | None = Field(default=None, max_length=10000)


class FollowUpStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    DUE = "DUE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FollowUpCreate(BaseModel):
    doctor_id: uuid.UUID | None = None
    reason: str = Field(min_length=1, max_length=2000)
    due_at: datetime
    priority: str = Field(default="NORMAL", pattern=r"^(LOW|NORMAL|HIGH|URGENT)$")
    notes: str | None = Field(default=None, max_length=5000)


class FollowUpUpdate(BaseModel):
    status: FollowUpStatus


@router.post("/patients/{patient_id}/assignments", status_code=201)
async def assign_doctor(
    patient_id: uuid.UUID,
    body: AssignmentCreate,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    patient = await authorized_patient(ctx, patient_id)
    doctor = await ctx.session.get(User, body.doctor_id)
    if not doctor or doctor.role != Role.DOCTOR or not doctor.is_active:
        raise AppError("DOCTOR_NOT_FOUND", "Doctor was not found.", 404)
    scopes = set(
        (
            await ctx.session.scalars(
                select(UserBranchScope.branch_id).where(UserBranchScope.user_id == doctor.id)
            )
        ).all()
    )
    if patient.branch_id not in scopes:
        raise AppError("DOCTOR_BRANCH_MISMATCH", "Doctor is not assigned to this branch.", 422)
    existing = await ctx.session.scalar(
        select(PatientDoctorAssignment).where(
            PatientDoctorAssignment.patient_id == patient.id,
            PatientDoctorAssignment.doctor_id == doctor.id,
            PatientDoctorAssignment.active.is_(True),
        )
    )
    if existing:
        raise AppError("ASSIGNMENT_EXISTS", "Doctor is already assigned to this patient.", 409)
    assignment = PatientDoctorAssignment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        branch_id=patient.branch_id,
        assigned_by=ctx.user.id,
    )
    ctx.session.add(assignment)
    await ctx.session.flush()
    await audit(
        ctx.session,
        ctx.user,
        "PATIENT_ASSIGNED_TO_DOCTOR",
        "PatientDoctorAssignment",
        assignment.id,
        patient.branch_id,
    )
    await ctx.session.commit()
    return model_dict(assignment)


@router.post("/patients/{patient_id}/visits", status_code=201)
async def create_visit(
    patient_id: uuid.UUID,
    body: VisitCreate,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    patient = await authorized_patient(ctx, patient_id)
    if ctx.user.role != Role.DOCTOR:
        raise AppError("FORBIDDEN", "Only Doctors may create clinical visits.", 403)
    visit = Visit(
        patient_id=patient.id,
        doctor_id=ctx.user.id,
        branch_id=patient.branch_id,
        **body.model_dump(),
    )
    ctx.session.add(visit)
    await ctx.session.commit()
    return model_dict(visit)


@router.get("/patients/{patient_id}/future-risk")
async def future_risk(patient_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]):
    await authorized_patient(ctx, patient_id)
    rows = (
        await ctx.session.scalars(
            select(FutureRiskProfile).where(FutureRiskProfile.patient_id == patient_id)
        )
    ).all()
    return [model_dict(row) for row in rows]


@router.get("/patients/{patient_id}/future-care")
async def future_care(patient_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]):
    await authorized_patient(ctx, patient_id)
    rows = (
        await ctx.session.scalars(
            select(CareTimelineItem).where(CareTimelineItem.patient_id == patient_id)
        )
    ).all()
    return [model_dict(row) for row in rows]


@router.post("/patients/{patient_id}/follow-ups", status_code=201)
async def create_follow_up(
    patient_id: uuid.UUID,
    body: FollowUpCreate,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    patient = await authorized_patient(ctx, patient_id)
    doctor_id = body.doctor_id or (ctx.user.id if ctx.user.role == Role.DOCTOR else None)
    follow_up = FollowUp(
        patient_id=patient.id,
        doctor_id=doctor_id,
        branch_id=patient.branch_id,
        reason=body.reason,
        due_at=body.due_at,
        status=FollowUpStatus.SCHEDULED.value,
        priority=body.priority,
        notes=body.notes,
        created_by=ctx.user.id,
    )
    ctx.session.add(follow_up)
    await ctx.session.flush()
    await audit(
        ctx.session,
        ctx.user,
        "FOLLOWUP_CREATED",
        "FollowUp",
        follow_up.id,
        patient.branch_id,
    )
    await ctx.session.commit()
    return model_dict(follow_up)


@router.get("/follow-ups")
async def list_follow_ups(
    ctx: Annotated[AuthContext, Depends(current_context)],
    status: FollowUpStatus | None = None,
    due_before: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    query = select(FollowUp)
    if ctx.user.role == Role.MANAGER:
        query = query.where(FollowUp.branch_id.in_(ctx.branch_ids))
    elif ctx.user.role == Role.DOCTOR:
        query = query.where(FollowUp.doctor_id == ctx.user.id)
    if status:
        query = query.where(FollowUp.status == status.value)
    if due_before:
        query = query.where(FollowUp.due_at <= due_before)
    rows = (await ctx.session.scalars(query.offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [model_dict(row) for row in rows], "page": page, "page_size": page_size}


@router.patch("/follow-ups/{follow_up_id}")
async def update_follow_up(
    follow_up_id: uuid.UUID,
    body: FollowUpUpdate,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    follow_up = await ctx.session.get(FollowUp, follow_up_id)
    if not follow_up:
        raise AppError("FOLLOWUP_NOT_FOUND", "Follow-up was not found.", 404)
    await authorized_patient(ctx, follow_up.patient_id)
    follow_up.status = body.status.value
    follow_up.completed_at = datetime.now(UTC) if body.status == FollowUpStatus.COMPLETED else None
    action = "FOLLOWUP_COMPLETED" if body.status == FollowUpStatus.COMPLETED else "FOLLOWUP_UPDATED"
    await audit(ctx.session, ctx.user, action, "FollowUp", follow_up.id, follow_up.branch_id)
    await ctx.session.commit()
    return model_dict(follow_up)
