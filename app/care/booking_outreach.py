from datetime import UTC, datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care import service as care_service
from app.care.booking_links import booking_message_suffix, booking_url
from app.care.models import CareConversation, CareConversationMessage, CarePlan, CarePlanItem
from app.database.models import Patient
from app.outreach.whatsapp_client import WhatsAppServiceClient


async def start_or_continue_outreach_with_booking(
    session: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    clinic_name: str,
    patient: Patient,
    plan: CarePlan,
    items: list[CarePlanItem],
) -> CareConversation | None:
    """Start clinician-approved follow-up outreach with a signed booking URL.

    This keeps the existing care-plan and tooth-image behavior intact, but replaces
    free-text slot negotiation in the initial follow-up with a tamper-proof booking
    form whose availability is calculated live from the doctor's working hours.
    """
    phone = care_service._safe_phone(patient.whatsapp_phone or patient.phone)
    if not phone or not items:
        return None

    conversation = await care_service._conversation(
        session, patient=patient, plan=plan, phone=phone
    )
    prior_item_ids = set(
        (
            await session.scalars(
                select(CareConversationMessage.care_plan_item_id).where(
                    CareConversationMessage.conversation_id == conversation.id,
                    CareConversationMessage.direction == "OUT",
                    CareConversationMessage.care_plan_item_id.is_not(None),
                )
            )
        ).all()
    )
    pending = [item for item in items if item.id not in prior_item_ids]
    if not pending:
        return conversation

    settings = await care_service.settings_for_branch(session, patient.branch_id)
    client = WhatsAppServiceClient()
    for item in pending:
        url = booking_url(
            clinic_id=clinic_id,
            branch_id=patient.branch_id,
            doctor_id=plan.doctor_id,
            patient_id=patient.id,
            care_plan_id=plan.id,
            care_plan_item_id=item.id,
        )
        message = care_service._message(
            conversation.language,
            patient.first_name,
            item.tooth_fdi,
            item.finding_type,
        )
        message = f"{message}\n\n{booking_message_suffix(conversation.language, url)}"
        crop = (
            await care_service._finding_crop(session, plan, item)
            if settings.attach_tooth_image and item.image_required
            else None
        )
        result = await (
            client.send_image_message(clinic_id, phone, message, crop)
            if crop
            else client.send_message(clinic_id, phone, message)
        )
        session.add(
            CareConversationMessage(
                conversation_id=conversation.id,
                care_plan_item_id=item.id,
                direction="OUT",
                body=message,
                language=conversation.language,
                status="SENT",
                sent_at=datetime.now(UTC),
                attempt_count=1,
                provider_message_id=result.get("message_id"),
                message_metadata={
                    "clinic": clinic_name,
                    "kind": "finding_followup",
                    "tooth_fdi": item.tooth_fdi,
                    "image_attached": bool(crop),
                    "booking_url": url,
                    "booking_flow": "SIGNED_LINK_V1",
                },
            )
        )
        item.status = "CONTACTED"

    conversation.last_message_at = datetime.now(UTC)
    conversation.summary = (
        f"{len(pending)} clinician-confirmed tooth finding(s) sent with booking link. "
        "Awaiting appointment request."
    )
    return conversation


def install_booking_outreach() -> None:
    # approve_care_plan resolves this symbol from app.care.service at runtime, so
    # installing here upgrades the existing orchestration without duplicating or
    # replacing the clinical approval endpoints.
    care_service.start_or_continue_outreach = start_or_continue_outreach_with_booking
