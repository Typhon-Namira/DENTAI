import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.care.conversation_flow import (
    WAITING_DOCTOR_APPROVAL,
    WAITING_PATIENT_SLOT_CONFIRMATION,
    process_staged_inbound_message,
)
from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
    ClinicCareSettings,
)
from app.database.base import Base
from app.database.models import Patient


async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_booking_requires_patient_confirmation_before_appointment(monkeypatch):
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    clinic_id = uuid.uuid4()
    slot = datetime(2026, 9, 14, 6, 0, tzinfo=UTC)

    async def fake_slots(*_args, **_kwargs):
        return [slot]

    sent_messages = []

    async def fake_send(self, _clinic_id, _phone, message):
        sent_messages.append(message)
        return {"message_id": f"wamid-{len(sent_messages)}", "status": "sent"}

    monkeypatch.setattr("app.care.conversation_flow.available_slots", fake_slots)
    monkeypatch.setattr("app.care.conversation_flow.WhatsAppServiceClient.send_message", fake_send)

    try:
        async with factory() as session:
            patient = Patient(
                patient_number="STAGED-1",
                first_name="Ani",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493123456",
            )
            session.add(patient)
            session.add(
                ClinicCareSettings(
                    branch_id=branch_id,
                    timezone="Asia/Yerevan",
                    working_days=[0, 1, 2, 3, 4, 5],
                    day_start="09:00",
                    day_end="18:00",
                    appointment_minutes=30,
                    slot_interval_minutes=30,
                    min_booking_notice_minutes=0,
                    booking_horizon_days=30,
                    buffer_minutes=0,
                    preferred_times=[],
                    blocked_windows=[],
                )
            )
            await session.flush()
            plan = CarePlan(
                patient_id=patient.id,
                analysis_id=uuid.uuid4(),
                branch_id=branch_id,
                doctor_id=doctor_id,
                status="ACTIVE",
                language="en",
            )
            session.add(plan)
            await session.flush()
            item = CarePlanItem(
                care_plan_id=plan.id,
                finding_id=uuid.uuid4(),
                tooth_fdi="18",
                finding_type="CARIES",
                confidence=0.8,
                recommended_window="within 30 days",
                target_followup_at=slot + timedelta(days=30),
                status="CONTACTED",
                rationale="Follow-up recommended",
                message_preview="Opening message",
                appointment_required=True,
                image_required=False,
                sequence_order=1,
                priority_score=88,
                priority_level="HIGH",
            )
            session.add(item)
            await session.flush()
            conversation = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="ACTIVE",
                booking_context={"sequence_mode": True},
            )
            session.add(conversation)
            await session.flush()

            first = await process_staged_inbound_message(
                session,
                clinic_id=clinic_id,
                clinic_name="Clinic",
                phone=patient.whatsapp_phone,
                text="I want to book an appointment",
                provider_message_id="wamid-in-1",
            )
            await session.flush()

            assert first["stage"] == WAITING_PATIENT_SLOT_CONFIRMATION
            assert first["appointment_proposed"] is False
            assert await session.scalar(select(CareAppointment.id)) is None
            assert "Does this work for you?" in sent_messages[-1]

            second = await process_staged_inbound_message(
                session,
                clinic_id=clinic_id,
                clinic_name="Clinic",
                phone=patient.whatsapp_phone,
                text="yes",
                provider_message_id="wamid-in-2",
            )
            await session.flush()

            appointment = await session.scalar(select(CareAppointment))
            assert second["stage"] == WAITING_DOCTOR_APPROVAL
            assert second["appointment_proposed"] is True
            assert appointment is not None
            assert appointment.status == "PROPOSED"
            assert appointment.patient_confirmed_at is not None
            assert item.status == "APPOINTMENT_PENDING_APPROVAL"
            assert "doctor's final approval" in sent_messages[-1]

            messages = (
                await session.scalars(
                    select(CareConversationMessage).where(
                        CareConversationMessage.conversation_id == conversation.id
                    )
                )
            ).all()
            assert len(messages) == 4
    finally:
        await engine.dispose()


def test_staged_routes_are_registered_before_legacy_duplicates():
    from app.main import app

    inbound = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/care/internal/whatsapp/inbound"
        and "POST" in getattr(route, "methods", set())
    ]
    approve = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/care/appointments/{appointment_id}/approve"
        and "POST" in getattr(route, "methods", set())
    ]

    assert inbound
    assert approve
    assert inbound[0].endpoint.__module__ == "app.care.staged_api"
    assert approve[0].endpoint.__module__ == "app.care.staged_api"
