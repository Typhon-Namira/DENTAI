import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context
from app.care.generation_engine import build_followup_plan, generation_readiness
from app.care.models import CarePlanItem
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import AIAnalysis, AIStatus, Role

router = APIRouter(prefix="/care", tags=["care"])


async def _completed_analysis(ctx: AuthContext, analysis_id: uuid.UUID) -> AIAnalysis:
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
    return analysis


@router.get("/analyses/{analysis_id}/generation-readiness")
async def followup_generation_readiness(
    analysis_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    analysis = await _completed_analysis(ctx, analysis_id)
    return await generation_readiness(ctx.session, analysis)


@router.post("/analyses/{analysis_id}/generate-plan")
async def generate_followup_plan(
    analysis_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    analysis = await _completed_analysis(ctx, analysis_id)
    plan = await build_followup_plan(ctx.session, analysis)
    if not plan:
        raise AppError(
            "NO_FOLLOWUP_CANDIDATES",
            "No pathological tooth findings with a resolved FDI are available for follow-up.",
            409,
        )

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
    await audit(
        ctx.session,
        ctx.user,
        "CARE_PLAN_GENERATED",
        "CarePlan",
        plan.id,
        plan.branch_id,
        {"review_status": str(analysis.review_status), "tooth_count": len(items)},
    )
    await ctx.session.commit()
    return {**model_dict(plan), "items": [model_dict(item) for item in items]}
