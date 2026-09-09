import uuid
from datetime import UTC, datetime, time, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from PIL import Image
from sqlalchemy import select
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
from app.database.models import AIAnalysis, DentalFinding, FollowUp, Patient, XRay
from app.outreach.service import timing_for_finding
from app.outreach.timing import eligible_finding
from app.outreach.whatsapp_client import WhatsAppServiceClient, normalize_phone
from app.storage.providers import storage_provider

_RESTORATIVE_ONLY = {"FILLING", "CROWN", "ROOT_CANAL_TREATMENT", "IMPLANT", "BRIDGE"}
_ACTIVE_APPOINTMENT_STATES = ["PROPOSED", "CONFIRMED", "RESCHEDULE_PROPOSED"]


def _pathology(finding: DentalFinding) -> bool:
    return (
        bool(finding.tooth_code)
        and finding.finding_type.upper() not in _RESTORATIVE_ONLY
        and eligible_finding(finding.tooth_code, finding.confidence)
    )


def _safe_phone(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return normalize_phone(value)
    except ValueError:
        return None


def _message(language: str, patient_name: str, tooth: str, finding_type: str) -> str:
    label = finding_type.replace("_", " ").lower()
    if language == "hy":
        return f"Բարև {patient_name}։ Ձեր OPG-ի կլինիկական վերանայումից հետո ատամ {tooth}-ի շրջանում նշվել է հնարավոր {label}։ Խորհուրդ է տրվում ստուգում ատամնաբույժի մոտ։"
    if language == "ru":
        return f"Здравствуйте, {patient_name}. После клинической проверки вашей OPG в области зуба {tooth} отмечена возможная находка: {label}. Рекомендуется осмотр стоматолога."
    if language == "fa":
        return f"سلام {patient_name}. پس از بررسی بالینی OPG شما، در ناحیه دندان {tooth} یک یافته احتمالی ({label}) ثبت شده است. بهتر است توسط دندان‌پزشک بررسی شود."
    if language == "tr":
        return f"Merhaba {patient_name}. OPG'nizin klinik incelemesinden sonra {tooth} numaralı diş bölgesinde olası bir {label} bulgusu kaydedildi. Diş hekimi kontrolü önerilir."
    return f"Hello {patient_name}. After clinical review of your OPG, a possible {label} finding was noted around tooth {tooth}. A dentist check-up is recommended."


def _slot_heading(language: str) -> str:
    return {
        "hy": "Հարմար ժամ ընտրելու համար կարող եք պատասխանել այս տարբերակներից մեկով:",
        "ru": "Чтобы выбрать удобное время, ответьте одним из этих вариантов:",
        "fa": "برای انتخاب زمان مناسب، می‌توانید یکی از این زمان‌ها را پاسخ دهید:",
        "tr": "Uygun bir saat seçmek için bu seçeneklerden birini yanıtlayabilirsiniz:",
    }.get(language, "Reply with one of these available options and I can book it for you:")


def _time_range(item: object) -> tuple[str, str] | None:
    if isinstance(item, str) and "-" in item:
        start, end = item.split("-", 1)
        return start.strip(), end.strip()
    if isinstance(item, dict):
        start, end = item.get("start"), item.get("end")
        if isinstance(start, str) and isinstance(end, str):
            return start, end
    return None


def _is_blocked(local_start: datetime, local_end: datetime, settings: ClinicCareSettings) -> bool:
    for item in settings.blocked_windows or []:
        if not isinstance(item, dict):
            continue
        start_raw, end_raw = item.get("start"), item.get("end")
        try:
            if isinstance(start_raw, str) and isinstance(end_raw, str) and "T" in start_raw:
                block_start = datetime.fromisoformat(start_raw)
                block_end = datetime.fromisoformat(end_raw)
                if block_start.tzinfo is None:
                    block_start = block_start.replace(tzinfo=local_start.tzinfo)
                if block_end.tzinfo is None:
                    block_end = block_end.replace(tzinfo=local_start.tzinfo)
                if local_start < block_end and local_end > block_start:
                    return True
            elif item.get("day") == local_start.weekday() and isinstance(start_raw, str) and isinstance(end_raw, str):
                h1, m1 = map(int, start_raw.split(":"))
                h2, m2 = map(int, end_raw.split(":"))
                block_start = datetime.combine(local_start.date(), time(h1, m1), tzinfo=local_start.tzinfo)
                block_end = datetime.combine(local_start.date(), time(h2, m2), tzinfo=local_start.tzinfo)
                if local_start < block_end and local_end > block_start:
                    return True
        except (ValueError, TypeError):
            continue
    return False


def _preference_score(slot: datetime, settings: ClinicCareSettings) -> int:
    if not settings.preferred_times:
        return 1
    current = slot.strftime("%H:%M")
    for item in settings.preferred_times:
        pair = _time_range(item)
        if pair and pair[0] <= current < pair[1]:
            return 0
    return 1


def _crop_box(raw: object, width: int, height: int) -> tuple[int, int, int, int] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        values = [float(v) for v in raw]
    except (TypeError, ValueError):
        return None
    if all(0 <= value <= 1.0 for value in values):
        x1, y1, x2, y2 = values[0] * width, values[1] * height, values[2] * width, values[3] * height
    else:
        x1, y1, x2, y2 = values
    if x2 <= x1 or y2 <= y1:
        return None
    pad_x = max(10.0, (x2 - x1) * 0.28)
    pad_y = max(10.0, (y2 - y1) * 0.28)
    return (
        max(0, int(x1 - pad_x)),
        max(0, int(y1 - pad_y)),
        min(width, int(x2 + pad_x)),
        min(height, int(y2 + pad_y)),
    )


async def _finding_crop(session: AsyncSession, plan: CarePlan, item: CarePlanItem) -> bytes | None:
    finding = await session.get(DentalFinding, item.finding_id)
    analysis = await session.get(AIAnalysis, plan.analysis_id)
    if not finding or not analysis or not isinstance(finding.provenance, dict):
        return None
    raw_box = finding.provenance.get("bounding_box")
    if raw_box is None:
        return None
    xray = await session.get(XRay, analysis.xray_id)
    if not xray or not xray.mime_type.startswith("image/"):
        return None
    try:
        raw = await storage_provider().read(xray.storage_key)
        with Image.open(BytesIO(raw)) as image:
            image = image.convert("RGB")
            box = _crop_box(raw_box, image.width, image.height)
            if not box:
                return None
            crop = image.crop(box)
            output = BytesIO()
            crop.save(output, format="JPEG", quality=90, optimize=True)
            return output.getvalue()
    except Exception:
        return None


async def settings_for_branch(session: AsyncSession, branch_id: uuid.UUID) -> ClinicCareSettings:
    row = await session.scalar(select(ClinicCareSettings).where(ClinicCareSettings.branch_id == branch_id))
    if row:
        return row
    row = ClinicCareSettings(branch_id=branch_id, working_days=[0, 1, 2, 3, 4, 5], preferred_times=[], blocked_windows=[])
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
    settings = await settings_for_branch(session, patient.branch_id)
    if not settings.auto_followup_enabled:
        return None
    findings = (await session.scalars(select(DentalFinding).where(DentalFinding.analysis_id == analysis.id))).all()
    candidates = [finding for finding in findings if _pathology(finding)]
    if not candidates:
        return None
    language = language_for_phone(patient.whatsapp_phone or patient.phone, settings.default_language)
    plan = CarePlan(patient_id=patient.id, analysis_id=analysis.id, branch_id=patient.branch_id, doctor_id=analysis.requested_by, status="READY_FOR_REVIEW", language=language, summary=f"{len(candidates)} possible finding(s) prepared for clinician review.")
    session.add(plan)
    await session.flush()
    for finding in candidates:
        timing = timing_for_finding(analysis, finding)
        session.add(CarePlanItem(care_plan_id=plan.id, finding_id=finding.id, tooth_fdi=str(finding.tooth_code), finding_type=finding.finding_type, confidence=finding.confidence, recommended_window=timing.recommended_window, target_followup_at=timing.target_followup_at, status="AWAITING_REVIEW", rationale=timing.timing_reason, message_preview=_message(language, patient.first_name, str(finding.tooth_code), finding.finding_type), appointment_required=True, image_required=True))
    await session.flush()
    return plan


async def activate_reviewed_plan(session: AsyncSession, *, clinic_id: uuid.UUID, clinic_name: str, analysis: AIAnalysis) -> CarePlan | None:
    plan = await ensure_care_plan(session, analysis)
    if not plan:
        return None
    patient = await session.get(Patient, plan.patient_id)
    if not patient:
        return plan
    settings = await settings_for_branch(session, plan.branch_id)
    items = (await session.scalars(select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id))).all()
    findings = {row.id: row for row in (await session.scalars(select(DentalFinding).where(DentalFinding.analysis_id == analysis.id))).all()}
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
        existing_followup = await session.scalar(select(FollowUp).where(FollowUp.patient_id == patient.id, FollowUp.reason.like(f"Teta2 Care · tooth {item.tooth_fdi}%")))
        if not existing_followup:
            session.add(FollowUp(patient_id=patient.id, doctor_id=plan.doctor_id, branch_id=plan.branch_id, reason=f"Teta2 Care · tooth {item.tooth_fdi} · {item.finding_type.replace('_', ' ')}", due_at=item.target_followup_at, status="SCHEDULED", priority="HIGH" if (item.confidence or 0) >= 0.8 else "NORMAL", notes=f"AI-assisted possible finding confirmed by clinician. {item.rationale}", created_by=plan.doctor_id or analysis.requested_by))
    await session.flush()
    if settings.auto_outreach_after_review and (patient.whatsapp_phone or patient.phone):
        await start_or_continue_outreach(session, clinic_id=clinic_id, clinic_name=clinic_name, patient=patient, plan=plan, items=confirmed)
    return plan


