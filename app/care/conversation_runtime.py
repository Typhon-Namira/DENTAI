"""Live WhatsApp conversation runtime for sequential Teta2 Care follow-up.

The backend owns workflow state, appointment availability and booking transitions.
Groq owns natural-language understanding and phrasing inside the active conversation.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.conversation_flow import (
    APPOINTMENT_CONFIRMED,
    WAITING_DOCTOR_APPROVAL,
    WAITING_PATIENT_REPLY,
    WAITING_PATIENT_SLOT_CONFIRMATION,
    _active_item,
    _agent,
    _clear_booking_request,
    _context,
    _find_patient,
    _history,
    _next_slot,
    _slot_label,
    _slot_signal,
    booking_cancelled_message,
    clarify_slot_message,
    no_slot_message,
    slot_offer_message,
    still_waiting_doctor_message,
    waiting_doctor_message,
)
from app.care.groq import CareAgentReply, care_conversation_message
from app.care.models import CareAppointment, CareConversation, CareConversationMessage, CarePlan
from app.care.service import available_slots, settings_for_branch
from app.database.models import Patient
from app.outreach.whatsapp_client import WhatsAppServiceClient, normalize_phone


async def _send(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    conversation: CareConversation,
    item,
    phone: str,
    message: str,
    metadata: dict,
) -> None:
    result = await WhatsAppServiceClient().send_message(clinic_id, phone, message)
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
            provider_message_id=result.get("message_id"),
            message_metadata=metadata,
        )
    )
    conversation.last_message_at = now


async def _natural_message(
    *,
    conversation: CareConversation,
    patient: Patient,
    history: list[CareConversationMessage],
    latest_patient_message: str | None,
    event: str,
    required_facts: dict,
    fallback_message: str,
):
    return await care_conversation_message(
        language=conversation.language,
        patient_name=f"{patient.first_name} {patient.last_name}".strip(),
        history=[
            {
                "role": "assistant" if row.direction == "OUT" else "user",
                "content": row.body,
            }
            for row in history
        ],
        latest_patient_message=latest_patient_message,
        event=event,
        required_facts=required_facts,
        fallback_message=fallback_message,
    )


async def _send_natural(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    conversation: CareConversation,
    patient: Patient,
    item,
    phone: str,
    history: list[CareConversationMessage],
    latest_patient_message: str | None,
    event: str,
    required_facts: dict,
    fallback_message: str,
    metadata: dict,
) -> None:
    generated = await _natural_message(
        conversation=conversation,
        patient=patient,
        history=history,
        latest_patient_message=latest_patient_message,
        event=event,
        required_facts=required_facts,
        fallback_message=fallback_message,
    )
    await _send(
        session,
        clinic_id=clinic_id,
        conversation=conversation,
        item=item,
        phone=phone,
        message=generated.reply,
        metadata={
            **metadata,
            "ai_provider": generated.provider,
            "ai_model": generated.model,
            "ai_generated": generated.provider == "groq",
        },
    )


async def _offer_slot(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    conversation: CareConversation,
    patient: Patient,
    plan: CarePlan | None,
    item,
    phone: str,
    context: dict,
    history: list[CareConversationMessage],
    latest_patient_message: str,
    exclude: str | None = None,
) -> dict:
    slot, settings = await _next_slot(
        session,
        patient=patient,
        plan=plan,
        exclude=exclude,
    )
    if slot is None:
        await _send_natural(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            patient=patient,
            item=item,
            phone=phone,
            history=history,
            latest_patient_message=latest_patient_message,
            event="BOOKING_NO_SLOT",
            required_facts={
                "available_slot": None,
                "needs_human": True,
                "must_not_invent_slot": True,
            },
            fallback_message=no_slot_message(conversation.language),
            metadata={"kind": "booking_no_slot", "needs_human": True},
        )
        context["needs_human"] = True
        conversation.booking_context = context
        conversation.summary = "Patient wants an appointment; no doctor slot is available."
        return {
            "handled": True,
            "stage": context.get("stage", WAITING_PATIENT_REPLY),
            "appointment_proposed": False,
            "needs_human": True,
        }

    slot_iso = slot.isoformat()
    context.update(
        {
            "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
            "booking_requested": True,
            "offered_slot": slot_iso,
            "offered_at": datetime.now(UTC).isoformat(),
            "appointment_id": None,
            "needs_human": False,
        }
    )
    await _send_natural(
        session,
        clinic_id=clinic_id,
        conversation=conversation,
        patient=patient,
        item=item,
        phone=phone,
        history=history,
        latest_patient_message=latest_patient_message,
        event="BOOKING_SLOT_OFFER",
        required_facts={
            "offered_slot": slot_iso,
            "local_slot": _slot_label(slot, settings.timezone),
            "timezone": settings.timezone,
            "appointment_is_not_booked_yet": True,
            "patient_must_confirm_or_request_another_time": True,
        },
        fallback_message=slot_offer_message(conversation.language, slot, settings.timezone),
        metadata={
            "kind": "booking_slot_offer",
            "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
            "offered_slot": slot_iso,
        },
    )
    conversation.booking_context = context
    conversation.summary = (
        f"Offered {_slot_label(slot, settings.timezone)}; waiting for patient confirmation."
    )
    return {
        "handled": True,
        "intent": "BOOKING",
        "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
        "offered_slot": slot_iso,
        "appointment_proposed": False,
    }


async def process_staged_inbound_message(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    phone: str,
    text: str,
    provider_message_id: str | None,
) -> dict:
    patient = await _find_patient(session, phone)
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
        return {"handled": False, "reason": "conversation_not_active"}

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
    context = _context(conversation)
    active_item_id = str(item.id) if item else None

    if (
        item
        and context.get("active_item_id")
        and context.get("active_item_id") != active_item_id
        and item.status in {"FOLLOWUP_READY", "CONTACTED"}
    ):
        context = {
            key: value
            for key, value in context.items()
            if key.startswith("last_visit_") or key == "sequence_mode"
        }

    stage = str(context.get("stage") or WAITING_PATIENT_REPLY)
    if stage == APPOINTMENT_CONFIRMED:
        conversation.status = "WAITING_NEXT_TOOTH"
        conversation.summary = "Appointment confirmed; AI is inactive until the next tooth follow-up."
        return {"handled": False, "reason": "conversation_completed"}

    context.update({"stage": stage, "active_item_id": active_item_id})

    # Read history before storing this inbound message. The latest patient text is
    # passed separately to Groq, so it is not duplicated in the model context.
    history = await _history(session, conversation.id)
    session.add(
        CareConversationMessage(
            conversation_id=conversation.id,
            care_plan_item_id=item.id if item else None,
            direction="IN",
            body=text,
            language=conversation.language,
            status="RECEIVED",
            provider_message_id=provider_message_id,
            message_metadata={"stage_received": stage},
        )
    )
    await session.flush()

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
            await _send_natural(
                session,
                clinic_id=clinic_id,
                conversation=conversation,
                patient=patient,
                item=item,
                phone=normalized_phone,
                history=history,
                latest_patient_message=text,
                event="WAITING_DOCTOR_APPROVAL",
                required_facts={
                    "appointment_status": "PROPOSED",
                    "selected_slot": proposed.starts_at.isoformat(),
                    "timezone": proposed.timezone,
                    "doctor_approval_required": True,
                    "must_not_claim_confirmed": True,
                },
                fallback_message=still_waiting_doctor_message(conversation.language),
                metadata={
                    "kind": "booking_waiting_doctor",
                    "stage": WAITING_DOCTOR_APPROVAL,
                    "appointment_id": str(proposed.id),
                },
            )
            conversation.booking_context = context
            conversation.summary = "Patient confirmed a slot; waiting for doctor approval."
            return {
                "handled": True,
                "stage": WAITING_DOCTOR_APPROVAL,
                "appointment_proposed": True,
            }
        context["stage"] = WAITING_PATIENT_REPLY
        stage = WAITING_PATIENT_REPLY

    if stage == WAITING_PATIENT_REPLY:
        reply = await _agent(
            conversation=conversation,
            patient=patient,
            clinic_name=clinic_name,
            item=item,
            history=history,
            text=text,
            available_slot_strings=[],
            instructions=(
                (settings.booking_instructions or "")
                + "\nStage: WAITING_PATIENT_REPLY. Understand the patient's latest message in context. "
                "Use intent=BOOKING only when they clearly want to arrange a visit. "
                "Do not invent or offer a time. Answer naturally and specifically to what they said."
            ),
        )
        booking = reply.intent in {"BOOKING", "RESCHEDULE"}
        if reply.provider == "fallback":
            booking = booking or _clear_booking_request(text)

        if booking:
            return await _offer_slot(
                session,
                clinic_id=clinic_id,
                conversation=conversation,
                patient=patient,
                plan=plan,
                item=item,
                phone=normalized_phone,
                context=context,
                history=history,
                latest_patient_message=text,
            )

        await _send(
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
                "ai_generated": reply.provider == "groq",
            },
        )
        context.update(
            {
                "stage": WAITING_PATIENT_REPLY,
                "last_intent": reply.intent,
                "needs_human": reply.needs_human,
            }
        )
        conversation.booking_context = context
        conversation.summary = (
            f"Patient replied; intent {reply.intent}. No appointment requested yet."
        )
        return {
            "handled": True,
            "intent": reply.intent,
            "stage": WAITING_PATIENT_REPLY,
            "appointment_proposed": False,
            "needs_human": reply.needs_human,
        }

    if stage != WAITING_PATIENT_SLOT_CONFIRMATION:
        context["stage"] = WAITING_PATIENT_REPLY
        conversation.booking_context = context
        conversation.summary = "Conversation state repaired; waiting for patient response."
        return {"handled": True, "stage": WAITING_PATIENT_REPLY, "recovered": True}

    offered_raw = context.get("offered_slot")
    try:
        offered = datetime.fromisoformat(str(offered_raw))
    except (TypeError, ValueError):
        offered = None
    if offered is None:
        return await _offer_slot(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            patient=patient,
            plan=plan,
            item=item,
            phone=normalized_phone,
            context=context,
            history=history,
            latest_patient_message=text,
        )

    offered_iso = offered.isoformat()
    ai_reply: CareAgentReply = await _agent(
        conversation=conversation,
        patient=patient,
        clinic_name=clinic_name,
        item=item,
        history=history,
        text=text,
        available_slot_strings=[offered_iso],
        instructions=(
            (settings.booking_instructions or "")
            + f"\nStage: WAITING_PATIENT_SLOT_CONFIRMATION. The only offered slot is {offered_iso}. "
            "Understand the patient's meaning in context. If they clearly accept this exact slot, "
            "use intent=BOOKING and selected_slot exactly equal to it. If they want another time, "
            "use intent=RESCHEDULE. If they no longer want a visit, use intent=DECLINE."
        ),
    )
    signal = None
    if ai_reply.selected_slot == offered_iso and ai_reply.intent == "BOOKING":
        signal = "CONFIRM"
    elif ai_reply.wants_reschedule or ai_reply.intent == "RESCHEDULE":
        signal = "RESCHEDULE"
    elif ai_reply.intent == "DECLINE":
        signal = "CANCEL"
    elif ai_reply.provider == "fallback":
        signal = _slot_signal(text)

    if signal == "CANCEL":
        context.update(
            {
                "stage": WAITING_PATIENT_REPLY,
                "booking_requested": False,
                "offered_slot": None,
                "appointment_id": None,
            }
        )
        await _send_natural(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            patient=patient,
            item=item,
            phone=normalized_phone,
            history=history,
            latest_patient_message=text,
            event="BOOKING_CANCELLED_BY_PATIENT",
            required_facts={
                "appointment_created": False,
                "patient_declined_booking_for_now": True,
            },
            fallback_message=booking_cancelled_message(conversation.language),
            metadata={"kind": "booking_cancelled", "stage": WAITING_PATIENT_REPLY},
        )
        conversation.booking_context = context
        conversation.summary = "Patient does not want an appointment right now."
        return {
            "handled": True,
            "intent": "DECLINE",
            "stage": WAITING_PATIENT_REPLY,
            "appointment_proposed": False,
        }

    if signal == "RESCHEDULE":
        return await _offer_slot(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            patient=patient,
            plan=plan,
            item=item,
            phone=normalized_phone,
            context=context,
            history=history,
            latest_patient_message=text,
            exclude=offered_iso,
        )

    if signal != "CONFIRM":
        await _send_natural(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            patient=patient,
            item=item,
            phone=normalized_phone,
            history=history,
            latest_patient_message=text,
            event="BOOKING_SLOT_CLARIFICATION",
            required_facts={
                "offered_slot": offered_iso,
                "local_slot": _slot_label(offered, settings.timezone),
                "timezone": settings.timezone,
                "must_ask_whether_slot_is_accepted_or_another_is_wanted": True,
                "appointment_is_not_booked_yet": True,
            },
            fallback_message=clarify_slot_message(
                conversation.language,
                offered,
                settings.timezone,
            ),
            metadata={
                "kind": "booking_slot_clarification",
                "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
                "offered_slot": offered_iso,
                "ai_intent": ai_reply.intent,
            },
        )
        conversation.booking_context = context
        conversation.summary = "Waiting for patient to confirm or change the offered time."
        return {
            "handled": True,
            "stage": WAITING_PATIENT_SLOT_CONFIRMATION,
            "appointment_proposed": False,
        }

    fresh_slots = await available_slots(
        session,
        branch_id=patient.branch_id,
        settings=settings,
        doctor_id=plan.doctor_id if plan else None,
        limit=64,
    )
    fresh_by_iso = {slot.isoformat(): slot for slot in fresh_slots}
    if offered_iso not in fresh_by_iso:
        return await _offer_slot(
            session,
            clinic_id=clinic_id,
            conversation=conversation,
            patient=patient,
            plan=plan,
            item=item,
            phone=normalized_phone,
            context=context,
            history=history,
            latest_patient_message=text,
            exclude=offered_iso,
        )

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
        if existing.status == "APPROVED":
            conversation.status = "WAITING_NEXT_TOOTH"
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
        reason=(f"Teta2 Care check-up · tooth {item.tooth_fdi}" if item else "Teta2 Care check-up"),
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
    await _send_natural(
        session,
        clinic_id=clinic_id,
        conversation=conversation,
        patient=patient,
        item=item,
        phone=normalized_phone,
        history=history,
        latest_patient_message=text,
        event="PATIENT_CONFIRMED_SLOT_WAITING_DOCTOR",
        required_facts={
            "patient_confirmed_slot": offered_iso,
            "local_slot": _slot_label(selected, settings.timezone),
            "timezone": settings.timezone,
            "appointment_status": "PROPOSED",
            "doctor_approval_required": True,
            "must_not_claim_final_confirmation": True,
        },
        fallback_message=waiting_doctor_message(
            conversation.language,
            selected,
            settings.timezone,
        ),
        metadata={
            "kind": "booking_patient_confirmed",
            "stage": WAITING_DOCTOR_APPROVAL,
            "appointment_id": str(appointment.id),
            "selected_slot": offered_iso,
        },
    )
    conversation.booking_context = context
    conversation.summary = (
        f"Patient confirmed {_slot_label(selected, settings.timezone)}; waiting for doctor approval."
    )
    return {
        "handled": True,
        "intent": "BOOKING",
        "stage": WAITING_DOCTOR_APPROVAL,
        "appointment_proposed": True,
        "appointment_id": str(appointment.id),
    }
