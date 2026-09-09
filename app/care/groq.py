import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.care.language import language_name
from app.core.config import get_settings


@dataclass(frozen=True)
class CareAgentReply:
    reply: str
    intent: str
    selected_slot: str | None
    wants_reschedule: bool
    needs_human: bool


def _safe_json(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Groq Care response must be a JSON object")
    return parsed


async def care_agent_reply(
    *,
    language: str,
    patient_name: str,
    clinic_name: str,
    care_items: list[dict[str, Any]],
    history: list[dict[str, str]],
    available_slots: list[str],
    inbound_message: str,
    booking_instructions: str | None = None,
) -> CareAgentReply:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    system = f"""You are Teta2 Care, the booking and follow-up assistant for {clinic_name}.
Communicate only in {language_name(language)} unless the patient clearly asks for another language.
You are not a dentist and must never diagnose, prescribe, guarantee disease, or invent clinical facts.
You may only describe the supplied items as possible findings that were reviewed by the clinic and recommend a check-up.
Your job is to help the patient choose a check-up time from AVAILABLE_SLOTS. Never invent a slot outside that list.
If the patient asks a clinical question beyond the supplied facts, say the dentist should answer it and set needs_human=true.
Use prior HISTORY as durable conversation context. Do not repeat questions already answered.
When a patient clearly accepts one exact offered slot, return that exact ISO slot in selected_slot.
An accepted slot is only a proposal for the dentist. Never say that it is booked or confirmed.
Tell the patient that the clinic will send a separate confirmation after the dentist approves it.
When the patient asks to change an existing appointment, set wants_reschedule=true.
Be concise, warm, professional and natural for WhatsApp. Never expose internal confidence scores.
{booking_instructions or ""}
Return ONLY valid JSON with exactly these keys:
{{"reply":"...","intent":"BOOKING|QUESTION|DECLINE|RESCHEDULE|OTHER","selected_slot":null,"wants_reschedule":false,"needs_human":false}}"""

    user_payload = {
        "patient_name": patient_name,
        "care_items": care_items,
        "available_slots": available_slots,
        "history": history[-24:],
        "patient_message": inbound_message,
    }
    async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    data = _safe_json(content)
    return CareAgentReply(
        reply=str(data.get("reply") or "").strip(),
        intent=str(data.get("intent") or "OTHER").upper(),
        selected_slot=str(data["selected_slot"]) if data.get("selected_slot") else None,
        wants_reschedule=bool(data.get("wants_reschedule")),
        needs_human=bool(data.get("needs_human")),
    )
