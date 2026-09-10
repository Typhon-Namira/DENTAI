import pytest

import app.care.groq as care_groq


@pytest.mark.asyncio
async def test_outreach_drafts_are_bound_to_requested_teeth(monkeypatch):
    async def fake_groq_json(**kwargs):
        return care_groq._OutreachDraftBatch(
            messages=[
                care_groq._OutreachDraft(
                    tooth_fdi="38",
                    message="Hi Amir, we'd like to check one area around tooth 38. Reply if you'd like help arranging a visit.",
                )
            ]
        )

    monkeypatch.setattr(care_groq, "_groq_json", fake_groq_json)
    drafts = await care_groq.care_outreach_drafts(
        language="en",
        patient_name="Amir Example",
        clinic_name="Example Clinic",
        care_items=[
            {
                "tooth": "38",
                "finding": "CARIES",
                "window": "soon",
                "clinician_reviewed": False,
                "patient_id": "must-not-leave-dentai",
                "phone": "+000000000",
                "confidence": 0.91,
            }
        ],
    )
    assert list(drafts) == ["38"]
    assert "tooth 38" in drafts["38"]


@pytest.mark.asyncio
async def test_reply_falls_back_safely_when_groq_is_unavailable(monkeypatch):
    async def unavailable(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(care_groq, "_groq_json", unavailable)
    reply = await care_groq.care_agent_reply(
        language="en",
        patient_name="Amir Example",
        clinic_name="Example Clinic",
        care_items=[{"tooth": "38", "finding": "CARIES", "window": "soon"}],
        history=[],
        available_slots=[],
        inbound_message="Does this mean I definitely have a cavity?",
    )
    assert reply.provider == "fallback"
    assert reply.needs_human is True
    assert reply.selected_slot is None
    assert reply.reply


def test_safe_item_excludes_direct_identifiers_and_model_scores():
    safe = care_groq._safe_care_item(
        {
            "tooth": "38",
            "finding": "CARIES",
            "window": "soon",
            "clinician_reviewed": True,
            "patient_id": "secret-id",
            "phone": "+37400000000",
            "confidence": 0.87,
            "raw_image": "never-send",
        }
    )
    assert safe == {
        "tooth": "38",
        "finding": "CARIES",
        "window": "soon",
        "clinician_reviewed": True,
        "visit_outcome": None,
    }
