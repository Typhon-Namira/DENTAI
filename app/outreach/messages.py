import json
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict

from app.core.config import get_settings
from app.outreach.timing import FollowupTiming


class ArmenianIntro(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intro: str


def _date_text(timing: FollowupTiming) -> str:
    local = timing.target_followup_at.astimezone(ZoneInfo(timing.clinic_timezone))
    return local.strftime("%d.%m.%Y")


def deterministic_armenian_message(timing: FollowupTiming) -> str:
    return (
        "Բարև։ Ձեր վերջին ատամնաբուժական հետազոտության հիման վրա խորհուրդ է տրվում "
        f"վերահսկիչ այց՝ {timing.tooth_fdi} ատամի հատվածը կրկին գնահատելու համար։ "
        f"Առաջարկվող այցի ամսաթիվն է՝ {_date_text(timing)}։ "
        "Խնդրում ենք կապվել կլինիկայի հետ և ամրագրել հարմար ժամ։"
    )


def deterministic_group_armenian_message(timings: list[FollowupTiming]) -> str:
    if not timings:
        raise ValueError("At least one follow-up timing is required.")
    teeth = ", ".join(dict.fromkeys(item.tooth_fdi for item in timings))
    return (
        "Բարև։ Ձեր վերջին ատամնաբուժական հետազոտության հիման վրա խորհուրդ է տրվում "
        f"վերահսկիչ այց՝ {teeth} ատամների հատվածները կրկին գնահատելու համար։ "
        f"Առաջարկվող այցի ամսաթիվն է՝ {_date_text(timings[0])}։ "
        "Խնդրում ենք կապվել կլինիկայի հետ և ամրագրել հարմար ժամ։"
    )


async def _groq_intro(evidence: dict, fallback: str) -> str:
    settings = get_settings()
    if not settings.groq_api_key:
        return fallback
    system = (
        "You are not a dental diagnostic model. You do not analyze radiographs "
        "or perform clinical inference. Render one calm Eastern Armenian introductory "
        "sentence using only the supplied DENTAI evidence. "
        "Do not add diagnoses, treatment, urgency, certainty, scores, or dates. "
        "Return strict JSON with only the required intro field."
    )
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
        return intro if intro and len(intro) <= 400 else fallback
    except (httpx.HTTPError, KeyError, ValueError):
        return fallback


async def armenian_message(timing: FollowupTiming) -> str:
    fallback = deterministic_armenian_message(timing)
    intro = await _groq_intro(
        {
            "finding_type": timing.finding_type,
            "tooth_fdi": timing.tooth_fdi,
            "recommended_window": timing.recommended_window,
            "target_followup_at": timing.target_followup_at.isoformat(),
        },
        fallback,
    )
    if intro == fallback:
        return fallback
    return (
        f"{intro} Առաջարկվող այցի ամսաթիվն է՝ {_date_text(timing)}։ "
        "Խնդրում ենք կապվել կլինիկայի հետ և ամրագրել հարմար ժամ։"
    )


async def armenian_group_message(timings: list[FollowupTiming]) -> str:
    if not timings:
        raise ValueError("At least one follow-up timing is required.")
    fallback = deterministic_group_armenian_message(timings)
    intro = await _groq_intro(
        {
            "monitoring_items": [
                {
                    "finding_type": item.finding_type,
                    "tooth_fdi": item.tooth_fdi,
                    "recommended_window": item.recommended_window,
                }
                for item in timings
            ],
            "target_followup_at": timings[0].target_followup_at.isoformat(),
        },
        fallback,
    )
    if intro == fallback:
        return fallback
    return (
        f"{intro} Առաջարկվող այցի ամսաթիվն է՝ {_date_text(timings[0])}։ "
        "Խնդրում ենք կապվել կլինիկայի հետ և ամրագրել հարմար ժամ։"
    )
