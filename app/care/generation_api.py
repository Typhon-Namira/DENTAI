import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context
from app.care.models import CarePlanItem
from app.care.service import activate_reviewed_plan
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import AIAnalysis, AIStatus, ReviewStatus, Role

router = APIRouter(prefix="/care", tags=["care"])


@router.post("/analyses/{analysis_id}/generate-plan")
async def generate_followup_plan(
    analysis_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    if ctx.user.role != Role.DOCTOR:
        raise AppError("FORBIDDEN", "Only Doctors may generate a follow-up plan.", 403)

    analysis = await ctx.session.get(AIAnalysis, analysis_id)
    if not analysis:
        raise AppError("ANALYSIS_NOT_FOUND", "Analysis was not found.", 404)

    await authorized_patient(ctx, analysis.patient_id)

    if analysis.status != AIStatus.COMPLETED:
        raise AppError(
            "ANALYSIS_NOT_READY",
            "The OPG analysis must be completed before a follow-up plan can be generated.",
            409,
        )
    if analysis.review_status != ReviewStatus.REVIEWED:
        raise AppError(
            "CLINICIAN_REVIEW_REQUIRED",
            "Review the AI findings before generating the follow-up plan.",
            409,
        )

    plan = await activate_reviewed_plan(
        ctx.session,
        clinic_id=ctx.clinic.id,
        clinic_name=ctx.clinic.name,
        analysis=analysis,
    )
    if not plan:
        raise AppError(
            "NO_FOLLOWUP_CANDIDATES",
            "No eligible tooth findings are available for a follow-up plan.",
            409,
        )
    if plan.status == "REVIEWED_NO_ACTION":
        raise AppError(
            "NO_CONFIRMED_FINDINGS",
            "No clinician-confirmed problem teeth require follow-up.",
            409,
        )
    if plan.status == "READY_FOR_REVIEW":
        raise AppError(
            "CLINICIAN_REVIEW_REQUIRED",
            "Confirm or reject the detected problem teeth before generating the plan.",
            409,
        )

    items = (
        await ctx.session.scalars(
            select(CarePlanItem)
            .where(CarePlanItem.care_plan_id == plan.id)
            .order_by(CarePlanItem.target_followup_at.asc())
        )
    ).all()
    await audit(
        ctx.session,
        ctx.user,
        "CARE_PLAN_GENERATED",
        "CarePlan",
        plan.id,
        plan.branch_id,
    )
    await ctx.session.commit()
    return {**model_dict(plan), "items": [model_dict(item) for item in items]}
