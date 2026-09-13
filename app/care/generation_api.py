import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context
from app.care.generation_engine import build_followup_plan, generation_readiness
from app.care.groq import care_outreach_drafts
from app.care.models import CarePlanItem
from app.care.service import settings_for_branch
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import AIAnalysis, AIStatus, DentalFinding, FindingReview, Patient

router = APIRouter(prefix="/care", tags=["care"])


async def _completed_analysis(ctx: AuthContext, analysis_id: uuid.UUID) -> AIAnalysis:
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

    patient = await ctx.session.get(Patient, plan.patient_id)
    findings = {
        finding.id: finding
        for finding in (
            await ctx.session.scalars(
                select(DentalFinding).where(DentalFinding.analysis_id == analysis.id)
            )
        ).all()
    }
    settings = await settings_for_branch(ctx.session, plan.branch_id)
    groq_drafts: dict[str, str] = {}
    if patient and items:
        groq_drafts = await care_outreach_drafts(
            language=plan.language,
            patient_name=f"{patient.first_name} {patient.last_name}".strip(),
            clinic_name=ctx.clinic.name,
            care_items=[
                {
                    "tooth": item.tooth_fdi,
                    "finding": item.finding_type,
                    "window": item.recommended_window,
                    "rationale": item.rationale,
                    "clinician_reviewed": bool(
                        findings.get(item.finding_id)
                        and findings[item.finding_id].review_status == FindingReview.CONFIRMED
                    ),
                    "visit_outcome": item.outcome,
                }
                for item in items
            ],
            booking_instructions=settings.booking_instructions,
        )
        missing = [item.tooth_fdi for item in items if not groq_drafts.get(item.tooth_fdi)]
        if missing:
            await ctx.session.rollback()
            raise AppError(
                "AI_OUTREACH_DRAFT_UNAVAILABLE",
                "Teta2 could not create individualized patient messages. Please try again; no template message was saved.",
                503,
            )
        for item in items:
            item.message_preview = groq_drafts[item.tooth_fdi]

    await audit(
        ctx.session,
        ctx.user,
        "CARE_PLAN_GENERATED",
        "CarePlan",
        plan.id,
        plan.branch_id,
        {
            "review_status": str(analysis.review_status),
            "tooth_count": len(items),
            "groq_draft_count": len(groq_drafts),
        },
    )
    await ctx.session.commit()
    return {**model_dict(plan), "items": [model_dict(item) for item in items]}
