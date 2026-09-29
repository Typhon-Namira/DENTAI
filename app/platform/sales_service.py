import base64
import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.control_models import (
    AccessRequest,
    PlatformSubscriptionPayment,
    SalesClinicAttribution,
    SalesClinicContact,
    SalesCommission,
    SalesDailyReport,
    SalesManager,
    SalesManagerActivity,
    SalesManagerSession,
    SalesWithdrawal,
)

MANAGER_SESSION_HOURS = 12
SALES_COMMISSION_RATE_BPS = 3000


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits[-12:] if digits else None


def normalize_website(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().casefold()
    if "://" not in raw:
        raw = "https://" + raw
    try:
        parsed = urlparse(raw)
        host = (parsed.hostname or "").removeprefix("www.")
        return host or None
    except ValueError:
        return None


def generated_username(full_name: str, email: str) -> str:
    base = re.sub(r"[^a-z0-9]+", ".", full_name.casefold()).strip(".")
    if not base:
        base = email.split("@", 1)[0].casefold()
    return base[:60] or f"manager.{secrets.token_hex(2)}"


def generated_password(length: int = 18) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _bank_fernet() -> Fernet:
    secret = get_settings().app_secret
    key = base64.urlsafe_b64encode(hashlib.sha256(f"{secret}:sales-bank".encode()).digest())
    return Fernet(key)


def encrypt_bank_card(card_number: str) -> tuple[str, str]:
    digits = re.sub(r"\D", "", card_number)
    if len(digits) < 12 or len(digits) > 24:
        raise AppError("BANK_CARD_INVALID", "Enter a valid bank card or account number.", 422)
    return _bank_fernet().encrypt(digits.encode()).decode(), digits[-4:]


def decrypt_bank_card(ciphertext: str) -> str:
    return _bank_fernet().decrypt(ciphertext.encode()).decode()


def manager_public_payload(manager: SalesManager) -> dict:
    return {
        "id": str(manager.id),
        "full_name": manager.full_name,
        "title": manager.title,
        "email": manager.email,
        "phone": manager.phone,
        "territory": manager.territory,
        "bio": manager.bio,
        "photo_available": bool(manager.photo_storage_key),
        "verified": bool(manager.public_verified and manager.is_active and not manager.deleted_at),
    }


def manager_admin_payload(manager: SalesManager) -> dict:
    return {
        **manager_public_payload(manager),
        "username": manager.username,
        "is_active": manager.is_active,
        "public_verified": manager.public_verified,
        "commission_rate_bps": manager.commission_rate_bps,
        "bank_card_last4": manager.bank_card_last4,
        "bank_card_holder": manager.bank_card_holder,
        "bank_card_updated_at": manager.bank_card_updated_at,
        "last_login_at": manager.last_login_at,
        "created_at": manager.created_at,
        "updated_at": manager.updated_at,
        "deleted_at": manager.deleted_at,
    }


async def unique_manager_username(session: AsyncSession, full_name: str, email: str) -> str:
    base = generated_username(full_name, email)
    candidate = base
    suffix = 2
    while await session.scalar(select(SalesManager.id).where(SalesManager.username == candidate)):
        candidate = f"{base[:54]}.{suffix}"
        suffix += 1
    return candidate


async def create_manager_session(
    session: AsyncSession,
    manager: SalesManager,
    request: Request,
) -> str:
    now = datetime.now(UTC)
    token = secrets.token_urlsafe(48)
    client = request.client.host if request.client else None
    row = SalesManagerSession(
        manager_id=manager.id,
        token_hash=_token_hash(token),
        ip_address=client,
        user_agent=request.headers.get("user-agent", "")[:500] or None,
        login_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=MANAGER_SESSION_HOURS),
    )
    session.add(row)
    manager.last_login_at = now
    manager.updated_at = now
    await session.flush()
    session.add(
        SalesManagerActivity(
            manager_id=manager.id,
            session_id=row.id,
            action="LOGIN",
            details={},
            ip_address=client,
        )
    )
    return token