async def available_slots(session: AsyncSession, *, branch_id: uuid.UUID, settings: ClinicCareSettings, doctor_id: uuid.UUID | None = None, now: datetime | None = None, limit: int = 12) -> list[datetime]:
    tz = ZoneInfo(settings.timezone)
    local_now = (now or datetime.now(UTC)).astimezone(tz)
    earliest = local_now + timedelta(minutes=settings.min_booking_notice_minutes)
    end_date = local_now.date() + timedelta(days=settings.booking_horizon_days)
    occupied = (await session.scalars(select(CareAppointment).where(CareAppointment.branch_id == branch_id, CareAppointment.status.in_(_ACTIVE_APPOINTMENT_STATES), CareAppointment.starts_at >= local_now.astimezone(UTC), CareAppointment.starts_at <= datetime.combine(end_date, time.max, tzinfo=tz).astimezone(UTC)))).all()
    busy = [(x.starts_at, x.ends_at) for x in occupied if not doctor_id or x.doctor_id in (None, doctor_id)]
    candidates: list[datetime] = []
    day = local_now.date()
    buffer = timedelta(minutes=settings.buffer_minutes)
    while day <= end_date:
        if day.weekday() in set(settings.working_days or []):
            h1, m1 = map(int, settings.day_start.split(":")); h2, m2 = map(int, settings.day_end.split(":"))
            cursor = datetime.combine(day, time(h1, m1), tzinfo=tz); close = datetime.combine(day, time(h2, m2), tzinfo=tz)
            while cursor + timedelta(minutes=settings.appointment_minutes) <= close:
                end = cursor + timedelta(minutes=settings.appointment_minutes)
                utc_start, utc_end = cursor.astimezone(UTC), end.astimezone(UTC)
                candidate_start, candidate_end = utc_start - buffer, utc_end + buffer
                collision = any(candidate_start < b_end + buffer and candidate_end > b_start - buffer for b_start, b_end in busy)
                if cursor >= earliest and not collision and not _is_blocked(cursor, end, settings):
                    candidates.append(cursor)
                cursor += timedelta(minutes=settings.slot_interval_minutes)
        day += timedelta(days=1)
    candidates.sort(key=lambda slot: (_preference_score(slot, settings), slot))
    return candidates[:limit]


