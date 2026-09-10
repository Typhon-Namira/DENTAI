import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context, roles
from app.care.models import CarePlan, CarePlanItem
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import Patient, PatientDoctorAssignment, Role

router = APIRouter(prefix="/care", tags=["care-sequential"])


class SequenceScheduleUpdate(BaseModel):
    conversation_start_at: datetime | None = None


def _branch_allowed(ctx: AuthContext, branch_id: uuid.UUID) -> bool:
    return ctx.user.role == Role.DIRECTOR or branch_id in ctx.branch_ids


@router.get("/sequential-plans/search")
async def search_sequential_plans(
    ctx: Annotated[AuthContext, Depends(current_context)],
    q: str | None = Query(default=None, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    query = select(CarePlan).join(Patient, Patient.id == CarePlan.patient_id)
    if ctx.user.role != Role.DIRECTOR:
        query = query.where(CarePlan.branch_id.in_(ctx.branch_ids))
    if ctx.user.role == Role.DOCTOR:
        query = query.where(
            CarePlan.patient_id.in_(
                select(PatientDoctorAssignment.patient_id).where(
                    PatientDoctorAssignment.doctor_id == ctx.user.id,
                    PatientDoctorAssignment.active.is_(True),
                )
            )
        )
    term = (q or "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(
            or_(
                Patient.first_name.ilike(pattern),
                Patient.last_name.ilike(pattern),
                Patient.patient_number.ilike(pattern),
                Patient.whatsapp_phone.ilike(pattern),
                Patient.phone.ilike(pattern),
            )
        )
    query = query.order_by(CarePlan.created_at.desc()).offset(offset).limit(limit + 1)
    plans = (await ctx.session.scalars(query)).all()
    has_more = len(plans) > limit
    plans = plans[:limit]
    patient_ids = {plan.patient_id for plan in plans}
    patients = (
        {
            patient.id: patient
            for patient in (
                await ctx.session.scalars(select(Patient).where(Patient.id.in_(patient_ids)))
            ).all()
        }
        if patient_ids
        else {}
    )
    rows = []
    for plan in plans:
        items = (
            await ctx.session.scalars(
                select(CarePlanItem)
                .where(
                    CarePlanItem.care_plan_id == plan.id,
                    CarePlanItem.status != "REJECTED",
                )
                .order_by(CarePlanItem.sequence_order.asc(), CarePlanItem.priority_score.desc())
            )
        ).all()
        patient = patients.get(plan.patient_id)
        rows.append(
            {
                **model_dict(plan),
                "patient": model_dict(patient) if patient else None,
                "items": [model_dict(item) for item in items],
            }
        )
    return {"items": rows, "offset": offset, "limit": limit, "has_more": has_more}


@router.patch("/plans/{plan_id}/items/{item_id}/sequence-schedule")
async def update_sequence_schedule(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    body: SequenceScheduleUpdate,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR))],
):
    plan = await ctx.session.get(CarePlan, plan_id)
    if not plan:
        raise AppError("CARE_PLAN_NOT_FOUND", "Care plan was not found.", 404)
    if not _branch_allowed(ctx, plan.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Care plan is outside your scope.", 403)
    await authorized_patient(ctx, plan.patient_id)
    if plan.status != "PENDING_APPROVAL":
        raise AppError("CARE_PLAN_LOCKED", "Only a pending plan can be edited.", 409)
    item = await ctx.session.get(CarePlanItem, item_id)
    if not item or item.care_plan_id != plan.id:
        raise AppError("CARE_PLAN_ITEM_NOT_FOUND", "Care plan item was not found.", 404)
    if item.sequence_order > 1 and body.conversation_start_at is not None:
        raise AppError(
            "SEQUENCE_DEPENDENCY_REQUIRED",
            "Later tooth conversations are unlocked by the previous tooth outcome and cannot be pre-scheduled independently.",
            409,
        )
    item.conversation_start_at = body.conversation_start_at
    await audit(
        ctx.session,
        ctx.user,
        "CARE_PLAN_SEQUENCE_SCHEDULE_UPDATED",
        "CarePlanItem",
        item.id,
        plan.branch_id,
        {
            "conversation_start_at": body.conversation_start_at.isoformat()
            if body.conversation_start_at
            else None
        },
    )
    await ctx.session.commit()
    return model_dict(item)
