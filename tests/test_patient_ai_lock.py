import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.care.lifecycle_guard_api import _enforce_post_confirmation_patient_lock
from app.care.models import CareConversation, CareConversationMessage, CarePlan
from app.database.base import Base
from app.database.models import Patient


async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_stale_second_active_conversation_cannot_restart_ai_after_confirmation():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="LOCK-1",
                first_name="Ani",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493123456",
            )
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

            locked_at = datetime.now(UTC) - timedelta(seconds=2)
            confirmed = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="WAITING_NEXT_TOOTH",
                booking_context={
                    "stage": "APPOINTMENT_CONFIRMED",
                    "patient_ai_locked_at": locked_at.isoformat(),
                },
                last_message_at=locked_at,
            )
            stale_active = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="ACTIVE",
                booking_context={"stage": "WAITING_PATIENT_REPLY"},
                last_message_at=locked_at + timedelta(seconds=1),
            )
            session.add_all([confirmed, stale_active])
            await session.flush()

            blocked = await _enforce_post_confirmation_patient_lock(
                session,
                phone=patient.whatsapp_phone,
            )

            assert blocked is True
            assert stale_active.status == "WAITING_NEXT_TOOTH"
            assert stale_active.booking_context["stage"] == "APPOINTMENT_CONFIRMED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_real_next_tooth_outreach_is_the_only_event_that_reopens_ai():
    engine, factory = await session_factory()
    branch_id = uuid.uuid4()
    try:
        async with factory() as session:
            patient = Patient(
                patient_number="LOCK-2",
                first_name="Ani",
                last_name="Test",
                branch_id=branch_id,
                status="ACTIVE",
                whatsapp_phone="+37493123457",
            )
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

            locked_at = datetime.now(UTC) - timedelta(minutes=1)
            confirmed = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="WAITING_NEXT_TOOTH",
                booking_context={
                    "stage": "APPOINTMENT_CONFIRMED",
                    "patient_ai_locked_at": locked_at.isoformat(),
                },
                last_message_at=locked_at,
            )
            next_tooth = CareConversation(
                patient_id=patient.id,
                care_plan_id=plan.id,
                branch_id=branch_id,
                whatsapp_phone=patient.whatsapp_phone,
                language="en",
                status="ACTIVE",
                booking_context={"stage": "WAITING_PATIENT_REPLY"},
                last_message_at=locked_at + timedelta(seconds=30),
            )
            session.add_all([confirmed, next_tooth])
            await session.flush()
            session.add(
                CareConversationMessage(
                    conversation_id=next_tooth.id,
                    direction="OUT",
                    body="Next tooth follow-up",
                    language="en",
                    status="SENT",
                    sent_at=locked_at + timedelta(seconds=30),
                    provider_message_id="next-tooth-outreach",
                    message_metadata={"kind": "scheduled_sequential_followup"},
                )
            )
            await session.flush()

            blocked = await _enforce_post_confirmation_patient_lock(
                session,
                phone=patient.whatsapp_phone,
            )

            assert blocked is False
            assert next_tooth.status == "ACTIVE"
    finally:
        await engine.dispose()