async def manager_from_token(
    session: AsyncSession,
    token: str,
    request: Request | None = None,
) -> tuple[SalesManager, SalesManagerSession]:
    if not token:
        raise AppError("MANAGER_AUTH_REQUIRED", "Manager authentication is required.", 401)
    now = datetime.now(UTC)
    row = await session.scalar(
        select(SalesManagerSession).where(SalesManagerSession.token_hash == _token_hash(token))
    )
    if not row or row.logout_at is not None or row.expires_at <= now:
        raise AppError("MANAGER_SESSION_INVALID", "Manager session is invalid or expired.", 401)
    manager = await session.get(SalesManager, row.manager_id)
    if not manager or not manager.is_active or manager.deleted_at is not None:
        raise AppError("MANAGER_ACCESS_DISABLED", "This manager account is disabled.", 403)
    row.last_seen_at = now
    if request:
        current_ip = request.client.host if request.client else None
        if current_ip and not row.ip_address:
            row.ip_address = current_ip
    return manager, row


async def log_manager_activity(
    session: AsyncSession,
    manager: SalesManager,
    *,
    action: str,
    details: dict | None = None,
    manager_session: SalesManagerSession | None = None,
    request: Request | None = None,
) -> None:
    session.add(
        SalesManagerActivity(
            manager_id=manager.id,
            session_id=manager_session.id if manager_session else None,
            action=action,
            details=details or {},
            ip_address=request.client.host if request and request.client else None,
        )
    )


def manager_credentials_email(manager: SalesManager, password: str) -> tuple[str, str]:
    subject = "Your Teta2 sales manager workspace is ready"
    body = (
        f"Hello {manager.full_name},\n\n"
        "A Teta2 sales manager account has been created for you.\n\n"
        f"Workspace: {get_settings().platform_public_url.rstrip('/')}/platform-managers\n"
        f"Username: {manager.username}\n"
        f"Temporary password: {password}\n\n"
        "Sign in and update your bank card details before requesting a payout. "
        "Keep these credentials private.\n\nTeta2"
    )
    return subject, body


def _score_contact(contact: SalesClinicContact, request: AccessRequest) -> tuple[int, dict]:
    score = 0
    signals: dict[str, bool] = {}
    request_email = normalize_text(request.email)
    request_phone = normalize_phone(request.phone)
    request_site = normalize_website(request.website)
    request_name = normalize_text(request.clinic_name)
    request_city = normalize_text(request.city)
    request_address = normalize_text(request.address)

    checks = (
        ("email", contact.email_norm, request_email, 50),
        ("phone", contact.phone_norm, request_phone, 45),
        ("website", contact.website_norm, request_site, 30),
        ("clinic_name", contact.clinic_name_norm, request_name, 30),
        ("city", contact.city_norm, request_city, 10),
        ("address", contact.address_norm, request_address, 15),
    )
    for name, left, right, weight in checks:
        matched = bool(left and right and left == right)
        signals[name] = matched
        if matched:
            score += weight
    return score, signals


async def find_sales_attribution_candidate(
    session: AsyncSession,
    request: AccessRequest,
) -> tuple[SalesClinicContact | None, int, dict, bool]:
    contacts = list(
        (
            await session.scalars(
                select(SalesClinicContact).order_by(SalesClinicContact.created_at.desc()).limit(2500)
            )
        ).all()
    )
    best_by_manager: dict[uuid.UUID, tuple[int, SalesClinicContact, dict]] = {}
    for contact in contacts:
        score, signals = _score_contact(contact, request)
        if not score:
            continue
        current = best_by_manager.get(contact.manager_id)
        if current is None or (score, contact.created_at) > (current[0], current[1].created_at):
            best_by_manager[contact.manager_id] = (score, contact, signals)
    scored = sorted(
        best_by_manager.values(),
        key=lambda item: (item[0], item[1].created_at),
        reverse=True,
    )
    if not scored:
        return None, 0, {}, False
    top_score, top_contact, top_signals = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else -1
    strong_identity = bool(top_signals.get("email") or top_signals.get("phone"))
    auto_confirm = top_score >= 60 and strong_identity and top_score > second_score
    return top_contact, top_score, top_signals, auto_confirm