async def _conversation(session: AsyncSession, *, patient: Patient, plan: CarePlan, phone: str) -> CareConversation:
    existing = await session.scalar(select(CareConversation).where(CareConversation.patient_id == patient.id, CareConversation.status == "ACTIVE").order_by(CareConversation.created_at.desc()))
    if existing:
        return existing
    normalized = _safe_phone(phone) or phone
    row = CareConversation(patient_id=patient.id, care_plan_id=plan.id, branch_id=patient.branch_id, whatsapp_phone=normalized, language=language_for_phone(normalized, plan.language), status="ACTIVE", booking_context={})
    session.add(row)
    await session.flush()
    return row


async def start_or_continue_outreach(session: AsyncSession, *, clinic_id: uuid.UUID, clinic_name: str, patient: Patient, plan: CarePlan, items: list[CarePlanItem]) -> CareConversation | None:
    phone = _safe_phone(patient.whatsapp_phone or patient.phone)
    if not phone or not items:
        return None
    conversation = await _conversation(session, patient=patient, plan=plan, phone=phone)
    prior_item_ids = set((await session.scalars(select(CareConversationMessage.care_plan_item_id).where(CareConversationMessage.conversation_id == conversation.id, CareConversationMessage.direction == "OUT", CareConversationMessage.care_plan_item_id.is_not(None)))).all())
    pending = [item for item in items if item.id not in prior_item_ids]
    if not pending:
        return conversation
    settings = await settings_for_branch(session, patient.branch_id)
    slots = await available_slots(session, branch_id=patient.branch_id, settings=settings, doctor_id=plan.doctor_id, limit=4)
    client = WhatsAppServiceClient()
    for index, item in enumerate(pending):
        message = _message(conversation.language, patient.first_name, item.tooth_fdi, item.finding_type)
        if index == len(pending) - 1 and slots:
            slot_lines = "\n".join(f"• {slot.strftime('%Y-%m-%d %H:%M')}" for slot in slots)
            message += f"\n\n{_slot_heading(conversation.language)}\n{slot_lines}"
        crop = await _finding_crop(session, plan, item) if settings.attach_tooth_image and item.image_required else None
        result = await (client.send_image_message(clinic_id, phone, message, crop) if crop else client.send_message(clinic_id, phone, message))
        session.add(CareConversationMessage(conversation_id=conversation.id, care_plan_item_id=item.id, direction="OUT", body=message, language=conversation.language, status="SENT", provider_message_id=result.get("message_id"), message_metadata={"clinic": clinic_name, "kind": "finding_followup", "tooth_fdi": item.tooth_fdi, "image_attached": bool(crop)}))
        item.status = "CONTACTED"
    conversation.last_message_at = datetime.now(UTC)
    conversation.summary = f"{len(pending)} clinician-confirmed tooth finding(s) sent. Awaiting patient response."
    return conversation


