from collections import defaultdict
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
from app.outreach.messages import armenian_group_message, armenian_message
from app.outreach.timing import FollowupTiming, FollowupTimingEngine, eligible_finding


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


def timing_for_finding(analysis: AIAnalysis, finding: DentalFinding) -> FollowupTiming:
    analysis_at = analysis.completed_at or analysis.requested_at or datetime.now(UTC)
    return FollowupTimingEngine().calculate(
        finding_type=finding.finding_type,
        tooth_fdi=finding.tooth_code,
        analysis_at=analysis_at,
        review_required=bool((finding.provenance or {}).get("review_required")),
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
    timing = timing_for_finding(analysis, finding)
    row = WhatsAppOutreach(
        patient_id=patient.id,
        analysis_id=analysis.id,
        finding_id=finding.id,
        source_finding_ids=[str(finding.id)],
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


async def build_grouped_outreach(
    session: AsyncSession,
    *,
    patient: Patient,
    analysis: AIAnalysis,
    items: list[tuple[DentalFinding, FollowupTiming]],
) -> WhatsAppOutreach:
    if not items:
        raise ValueError("At least one finding is required for grouped outreach.")
    findings = [item[0] for item in items]
    timings = [item[1] for item in items]
    first_finding, first_timing = items[0]
    teeth = list(dict.fromkeys(finding.tooth_code for finding in findings if finding.tooth_code))
    finding_types = list(dict.fromkeys(finding.finding_type for finding in findings))
    rule_ids = list(dict.fromkeys(timing.policy_rule_id for timing in timings))
    reasons = list(dict.fromkeys(timing.timing_reason for timing in timings))
    versions = list(dict.fromkeys(timing.policy_version for timing in timings))
    windows = list(dict.fromkeys(timing.recommended_window for timing in timings))
    tooth_summary = teeth[0] if len(teeth) == 1 else "MULTIPLE"
    finding_summary = ", ".join(finding_types)
    if len(finding_summary) > 500:
        finding_summary = "MULTIPLE_FINDINGS"
    row = WhatsAppOutreach(
        patient_id=patient.id,
        analysis_id=analysis.id,
        finding_id=first_finding.id,
        source_finding_ids=[str(finding.id) for finding in findings],
        tooth_fdi=tooth_summary,
        finding_type=finding_summary,
        recommended_window=windows[0] if len(windows) == 1 else "; ".join(windows),
        target_followup_at=first_timing.target_followup_at,
        scheduled_send_at=first_timing.scheduled_send_at,
        message=await armenian_group_message(timings),
        language="hy-AM",
        status=WhatsAppOutreachStatus.SCHEDULED,
        timing_reason="; ".join(reasons),
        timing_policy_rule_id=",".join(rule_ids),
        timing_policy_version=versions[0] if len(versions) == 1 else ",".join(versions),
        clinic_timezone=first_timing.clinic_timezone,
        include_image=False,
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

    eligible: list[tuple[DentalFinding, FollowupTiming]] = []
    for finding in findings:
        if eligible_finding(finding.tooth_code, finding.confidence):
            eligible.append((finding, timing_for_finding(analysis, finding)))

    groups: dict[tuple[datetime, datetime, str], list[tuple[DentalFinding, FollowupTiming]]] = (
        defaultdict(list)
    )
    for item in eligible:
        timing = item[1]
        groups[
            (timing.target_followup_at, timing.scheduled_send_at, timing.clinic_timezone)
        ].append(item)

    count = 0
    for items in groups.values():
        representative = items[0][0]
        existing = await session.scalar(
            select(WhatsAppOutreach.id).where(
                WhatsAppOutreach.analysis_id == analysis.id,
                WhatsAppOutreach.finding_id == representative.id,
            )
        )
        if existing:
            continue
        await build_grouped_outreach(
            session,
            patient=patient,
            analysis=analysis,
            items=items,
        )
        count += 1
    return count