async def ensure_attribution_for_payment(
    session: AsyncSession,
    request: AccessRequest,
    clinic_id: uuid.UUID,
) -> SalesClinicAttribution | None:
    existing = await session.scalar(
        select(SalesClinicAttribution).where(SalesClinicAttribution.clinic_id == clinic_id)
    )
    if existing:
        return existing
    contact, score, signals, auto_confirm = await find_sales_attribution_candidate(session, request)
    if not contact:
        return None
    attribution = SalesClinicAttribution(
        manager_id=contact.manager_id,
        clinic_id=clinic_id,
        access_request_id=request.id,
        clinic_contact_id=contact.id,
        match_score=score,
        matched_signals=signals,
        status="AUTO_CONFIRMED" if auto_confirm else "REVIEW_REQUIRED",
    )
    session.add(attribution)
    await session.flush()
    return attribution


async def available_balance(session: AsyncSession, manager_id: uuid.UUID) -> dict[str, int]:
    earned = (
        await session.execute(
            select(SalesCommission.currency, func.coalesce(func.sum(SalesCommission.commission_amount), 0))
            .where(SalesCommission.manager_id == manager_id)
            .group_by(SalesCommission.currency)
        )
    ).all()
    committed = (
        await session.execute(
            select(SalesWithdrawal.currency, func.coalesce(func.sum(SalesWithdrawal.amount), 0))
            .where(
                SalesWithdrawal.manager_id == manager_id,
                SalesWithdrawal.status.in_(["REQUESTED", "PAID"]),
            )
            .group_by(SalesWithdrawal.currency)
        )
    ).all()
    result = {str(currency): int(amount) for currency, amount in earned}
    for currency, amount in committed:
        result[str(currency)] = max(0, result.get(str(currency), 0) - int(amount))
    return result


