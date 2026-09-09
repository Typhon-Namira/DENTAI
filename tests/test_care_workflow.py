import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.care.models import (
    CareAppointment,
    CareAvailabilityException,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    ClinicCareSettings,
)
from app.care.service import available_slots, process_inbound_message
from app.database.base import Base
from app.database.models import Patient


async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_availability_respects_timezone_working_hours_and_doctor_collision():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    try:
        async with factory() as session:
            settings = ClinicCareSettings(
                branch_id=branch_id,
                timezone="Asia/Yerevan",
                working_days=[0],
                day_start="09:00",
                day_end="11:00",
                appointment_minutes=30,
                slot_interval_minutes=30,
                min_booking_notice_minutes=0,
                booking_horizon_days=1,
                buffer_minutes=0,
                preferred_times=[],
                blocked_windows=[],
            )
            session.add(settings)
            local_monday = datetime(2026, 9, 14, 5, 0, tzinfo=UTC)
            session.add(
                CareAppointment(
                    patient_id=uuid.uuid4(),
                    branch_id=branch_id,
                    doctor_id=doctor_id,
                    starts_at=local_monday,
                    ends_at=local_monday + timedelta(minutes=30),
                    timezone="Asia/Yerevan",
                    status="PROPOSED",
                    source="AI",
                    reason="Collision test",
                )
            )
            await session.flush()

            slots = await available_slots(
                session,
                branch_id=branch_id,
                settings=settings,
                doctor_id=doctor_id,
                now=local_monday,
                limit=10,
            )

            assert all(slot.tzinfo is not None for slot in slots)
            assert all(slot.weekday() == 0 for slot in slots)
            assert all(9 <= slot.hour < 11 for slot in slots)
            assert local_monday not in {slot.astimezone(UTC) for slot in slots}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_inbound_provider_message_is_idempotent(monkeypatch):
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    patient = Patient(
        patient_number="CARE-1",
        first_name="Ani",
        last_name="Test",
        branch_id=branch_id,
        status="ACTIVE",
        whatsapp_phone="+37493123456",
    )
    try:
        async with factory() as session:
            session.add(patient)
            await session.flush()
            plan = CarePlan(
                patient_id=patient.id,
                analysis_id=uuid.uuid4(),
                branch_id=branch_id,
                doctor_id=uuid.uuid4(),
                status="ACTIVE",
                language="en",
            )
            session.add(plan)
            await session.flush()
            conversation = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="ACTIVE",
                booking_context={},
            )
            session.add(conversation)
            await session.flush()
            session.add(
                CareConversationMessage(
                    conversation_id=conversation.id,
                    direction="IN",
                    body="Monday works",
                    status="RECEIVED",
                    provider_message_id="wamid-duplicate",
                    message_metadata={},
                )
            )
            await session.flush()

            async def unexpected_agent_call(**_kwargs):
                raise AssertionError("duplicate messages must not reach the agent")

            monkeypatch.setattr("app.care.service.care_agent_reply", unexpected_agent_call)
            result = await process_inbound_message(
                session,
                clinic_id=uuid.uuid4(),
                clinic_name="Clinic",
                phone=patient.whatsapp_phone,
                text="Monday works",
                provider_message_id="wamid-duplicate",
            )

            assert result == {"handled": True, "duplicate": True}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_availability_exception_removes_overlapping_slots():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    doctor_id = uuid.uuid4()
    try:
        async with factory() as session:
            settings = ClinicCareSettings(
                branch_id=branch_id,
                timezone="Asia/Yerevan",
                working_days=[0],
                day_start="09:00",
                day_end="12:00",
                appointment_minutes=30,
                slot_interval_minutes=30,
                min_booking_notice_minutes=0,
                booking_horizon_days=1,
                buffer_minutes=0,
                preferred_times=[],
                blocked_windows=[],
            )
            monday = datetime(2026, 9, 14, 5, 0, tzinfo=UTC)
            session.add(settings)
            session.add(
                CareAvailabilityException(
                    branch_id=branch_id,
                    doctor_id=doctor_id,
                    starts_at=monday + timedelta(hours=1),
                    ends_at=monday + timedelta(hours=2),
                    kind="BREAK",
                    reason="Lunch",
                )
            )
            await session.flush()

            slots = await available_slots(
                session,
                branch_id=branch_id,
                settings=settings,
                doctor_id=doctor_id,
                now=monday,
                limit=20,
            )

            utc_slots = {slot.astimezone(UTC) for slot in slots}
            assert monday + timedelta(hours=1) not in utc_slots
            assert monday + timedelta(hours=1, minutes=30) not in utc_slots
            assert monday in utc_slots
    finally:
        await engine.dispose()
