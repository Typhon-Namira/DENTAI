import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinic_resolution.service import ResolvedClinic
from app.core.errors import AppError
from app.database.models import Patient, XRay

FREE_PATIENT_LIMIT = 3
FREE_OPG_PER_PATIENT_LIMIT = 1
FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT = 1


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def subscription_state(clinic: ResolvedClinic, *, now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    configured = (clinic.subscription_state or "ACTIVE").upper()
    if configured in {"PAYMENT_REVIEW", "UPGRADE_PENDING"}:
        return "PAYMENT_REVIEW"
    expires = _utc(clinic.subscription_expires_at)
    if expires is not None and expires <= current:
        return "FREE_EXPIRED" if (clinic.subscription_plan or "").upper() == "FREE" else "EXPIRED"
    return "ACTIVE"


def is_free(clinic: ResolvedClinic) -> bool:
    return (clinic.subscription_plan or "").upper() == "FREE"


def seconds_remaining(clinic: ResolvedClinic, *, now: datetime | None = None) -> int | None:
    expires = _utc(clinic.subscription_expires_at)
    if expires is None:
        return None
    return max(0, int((expires - (now or datetime.now(UTC))).total_seconds()))


def require_product_access(clinic: ResolvedClinic) -> None:
    state = subscription_state(clinic)
    if state == "ACTIVE":
        return
    if state == "PAYMENT_REVIEW":
        raise AppError(
            "SUBSCRIPTION_PAYMENT_REVIEW",
            "Your Premium activation is waiting for payment approval. Existing clinic data is preserved.",
            403,
        )
    raise AppError(
        "SUBSCRIPTION_EXPIRED",
        "Your Teta2 access period has ended. Existing clinic data is preserved; activate Premium to continue.",
        403,
    )


async def enforce_free_patient_limit(session: AsyncSession, clinic: ResolvedClinic) -> None:
    if not is_free(clinic):
        return
    total = int(await session.scalar(select(func.count()).select_from(Patient)) or 0)
    if total >= FREE_PATIENT_LIMIT:
        raise AppError(
            "FREE_PATIENT_LIMIT_REACHED",
            f"The Free plan supports up to {FREE_PATIENT_LIMIT} patients. Upgrade to Premium to continue.",
            403,
        )


async def enforce_free_opg_limit(
    session: AsyncSession, clinic: ResolvedClinic, patient_id: uuid.UUID
) -> None:
    if not is_free(clinic):
        return
    total = int(
        await session.scalar(
            select(func.count()).select_from(XRay).where(XRay.patient_id == patient_id)
        )
        or 0
    )
    if total >= FREE_OPG_PER_PATIENT_LIMIT:
        raise AppError(
            "FREE_OPG_LIMIT_REACHED",
            "The Free plan supports one OPG per patient. Upgrade to Premium to continue.",
            403,
        )


def entitlement_payload(clinic: ResolvedClinic) -> dict:
    free = is_free(clinic)
    return {
        "patient_limit": FREE_PATIENT_LIMIT if free else None,
        "opg_per_patient_limit": FREE_OPG_PER_PATIENT_LIMIT if free else None,
        "followup_teeth_per_opg_limit": FREE_FOLLOWUP_TEETH_PER_OPG_LIMIT if free else None,
    }
