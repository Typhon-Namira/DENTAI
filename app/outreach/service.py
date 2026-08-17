from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AIAnalysis,
    AIStatus,
    DentalFinding,
    Patient,
    WhatsAppOutreach,
    WhatsAppOutreachStatus,
)
from app.outreach.messages import armenian_message
from app.outreach.timing import FollowupTimingEngine, eligible_finding


async def latest_eligible_finding(session: AsyncSession, patient_id):
    analysis = await session.scalar(
        select(AIAnalysis)
        .where(AIAnalysis.patient_id == patient_id, AIAnalysis.status == AIStatus.COMPLETED)
        .order_by(AIAnalysis.completed_at.desc())
        .limit(1)
    )
    if analysis is None:
        return None, None
    findings = (
        await session.scalars(
            select(DentalFinding)
            .where(DentalFinding.analysis_id == analysis.id)
            .order_by(DentalFinding.confidence.desc())
        )
    ).all()
    return analysis, next(
        (item for item in findings if eligible_finding(item.tooth_code, item.confidence)), None
    )


async def build_outreach(
    session: AsyncSession,
    *,
    patient: Patient,
    analysis: AIAnalysis,
    finding: DentalFinding,
    immediate: bool = False,
    include_image: bool = False,
) -> WhatsAppOutreach:
    analysis_at = analysis.completed_at or analysis.requested_at or datetime.now(UTC)
    timing = FollowupTimingEngine().calculate(
        finding_type=finding.finding_type,
        tooth_fdi=finding.tooth_code,
        analysis_at=analysis_at,
        review_required=bool((finding.provenance or {}).get("review_required")),
    )
    row = WhatsAppOutreach(
        patient_id=patient.id,
        analysis_id=analysis.id,
        finding_id=finding.id,
        tooth_fdi=finding.tooth_code,
        finding_type=finding.finding_type,
        recommended_window=timing.recommended_window,
        target_followup_at=timing.target_followup_at,
        scheduled_send_at=datetime.now(UTC) if immediate else timing.scheduled_send_at,
        message=await armenian_message(timing),
        language="hy-AM",
        status=WhatsAppOutreachStatus.QUEUED if immediate else WhatsAppOutreachStatus.SCHEDULED,
        timing_reason=timing.timing_reason,
        timing_policy_rule_id=timing.policy_rule_id,
        timing_policy_version=timing.policy_version,
        clinic_timezone=timing.clinic_timezone,
        include_image=include_image,
    )
    session.add(row)
    await session.flush()
    return row


async def schedule_analysis_outreach(
    session: AsyncSession, analysis: AIAnalysis, findings: list[DentalFinding]
) -> int:
    patient = await session.get(Patient, analysis.patient_id)
    if patient is None:
        return 0
    count = 0
    for finding in findings:
        if not eligible_finding(finding.tooth_code, finding.confidence):
            continue
        existing = await session.scalar(
            select(WhatsAppOutreach.id).where(
                WhatsAppOutreach.analysis_id == analysis.id,
                WhatsAppOutreach.finding_id == finding.id,
            )
        )
        if existing:
            continue
        await build_outreach(session, patient=patient, analysis=analysis, finding=finding)
        count += 1
    return count
