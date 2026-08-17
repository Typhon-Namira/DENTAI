import json
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.outreach.timing import FollowupTiming


class ArmenianIntro(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intro: str


def deterministic_armenian_message(timing: FollowupTiming) -> str:
    local = timing.target_followup_at.astimezone(ZoneInfo(timing.clinic_timezone))
    return (
        "Բարև։ Ձեր վերջին ատամնաբուժական հետազոտության հիման վրա խորհուրդ է տրվում "
        f"վերահսկիչ այց՝ {timing.tooth_fdi} ատամի հատվածը կրկին գնահատելու համար։ "
        f"Առաջարկվող այցի ամսաթիվն է՝ {local.strftime('%d.%m.%Y')}։ "
        "Խնդրում ենք կապվել կլինիկայի հետ և ամրագրել հարմար ժամ։"
    )


async def armenian_message(timing: FollowupTiming) -> str:
    settings = get_settings()
    fallback = deterministic_armenian_message(timing)
    if not settings.groq_api_key:
        return fallback
    system = (
        "You are not a dental diagnostic model. You do not analyze radiographs "
        "or perform clinical inference. Render one calm Eastern Armenian introductory "
        "sentence using only the supplied DENTAI evidence. "
        "Do not add diagnoses, treatment, urgency, certainty, scores, or dates. "
        "Return strict JSON with only the required intro field."
    )
    evidence = {
        "finding_type": timing.finding_type,
        "tooth_fdi": timing.tooth_fdi,
        "recommended_window": timing.recommended_window,
        "target_followup_at": timing.target_followup_at.isoformat(),
    }
    try:
        async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(evidence)},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "armenian_intro",
                            "strict": True,
                            "schema": ArmenianIntro.model_json_schema(),
                        },
                    },
                },
            )
            response.raise_for_status()
            intro = ArmenianIntro.model_validate_json(
                response.json()["choices"][0]["message"]["content"]
            ).intro.strip()
        if not intro or len(intro) > 400:
            return fallback
        local = timing.target_followup_at.astimezone(ZoneInfo(timing.clinic_timezone))
        return (
            f"{intro} Առաջարկվող այցի ամսաթիվն է՝ "
            f"{local.strftime('%d.%m.%Y')}։ Խնդրում ենք կապվել կլինիկայի հետ և "
            "ամրագրել հարմար ժամ։"
        )
    except (httpx.HTTPError, KeyError, ValueError):
        return fallback
