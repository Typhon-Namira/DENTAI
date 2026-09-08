import uuid
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.groq import care_agent_reply
from app.care.language import language_for_phone, language_name
from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
    ClinicCareSettings,
)
from app.database.models import AIAnalysis, DentalFinding, FollowUp, Patient
from app.outreach.timing import eligible_finding
from app.outreach.service import timing_for_finding
from app.outreach.whatsapp_client import WhatsAppServiceClient

_RESTORATIVE_ONLY = {"FILLING", "CROWN", "ROOT_CANAL_TREATMENT", "IMPLANT", "BRIDGE"}


def _pathology(finding: DentalFinding) -> bool:
    return (
        bool(finding.tooth_code)
        and finding.finding_type.upper() not in _RESTORATIVE_ONLY
        and eligible_finding(finding.tooth_code, finding.confidence)
    )


def _message(language: str, patient_name: str, tooth: str, finding_type: str) -> str:
    label = finding_type.replace("_", " ").lower()
    if language == "hy":
        return f"Բարև {patient_name}։ Ձեր OPG-ի կլինիկայի վերանայումից հետո ատամ {tooth}-ի շրջանում նշվել է հնարավոր {label}։ Խորհուրդ է տրվում ստուգում ատամնաբույժի մոտ։ Կարող եմ օգնել հարմար ժամ ընտրել։"
    if language == "ru":
        return f"Здравствуйте, {patient_name}. После проверки вашей OPG в клинике в области зуба {tooth} отмечена возможная находка: {label}. Рекомендуется осмотр стоматолога. Я могу помочь выбрать удобное время."
    if language == "fa":
        return f"سلام {patient_name}. پس از بررسی OPG شما توسط کلینیک، در ناحیه دندان {tooth} یک یافته احتمالی ({label}) ثبت شده است. بهتر است توسط دندان‌پزشک بررسی شود. می‌توانم برای انتخاب زمان مناسب چکاپ کمک کنم."
    if language == "tr":
        return f"Merhaba {patient_name}. Kliniğin OPG incelemesinden sonra {tooth} numaralı diş bölgesinde olası bir {label} bulgusu kaydedildi. Diş hekimi kontrolü önerilir. Uygun bir kontrol saati seçmenize yardımcı olabilirim."
    return f"Hello {patient_name}. After your clinic reviewed the OPG, a possible {label} finding was noted around tooth {tooth}. A dentist check-up is recommended. I can help you choose a suitable appointment time."


async def settings_for_branch(session: AsyncSession, branch_id: uuid.UUID) -> ClinicCareSettings:
    row = await session.scalar(select(ClinicCareSettings).where(ClinicCareSettings.branch_id == branch_id))
    if row:
        return row
    row = ClinicCareSettings(
        branch_id=branch_id,
        working_days=[0, 1, 2, 3, 4, 5],
        preferred_times=[],
        blocked_windows=[],
    )
    session.add(row)
    await session.flush()
    return row


async def ensure_care_plan(session: AsyncSession, analysis: AIAnalysis) -> CarePlan | None:
    existing = await session.scalar(select(CarePlan).where(CarePlan.analysis_id == analysis.id))
    if existing:
        return existing
    patient = await session.get(Patient, analysis.patient_id)
    if not patient:
        return None
    findings = (await session.scalars(select(DentalFinding).where(DentalFinding.analysis_id == analysis.id))).all()
    candidates = [finding for finding in findings if _pathology(finding)]
    if not candidates:
        return None
    language = language_for_phone(patient.whatsapp_phone or patient.phone, "en")
    plan = CarePlan(
        patient_id=patient.id,
        analysis_id=analysis.id,
        branch_id=patient.branch_id,
        doctor_id=analysis.requested_by,
        status="READY_FOR_REVIEW",
        language=language,
        summary=f"{len(candidates)} possible finding(s) prepared for clinician review.",
    )
    session.add(plan)
    await session.flush()
    for finding in candidates:
        timing = timing_for_finding(analysis, finding)
        session.add(CarePlanItem(
            care_plan_id=plan.id,
            finding_id=finding.id,
            tooth_fdi=str(finding.tooth_code),
            finding_type=finding.finding_type,
            confidence=finding.confidence,
            recommended_window=timing.recommended_window,
            target_followup_at=timing.target_followup_at,
            status="AWAITING_REVIEW",
            rationale=timing.timing_reason,
            message_preview=_message(language, patient.first_name, str(finding.tooth_code), finding.finding_type),
            appointment_required=True,
            image_required=True,
        ))
    await session.flush()
    return plan


