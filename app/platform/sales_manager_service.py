import base64
import hashlib
import re
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.control_models import (
    AccessRequest,
    SalesCommission,
    SalesDailyReport,
    SalesManager,
    SalesReferralAttribution,
    SalesReportClinic,
    SalesSubscriptionPayment,
    SalesWithdrawalRequest,
)

COMMISSION_RATE_BPS = 3000


def _fernet() -> Fernet:
    digest = hashlib.sha256((get_settings().app_secret + ":sales-financial-data").encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_bank_card(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_bank_card(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def normalize_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def normalize_email(value: str | None) -> str | None:
    normalized = (value or "").strip().casefold()
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D+", "", value or "")
    return digits[-12:] if digits else None


def normalize_website(value: str | None) -> str | None:
    raw = (value or "").strip().casefold()
    if not raw:
        return None
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").removeprefix("www.")
    return host or None


def commission_amount(payment_amount: int, rate_bps: int = COMMISSION_RATE_BPS) -> int:
    amount = (Decimal(payment_amount) * Decimal(rate_bps) / Decimal(10000)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    return int(amount)


async def manager_balances(session: AsyncSession, manager_id: uuid.UUID) -> list[dict]:
    commission_rows = (
        await session.execute(
            select(
                SalesCommission.currency,
                func.coalesce(func.sum(SalesCommission.commission_amount), 0),
            )
            .where(SalesCommission.manager_id == manager_id)
            .group_by(SalesCommission.currency)
        )
    ).all()
    pending_rows = (
        await session.execute(
            select(
                SalesWithdrawalRequest.currency,
                func.coalesce(func.sum(SalesWithdrawalRequest.amount), 0),
            )
            .where(
                SalesWithdrawalRequest.manager_id == manager_id,
                SalesWithdrawalRequest.status == "PENDING",
            )
            .group_by(SalesWithdrawalRequest.currency)
        )
    ).all()
    paid_rows = (
        await session.execute(
            select(
                SalesWithdrawalRequest.currency,
                func.coalesce(func.sum(SalesWithdrawalRequest.amount), 0),
            )
            .where(
                SalesWithdrawalRequest.manager_id == manager_id,
                SalesWithdrawalRequest.status == "PAID",
            )
            .group_by(SalesWithdrawalRequest.currency)
        )
    ).all()
    gross = {str(currency): int(amount) for currency, amount in commission_rows}
    pending = {str(currency): int(amount) for currency, amount in pending_rows}
    paid = {str(currency): int(amount) for currency, amount in paid_rows}
    currencies = sorted(set(gross) | set(pending) | set(paid))
    return [
        {
            "currency": currency,
            "earned": gross.get(currency, 0),
            "pending_withdrawal": pending.get(currency, 0),
            "paid_out": paid.get(currency, 0),
            "available": max(
                0,
                gross.get(currency, 0)
                - pending.get(currency, 0)
                - paid.get(currency, 0),
            ),
        }
        for currency in currencies
    ]


def _candidate_score(request: AccessRequest, entry: SalesReportClinic) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0
    req_email = normalize_email(request.email)
    req_phone = normalize_phone(request.phone)
    req_website = normalize_website(request.website)
    req_name = normalize_name(request.clinic_name)
    req_city = normalize_name(request.city)

    if req_email and entry.normalized_email and req_email == entry.normalized_email:
        score += 100
        reasons.append("email")
    if req_phone and entry.normalized_phone and req_phone == entry.normalized_phone:
        score += 100
        reasons.append("phone")
    if req_website and entry.normalized_website and req_website == entry.normalized_website:
        score += 90
        reasons.append("website")
    if req_name and req_name == entry.normalized_name:
        if req_city and req_city == normalize_name(entry.city):
            score += 80
            reasons.append("clinic_name_city")
        else:
            score += 50
            reasons.append("clinic_name")
    return score, reasons


async def ensure_referral_attribution(
    session: AsyncSession,
    request: AccessRequest,
    *,
    clinic_id: uuid.UUID | None = None,
) -> SalesReferralAttribution:
    existing = await session.scalar(
        select(SalesReferralAttribution).where(
            SalesReferralAttribution.access_request_id == request.id
        )
    )
    if existing:
        if clinic_id and not existing.clinic_id:
            existing.clinic_id = clinic_id
            existing.updated_at = datetime.now(UTC)
        return existing

    entries = list(
        (
            await session.scalars(
                select(SalesReportClinic)
                .join(SalesDailyReport, SalesDailyReport.id == SalesReportClinic.report_id)
                .join(SalesManager, SalesManager.id == SalesReportClinic.manager_id)
                .where(
                    SalesDailyReport.status == "SUBMITTED",
                    SalesManager.is_active.is_(True),
                )
                .order_by(SalesReportClinic.contacted_at.desc())
            )
        ).all()
    )

    scored: list[tuple[int, SalesReportClinic, list[str]]] = []
    for entry in entries:
        score, reasons = _candidate_score(request, entry)
        if score > 0:
            scored.append((score, entry, reasons))
    scored.sort(key=lambda item: item[0], reverse=True)

    now = datetime.now(UTC)
    attribution = SalesReferralAttribution(
        access_request_id=request.id,
        clinic_id=clinic_id,
        status="UNMATCHED",
        match_score=0,
        match_details={},
        created_at=now,
        updated_at=now,
    )

    if scored:
        top_score = scored[0][0]
        top = [item for item in scored if item[0] == top_score]
        manager_ids = {item[1].manager_id for item in top}
        best = top[0]
        attribution.match_score = top_score
        attribution.match_details = {
            "candidate_count": len(scored),
            "top_manager_count": len(manager_ids),
            "reasons": best[2],
        }
        if top_score >= 80 and len(manager_ids) == 1:
            attribution.status = "AUTO_MATCHED"
            attribution.manager_id = best[1].manager_id
            attribution.report_clinic_id = best[1].id
            attribution.match_method = "+".join(best[2])
            attribution.matched_at = now
        elif top_score >= 80:
            attribution.status = "AMBIGUOUS"
            attribution.match_method = "+".join(best[2])

    session.add(attribution)
    await session.flush()
    return attribution


async def create_commission_for_payment(
    session: AsyncSession,
    payment: SalesSubscriptionPayment,
    attribution: SalesReferralAttribution | None,
) -> SalesCommission | None:
    existing = await session.scalar(
        select(SalesCommission).where(SalesCommission.payment_id == payment.id)
    )
    if existing:
        return existing
    if not attribution or not attribution.manager_id or attribution.status not in {
        "AUTO_MATCHED",
        "ADMIN_CONFIRMED",
    }:
        return None
    commission = SalesCommission(
        manager_id=attribution.manager_id,
        payment_id=payment.id,
        attribution_id=attribution.id,
        clinic_id=payment.clinic_id,
        gross_amount=payment.amount,
        commission_rate_bps=COMMISSION_RATE_BPS,
        commission_amount=commission_amount(payment.amount),
        currency=payment.currency,
        status="AVAILABLE",
    )
    session.add(commission)
    await session.flush()
    return commission


async def record_initial_verified_payment(
    session: AsyncSession,
    request: AccessRequest,
    *,
    clinic_id: uuid.UUID,
    amount: int,
    currency: str,
    reference: str | None,
    subscription_days: int | None,
) -> tuple[SalesSubscriptionPayment, SalesReferralAttribution, SalesCommission | None]:
    existing_payment = await session.scalar(
        select(SalesSubscriptionPayment).where(
            SalesSubscriptionPayment.access_request_id == request.id
        )
    )
    attribution = await ensure_referral_attribution(session, request, clinic_id=clinic_id)
    if existing_payment:
        commission = await create_commission_for_payment(session, existing_payment, attribution)
        return existing_payment, attribution, commission

    payment = SalesSubscriptionPayment(
        clinic_id=clinic_id,
        access_request_id=request.id,
        kind="INITIAL",
        amount=amount,
        currency=currency.upper(),
        reference=reference,
        subscription_days=subscription_days,
        verified_at=request.payment_verified_at or datetime.now(UTC),
    )
    session.add(payment)
    await session.flush()
    commission = await create_commission_for_payment(session, payment, attribution)
    return payment, attribution, commission


async def confirm_attribution(
    session: AsyncSession,
    attribution: SalesReferralAttribution,
    *,
    manager_id: uuid.UUID,
    report_clinic_id: uuid.UUID | None = None,
) -> SalesCommission | None:
    now = datetime.now(UTC)
    attribution.manager_id = manager_id
    attribution.report_clinic_id = report_clinic_id or attribution.report_clinic_id
    attribution.status = "ADMIN_CONFIRMED"
    attribution.confirmed_at = now
    attribution.updated_at = now
    payment = await session.scalar(
        select(SalesSubscriptionPayment).where(
            SalesSubscriptionPayment.access_request_id == attribution.access_request_id
        )
    )
    return await create_commission_for_payment(session, payment, attribution) if payment else None
