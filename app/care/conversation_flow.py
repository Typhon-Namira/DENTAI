import re
import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.groq import CareAgentReply, care_agent_reply
from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
)
from app.care.service import available_slots, settings_for_branch
from app.database.models import Patient
from app.outreach.whatsapp_client import WhatsAppServiceClient, normalize_phone

WAITING_PATIENT_REPLY = "WAITING_PATIENT_REPLY"
WAITING_PATIENT_SLOT_CONFIRMATION = "WAITING_PATIENT_SLOT_CONFIRMATION"
WAITING_DOCTOR_APPROVAL = "WAITING_DOCTOR_APPROVAL"
APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED"

_ACTIVE_ITEM_STATES = {
    "FOLLOWUP_READY",
    "CONTACTED",
    "APPOINTMENT_PENDING_APPROVAL",
    "BOOKED",
}

_BOOKING_PATTERNS = (
    r"\b(book|booking|appointment|schedule|reserve|reservation)\b",
    r"\b(i want|i'd like|i would like|can i|could i)\b.*\b(come|visit|appointment|book)\b",
    r"وقت\s*(می.?خوام|میخواهم|بگیرم|رزرو)",
    r"رزرو\s*(وقت|نوبت)?",
    r"نوبت\s*(می.?خوام|بگیرم|رزرو)",
    r"می.?خوام\s*(بیام|مراجعه کنم)",
    r"\b(запис|прием|приём|время к врачу)\w*\b",
    r"\b(randevu|rezervasyon|rezerv|muayene)\w*\b",
    r"(ժամադր|գրանցվ|այցել|ժամ վերցն)\w*",
)

_CANCEL_BOOKING_PATTERNS = (
    r"\b(don't|do not|dont|no longer|cancel)\b.*\b(appointment|book|booking|visit)\b",
    r"\b(i don't want|i do not want|not interested)\b",
    r"وقت\s*(نمی.?خوام|نمیخواهم)",
    r"نوبت\s*(نمی.?خوام|نمیخواهم)",
    r"نمی.?خوام\s*(بیام|مراجعه کنم)",
    r"\b(не хочу|отменить|не нужна запись)\b",
    r"\b(randevu istemiyorum|iptal|gelmek istemiyorum)\b",
    r"(չեմ ուզում|չեղարկել).*(ժամադր|այցել)",
)

_RESCHEDULE_PATTERNS = (
    r"\b(another|different|other|change|reschedule|later|earlier)\b.*\b(time|slot|day|appointment)?\b",
    r"\bthat (time|slot) (doesn't|does not|won't|will not) work\b",
    r"\b(can't|cannot|cant) make (it|that time)\b",
    r"(وقت|زمان|ساعت|روز)\s*(دیگه|دیگری|دیگه‌ای|دیگری‌ای)",
    r"(این|اون)\s*(وقت|زمان|ساعت).*مناسب\s*نیست",
    r"(عوض|تغییر)\s*(کن|بدین|بده|زمان|وقت)",
    r"\b(другое|другой|перенести|поменять|не подходит)\b",
    r"\b(başka|değiştir|ertele|uygun değil)\b",
    r"(այլ|փոխել|հարմար չէ).*(ժամ|օր)?",
)

_CONFIRM_WORDS = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "ok",
    "okay",
    "works",
    "perfect",
    "fine",
    "confirm",
    "confirmed",
    "بله",
    "آره",
    "اره",
    "باشه",
    "اوکی",
    "خوبه",
    "مناسبه",
    "موافقم",
    "حتما",
    "да",
    "ок",
    "хорошо",
    "подходит",
    "согласен",
    "согласна",
    "evet",
    "tamam",
    "olur",
    "uygun",
    "այո",
    "հա",
    "լավ",
    "հարմար է",
}

_NEGATIVE_SLOT_WORDS = {
    "no",
    "nope",
    "nah",
    "نه",
    "خیر",
    "нет",
    "hayır",
    "ոչ",
}