async def activate_reviewed_plan(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    analysis: AIAnalysis,
) -> CarePlan | None:
    plan = await ensure_care_plan(session, analysis)
    if not plan:
        return None
    patient = await session.get(Patient, plan.patient_id)
    if not patient:
        return plan
    settings = await settings_for_branch(session, plan.branch_id)
    items = (await session.scalars(select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id))).all()
    findings = {
        row.id: row for row in (
            await session.scalars(select(DentalFinding).where(DentalFinding.analysis_id == analysis.id))
        ).all()
    }
    confirmed = [item for item in items if findings.get(item.finding_id) and findings[item.finding_id].review_status == "CONFIRMED"]
    rejected = [item for item in items if findings.get(item.finding_id) and findings[item.finding_id].review_status == "REJECTED"]
    for item in rejected:
        item.status = "REJECTED"
    if not confirmed:
        plan.status = "REVIEWED_NO_ACTION" if rejected else "READY_FOR_REVIEW"
        return plan
    plan.status = "ACTIVE"
    plan.activated_at = datetime.now(UTC)
    for item in confirmed:
        item.status = "FOLLOWUP_READY"
        existing_followup = await session.scalar(
            select(FollowUp).where(FollowUp.patient_id == patient.id, FollowUp.reason.like(f"Teta2 Care · tooth {item.tooth_fdi}%"))
        )
        if not existing_followup:
            session.add(FollowUp(
                patient_id=patient.id,
                doctor_id=plan.doctor_id,
                branch_id=plan.branch_id,
                reason=f"Teta2 Care · tooth {item.tooth_fdi} · {item.finding_type.replace('_', ' ')}",
                due_at=item.target_followup_at,
                status="SCHEDULED",
                priority="HIGH" if (item.confidence or 0) >= 0.8 else "NORMAL",
                notes=f"AI-assisted possible finding confirmed by clinician. {item.rationale}",
                created_by=plan.doctor_id or analysis.requested_by,
            ))
    await session.flush()
    if settings.auto_outreach_after_review and (patient.whatsapp_phone or patient.phone):
        await start_or_continue_outreach(
            session,
            clinic_id=clinic_id,
            clinic_name=clinic_name,
            patient=patient,
            plan=plan,
            items=confirmed,
        )
    return plan


