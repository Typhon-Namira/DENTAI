import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
)
from app.care.service import ensure_care_plan, settings_for_branch
from app.database.models import (
    AIAnalysis,
    DentalFinding,
    FindingReview,
    FollowUp,
    Patient,
    WhatsAppOutreach,
    WhatsAppOutreachStatus,
)

_PRIORITY_BASE = {
    "BONE_RESORPTION": ("URGENT", 100.0),
    "FURCATION_LESION": ("URGENT", 98.0),
    "DEEP_CARIES": ("HIGH", 92.0),
    "APICAL_PERIODONTITIS": ("HIGH", 90.0),
    "ROOT_FRAGMENT": ("HIGH", 88.0),
    "RESIDUAL_ROOT": ("HIGH", 86.0),
    "CARIES": ("HIGH", 82.0),
    "IMPACTED": ("MEDIUM", 62.0),
}


def _priority(finding: DentalFinding) -> tuple[str, float]:
    level, base = _PRIORITY_BASE.get(finding.finding_type.upper(), ("ROUTINE", 45.0))
    confidence = float(finding.confidence or 0.0)
    review_bonus = 2.0 if finding.review_status == FindingReview.CONFIRMED else 0.0
    return level, base + confidence * 8.0 + review_bonus


def _next_local_contact(timezone_name: str, *, days: int) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_now = datetime.now(UTC).astimezone(zone)
    target_date = local_now.date() + timedelta(days=days)
    return datetime.combine(target_date, time(16, 0), tzinfo=zone).astimezone(UTC)


async def generate_sequential_plan(session: AsyncSession, analysis: AIAnalysis) -> CarePlan | None:
    plan = await ensure_care_plan(session, analysis)
    if not plan:
        return None

    patient = await session.get(Patient, plan.patient_id)
    if not patient:
        return None
    settings = await settings_for_branch(session, patient.branch_id)

    items = (
        await session.scalars(select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id))
    ).all()
    findings = {
        row.id: row
        for row in (
            await session.scalars(
                select(DentalFinding).where(DentalFinding.analysis_id == analysis.id)
            )
        ).all()
    }

    eligible: list[tuple[CarePlanItem, DentalFinding]] = []
    for item in items:
        finding = findings.get(item.finding_id)
        if not finding:
            item.status = "REJECTED"
            continue
        if finding.review_status == FindingReview.REJECTED:
            item.status = "REJECTED"
            item.outcome = "CLINICIAN_REJECTED"
            item.outcome_at = datetime.now(UTC)
            continue
        eligible.append((item, finding))

    if not eligible:
        plan.status = "REVIEWED_NO_ACTION"
        plan.summary = "No pathological tooth findings remain eligible for follow-up."
        return plan

    ranked = sorted(eligible, key=lambda pair: _priority(pair[1])[1], reverse=True)
    first_start = _next_local_contact(settings.timezone, days=1)
    unreviewed = 0
    for order, (item, finding) in enumerate(ranked, start=1):
        level, score = _priority(finding)
        item.sequence_order = order
        item.priority_level = level
        item.priority_score = score
        item.outcome = None
        item.outcome_at = None
        if finding.review_status == FindingReview.PENDING:
            unreviewed += 1
        if order == 1:
            item.status = "FOLLOWUP_READY"
            item.conversation_start_at = first_start
        else:
            item.status = "WAITING_PREVIOUS_TOOTH"
            item.conversation_start_at = None

    reviewed = len(ranked) - unreviewed
    plan.status = "PENDING_APPROVAL"
    plan.summary = (
        f"Sequential AI follow-up for {len(ranked)} pathological tooth finding(s). "
        f"{reviewed} reviewed, {unreviewed} not yet reviewed. Clinician review is recommended but not required."
    )
    await session.flush()
    return plan