async def manager_dashboard(session: AsyncSession, manager: SalesManager) -> dict:
    reports = int(
        await session.scalar(
            select(func.count()).select_from(SalesDailyReport).where(SalesDailyReport.manager_id == manager.id)
        )
        or 0
    )
    contacts = int(
        await session.scalar(
            select(func.count()).select_from(SalesClinicContact).where(SalesClinicContact.manager_id == manager.id)
        )
        or 0
    )
    attributed = int(
        await session.scalar(
            select(func.count()).select_from(SalesClinicAttribution).where(
                SalesClinicAttribution.manager_id == manager.id,
                SalesClinicAttribution.status.in_(["AUTO_CONFIRMED", "ADMIN_CONFIRMED"]),
            )
        )
        or 0
    )
    commissions = list(
        (
            await session.scalars(
                select(SalesCommission)
                .where(SalesCommission.manager_id == manager.id)
                .order_by(SalesCommission.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    withdrawals = list(
        (
            await session.scalars(
                select(SalesWithdrawal)
                .where(SalesWithdrawal.manager_id == manager.id)
                .order_by(SalesWithdrawal.requested_at.desc())
                .limit(100)
            )
        ).all()
    )
    return {
        "manager": manager_admin_payload(manager),
        "metrics": {
            "reports": reports,
            "clinic_contacts": contacts,
            "attributed_clinics": attributed,
        },
        "available_balance": await available_balance(session, manager.id),
        "commissions": [
            {
                "id": str(row.id),
                "clinic_id": str(row.clinic_id),
                "gross_amount": row.gross_amount,
                "commission_amount": row.commission_amount,
                "currency": row.currency,
                "rate_percent": row.rate_bps / 100,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in commissions
        ],
        "withdrawals": [
            {
                "id": str(row.id),
                "currency": row.currency,
                "amount": row.amount,
                "status": row.status,
                "bank_card_last4": row.bank_card_last4,
                "requested_at": row.requested_at,
                "processed_at": row.processed_at,
                "payment_reference": row.payment_reference,
                "admin_note": row.admin_note,
            }
            for row in withdrawals
        ],
    }


def report_contact_payload(contact: SalesClinicContact) -> dict:
    return {
        "id": str(contact.id),
        "clinic_name": contact.clinic_name,
        "country": contact.country,
        "city": contact.city,
        "address": contact.address,
        "website": contact.website,
        "contact_name": contact.contact_name,
        "contact_role": contact.contact_role,
        "email": contact.email,
        "phone": contact.phone,
        "negotiation_result": contact.negotiation_result,
        "outcome": contact.outcome,
        "next_step": contact.next_step,
        "follow_up_date": contact.follow_up_date,
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
    }


async def reports_payload(session: AsyncSession, manager_id: uuid.UUID) -> list[dict]:
    reports = list(
        (
            await session.scalars(
                select(SalesDailyReport)
                .where(SalesDailyReport.manager_id == manager_id)
                .order_by(SalesDailyReport.report_date.desc())
            )
        ).all()
    )
    result = []
    for report in reports:
        contacts = list(
            (
                await session.scalars(
                    select(SalesClinicContact)
                    .where(SalesClinicContact.report_id == report.id)
                    .order_by(SalesClinicContact.created_at.asc())
                )
            ).all()
        )
        result.append(
            {
                "id": str(report.id),
                "report_date": report.report_date,
                "summary": report.summary,
                "submitted_at": report.submitted_at,
                "updated_at": report.updated_at,
                "contacts": [report_contact_payload(contact) for contact in contacts],
            }
        )
    return result



async def create_commission_for_payment(
    session: AsyncSession,
    payment: PlatformSubscriptionPayment,
    attribution: SalesClinicAttribution,
) -> SalesCommission | None:
    if attribution.status not in {"AUTO_CONFIRMED", "ADMIN_CONFIRMED"}:
        return None
    existing = await session.scalar(
        select(SalesCommission).where(SalesCommission.payment_id == payment.id)
    )
    if existing:
        return existing
    manager = await session.get(SalesManager, attribution.manager_id)
    if not manager or manager.deleted_at is not None:
        return None
    rate_bps = SALES_COMMISSION_RATE_BPS
    amount = (payment.amount * rate_bps) // 10000
    commission = SalesCommission(
        manager_id=manager.id,
        clinic_id=payment.clinic_id,
        payment_id=payment.id,
        attribution_id=attribution.id,
        rate_bps=rate_bps,
        gross_amount=payment.amount,
        commission_amount=amount,
        currency=payment.currency,
        status="AVAILABLE",
    )
    session.add(commission)
    await session.flush()
    return commission


async def record_verified_subscription_payment(
    session: AsyncSession,
    request: AccessRequest,
    clinic_id: uuid.UUID,
    *,
    kind: str,
) -> tuple[PlatformSubscriptionPayment | None, SalesClinicAttribution | None, SalesCommission | None]:
    if request.payment_amount is None or not request.payment_currency:
        return None, None, None
    reference = (request.payment_reference or "").strip() or None
    if reference:
        existing = await session.scalar(
            select(PlatformSubscriptionPayment).where(
                PlatformSubscriptionPayment.clinic_id == clinic_id,
                PlatformSubscriptionPayment.reference == reference,
                PlatformSubscriptionPayment.amount == request.payment_amount,
                PlatformSubscriptionPayment.currency == request.payment_currency,
            )
        )
        if existing:
            attribution = await session.scalar(
                select(SalesClinicAttribution).where(SalesClinicAttribution.clinic_id == clinic_id)
            )
            commission = (
                await session.scalar(
                    select(SalesCommission).where(SalesCommission.payment_id == existing.id)
                )
                if attribution
                else None
            )
            return existing, attribution, commission
    payment = PlatformSubscriptionPayment(
        clinic_id=clinic_id,
        access_request_id=request.id,
        kind=kind,
        amount=int(request.payment_amount),
        currency=str(request.payment_currency).upper(),
        reference=reference,
        note=request.payment_proof_note,
        verified_at=request.payment_verified_at or datetime.now(UTC),
    )
    session.add(payment)
    await session.flush()
    attribution = await ensure_attribution_for_payment(session, request, clinic_id)
    commission = (
        await create_commission_for_payment(session, payment, attribution)
        if attribution is not None
        else None
    )
    return payment, attribution, commission


async def backfill_commissions_for_attribution(
    session: AsyncSession,
    attribution: SalesClinicAttribution,
) -> list[SalesCommission]:
    payments = list(
        (
            await session.scalars(
                select(PlatformSubscriptionPayment)
                .where(PlatformSubscriptionPayment.clinic_id == attribution.clinic_id)
                .order_by(PlatformSubscriptionPayment.verified_at.asc())
            )
        ).all()
    )
    created: list[SalesCommission] = []
    for payment in payments:
        commission = await create_commission_for_payment(session, payment, attribution)
        if commission:
            created.append(commission)
    return created
