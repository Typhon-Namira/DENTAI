import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.care import service as care_service
from app.care.models import CareConversation, CarePlan, CarePlanItem
from app.database.models import Patient


async def start_or_continue_outreach_with_booking(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    patient: Patient,
    plan: CarePlan,
    items: list[CarePlanItem],
) -> CareConversation | None:
    """Compatibility adapter for legacy plan approval.

    Historically this function sent every pending tooth immediately in a loop. It
    now only creates the same dated monthly schedule used by the sequential flow;
    the outreach worker owns the actual WhatsApp send on each tooth's exact date.
    """
    del clinic_id, clinic_name  # dispatch happens later in the outreach worker

    phone = care_service._safe_phone(patient.whatsapp_phone or patient.phone)
    if not phone or not items:
        return None

    # Local import avoids a module cycle: sequential imports settings from service,
    # while booking_bootstrap installs this compatibility function at startup.
    from app.care.sequential import (
        _conversation_for_plan,
        _monthly_contact,
        _next_local_contact,
        schedule_item_outreach,
    )

    settings = await care_service.settings_for_branch(session, patient.branch_id)
    conversation = await _conversation_for_plan(session, plan=plan, patient=patient)
    if not conversation:
        return None

    ranked = sorted(
        items,
        key=lambda item: (float(item.priority_score or 0.0), float(item.confidence or 0.0)),
        reverse=True,
    )
    first_start = _next_local_contact(settings.timezone, days=1)
    seen_teeth: set[str] = set()
    sequence = 0
    for item in ranked:
        tooth = str(item.tooth_fdi).strip()
        if tooth in seen_teeth:
            item.status = "DUPLICATE_TOOTH_SUPPRESSED"
            item.outcome = "DUPLICATE_TOOTH_SUPPRESSED"
            item.outcome_at = datetime.now(UTC)
            item.conversation_start_at = None
            continue
        seen_teeth.add(tooth)
        sequence += 1
        item.sequence_order = sequence
        item.conversation_start_at = _monthly_contact(first_start, settings.timezone, sequence - 1)
        item.status = "FOLLOWUP_READY" if sequence == 1 else "SCHEDULED_FUTURE_TOOTH"
        await schedule_item_outreach(
            session,
            plan=plan,
            patient=patient,
            item=item,
            start_at=item.conversation_start_at,
        )

    conversation.status = "WAITING_NEXT_TOOTH"
    conversation.booking_context = {"sequence_mode": True}
    conversation.summary = (
        f"{sequence} unique tooth follow-up(s) scheduled one calendar month apart. "
        "AI remains inactive until each tooth's scheduled outreach is actually sent."
    )
    await session.flush()
    return conversation


def install_booking_outreach() -> None:
    care_service.start_or_continue_outreach = start_or_continue_outreach_with_booking
