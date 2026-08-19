from zoneinfo import ZoneInfo

from app.outreach.timing import FollowupTiming


def _date_text(timing: FollowupTiming) -> str:
    local = timing.target_followup_at.astimezone(ZoneInfo(timing.clinic_timezone))
    return local.strftime("%d.%m.%Y")


def _armenian_ordinal(tooth_fdi: str) -> str:
    return f"{tooth_fdi}-րդ"


def deterministic_armenian_message(timing: FollowupTiming) -> str:
    return (
        "Բարև Ձեզ։ Ձեր վերջին ատամնաբուժական հետազոտության հիման վրա խորհուրդ է տրվում "
        f"վերահսկիչ այց՝ {_armenian_ordinal(timing.tooth_fdi)} ատամի հատվածը կրկին գնահատելու համար։ "
        f"Առաջարկվող այցի ամսաթիվն է՝ {_date_text(timing)}թ.։ "
        "Խնդրում ենք կապվել կլինիկայի հետ և ամրագրել հարմար ժամ։"
    )


def deterministic_group_armenian_message(timings: list[FollowupTiming]) -> str:
    if not timings:
        raise ValueError("At least one follow-up timing is required.")
    teeth = ", ".join(
        _armenian_ordinal(tooth_fdi)
        for tooth_fdi in dict.fromkeys(item.tooth_fdi for item in timings)
    )
    return (
        "Բարև Ձեզ։ Ձեր վերջին ատամնաբուժական հետազոտության հիման վրա խորհուրդ է տրվում "
        f"վերահսկիչ այց՝ {teeth} ատամների հատվածները կրկին գնահատելու համար։ "
        f"Առաջարկվող այցի ամսաթիվն է՝ {_date_text(timings[0])}թ.։ "
        "Խնդրում ենք կապվել կլինիկայի հետ և ամրագրել հարմար ժամ։"
    )


async def armenian_message(timing: FollowupTiming) -> str:
    """Return the approved native Armenian patient outreach template.

    The wording is intentionally deterministic so Groq cannot make patient-facing
    Armenian sound translated or robotic. Only the evidence-bound tooth number and
    scheduled follow-up date are inserted dynamically.
    """
    return deterministic_armenian_message(timing)


async def armenian_group_message(timings: list[FollowupTiming]) -> str:
    """Return the approved native Armenian template for grouped follow-ups."""
    return deterministic_group_armenian_message(timings)