async def available_slots(
    session: AsyncSession,
    *,
    branch_id: uuid.UUID,
    settings: ClinicCareSettings,
    doctor_id: uuid.UUID | None = None,
    now: datetime | None = None,
    limit: int = 12,
) -> list[datetime]:
    tz = ZoneInfo(settings.timezone)
    local_now = (now or datetime.now(UTC)).astimezone(tz)
    earliest = local_now + timedelta(minutes=settings.min_booking_notice_minutes)
    end_date = local_now.date() + timedelta(days=settings.booking_horizon_days)
    occupied = (
        await session.scalars(
            select(CareAppointment).where(
                CareAppointment.branch_id == branch_id,
                CareAppointment.status.in_(["PROPOSED", "CONFIRMED", "RESCHEDULE_PROPOSED"]),
                CareAppointment.starts_at >= local_now.astimezone(UTC),
                CareAppointment.starts_at <= datetime.combine(end_date, time.max, tzinfo=tz).astimezone(UTC),
            )
        )
    ).all()
    busy = [(x.starts_at, x.ends_at) for x in occupied if not doctor_id or x.doctor_id in (None, doctor_id)]
    slots: list[datetime] = []
    day = local_now.date()
    while day <= end_date and len(slots) < limit:
        if day.weekday() in set(settings.working_days or []):
            h1, m1 = map(int, settings.day_start.split(":"))
            h2, m2 = map(int, settings.day_end.split(":"))
            cursor = datetime.combine(day, time(h1, m1), tzinfo=tz)
            close = datetime.combine(day, time(h2, m2), tzinfo=tz)
            while cursor + timedelta(minutes=settings.appointment_minutes) <= close and len(slots) < limit:
                end = cursor + timedelta(minutes=settings.appointment_minutes)
                utc_start, utc_end = cursor.astimezone(UTC), end.astimezone(UTC)
                if cursor >= earliest and not any(utc_start < b_end and utc_end > b_start for b_start, b_end in busy):
                    slots.append(cursor)
                cursor += timedelta(minutes=settings.slot_interval_minutes)
        day += timedelta(days=1)
    return slots


async def _conversation(
    session: AsyncSession, *, patient: Patient, plan: CarePlan, phone: str
) -> CareConversation:
    existing = await session.scalar(
        select(CareConversation).where(
            CareConversation.patient_id == patient.id,
            CareConversation.status == "ACTIVE",
        ).order_by(CareConversation.created_at.desc())
    )
    if existing:
        return existing
    row = CareConversation(
        patient_id=patient.id,
        care_plan_id=plan.id,
        branch_id=patient.branch_id,
        whatsapp_phone=phone,
        language=language_for_phone(phone, plan.language),
        status="ACTIVE",
        booking_context={},
    )
    session.add(row)
    await session.flush()
    return row


async def start_or_continue_outreach(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    patient: Patient,
    plan: CarePlan,
    items: list[CarePlanItem],
) -> CareConversation | None:
    phone = patient.whatsapp_phone or patient.phone
    if not phone or not items:
        return None
    conversation = await _conversation(session, patient=patient, plan=plan, phone=phone)
    prior = await session.scalar(
        select(CareConversationMessage.id).where(
            CareConversationMessage.conversation_id == conversation.id,
            CareConversationMessage.direction == "OUT",
        ).limit(1)
    )
    if prior:
        return conversation
    first = items[0]
    message = _message(conversation.language, patient.first_name, first.tooth_fdi, first.finding_type)
    settings = await settings_for_branch(session, patient.branch_id)
    slots = await available_slots(session, branch_id=patient.branch_id, settings=settings, doctor_id=plan.doctor_id, limit=4)
    if slots:
        slot_lines = "\n".join(f"• {slot.strftime('%Y-%m-%d %H:%M')}" for slot in slots)
        message += ("\n\n" + ("Առաջարկվող ժամեր:" if conversation.language == "hy" else "Предлагаемые варианты:" if conversation.language == "ru" else "Available options:") + "\n" + slot_lines)
    result = await WhatsAppServiceClient().send_message(clinic_id, phone, message)
    session.add(CareConversationMessage(
        conversation_id=conversation.id,
        care_plan_item_id=first.id,
        direction="OUT",
        body=message,
        language=conversation.language,
        status="SENT",
        provider_message_id=result.get("message_id"),
        message_metadata={"clinic": clinic_name, "kind": "initial_followup"},
    ))
    conversation.last_message_at = datetime.now(UTC)
    for item in items:
        item.status = "CONTACTED"
    return conversation


