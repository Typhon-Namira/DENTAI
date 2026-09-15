import uuid
from datetime import UTC, datetime
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
from app.platform.entitlements import FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT, is_free

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
    result = await generation_readiness(ctx.session, analysis)
    if is_free(ctx.clinic):
        result["free_plan_limit"] = FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT
        result["candidate_count_before_plan_limit"] = result.get("candidate_count", 0)
    return result


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

    items = list(
        (
            await ctx.session.scalars(
                select(CarePlanItem)
                .where(
                    CarePlanItem.care_plan_id == plan.id,
                    CarePlanItem.status != "REJECTED",
                )
                .order_by(CarePlanItem.sequence_order.asc(), CarePlanItem.priority_score.desc())
            )
        ).all()
    )

    if is_free(ctx.clinic) and len(items) > FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT:
        keep = items[:FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT]
        for item in items[FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT:]:
            item.status = "REJECTED"
            item.outcome = "FREE_PLAN_LIMIT"
            item.outcome_at = datetime.now(UTC)
            item.conversation_start_at = None
        items = keep
        plan.summary = (
            "Free plan follow-up: the highest-priority pathological tooth is included. "
            "Upgrade to Premium to follow all eligible teeth from this OPG."
        )

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
            "subscription_plan": ctx.clinic.subscription_plan,
        },
    )
    await ctx.session.commit()
    return {**model_dict(plan), "items": [model_dict(item) for item in items]}