def _normalize_text(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[\s\u200c]+", " ", value)
    return value


def _matches_any(value: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in patterns)


def _clear_booking_request(value: str) -> bool:
    normalized = _normalize_text(value)
    if _matches_any(normalized, _CANCEL_BOOKING_PATTERNS):
        return False
    return _matches_any(normalized, _BOOKING_PATTERNS)


def _slot_signal(value: str) -> str | None:
    normalized = _normalize_text(value)
    if _matches_any(normalized, _CANCEL_BOOKING_PATTERNS):
        return "CANCEL"
    if _matches_any(normalized, _RESCHEDULE_PATTERNS):
        return "RESCHEDULE"
    tokens = set(re.findall(r"[\w\u0530-\u058f\u0600-\u06ff]+", normalized))
    if normalized in _CONFIRM_WORDS or tokens.intersection(_CONFIRM_WORDS):
        return "CONFIRM"
    if normalized in _NEGATIVE_SLOT_WORDS or tokens.intersection(_NEGATIVE_SLOT_WORDS):
        return "RESCHEDULE"
    return None


def _local_slot(slot: datetime, timezone_name: str) -> datetime:
    if slot.tzinfo is None:
        slot = slot.replace(tzinfo=UTC)
    return slot.astimezone(ZoneInfo(timezone_name))


def _slot_label(slot: datetime, timezone_name: str) -> str:
    local = _local_slot(slot, timezone_name)
    return local.strftime("%Y-%m-%d %H:%M")


def slot_offer_message(language: str, slot: datetime, timezone_name: str) -> str:
    label = _slot_label(slot, timezone_name)
    messages = {
        "hy": (
            f"Ձեր բժշկի ժամանակացույցում ազատ ժամ կա՝ {label} ({timezone_name})։ "
            "Հարմա՞ր է այս ժամը։ Պատասխանեք այո, եթե հաստատում եք, կամ գրեք, որ այլ ժամ եք ուզում։"
        ),
        "ru": (
            f"В расписании вашего врача есть свободное время: {label} ({timezone_name}). "
            "Вам подходит? Ответьте «да», чтобы подтвердить, или попросите другое время."
        ),
        "fa": (
            f"در برنامه پزشک شما این زمان خالی است: {label} ({timezone_name}). "
            "این زمان برایتان مناسب است؟ اگر تأیید می‌کنید بگویید بله؛ اگر نه، بگویید زمان دیگری می‌خواهید."
        ),
        "tr": (
            f"Doktorunuzun programında şu saat uygun: {label} ({timezone_name}). "
            "Bu saat size uygun mu? Onaylıyorsanız evet deyin; değilse başka bir saat isteyin."
        ),
    }
    return messages.get(
        language,
        (
            f"Your doctor has an available time at {label} ({timezone_name}). "
            "Does this work for you? Reply yes to confirm, or ask for another time."
        ),
    )


def waiting_doctor_message(language: str, slot: datetime, timezone_name: str) -> str:
    label = _slot_label(slot, timezone_name)
    messages = {
        "hy": (
            f"Շնորհակալություն։ Դուք հաստատել եք {label} ({timezone_name}) ժամը։ "
            "Այժմ այն սպասում է բժշկի վերջնական հաստատմանը։ Հաստատումից հետո անմիջապես կգրենք ձեզ։"
        ),
        "ru": (
            f"Спасибо. Вы подтвердили время {label} ({timezone_name}). "
            "Теперь запись ожидает окончательного подтверждения врача. Мы сразу напишем вам после подтверждения."
        ),
        "fa": (
            f"ممنون. شما زمان {label} ({timezone_name}) را تأیید کردید. "
            "حالا این وقت منتظر تأیید نهایی پزشک است و بعد از تأیید فوراً به شما پیام می‌دهیم."
        ),
        "tr": (
            f"Teşekkürler. {label} ({timezone_name}) saatini onayladınız. "
            "Şimdi randevu doktorun son onayını bekliyor. Onaylanınca size hemen yazacağız."
        ),
    }
    return messages.get(
        language,
        (
            f"Thanks. You confirmed {label} ({timezone_name}). "
            "The appointment is now waiting for the doctor's final approval. We'll message you as soon as it is approved."
        ),
    )


def still_waiting_doctor_message(language: str) -> str:
    return {
        "hy": "Ձեր ընտրած ժամը դեռ սպասում է բժշկի հաստատմանը։ Հաստատվելուն պես անմիջապես կգրենք ձեզ։",
        "ru": "Выбранное время всё ещё ожидает подтверждения врача. Мы сразу напишем вам, как только оно будет подтверждено.",
        "fa": "زمانی که انتخاب کردید هنوز منتظر تأیید پزشک است. به محض تأیید، فوراً به شما پیام می‌دهیم.",
        "tr": "Seçtiğiniz saat hâlâ doktor onayını bekliyor. Onaylanır onaylanmaz size hemen yazacağız.",
    }.get(
        language,
        "Your selected time is still waiting for the doctor's approval. We'll message you as soon as it is confirmed.",
    )


def no_slot_message(language: str) -> str:
    return {
        "hy": "Այս պահին բժշկի ժամանակացույցում ազատ ժամ չեմ գտնում։ Կլինիկայի թիմը պետք է օգնի ձեզ ժամ նշանակել։",
        "ru": "Сейчас я не вижу свободного времени в расписании врача. Команда клиники поможет подобрать время.",
        "fa": "در حال حاضر زمان خالی مناسبی در برنامه پزشک پیدا نکردم. تیم کلینیک باید برای هماهنگی وقت به شما کمک کند.",
        "tr": "Şu anda doktorun programında uygun boş saat bulamıyorum. Klinik ekibi size saat ayarlamada yardımcı olacak.",
    }.get(
        language,
        "I can't find an available time in the doctor's schedule right now. The clinic team will need to help arrange a time.",
    )


def clarify_slot_message(language: str, slot: datetime, timezone_name: str) -> str:
    label = _slot_label(slot, timezone_name)
    return {
        "hy": f"Պարզապես հաստատեք՝ {label} ժամը հարմար է, թե ցանկանում եք այլ ժամ։",
        "ru": f"Пожалуйста, подтвердите: время {label} вам подходит или предложить другое?",
        "fa": f"لطفاً فقط مشخص کنید: زمان {label} برایتان مناسب است یا زمان دیگری پیشنهاد بدهم؟",
        "tr": f"Lütfen netleştirin: {label} size uygun mu, yoksa başka bir saat önereyim mi?",
    }.get(
        language,
        f"Please confirm whether {label} works for you, or tell me to offer another time.",
    )


def booking_cancelled_message(language: str) -> str:
    return {
        "hy": "Լավ, այս պահին ժամ չեմ ամրագրի։ Եթե հետագայում ցանկանաք այցելություն կազմակերպել, պարզապես գրեք մեզ։",
        "ru": "Хорошо, сейчас запись оформлять не буду. Если позже захотите записаться, просто напишите нам.",
        "fa": "باشه، فعلاً وقتی برای شما رزرو نمی‌کنم. اگر بعداً خواستید وقت بگیرید، کافی است دوباره به ما پیام بدهید.",
        "tr": "Tamam, şimdilik randevu oluşturmayacağım. Daha sonra randevu isterseniz bize tekrar yazmanız yeterli.",
    }.get(
        language,
        "Okay, I won't create an appointment right now. If you'd like to book later, just message us again.",
    )


def appointment_confirmed_message(
    language: str,
    slot: datetime,
    timezone_name: str,
    clinic_name: str,
) -> str:
    label = _slot_label(slot, timezone_name)
    return {
        "hy": (
            f"Ձեր այցը հաստատված է՝ {label} ({timezone_name})։ "
            f"Խնդրում ենք այդ ժամին ներկայանալ {clinic_name} կլինիկա։ Կտեսնվենք։"
        ),
        "ru": (
            f"Ваш визит подтверждён на {label} ({timezone_name}). "
            f"Пожалуйста, приходите в клинику {clinic_name} к назначенному времени. До встречи."
        ),
        "fa": (
            f"وقت شما برای {label} ({timezone_name}) نهایی و تأیید شد. "
            f"لطفاً سر موعد در کلینیک {clinic_name} حضور داشته باشید. منتظرتان هستیم."
        ),
        "tr": (
            f"Randevunuz {label} ({timezone_name}) için kesin olarak onaylandı. "
            f"Lütfen belirtilen saatte {clinic_name} kliniğinde olun. Görüşmek üzere."
        ),
    }.get(
        language,
        (
            f"Your appointment is confirmed for {label} ({timezone_name}). "
            f"Please be at {clinic_name} at the scheduled time. See you then."
        ),
    )


def _safe_context(conversation: CareConversation) -> dict:
    value = conversation.booking_context
    return dict(value) if isinstance(value, dict) else {}


async def _active_item(session: AsyncSession, plan: CarePlan | None) -> CarePlanItem | None:
    if not plan:
        return None
    return await session.scalar(
        select(CarePlanItem)
        .where(
            CarePlanItem.care_plan_id == plan.id,
            CarePlanItem.status.in_(_ACTIVE_ITEM_STATES),
        )
        .order_by(CarePlanItem.sequence_order.asc())
        .limit(1)
    )


async def _history(session: AsyncSession, conversation_id: uuid.UUID) -> list[CareConversationMessage]:
    return list(
        (
            await session.scalars(
                select(CareConversationMessage)
                .where(CareConversationMessage.conversation_id == conversation_id)
                .order_by(CareConversationMessage.created_at.asc())
            )
        ).all()
    )


async def _send_and_record(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    conversation: CareConversation,
    item: CarePlanItem | None,
    phone: str,
    message: str,
    metadata: dict,
) -> dict:
    sent = await WhatsAppServiceClient().send_message(clinic_id, phone, message)
    now = datetime.now(UTC)
    session.add(
        CareConversationMessage(
            conversation_id=conversation.id,
            care_plan_item_id=item.id if item else None,
            direction="OUT",
            body=message,
            language=conversation.language,
            status="SENT",
            sent_at=now,
            attempt_count=1,
            provider_message_id=sent.get("message_id"),
            message_metadata=metadata,
        )
    )
    conversation.last_message_at = now
    return sent


async def _agent_decision(
    *,
    conversation: CareConversation,
    patient: Patient,
    clinic_name: str,
    item: CarePlanItem | None,
    history: list[CareConversationMessage],
    text: str,
    available_slot_strings: list[str],
    instructions: str,
) -> CareAgentReply:
    return await care_agent_reply(
        language=conversation.language,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        clinic_name=clinic_name,
        care_items=(
            [
                {
                    "tooth": item.tooth_fdi,
                    "finding": item.finding_type,
                    "window": item.recommended_window,
                    "visit_outcome": item.outcome,
                }
            ]
            if item
            else []
        ),
        history=[
            {
                "role": "assistant" if row.direction == "OUT" else "user",
                "content": row.body,
            }
            for row in history
        ],
        available_slots=available_slot_strings,
        inbound_message=text,
        booking_instructions=instructions,
    )


async def _next_slot(
    session: AsyncSession,
    *,
    patient: Patient,
    plan: CarePlan | None,
    exclude: str | None = None,
) -> tuple[datetime | None, object]:
    settings = await settings_for_branch(session, patient.branch_id)
    slots = await available_slots(
        session,
        branch_id=patient.branch_id,
        settings=settings,
        doctor_id=plan.doctor_id if plan else None,
        limit=64,
    )
    for slot in slots:
        if slot.isoformat() != exclude:
            return slot, settings
    return None, settings


async def _find_patient_by_phone(session: AsyncSession, phone: str) -> Patient | None:
    try:
        normalized = normalize_phone(phone)
    except ValueError:
        return None
    rows = (
        await session.scalars(
            select(Patient).where(
                (Patient.whatsapp_phone.is_not(None)) | (Patient.phone.is_not(None))
            )
        )
    ).all()
    for patient in rows:
        for value in (patient.whatsapp_phone, patient.phone):
            if not value:
                continue
            try:
                if normalize_phone(value) == normalized:
                    return patient
            except ValueError:
                continue
    return None


async def process_staged_inbound_message(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    phone: str,
    text: str,
    provider_message_id: str | None,
) -> dict:
    """Process one patient message through the deterministic booking state machine.

    Groq may classify ambiguous language, but it never controls slot selection or appointment state.
    The database state machine is authoritative and only creates a PROPOSED appointment after the
    patient explicitly confirms the exact slot that DENTAI offered.
    """

    patient = await _find_patient_by_phone(session, phone)
    if not patient:
        return {"handled": False, "reason": "patient_not_found"}
    try:
        normalized_phone = normalize_phone(phone)
    except ValueError:
        return {"handled": False, "reason": "patient_not_found"}

    conversation = await session.scalar(
        select(CareConversation)
        .where(CareConversation.patient_id == patient.id, CareConversation.status == "ACTIVE")
        .order_by(CareConversation.created_at.desc())
        .limit(1)
    )
    if not conversation:
        return {"handled": False, "reason": "conversation_not_found"}

    if provider_message_id:
        duplicate = await session.scalar(
            select(CareConversationMessage.id).where(
                CareConversationMessage.conversation_id == conversation.id,
                CareConversationMessage.provider_message_id == provider_message_id,
            )
        )
        if duplicate:
            return {"handled": True, "duplicate": True}

    plan = (
        await session.get(CarePlan, conversation.care_plan_id)
        if conversation.care_plan_id
        else None
    )
    item = await _active_item(session, plan)
    context = _safe_context(conversation)

    active_item_id = str(item.id) if item else None
    previous_active_item = context.get("active_item_id")
    if (
        item
        and previous_active_item
        and previous_active_item != active_item_id
        and item.status in {"FOLLOWUP_READY", "CONTACTED"}
    ):
        preserved = {
            key: value
            for key, value in context.items()
            if key.startswith("last_visit_") or key == "sequence_mode"
        }
        context = preserved
        context["stage"] = WAITING_PATIENT_REPLY

    stage = str(context.get("stage") or WAITING_PATIENT_REPLY)
    context["active_item_id"] = active_item_id
    context["stage"] = stage

    inbound = CareConversationMessage(
        conversation_id=conversation.id,
        care_plan_item_id=item.id if item else None,
        direction="IN",
        body=text,
        language=conversation.language,
        status="RECEIVED",
        provider_message_id=provider_message_id,
        message_metadata={"stage_received": stage},
    )
    session.add(inbound)
    await session.flush()
    history = await _history(session, conversation.id)
    settings = await settings_for_branch(session, patient.branch_id)

    if stage == WAITING_DOCTOR_APPROVAL:
        proposed = await session.scalar(
            select(CareAppointment)
            .where(
                CareAppointment.conversation_id == conversation.id,
                CareAppointment.status == "PROPOSED",
            )
            .order_by(CareAppointment.created_at.desc())
            .limit(1)
        )
        if proposed:
            message = still_waiting_doctor_message(conversation.language)
            await _send_and_record(
                session,
                clinic_id=clinic_id,
                conversation=conversation,
                item=item,
                phone=normalized_phone,
                message=message,
                metadata={
                    "kind": "booking_waiting_doctor",
                    "stage": WAITING_DOCTOR_APPROVAL,
                    "appointment_id": str(proposed.id),
                },
            )
            conversation.summary = "Patient confirmed a slot; waiting for doctor approval."
            conversation.booking_context = context
            return {
                "handled": True,
                "stage": WAITING_DOCTOR_APPROVAL,
                "appointment_proposed": True,
            }
        context["stage"] = WAITING_PATIENT_REPLY
        stage = WAITING_PATIENT_REPLY

    if stage == APPOINTMENT_CONFIRMED:
        conversation.booking_context = context
        conversation.last_message_at = datetime.now(UTC)
        conversation.summary = "Appointment confirmed; automated booking conversation completed."
        return {
            "handled": True,
            "stage": APPOINTMENT_CONFIRMED,
            "terminal": True,
        }

    if stage == WAITING_PATIENT_REPLY:
        clear_booking = _clear_booking_request(text)
        reply = None
        wants_booking = clear_booking
        if not clear_booking:
            instructions = (
                (settings.booking_instructions or "")
                + "\nCurrent workflow stage: WAITING_PATIENT_REPLY. "
                "Decide whether the patient's latest message means they want to arrange an appointment. "
                "Use intent=BOOKING for a clear booking request or agreement to arrange a visit. "
                "Do not offer or invent a time at this stage; DENTAI will choose the slot separately."
            )
            reply = await _agent_decision(
                conversation=conversation,
                patient=patient,
                clinic_name=clinic_name,
                item=item,
                history=history,
                text=text,
                available_slot_strings=[],
                instructions=instructions,
            )
            wants_booking = reply.intent in {"BOOKING", "RESCHEDULE"}

        if wants_booking:
            slot, settings = await _next_slot(session, patient=patient, plan=plan)
            if not slot:
                message = no_slot_message(conversation.language)
                await _send_and_record(
                    session,
                    clinic_id=clinic_id,
                    conversation=conversation,
                    item=item,
                    phone=normalized_phone,
                    message=message,
                    metadata={
                        "kind": "booking_no_slot",
                        "stage": WAITING_PATIENT_REPLY,
                        "needs_human": True,
                    },
                )
                context.update(
                    {
                        "stage": WAITING_PATIENT_REPLY,
                        "booking_requested": True,
                        "needs_human": True,
                    }
                )
                conversation.summary = "Patient wants an appointment; no free doctor slot is available."
                conversation.booking_context = context
                return {
                    "handled": True,
                    "intent": "BOOKING",
                    "stage": WAITING_PATIENT_REPLY,
                    "appointment_proposed": False,
                    "needs_human": True,
                }

            context.update(
                {
                    "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                    "booking_requested": True,
                    "offered_slot": slot.isoformat(),
                    "offered_at": datetime.now(UTC).isoformat(),
                    "appointment_id": None,
                    "needs_human": False,
                }
            )
            message = slot_offer_message(conversation.language, slot, settings.timezone)
            await _send_and_record(
                session,
                clinic_id=clinic_id,
                conversation=conversation,
                item=item,
                phone=normalized_phone,
                message=message,
                metadata={
                    "kind": "booking_slot_offer",
                    "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                    "offered_slot": slot.isoformat(),
                },
            )
            conversation.summary = (
                f"Patient wants an appointment; offered {_slot_label(slot, settings.timezone)}. "
                "Waiting for patient confirmation."
            )
            conversation.booking_context = context
            return {
                "handled": True,
                "intent": "BOOKING",
                "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                "offered_slot": slot.isoformat(),
                "appointment_proposed": False,
            }

        if reply is None:
            reply = await _agent_decision(
                conversation=conversation,
                patient=patient,
                clinic_name=clinic_name,
                item=item,
                history=history,
                text=text,
                available_slot_strings=[],
                instructions=settings.booking_instructions or "",
            )
        await _send_and_record(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            item=item,
            phone=normalized_phone,
            message=reply.reply,
            metadata={
                "kind": "care_reply",
                "stage": WAITING_PATIENT_REPLY,
                "intent": reply.intent,
                "needs_human": reply.needs_human,
                "ai_provider": reply.provider,
                "ai_model": reply.model,
            },
        )
        context.update(
            {
                "stage": WAITING_PATIENT_REPLY,
                "last_intent": reply.intent,
                "needs_human": reply.needs_human,
            }
        )
        conversation.summary = (
            f"Patient replied; intent {reply.intent}. "
            "No appointment requested yet."
        )
        conversation.booking_context = context
        return {
            "handled": True,
            "intent": reply.intent,
            "stage": WAITING_PATIENT_REPLY,
            "appointment_proposed": False,
            "needs_human": reply.needs_human,
        }

    if stage == WAITING_PATIENT_SLOT_CONFIRMATION:
        offered_raw = context.get("offered_slot")
        try:
            offered = datetime.fromisoformat(str(offered_raw))
        except (TypeError, ValueError):
            offered = None

        if offered is None:
            replacement, settings = await _next_slot(session, patient=patient, plan=plan)
            if replacement is None:
                message = no_slot_message(conversation.language)
                await _send_and_record(
                    session,
                    clinic_id=clinic_id,
                    conversation=conversation,
                    item=item,
                    phone=normalized_phone,
                    message=message,
                    metadata={
                        "kind": "booking_no_slot",
                        "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                        "needs_human": True,
                    },
                )
                context["needs_human"] = True
                conversation.booking_context = context
                conversation.summary = "Booking requested; no doctor slot is available."
                return {
                    "handled": True,
                    "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                    "needs_human": True,
                }
            offered = replacement
            context["offered_slot"] = offered.isoformat()

        offered_iso = offered.isoformat()
        signal = _slot_signal(text)
        reply = None
        if signal is None:
            instructions = (
                (settings.booking_instructions or "")
                + "\nCurrent workflow stage: WAITING_PATIENT_SLOT_CONFIRMATION. "
                f"DENTAI already offered exactly this slot: {offered_iso}. "
                "If the patient clearly accepts that slot, set intent=BOOKING and selected_slot to that exact ISO value. "
                "If they want a different time, use intent=RESCHEDULE and wants_reschedule=true. "
                "If they no longer want an appointment, use intent=DECLINE. Do not invent a different slot."
            )
            reply = await _agent_decision(
                conversation=conversation,
                patient=patient,
                clinic_name=clinic_name,
                item=item,
                history=history,
                text=text,
                available_slot_strings=[offered_iso],
                instructions=instructions,
            )
            if reply.selected_slot == offered_iso:
                signal = "CONFIRM"
            elif reply.wants_reschedule or reply.intent == "RESCHEDULE":
                signal = "RESCHEDULE"
            elif reply.intent == "DECLINE":
                signal = "CANCEL"

        if signal == "CANCEL":
            context.update(
                {
                    "stage": WAITING_PATIENT_REPLY,
                    "booking_requested": False,
                    "offered_slot": None,
                    "appointment_id": None,
                }
            )
            message = booking_cancelled_message(conversation.language)
            await _send_and_record(
                session,
                clinic_id=clinic_id,
                conversation=conversation,
                item=item,
                phone=normalized_phone,
                message=message,
                metadata={
                    "kind": "booking_cancelled",
                    "stage": WAITING_PATIENT_REPLY,
                },
            )
            conversation.summary = "Patient does not want an appointment right now."
            conversation.booking_context = context
            return {
                "handled": True,
                "intent": "DECLINE",
                "stage": WAITING_PATIENT_REPLY,
                "appointment_proposed": False,
            }

        if signal == "RESCHEDULE":
            replacement, settings = await _next_slot(
                session,
                patient=patient,
                plan=plan,
                exclude=offered_iso,
            )
            if replacement is None:
                message = no_slot_message(conversation.language)
                await _send_and_record(
                    session,
                    clinic_id=clinic_id,
                    conversation=conversation,
                    item=item,
                    phone=normalized_phone,
                    message=message,
                    metadata={
                        "kind": "booking_no_alternate_slot",
                        "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                        "needs_human": True,
                    },
                )
                context["needs_human"] = True
                conversation.booking_context = context
                conversation.summary = "Patient requested another time; no alternate doctor slot is available."
                return {
                    "handled": True,
                    "intent": "RESCHEDULE",
                    "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                    "needs_human": True,
                }
            context.update(
                {
                    "offered_slot": replacement.isoformat(),
                    "offered_at": datetime.now(UTC).isoformat(),
                    "needs_human": False,
                }
            )
            message = slot_offer_message(
                conversation.language,
                replacement,
                settings.timezone,
            )
            await _send_and_record(
                session,
                clinic_id=clinic_id,
                conversation=conversation,
                item=item,
                phone=normalized_phone,
                message=message,
                metadata={
                    "kind": "booking_slot_offer",
                    "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                    "offered_slot": replacement.isoformat(),
                    "replaced_slot": offered_iso,
                },
            )
            conversation.summary = (
                f"Patient requested another time; offered {_slot_label(replacement, settings.timezone)}. "
                "Waiting for patient confirmation."
            )
            conversation.booking_context = context
            return {
                "handled": True,
                "intent": "RESCHEDULE",
                "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                "offered_slot": replacement.isoformat(),
                "appointment_proposed": False,
            }

        if signal == "CONFIRM":
            fresh_slots = await available_slots(
                session,
                branch_id=patient.branch_id,
                settings=settings,
                doctor_id=plan.doctor_id if plan else None,
                limit=64,
            )
            fresh_by_iso = {slot.isoformat(): slot for slot in fresh_slots}
            if offered_iso not in fresh_by_iso:
                replacement, settings = await _next_slot(
                    session,
                    patient=patient,
                    plan=plan,
                    exclude=offered_iso,
                )
                if replacement is None:
                    message = no_slot_message(conversation.language)
                    await _send_and_record(
                        session,
                        clinic_id=clinic_id,
                        conversation=conversation,
                        item=item,
                        phone=normalized_phone,
                        message=message,
                        metadata={
                            "kind": "booking_slot_expired_no_replacement",
                            "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                            "needs_human": True,
                        },
                    )
                    context["needs_human"] = True
                    conversation.booking_context = context
                    conversation.summary = "The offered slot became unavailable; manual scheduling is needed."
                    return {
                        "handled": True,
                        "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                        "needs_human": True,
                    }
                context.update(
                    {
                        "offered_slot": replacement.isoformat(),
                        "offered_at": datetime.now(UTC).isoformat(),
                    }
                )
                message = slot_offer_message(
                    conversation.language,
                    replacement,
                    settings.timezone,
                )
                await _send_and_record(
                    session,
                    clinic_id=clinic_id,
                    conversation=conversation,
                    item=item,
                    phone=normalized_phone,
                    message=message,
                    metadata={
                        "kind": "booking_slot_replaced_unavailable",
                        "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                        "offered_slot": replacement.isoformat(),
                        "replaced_slot": offered_iso,
                    },
                )
                conversation.summary = "The first offered slot became unavailable; a new slot was offered."
                conversation.booking_context = context
                return {
                    "handled": True,
                    "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                    "offered_slot": replacement.isoformat(),
                    "appointment_proposed": False,
                }

            existing = await session.scalar(
                select(CareAppointment)
                .where(
                    CareAppointment.conversation_id == conversation.id,
                    CareAppointment.status.in_(["PROPOSED", "APPROVED"]),
                )
                .order_by(CareAppointment.created_at.desc())
                .limit(1)
            )
            if existing:
                context.update(
                    {
                        "stage": (
                            APPOINTMENT_CONFIRMED
                            if existing.status == "APPROVED"
                            else WAITING_DOCTOR_APPROVAL
                        ),
                        "appointment_id": str(existing.id),
                    }
                )
                conversation.booking_context = context
                return {
                    "handled": True,
                    "stage": context["stage"],
                    "appointment_proposed": existing.status == "PROPOSED",
                }

            selected = fresh_by_iso[offered_iso]
            duration = timedelta(minutes=settings.appointment_minutes)
            appointment = CareAppointment(
                patient_id=patient.id,
                branch_id=patient.branch_id,
                doctor_id=plan.doctor_id if plan else None,
                conversation_id=conversation.id,
                care_plan_item_id=item.id if item else None,
                starts_at=selected.astimezone(UTC),
                ends_at=(selected + duration).astimezone(UTC),
                timezone=settings.timezone,
                status="PROPOSED",
                source="AI",
                tooth_fdi=item.tooth_fdi if item else None,
                finding_type=item.finding_type if item else None,
                reason=(
                    f"Teta2 Care check-up · tooth {item.tooth_fdi}"
                    if item
                    else "Teta2 Care check-up"
                ),
                patient_confirmed_at=datetime.now(UTC),
            )
            session.add(appointment)
            await session.flush()
            if item:
                item.status = "APPOINTMENT_PENDING_APPROVAL"
            context.update(
                {
                    "stage": WAITING_DOCTOR_APPROVAL,
                    "patient_confirmed_slot": offered_iso,
                    "patient_confirmed_at": datetime.now(UTC).isoformat(),
                    "appointment_id": str(appointment.id),
                    "needs_human": False,
                }
            )
            message = waiting_doctor_message(
                conversation.language,
                selected,
                settings.timezone,
            )
            await _send_and_record(
                session,
                clinic_id=clinic_id,
                conversation=conversation,
                item=item,
                phone=normalized_phone,
                message=message,
                metadata={
                    "kind": "booking_patient_confirmed",
                    "stage": WAITING_DOCTOR_APPROVAL,
                    "appointment_id": str(appointment.id),
                    "selected_slot": offered_iso,
                },
            )
            conversation.summary = (
                f"Patient confirmed {_slot_label(selected, settings.timezone)}; "
                "waiting for doctor approval."
            )
            conversation.booking_context = context
            return {
                "handled": True,
                "intent": "BOOKING",
                "stage": WAITING_DOCTOR_APPROVAL,
                "appointment_proposed": True,
                "appointment_id": str(appointment.id),
            }

        message = clarify_slot_message(
            conversation.language,
            offered,
            settings.timezone,
        )
        await _send_and_record(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            item=item,
            phone=normalized_phone,
            message=message,
            metadata={
                "kind": "booking_slot_clarification",
                "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                "offered_slot": offered_iso,
                "ai_intent": reply.intent if reply else None,
            },
        )
        conversation.summary = "Waiting for the patient to confirm or change the offered time."
        conversation.booking_context = context
        return {
            "handled": True,
            "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
            "appointment_proposed": False,
        }

    context["stage"] = WAITING_PATIENT_REPLY
    conversation.booking_context = context
    conversation.summary = "Conversation state was repaired; waiting for the patient's booking decision."
    return {
        "handled": True,
        "stage": WAITING_PATIENT_REPLY,
        "recovered": True,
    }