async def _find_patient_by_phone(session: AsyncSession, phone: str) -> Patient | None:
    normalized = _safe_phone(phone)
    if not normalized:
        return None
    exact = await session.scalar(select(Patient).where((Patient.whatsapp_phone == normalized) | (Patient.phone == normalized)).limit(1))
    if exact:
        return exact
    rows = (await session.scalars(select(Patient).where((Patient.whatsapp_phone.is_not(None)) | (Patient.phone.is_not(None))))).all()
    for patient in rows:
        if normalized in {_safe_phone(patient.whatsapp_phone), _safe_phone(patient.phone)}:
            return patient
    return None


async def process_inbound_message(session: AsyncSession, *, clinic_id: uuid.UUID, clinic_name: str, phone: str, text: str, provider_message_id: str | None) -> dict:
    normalized_phone = _safe_phone(phone)
    patient = await _find_patient_by_phone(session, phone)
    if not patient or not normalized_phone:
        return {"handled": False, "reason": "patient_not_found"}
    conversation = await session.scalar(select(CareConversation).where(CareConversation.patient_id == patient.id, CareConversation.status == "ACTIVE").order_by(CareConversation.created_at.desc()))
    if not conversation:
        return {"handled": False, "reason": "conversation_not_found"}
    session.add(CareConversationMessage(conversation_id=conversation.id, direction="IN", body=text, language=conversation.language, status="RECEIVED", provider_message_id=provider_message_id, message_metadata={}))
    await session.flush()
    plan = await session.get(CarePlan, conversation.care_plan_id) if conversation.care_plan_id else None
    items = [] if not plan else (await session.scalars(select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id, CarePlanItem.status != "REJECTED"))).all()
    history_rows = (await session.scalars(select(CareConversationMessage).where(CareConversationMessage.conversation_id == conversation.id).order_by(CareConversationMessage.created_at.asc()))).all()
    settings = await settings_for_branch(session, patient.branch_id)
    doctor_id = plan.doctor_id if plan else None
    slots = await available_slots(session, branch_id=patient.branch_id, settings=settings, doctor_id=doctor_id, limit=8)
    slot_strings = [slot.isoformat() for slot in slots]
    reply = await care_agent_reply(language=conversation.language, patient_name=f"{patient.first_name} {patient.last_name}".strip(), clinic_name=clinic_name, care_items=[{"tooth": x.tooth_fdi, "finding": x.finding_type, "window": x.recommended_window} for x in items], history=[{"role": "assistant" if x.direction == "OUT" else "user", "content": x.body} for x in history_rows], available_slots=slot_strings, inbound_message=text, booking_instructions=settings.booking_instructions)
    selected = None
    if reply.selected_slot and reply.selected_slot in slot_strings:
        fresh_slots = await available_slots(session, branch_id=patient.branch_id, settings=settings, doctor_id=doctor_id, limit=64)
        fresh_strings = {slot.isoformat() for slot in fresh_slots}
        if reply.selected_slot in fresh_strings:
            selected = datetime.fromisoformat(reply.selected_slot)
            duration = timedelta(minutes=settings.appointment_minutes)
            existing = await session.scalar(select(CareAppointment).where(CareAppointment.conversation_id == conversation.id, CareAppointment.status == "CONFIRMED").order_by(CareAppointment.starts_at.desc()))
            if existing and reply.wants_reschedule:
                existing.status = "RESCHEDULED"; existing.reschedule_count += 1
            first_item = items[0] if items else None
            appointment = CareAppointment(patient_id=patient.id, branch_id=patient.branch_id, doctor_id=doctor_id, conversation_id=conversation.id, care_plan_item_id=first_item.id if first_item else None, starts_at=selected.astimezone(UTC), ends_at=(selected + duration).astimezone(UTC), timezone=settings.timezone, status="CONFIRMED", source="AI", tooth_fdi=first_item.tooth_fdi if first_item else None, finding_type=first_item.finding_type if first_item else None, reason=f"Teta2 Care check-up{f' · tooth {first_item.tooth_fdi}' if first_item else ''}", patient_confirmed_at=datetime.now(UTC))
            session.add(appointment)
            for item in items:
                item.status = "BOOKED"
    sent = await WhatsAppServiceClient().send_message(clinic_id, normalized_phone, reply.reply)
    session.add(CareConversationMessage(conversation_id=conversation.id, direction="OUT", body=reply.reply, language=conversation.language, status="SENT", provider_message_id=sent.get("message_id"), message_metadata={"intent": reply.intent, "needs_human": reply.needs_human, "selected_slot": reply.selected_slot, "booked": bool(selected)}))
    conversation.last_message_at = datetime.now(UTC)
    conversation.summary = f"Last intent: {reply.intent}. Language: {language_name(conversation.language)}. {'Appointment confirmed.' if selected else 'Conversation active.'}"
    return {"handled": True, "intent": reply.intent, "booked": bool(selected), "needs_human": reply.needs_human}
