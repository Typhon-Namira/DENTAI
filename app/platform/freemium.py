from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import AccessRequest, ClinicRegistry, PlatformSettings
from app.platform.service import provision_clinic, send_logged_email

FREE_TRIAL_HOURS = 24
PREMIUM_DAYS = 30


def free_credentials_email_body(
    request: AccessRequest,
    *,
    slug: str,
    username: str,
    password: str,
    expires_at: datetime,
) -> str:
    public_url = get_settings().platform_public_url.rstrip("/")
    return (
        f"Hello {request.contact_name},\n\n"
        "Your one-time Teta2 Free access is ready. You can start immediately.\n\n"
        f"Clinic: {request.clinic_name}\n"
        f"Free access expires: {expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n"
        "Free limits: 3 patients, 1 OPG per patient, and 1 tooth follow-up per OPG.\n\n"
        f"Login URL: {public_url}/login\n"
        f"Clinic slug: {slug}\n"
        f"Username: {username}\n"
        f"Temporary password: {password}\n\n"
        "When the Free period ends, your dashboard data and history are preserved. "
        "Upgrade the same clinic to Premium from Settings to continue for 30 days.\n\n"
        "Teta2"
    )


def premium_upgrade_email_body(request: AccessRequest, settings: PlatformSettings) -> str:
    card = settings.payment_card.strip() or "Not configured"
    bank = settings.payment_bank_details.strip() or "Not configured"
    return (
        f"Hello {request.contact_name},\n\n"
        "Your Teta2 Premium upgrade request has been received. Complete the payment below and "
        "reply to this email with your receipt. Your existing clinic workspace and history will remain unchanged.\n\n"
        f"Plan: Teta2 Premium\nAccess period after approval: {PREMIUM_DAYS} days\n"
        f"Price: {settings.price_amount:,} {settings.price_currency}\n"
        f"Recipient: {settings.payment_recipient}\n"
        f"Card / payment number: {card}\nBank details: {bank}\n\n"
        "After payment verification, Premium is activated on the same dashboard. Approval may take 1–6 hours.\n\n"
        "Teta2"
    )


def premium_activated_email_body(request: AccessRequest, expires_at: datetime) -> str:
    return (
        f"Hello {request.contact_name},\n\n"
        "Your payment has been verified and Teta2 Premium is now active on your existing dashboard.\n\n"
        f"Premium expires: {expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        "No clinic data was reset or moved. Your patients, OPG history, follow-up plans, conversations, "
        "appointments and settings remain in the same workspace.\n\nTeta2"
    )


async def reject_reused_free_trial(session: AsyncSession, request: AccessRequest) -> None:
    normalized_email = request.email.casefold().strip()
    normalized_phone = request.phone.strip()
    prior = await session.scalar(
        select(AccessRequest.id).where(
            AccessRequest.id != request.id,
            AccessRequest.activated_clinic_id.is_not(None),
            or_(
                AccessRequest.email == normalized_email,
                AccessRequest.phone == normalized_phone,
            ),
        )
    )
    if prior:
        raise AppError(
            "FREE_TRIAL_ALREADY_USED",
            "This clinic/contact has already used the one-time Free plan. Sign in to the existing clinic and upgrade to Premium.",
            409,
        )

    same_clinic = await session.scalar(
        select(AccessRequest.id).where(
            AccessRequest.id != request.id,
            AccessRequest.activated_clinic_id.is_not(None),
            AccessRequest.clinic_name == request.clinic_name,
            AccessRequest.country == request.country,
            AccessRequest.city == request.city,
        )
    )
    if same_clinic:
        raise AppError(
            "FREE_TRIAL_ALREADY_USED",
            "This clinic has already used its one-time Free plan. Use the existing dashboard to upgrade.",
            409,
        )


