import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select

from app.ai.providers import ai_provider
from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context
from app.common.serialization import model_dict
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import sensitive_limit
from app.database.models import (
    AIAnalysis,
    AIStatus,
    DentalFinding,
    FindingReview,
    ReviewStatus,
    Role,
    XRay,
)
from app.storage.providers import storage_provider

router = APIRouter(prefix="/ai-analyses", tags=["ai-analyses"])


class CreateAnalysis(BaseModel):
    xray_id: uuid.UUID


class FindingDecision(BaseModel):
    finding_id: uuid.UUID
    decision: FindingReview


class ReviewRequest(BaseModel):
    decisions: list[FindingDecision]
    clinical_notes: str | None = None


@router.post("", status_code=201, dependencies=[Depends(sensitive_limit("ai-analysis", 30, 60))])
async def create(
    body: CreateAnalysis,
    response: Response,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    if ctx.user.role != Role.DOCTOR:
        raise AppError("FORBIDDEN", "Only Doctors may request dental AI analysis.", 403)
    xray = await ctx.session.get(XRay, body.xray_id)
    if not xray:
        raise AppError("XRAY_NOT_FOUND", "X-ray was not found.", 404)
    await authorized_patient(ctx, xray.patient_id)
    provider = ai_provider()
    prior_analysis = await ctx.session.scalar(
        select(AIAnalysis)
        .where(
            AIAnalysis.patient_id == xray.patient_id,
            AIAnalysis.status == AIStatus.COMPLETED,
            AIAnalysis.structured_result.is_not(None),
        )
        .order_by(AIAnalysis.completed_at.desc())
        .limit(1)
    )
    asynchronous = get_settings().ai_provider == "real_opg"
    analysis = AIAnalysis(
        patient_id=xray.patient_id,
        xray_id=xray.id,
        requested_by=ctx.user.id,
        status=AIStatus.QUEUED if asynchronous else AIStatus.PROCESSING,
        provider="pending",
        model_name="pending",
        model_version="pending",
        processing_started_at=None if asynchronous else datetime.now(UTC),
    )
    ctx.session.add(analysis)
    await ctx.session.flush()
    await audit(
        ctx.session,
        ctx.user,
        "AI_ANALYSIS_REQUESTED",
        "AIAnalysis",
        analysis.id,
        xray.branch_id,
    )
    await ctx.session.commit()
    if asynchronous:
        response.status_code = 202
        return model_dict(analysis)
    try:
        storage = storage_provider()
        image_bytes = await storage.read(xray.storage_key)
        result = await provider.analyze_xray(
            patient_context={"patient_id": str(xray.patient_id)},
            xray_reference=str(xray.id),
            image_bytes=image_bytes,
            prior_analysis=prior_analysis.structured_result if prior_analysis else None,
        )
        analysis.provider = result.provider
        analysis.model_name = result.model_name
        analysis.model_version = result.model_version
        analysis.analysis_schema_version = result.schema_version
        analysis.status = AIStatus.COMPLETED
        analysis.completed_at = datetime.now(UTC)
        analysis.structured_result = result.structured_result
        for item in result.findings:
            ctx.session.add(
                DentalFinding(
                    patient_id=xray.patient_id,
                    analysis_id=analysis.id,
                    source="AI",
                    review_status=FindingReview.PENDING,
                    **item,
                )
            )
        await audit(
            ctx.session,
            ctx.user,
            "AI_ANALYSIS_COMPLETED",
            "AIAnalysis",
            analysis.id,
            xray.branch_id,
        )
        await ctx.session.commit()
    except Exception as exc:
        await ctx.session.rollback()
        failed = await ctx.session.get(AIAnalysis, analysis.id)
        if failed:
            failed.status = AIStatus.FAILED
            failed.failed_at = datetime.now(UTC)
            failed.error_code = type(exc).__name__.upper()[:100]
            await audit(
                ctx.session,
                ctx.user,
                "AI_ANALYSIS_FAILED",
                "AIAnalysis",
                failed.id,
                xray.branch_id,
            )
            await ctx.session.commit()
        raise AppError("AI_ANALYSIS_FAILED", "The analysis could not be completed.", 422) from exc
    return model_dict(analysis)


@router.post("/{analysis_id}/review")
async def review(
    analysis_id: uuid.UUID,
    body: ReviewRequest,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    if ctx.user.role != Role.DOCTOR:
        raise AppError("FORBIDDEN", "Only Doctors may review AI findings.", 403)
    analysis = await ctx.session.get(AIAnalysis, analysis_id)
    if not analysis:
        raise AppError("ANALYSIS_NOT_FOUND", "Analysis was not found.", 404)
    await authorized_patient(ctx, analysis.patient_id)
    findings = {
        x.id: x
        for x in (
            await ctx.session.scalars(
                select(DentalFinding).where(DentalFinding.analysis_id == analysis.id)
            )
        ).all()
    }
    for decision in body.decisions:
        if decision.finding_id not in findings or decision.decision == FindingReview.PENDING:
            raise AppError("INVALID_FINDING_DECISION", "Finding decision is invalid.", 422)
        finding = findings[decision.finding_id]
        finding.review_status = decision.decision
        finding.confirmed_by = ctx.user.id
        finding.confirmed_at = datetime.now(UTC)
        if decision.decision == FindingReview.CONFIRMED:
            ctx.session.add(
                DentalFinding(
                    patient_id=finding.patient_id,
                    analysis_id=analysis.id,
                    tooth_code=finding.tooth_code,
                    finding_type=finding.finding_type,
                    description=finding.description,
                    source="DENTIST",
                    confidence=None,
                    review_status=FindingReview.CONFIRMED,
                    confirmed_by=ctx.user.id,
                    confirmed_at=datetime.now(UTC),
                )
            )
    analysis.review_status = ReviewStatus.REVIEWED
    analysis.reviewed_by = ctx.user.id
    analysis.reviewed_at = datetime.now(UTC)
    await audit(ctx.session, ctx.user, "AI_ANALYSIS_REVIEWED", "AIAnalysis", analysis.id)
    await ctx.session.commit()
    return model_dict(analysis)
