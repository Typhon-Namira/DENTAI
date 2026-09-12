import uuid
from typing import Any

import jwt

from app.core.config import get_settings
from app.core.errors import AppError

BOOKING_TOKEN_KIND = "teta2_booking"
BOOKING_TOKEN_VERSION = 1


def booking_token(
    *,
    clinic_id: uuid.UUID,
    branch_id: uuid.UUID,
    doctor_id: uuid.UUID | None = None,
    patient_id: uuid.UUID | None = None,
    care_plan_id: uuid.UUID | None = None,
    care_plan_item_id: uuid.UUID | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> str:
    """Create a stable, signed booking token.

    The token deliberately has no expiry: the clinic's master booking link is intended
    to remain stable. It contains UUIDs only, never patient names, phone numbers or
    other direct identifiers. Patient-specific follow-up links are also tamper-proof.
    """
    payload: dict[str, Any] = {
        "type": BOOKING_TOKEN_KIND,
        "v": BOOKING_TOKEN_VERSION,
        "clinic_id": str(clinic_id),
        "branch_id": str(branch_id),
    }
    if doctor_id:
        payload["doctor_id"] = str(doctor_id)
    if patient_id:
        payload["patient_id"] = str(patient_id)
    if care_plan_id:
        payload["care_plan_id"] = str(care_plan_id)
    if care_plan_item_id:
        payload["care_plan_item_id"] = str(care_plan_item_id)
    if window_start:
        payload["window_start"] = window_start
    if window_end:
        payload["window_end"] = window_end
    return jwt.encode(payload, get_settings().app_secret, algorithm="HS256")


def decode_booking_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, get_settings().app_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError("BOOKING_LINK_INVALID", "This booking link is invalid.", 404) from exc
    if payload.get("type") != BOOKING_TOKEN_KIND or payload.get("v") != BOOKING_TOKEN_VERSION:
        raise AppError("BOOKING_LINK_INVALID", "This booking link is invalid.", 404)
    for key in ("clinic_id", "branch_id"):
        try:
            uuid.UUID(str(payload.get(key) or ""))
        except (ValueError, TypeError) as exc:
            raise AppError("BOOKING_LINK_INVALID", "This booking link is invalid.", 404) from exc
    return payload


def booking_url(**kwargs: Any) -> str:
    base = get_settings().platform_public_url.rstrip("/")
    return f"{base}/book/{booking_token(**kwargs)}"


def booking_message_suffix(language: str, url: str) -> str:
    if language == "hy":
        return f"Ամրագրեք ստուգման հարմար ժամը այստեղ՝ {url}"
    if language == "ru":
        return f"Выберите удобное время для осмотра здесь: {url}"
    return f"Choose a convenient check-up time here: {url}"