async def provision_free_trial(
    session: AsyncSession,
    *,
    request: AccessRequest,
    settings: PlatformSettings,
) -> tuple[ClinicRegistry, str, str, datetime]:
    await reject_reused_free_trial(session, request)
    clinic, username, password, _ = await provision_clinic(
        session,
        request=request,
        settings=settings,
    )
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=FREE_TRIAL_HOURS)
    clinic.subscription_plan = "FREE"
    clinic.subscription_state = "ACTIVE"
    clinic.subscription_starts_at = now
    clinic.subscription_expires_at = expires_at
    clinic.free_trial_started_at = now
    clinic.upgrade_requested_at = None
    clinic.feature_flags = {
        **dict(clinic.feature_flags or {}),
        "free_trial_used": True,
        "free_patient_limit": 3,
        "free_opg_per_patient_limit": 1,
        "free_followup_teeth_per_opg_limit": 1,
    }
    request.status = "FREE_ACTIVE"
    request.payment_verified_at = None
    request.updated_at = now
    return clinic, username, password, expires_at


async def request_premium_upgrade(
    session: AsyncSession,
    *,
    clinic: ClinicRegistry,
    settings: PlatformSettings,
) -> AccessRequest:
    if (clinic.subscription_plan or "").upper() in {"PREMIUM", "TETA2_CARE"}:
        raise AppError("PREMIUM_ALREADY_ACTIVE", "This clinic already has a paid plan.", 409)

    request = await session.scalar(
        select(AccessRequest)
        .where(AccessRequest.activated_clinic_id == clinic.id)
        .order_by(AccessRequest.created_at.desc())
        .limit(1)
    )
    if not request:
        raise AppError(
            "ACCESS_REQUEST_NOT_FOUND", "The original clinic application was not found.", 404
        )
    if clinic.subscription_state == "PAYMENT_REVIEW" or request.status == "PAYMENT_REVIEW":
        return request
    if not settings.payment_card.strip() and not settings.payment_bank_details.strip():
        raise AppError(
            "PAYMENT_DETAILS_REQUIRED",
            "Premium payment details are temporarily unavailable. Please contact Teta2 support.",
            503,
        )

    await send_logged_email(
        session,
        recipient=request.email,
        subject=settings.payment_email_subject,
        body=premium_upgrade_email_body(request, settings),
        kind="PREMIUM_UPGRADE_PAYMENT",
        access_request_id=request.id,
        clinic_id=clinic.id,
    )
    now = datetime.now(UTC)
    request.status = "PAYMENT_REVIEW"
    request.payment_instructions_sent_at = now
    request.updated_at = now
    clinic.subscription_state = "PAYMENT_REVIEW"
    clinic.upgrade_requested_at = now
    clinic.updated_at = now
    return request


async def activate_existing_premium(
    session: AsyncSession,
    *,
    request: AccessRequest,
    settings: PlatformSettings,
    reference: str | None,
    proof_note: str | None,
) -> tuple[ClinicRegistry, datetime]:
    if not request.activated_clinic_id:
        raise AppError("CLINIC_NOT_FOUND", "The Free clinic for this request was not found.", 404)
    clinic = await session.get(ClinicRegistry, request.activated_clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    if request.status == "ACTIVE" and (clinic.subscription_plan or "").upper() == "PREMIUM":
        expires = clinic.subscription_expires_at
        if expires is None:
            raise AppError("SUBSCRIPTION_STATE_INVALID", "Premium expiry is missing.", 409)
        return clinic, expires
    if request.status not in {"PAYMENT_REQUESTED", "PAYMENT_REVIEW"}:
        raise AppError(
            "ACCESS_REQUEST_STATE_INVALID",
            "The Premium upgrade must be awaiting payment review before activation.",
            409,
        )

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=PREMIUM_DAYS)
    original_database = clinic.encrypted_database_url
    clinic.subscription_plan = "PREMIUM"
    clinic.subscription_state = "ACTIVE"
    clinic.subscription_starts_at = now
    clinic.subscription_expires_at = expires_at
    clinic.upgrade_requested_at = None
    clinic.is_active = True
    clinic.updated_at = now
    clinic.encrypted_database_url = original_database
    request.status = "ACTIVE"
    request.payment_reference = reference or request.payment_reference
    request.payment_proof_note = proof_note or request.payment_proof_note
    request.payment_verified_at = now
    request.updated_at = now
    await send_logged_email(
        session,
        recipient=request.email,
        subject=settings.activation_email_subject,
        body=premium_activated_email_body(request, expires_at),
        kind="PREMIUM_ACTIVATED",
        access_request_id=request.id,
        clinic_id=clinic.id,
    )
    return clinic, expires_at
