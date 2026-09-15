import pytest

from app.care import message_style_policy


@pytest.mark.asyncio
async def test_professional_policy_is_added_without_changing_call_shape(monkeypatch):
    captured = {}

    async def fake_base(*, booking_instructions=None, **kwargs):
        captured["booking_instructions"] = booking_instructions
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(message_style_policy, "_base_care_agent_reply", fake_base)

    result = await message_style_policy.professional_care_agent_reply(
        language="en",
        patient_name="Ani Test",
        clinic_name="Clinic",
        care_items=[],
        history=[],
        available_slots=[],
        inbound_message="How are you?",
        booking_instructions="Existing clinic instruction",
    )

    assert result == "ok"
    instructions = captured["booking_instructions"]
    assert "Existing clinic instruction" in instructions
    assert "Never call them a customer" in instructions
    assert "An empty AVAILABLE_SLOTS array by itself is NOT evidence" in instructions
    assert "If the patient is not asking to book or reschedule, do not mention appointment availability" in instructions


def test_policy_does_not_claim_empty_slots_mean_no_availability():
    instructions = message_style_policy.professional_booking_instructions(None)
    assert "empty AVAILABLE_SLOTS" in instructions
    assert "NOT evidence that the clinic has no availability" in instructions
    assert "Never say there are no appointments" in instructions