async def process_inbound_message(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    phone: str,
    text: str,
    provider_message_id: str | None,
) -> dict:
    patient = await session.scalar(
        select(Patient).where((Patient.whatsapp_phone == phone) | (Patient.phone == phone)).limit(1)
    )
    if not patient:
        return {"handled": False, "reason": "patient_not_found"}
    conversation = await session.scalar(
        select(CareConversation).where(
            CareConversation.patient_id == patient.id,
            CareConversation.status == "ACTIVE",
        ).order_by(CareConversation.created_at.desc())
    )
    if not conversation:
        return {"handled": False, "reason": "conversation_not_found"}
    session.add(CareConversationMessage(
        conversation_id=conversation.id,
        direction="IN",
        body=text,
        language=conversation.language,
        status="RECEIVED",
        provider_message_id=provider_message_id,
        message_metadata={},
    ))
    await session.flush()
    plan = await session.get(CarePlan, conversation.care_plan_id) if conversation.care_plan_id else None
    items = [] if not plan else (await session.scalars(select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id, CarePlanItem.status != "REJECTED"))).all()
    history_rows = (await session.scalars(
        select(CareConversationMessage).where(CareConversationMessage.conversation_id == conversation.id).order_by(CareConversationMessage.created_at.asc())
    )).all()
    settings = await settings_for_branch(session, patient.branch_id)
    slots = await available_slots(session, branch_id=patient.branch_id, settings=settings, doctor_id=plan.doctor_id if plan else None, limit=8)
    slot_strings = [slot.isoformat() for slot in slots]
    reply = await care_agent_reply(
        language=conversation.language,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        clinic_name=clinic_name,
        care_items=[{"tooth": x.tooth_fdi, "finding": x.finding_type, "window": x.recommended_window} for x in items],
        history=[{"role": "assistant" if x.direction == "OUT" else "user", "content": x.body} for x in history_rows],
        available_slots=slot_strings,
        inbound_message=text,
        booking_instructions=settings.booking_instructions,
    )
    selected = None
    if reply.selected_slot and reply.selected_slot in slot_strings:
        selected = datetime.fromisoformat(reply.selected_slot)
        duration = timedelta(minutes=settings.appointment_minutes)
        existing = await session.scalar(select(CareAppointment).where(CareAppointment.conversation_id == conversation.id, CareAppointment.status == "CONFIRMED").order_by(CareAppointment.starts_at.desc()))
        if existing and reply.wants_reschedule:
            existing.status = "RESCHEDULED"
            existing.reschedule_count += 1
        first_item = items[0] if items else None
        appointment = CareAppointment(
            patient_id=patient.id,
            branch_id=patient.branch_id,
            doctor_id=plan.doctor_id if plan else None,
            conversation_id=conversation.id,
            care_plan_item_id=first_item.id if first_item else None,
            starts_at=selected.astimezone(UTC),
            ends_at=(selected + duration).astimezone(UTC),
            timezone=settings.timezone,
            status="CONFIRMED",
            source="AI",
            tooth_fdi=first_item.tooth_fdi if first_item else None,
            finding_type=first_item.finding_type if first_item else None,
            reason=f"Teta2 Care check-up{f' · tooth {first_item.tooth_fdi}' if first_item else ''}",
            patient_confirmed_at=datetime.now(UTC),
        )
        session.add(appointment)
        for item in items:
            item.status = "BOOKED"
    sent = await WhatsAppServiceClient().send_message(clinic_id, phone, reply.reply)
    session.add(CareConversationMessage(
        conversation_id=conversation.id,
        direction="OUT",
        body=reply.reply,
        language=conversation.language,
        status="SENT",
        provider_message_id=sent.get("message_id"),
        message_metadata={"intent": reply.intent, "needs_human": reply.needs_human, "selected_slot": reply.selected_slot},
    ))
    conversation.last_message_at = datetime.now(UTC)
    conversation.summary = f"Last intent: {reply.intent}. Language: {language_name(conversation.language)}."
    return {"handled": True, "intent": reply.intent, "booked": bool(selected), "needs_human": reply.needs_human}
