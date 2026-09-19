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
from app.care.outreach_invariants import (
    add_calendar_months,
    align_sequence_schedule,
    monthly_sequence_at,
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


def _monthly_contact(first_start: datetime, timezone_name: str, month_offset: int) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_start = first_start.astimezone(zone)
    return add_calendar_months(local_start, month_offset).astimezone(UTC)


def _approval_schedule(item: CarePlanItem, fallback: datetime) -> datetime:
    """Use the clinician-edited follow-up date as the authoritative send date."""
    return item.target_followup_at or item.conversation_start_at or fallback


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
    now = datetime.now(UTC)
    for item in items:
        finding = findings.get(item.finding_id)
        if not finding:
            item.status = "REJECTED"
            continue
        if finding.review_status == FindingReview.REJECTED:
            item.status = "REJECTED"
            item.outcome = "CLINICIAN_REJECTED"
            item.outcome_at = now
            continue
        eligible.append((item, finding))

    if not eligible:
        plan.status = "REVIEWED_NO_ACTION"
        plan.summary = "No pathological tooth findings remain eligible for follow-up."
        return plan

    ranked_all = sorted(eligible, key=lambda pair: _priority(pair[1])[1], reverse=True)
    ranked: list[tuple[CarePlanItem, DentalFinding]] = []
    seen_teeth: set[str] = set()
    for item, finding in ranked_all:
        tooth = str(item.tooth_fdi).strip()
        if tooth in seen_teeth:
            item.status = "DUPLICATE_TOOTH_SUPPRESSED"
            item.outcome = "DUPLICATE_TOOTH_SUPPRESSED"
            item.outcome_at = now
            item.conversation_start_at = None
            continue
        seen_teeth.add(tooth)
        ranked.append((item, finding))

    if not ranked:
        plan.status = "REVIEWED_NO_ACTION"
        plan.summary = "No unique pathological teeth remain eligible for follow-up."
        return plan

    first_start = _next_local_contact(settings.timezone, days=1)
    unreviewed = 0
    for order, (item, finding) in enumerate(ranked, start=1):
        level, score = _priority(finding)
        scheduled_at = _monthly_contact(first_start, settings.timezone, order - 1)
        item.sequence_order = order
        item.priority_level = level
        item.priority_score = score
        item.outcome = None
        item.outcome_at = None
        item.conversation_start_at = scheduled_at
        item.target_followup_at = scheduled_at
        if finding.review_status == FindingReview.PENDING:
            unreviewed += 1
        item.status = "FOLLOWUP_READY" if order == 1 else "SCHEDULED_FUTURE_TOOTH"

    reviewed = len(ranked) - unreviewed
    plan.status = "PENDING_APPROVAL"
    plan.summary = (
        f"Sequential AI follow-up for {len(ranked)} unique pathological tooth finding(s). "
        "The first tooth is scheduled for the next clinic-local day and each later tooth is "
        "exactly one calendar month after the previous tooth. "
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
        status="WAITING_NEXT_TOOTH",
        booking_context={"sequence_mode": True},
        summary="Sequential tooth follow-up prepared. AI remains inactive until the first scheduled outreach is actually sent.",
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
    if not (patient.whatsapp_phone or patient.phone):
        return None

    existing = await session.scalar(
        select(WhatsAppOutreach)
        .where(
            WhatsAppOutreach.patient_id == patient.id,
            WhatsAppOutreach.analysis_id == plan.analysis_id,
            WhatsAppOutreach.tooth_fdi == item.tooth_fdi,
        )
        .order_by(WhatsAppOutreach.created_at.desc())
        .limit(1)
    )
    if existing:
        if existing.status in {
            WhatsAppOutreachStatus.QUEUED,
            WhatsAppOutreachStatus.SCHEDULED,
            WhatsAppOutreachStatus.CLAIMED,
        }:
            existing.scheduled_send_at = start_at
            existing.target_followup_at = start_at
            existing.finding_id = item.finding_id
            existing.source_finding_ids = [str(item.finding_id)]
            existing.safe_error = None
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
        target_followup_at=start_at,
        scheduled_send_at=start_at,
        message=item.message_preview
        or f"Hello {patient.first_name}. The clinic would like to follow up about tooth {item.tooth_fdi}.",
        language=plan.language,
        status=WhatsAppOutreachStatus.SCHEDULED,
        timing_reason=item.rationale,
        timing_policy_rule_id="CARE_SEQUENCE_MONTHLY",
        timing_policy_version="2.1",
        clinic_timezone=settings.timezone,
        include_image=settings.attach_tooth_image and item.image_required,
    )
    session.add(row)
    await session.flush()
    return row


async def reschedule_sequence_from_item(
    session: AsyncSession,
    *,
    plan: CarePlan,
    item: CarePlanItem,
    start_at: datetime,
) -> list[CarePlanItem]:
    """Persist a clinician-selected date and keep every later tooth one month apart."""
    settings = await settings_for_branch(session, plan.branch_id)
    normalized = start_at.replace(tzinfo=UTC) if start_at.tzinfo is None else start_at.astimezone(UTC)
    affected = (
        await session.scalars(
            select(CarePlanItem)
            .where(
                CarePlanItem.care_plan_id == plan.id,
                CarePlanItem.sequence_order >= item.sequence_order,
                CarePlanItem.status.notin_(["REJECTED", "COMPLETED", "SUPERSEDED_NEW_OPG"]),
            )
            .order_by(CarePlanItem.sequence_order.asc())
        )
    ).all()
    if not affected:
        return []

    patient = await session.get(Patient, plan.patient_id)
    for offset, row in enumerate(affected):
        scheduled_at = monthly_sequence_at(normalized, settings.timezone, offset)
        row.conversation_start_at = scheduled_at
        row.target_followup_at = scheduled_at

        followup = await session.scalar(
            select(FollowUp)
            .where(
                FollowUp.patient_id == plan.patient_id,
                FollowUp.reason.like(f"Teta2 Care · tooth {row.tooth_fdi}%"),
                FollowUp.status == "SCHEDULED",
            )
            .order_by(FollowUp.due_at.desc())
            .limit(1)
        )
        if followup:
            followup.due_at = scheduled_at

        if patient:
            outreach = await session.scalar(
                select(WhatsAppOutreach)
                .where(
                    WhatsAppOutreach.patient_id == patient.id,
                    WhatsAppOutreach.analysis_id == plan.analysis_id,
                    WhatsAppOutreach.tooth_fdi == row.tooth_fdi,
                    WhatsAppOutreach.status.in_(
                        [WhatsAppOutreachStatus.QUEUED, WhatsAppOutreachStatus.SCHEDULED]
                    ),
                )
                .order_by(WhatsAppOutreach.created_at.desc())
                .limit(1)
            )
            if outreach:
                outreach.target_followup_at = scheduled_at
                outreach.scheduled_send_at = scheduled_at
                outreach.status = WhatsAppOutreachStatus.SCHEDULED
                outreach.retry_at = None
                outreach.safe_error = None

    await session.flush()
    return list(affected)


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
            .where(
                CarePlanItem.care_plan_id == plan.id,
                CarePlanItem.status.in_(
                    ["FOLLOWUP_READY", "SCHEDULED_FUTURE_TOOTH", "WAITING_PREVIOUS_TOOTH"]
                ),
            )
            .order_by(CarePlanItem.sequence_order.asc())
        )
    ).all()
    if not items:
        return plan

    plan.status = "ACTIVE"
    plan.activated_at = datetime.now(UTC)
    await _conversation_for_plan(session, plan=plan, patient=patient)

    settings = await settings_for_branch(session, plan.branch_id)
    first_anchor = items[0].conversation_start_at or items[0].target_followup_at
    if first_anchor is None:
        first_anchor = _next_local_contact(settings.timezone, days=1)
    if any(item.status == "WAITING_PREVIOUS_TOOTH" for item in items):
        align_sequence_schedule(
            list(items),
            settings.timezone,
            first_start=first_anchor,
            force_rebase=True,
        )
    for order, item in enumerate(items, start=1):
        fallback = monthly_sequence_at(first_anchor, settings.timezone, order - 1)
        scheduled_at = item.conversation_start_at or item.target_followup_at or fallback
        item.sequence_order = order
        item.conversation_start_at = scheduled_at
        item.target_followup_at = scheduled_at
        item.status = "FOLLOWUP_READY" if order == 1 else "SCHEDULED_FUTURE_TOOTH"

        existing_followup = await session.scalar(
            select(FollowUp).where(
                FollowUp.patient_id == patient.id,
                FollowUp.reason.like(f"Teta2 Care · tooth {item.tooth_fdi}%"),
                FollowUp.status == "SCHEDULED",
            )
        )
        if existing_followup:
            existing_followup.due_at = scheduled_at
            existing_followup.priority = item.priority_level
            existing_followup.notes = (
                f"Sequential AI follow-up priority {item.sequence_order}; outreach date "
                f"{scheduled_at.isoformat()}. {item.rationale}"
            )
        else:
            session.add(
                FollowUp(
                    patient_id=patient.id,
                    doctor_id=plan.doctor_id,
                    branch_id=plan.branch_id,
                    reason=f"Teta2 Care · tooth {item.tooth_fdi} · {item.finding_type.replace('_', ' ')}",
                    due_at=scheduled_at,
                    status="SCHEDULED",
                    priority=item.priority_level,
                    notes=(
                        f"Sequential AI follow-up priority {item.sequence_order}; outreach date "
                        f"{scheduled_at.isoformat()}. {item.rationale}"
                    ),
                    created_by=plan.doctor_id or analysis.requested_by,
                )
            )

        await schedule_item_outreach(
            session,
            plan=plan,
            patient=patient,
            item=item,
            start_at=scheduled_at,
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
                    "scheduled_for": outreach.scheduled_send_at.isoformat(),
                },
            )
        )
    item.status = "CONTACTED"
    preserved_context = {
        key: value
        for key, value in dict(conversation.booking_context or {}).items()
        if key.startswith("last_visit_") or key == "sequence_mode"
    }
    preserved_context.update(
        {
            "sequence_mode": True,
            "stage": "WAITING_PATIENT_REPLY",
            "active_item_id": str(item.id),
            "active_tooth": item.tooth_fdi,
            "scheduled_outreach_at": outreach.scheduled_send_at.isoformat(),
        }
    )
    conversation.booking_context = preserved_context
    conversation.status = "ACTIVE"
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
    item.status = "COMPLETED"

    followup = await session.scalar(
        select(FollowUp)
        .where(
            FollowUp.patient_id == patient.id,
            FollowUp.reason.like(f"Teta2 Care · tooth {item.tooth_fdi}%"),
        )
        .order_by(FollowUp.due_at.desc())
        .limit(1)
    )
    if followup:
        followup.status = "COMPLETED"
        followup.completed_at = now

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
            f"Visit outcome for tooth {item.tooth_fdi}: {normalized.replace('_', ' ').title()}. "
            "This tooth is complete; the next tooth keeps its preassigned monthly outreach date."
        )

    next_item = await session.scalar(
        select(CarePlanItem)
        .where(
            CarePlanItem.care_plan_id == plan.id,
            CarePlanItem.sequence_order > item.sequence_order,
            CarePlanItem.status.in_(["SCHEDULED_FUTURE_TOOTH", "FOLLOWUP_READY"]),
        )
        .order_by(CarePlanItem.sequence_order.asc())
        .limit(1)
    )
    if next_item:
        if next_item.conversation_start_at is None:
            settings = await settings_for_branch(session, plan.branch_id)
            first_item = await session.scalar(
                select(CarePlanItem)
                .where(CarePlanItem.care_plan_id == plan.id, CarePlanItem.sequence_order == 1)
                .limit(1)
            )
            first_start = (
                first_item.conversation_start_at
                if first_item and first_item.conversation_start_at
                else _next_local_contact(settings.timezone, days=1)
            )
            next_item.conversation_start_at = _monthly_contact(
                first_start, settings.timezone, max(0, next_item.sequence_order - 1)
            )
            next_item.target_followup_at = next_item.conversation_start_at
        await schedule_item_outreach(
            session,
            plan=plan,
            patient=patient,
            item=next_item,
            start_at=next_item.conversation_start_at,
        )
        if conversation:
            conversation.summary = (
                f"Tooth {item.tooth_fdi} completed with visit outcome "
                f"{normalized.replace('_', ' ').title()}. AI remains inactive until tooth "
                f"{next_item.tooth_fdi} outreach is sent on its scheduled date "
                f"{next_item.conversation_start_at.isoformat()}."
            )
    else:
        remaining = await session.scalar(
            select(CarePlanItem.id)
            .where(
                CarePlanItem.care_plan_id == plan.id,
                CarePlanItem.status.in_(
                    ["SCHEDULED_FUTURE_TOOTH", "FOLLOWUP_READY", "CONTACTED", "BOOKED"]
                ),
            )
            .limit(1)
        )
        if remaining is None:
            plan.status = "COMPLETED"
            plan.completed_at = now
            if conversation:
                conversation.status = "CLOSED"
                conversation.summary = "All tooth-by-tooth follow-up steps are complete."

    await session.flush()
    return appointment