async def _conversation_for_plan(
    session: AsyncSession, *, plan: CarePlan, patient: Patient
) -> CareConversation | None:
    phone = patient.whatsapp_phone or patient.phone
    if not phone:
        return None
    existing = await session.scalar(
        select(CareConversation)
        .where(CareConversation.care_plan_id == plan.id)
        .order_by(CareConversation.created_at.desc())
        .limit(1)
    )
    if existing:
        return existing
    conversation = CareConversation(
        patient_id=patient.id,
        care_plan_id=plan.id,
        branch_id=plan.branch_id,
        whatsapp_phone=phone,
        language=plan.language,
        status="ACTIVE",
        booking_context={"sequence_mode": True},
        summary="Sequential tooth follow-up prepared. Waiting for the first scheduled contact.",
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def schedule_item_outreach(
    session: AsyncSession,
    *,
    plan: CarePlan,
    patient: Patient,
    item: CarePlanItem,
    start_at: datetime,
) -> WhatsAppOutreach | None:
    if not patient.whatsapp_phone:
        return None
    existing = await session.scalar(
        select(WhatsAppOutreach)
        .where(
            WhatsAppOutreach.finding_id == item.finding_id,
            WhatsAppOutreach.status.in_(
                [
                    WhatsAppOutreachStatus.QUEUED,
                    WhatsAppOutreachStatus.SCHEDULED,
                    WhatsAppOutreachStatus.CLAIMED,
                    WhatsAppOutreachStatus.SENDING,
                ]
            ),
        )
        .order_by(WhatsAppOutreach.created_at.desc())
        .limit(1)
    )
    if existing:
        existing.scheduled_send_at = start_at
        return existing

    settings = await settings_for_branch(session, plan.branch_id)
    row = WhatsAppOutreach(
        patient_id=patient.id,
        analysis_id=plan.analysis_id,
        finding_id=item.finding_id,
        source_finding_ids=[str(item.finding_id)],
        tooth_fdi=item.tooth_fdi,
        finding_type=item.finding_type,
        recommended_window=item.recommended_window,
        target_followup_at=item.target_followup_at,
        scheduled_send_at=start_at,
        message=item.message_preview
        or f"Hello {patient.first_name}. The clinic would like to follow up about tooth {item.tooth_fdi}.",
        language=plan.language,
        status=WhatsAppOutreachStatus.SCHEDULED,
        timing_reason=item.rationale,
        timing_policy_rule_id="CARE_SEQUENCE",
        timing_policy_version="1.0",
        clinic_timezone=settings.timezone,
        include_image=settings.attach_tooth_image and item.image_required,
    )
    session.add(row)
    await session.flush()
    return row


async def approve_sequential_plan(session: AsyncSession, *, plan: CarePlan) -> CarePlan:
    if plan.status != "PENDING_APPROVAL":
        return plan
    patient = await session.get(Patient, plan.patient_id)
    analysis = await session.get(AIAnalysis, plan.analysis_id)
    if not patient or not analysis:
        return plan

    items = (
        await session.scalars(
            select(CarePlanItem)
            .where(CarePlanItem.care_plan_id == plan.id, CarePlanItem.status != "REJECTED")
            .order_by(CarePlanItem.sequence_order.asc())
        )
    ).all()
    if not items:
        return plan

    plan.status = "ACTIVE"
    plan.activated_at = datetime.now(UTC)
    await _conversation_for_plan(session, plan=plan, patient=patient)

    for item in items:
        existing_followup = await session.scalar(
            select(FollowUp).where(
                FollowUp.patient_id == patient.id,
                FollowUp.reason.like(f"Teta2 Care · tooth {item.tooth_fdi}%"),
            )
        )
        if not existing_followup:
            session.add(
                FollowUp(
                    patient_id=patient.id,
                    doctor_id=plan.doctor_id,
                    branch_id=plan.branch_id,
                    reason=f"Teta2 Care · tooth {item.tooth_fdi} · {item.finding_type.replace('_', ' ')}",
                    due_at=item.target_followup_at,
                    status="SCHEDULED",
                    priority=item.priority_level,
                    notes=(
                        f"Sequential AI follow-up priority {item.sequence_order}. {item.rationale}"
                    ),
                    created_by=plan.doctor_id or analysis.requested_by,
                )
            )

    first = items[0]
    if first.conversation_start_at is None:
        settings = await settings_for_branch(session, plan.branch_id)
        first.conversation_start_at = _next_local_contact(settings.timezone, days=1)
    first.status = "FOLLOWUP_READY"
    await schedule_item_outreach(
        session,
        plan=plan,
        patient=patient,
        item=first,
        start_at=first.conversation_start_at,
    )
    await session.flush()
    return plan


async def record_scheduled_outreach_sent(
    session: AsyncSession,
    *,
    outreach: WhatsAppOutreach,
    provider_message_id: str | None,
) -> None:
    if not outreach.finding_id:
        return
    item = await session.scalar(
        select(CarePlanItem).where(CarePlanItem.finding_id == outreach.finding_id).limit(1)
    )
    if not item:
        return
    plan = await session.get(CarePlan, item.care_plan_id)
    patient = await session.get(Patient, outreach.patient_id)
    if not plan or not patient:
        return
    conversation = await _conversation_for_plan(session, plan=plan, patient=patient)
    if not conversation:
        return
    duplicate = None
    if provider_message_id:
        duplicate = await session.scalar(
            select(CareConversationMessage.id).where(
                CareConversationMessage.conversation_id == conversation.id,
                CareConversationMessage.provider_message_id == provider_message_id,
            )
        )
    if not duplicate:
        session.add(
            CareConversationMessage(
                conversation_id=conversation.id,
                care_plan_item_id=item.id,
                direction="OUT",
                body=outreach.message,
                language=conversation.language,
                status="SENT",
                sent_at=outreach.sent_at or datetime.now(UTC),
                attempt_count=max(1, outreach.attempt_count),
                provider_message_id=provider_message_id,
                message_metadata={
                    "kind": "scheduled_sequential_followup",
                    "tooth_fdi": item.tooth_fdi,
                    "sequence_order": item.sequence_order,
                    "priority_level": item.priority_level,
                },
            )
        )
    item.status = "CONTACTED"
    conversation.last_message_at = outreach.sent_at or datetime.now(UTC)
    conversation.summary = (
        f"AI follow-up active for tooth {item.tooth_fdi} (priority {item.sequence_order})."
    )


async def record_visit_outcome(
    session: AsyncSession,
    *,
    appointment: CareAppointment,
    outcome: str,
    note: str | None,
) -> CareAppointment:
    normalized = outcome.upper()
    if normalized not in {"TREATED", "ATTENDED_NOT_TREATED", "NO_SHOW"}:
        raise ValueError("INVALID_VISIT_OUTCOME")

    now = datetime.now(UTC)
    appointment.visit_outcome = normalized
    appointment.outcome_recorded_at = now
    appointment.doctor_note = note or appointment.doctor_note
    appointment.status = "COMPLETED" if normalized == "TREATED" else normalized

    item = (
        await session.get(CarePlanItem, appointment.care_plan_item_id)
        if appointment.care_plan_item_id
        else None
    )
    if not item:
        return appointment
    plan = await session.get(CarePlan, item.care_plan_id)
    patient = await session.get(Patient, appointment.patient_id)
    if not plan or not patient:
        return appointment

    item.outcome = normalized
    item.outcome_at = now
    conversation = (
        await session.get(CareConversation, appointment.conversation_id)
        if appointment.conversation_id
        else None
    )
    if conversation:
        context = dict(conversation.booking_context or {})
        context.update(
            {
                "last_visit_outcome": normalized,
                "last_visit_tooth": item.tooth_fdi,
                "last_visit_outcome_at": now.isoformat(),
                "last_visit_note": note,
            }
        )
        conversation.booking_context = context
        conversation.summary = (
            f"Visit outcome for tooth {item.tooth_fdi}: {normalized.replace('_', ' ').title()}."
        )

    settings = await settings_for_branch(session, plan.branch_id)
    if normalized == "ATTENDED_NOT_TREATED":
        item.status = "FOLLOWUP_READY"
        item.conversation_start_at = _next_local_contact(settings.timezone, days=7)
        await schedule_item_outreach(
            session,
            plan=plan,
            patient=patient,
            item=item,
            start_at=item.conversation_start_at,
        )
        return appointment

    item.status = "COMPLETED" if normalized == "TREATED" else "NO_SHOW"
    next_item = await session.scalar(
        select(CarePlanItem)
        .where(
            CarePlanItem.care_plan_id == plan.id,
            CarePlanItem.sequence_order > item.sequence_order,
            CarePlanItem.status == "WAITING_PREVIOUS_TOOTH",
        )
        .order_by(CarePlanItem.sequence_order.asc())
        .limit(1)
    )
    if next_item:
        delay_days = 1 if normalized == "TREATED" else 30
        next_item.status = "FOLLOWUP_READY"
        next_item.conversation_start_at = _next_local_contact(settings.timezone, days=delay_days)
        await schedule_item_outreach(
            session,
            plan=plan,
            patient=patient,
            item=next_item,
            start_at=next_item.conversation_start_at,
        )
    else:
        remaining = await session.scalar(
            select(CarePlanItem.id)
            .where(
                CarePlanItem.care_plan_id == plan.id,
                CarePlanItem.status.in_(
                    ["WAITING_PREVIOUS_TOOTH", "FOLLOWUP_READY", "CONTACTED", "BOOKED"]
                ),
            )
            .limit(1)
        )
        if remaining is None:
            plan.status = "COMPLETED"
            plan.completed_at = now
            if conversation:
                conversation.status = "CLOSED"

    await session.flush()
    return appointment
