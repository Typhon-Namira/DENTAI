import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.database.control_models import AccessRequest
from app.database.sessions import control_session
from app.platform.api import require_platform_admin
from app.platform.service import platform_settings, send_logged_email

router = APIRouter(prefix="/platform/market", tags=["platform-market"])

FUNDING_LIMIT = 50
MARKETS = {
    "AM": {
        "name": "Armenia",
        "currency": "AMD",
        "standard_price": 49000,
        "funding_price": 39000,
        "payment_subject": "Teta2 clinic access — Armenia payment instructions",
    },
    "RU": {
        "name": "Russia",
        "currency": "RUB",
        "standard_price": 14000,
        "funding_price": 11400,
        "payment_subject": "Teta2 — инструкция по оплате для клиники в России",
    },
}


class MarketPaymentDecision(BaseModel):
    note: str | None = Field(default=None, max_length=4000)


def _normalized(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().replace("-", " ").split())


def market_code(
    country: str | None, city: str | None = None, address: str | None = None
) -> str | None:
    country_value = _normalized(country)
    armenia = {"am", "armenia", "republic of armenia", "հայաստան", "армения"}
    russia = {"ru", "russia", "russian federation", "россия", "российская федерация"}
    if country_value in armenia:
        return "AM"
    if country_value in russia:
        return "RU"

    # Country is the primary routing signal. The location fallback exists for
    # older requests whose country field was entered inconsistently.
    location = " ".join((_normalized(city), _normalized(address)))
    if any(
        token in location
        for token in (
            "yerevan",
            "երեւան",
            "երևան",
            "armenia",
            "հայաստան",
            "ереван",
            "армения",
        )
    ):
        return "AM"
    if any(
        token in location
        for token in (
            "russia",
            "россия",
            "moscow",
            "москва",
            "saint petersburg",
            "санкт петербург",
        )
    ):
        return "RU"
    return None


def _market_for_request(row: AccessRequest) -> str | None:
    return market_code(row.country, row.city, row.address)


async def _funding_position(session: AsyncSession, row: AccessRequest, market: str) -> int:
    sent_rows = list(
        (
            await session.scalars(
                select(AccessRequest)
                .where(AccessRequest.payment_instructions_sent_at.is_not(None))
                .order_by(
                    AccessRequest.payment_instructions_sent_at.asc(),
                    AccessRequest.created_at.asc(),
                )
            )
        ).all()
    )
    market_rows = [candidate for candidate in sent_rows if _market_for_request(candidate) == market]
    if row.payment_instructions_sent_at is not None:
        for index, candidate in enumerate(market_rows, start=1):
            if candidate.id == row.id:
                return index
    return len(market_rows) + 1


def _format_price(amount: int, currency: str) -> str:
    return f"{amount:,} {currency}"


def _email_body(
    row: AccessRequest,
    *,
    market: str,
    tier: str,
    amount: int,
    currency: str,
    recipient: str,
    payment_card: str,
    bank_details: str,
) -> str:
    card = payment_card.strip() or "Not configured"
    bank = bank_details.strip() or "Not configured"
    if market == "RU":
        tier_text = "Funding Plan — для первых 50 клиник" if tier == "FUNDING" else "Standard"
        return (
            f"Здравствуйте, {row.contact_name}!\n\n"
            "Ваша заявка на доступ к Teta2 одобрена для российского рынка. "
            "Ниже указана цена, автоматически выбранная по стране, указанной в заявке.\n\n"
            f"Клиника: {row.clinic_name}\n"
            "Рынок: Россия\n"
            f"Тариф: {tier_text}\n"
            "Период доступа: 30 дней\n"
            f"Стоимость: {_format_price(amount, currency)} / месяц\n"
            f"Получатель: {recipient}\n"
            f"Карта / номер платежа: {card}\n"
            f"Банковские реквизиты: {bank}\n\n"
            "После оплаты ответьте на это письмо и приложите подтверждение платежа. "
            "Клиника будет активирована только после проверки платежа администратором.\n\n"
            "Teta2"
        )

    tier_text = "Funding Plan — first 50 clinics" if tier == "FUNDING" else "Standard"
    return (
        f"Hello {row.contact_name},\n\n"
        "Your Teta2 clinic access request has been approved for the Armenia market. "
        "The price below was selected automatically from the country recorded in your application.\n\n"
        f"Clinic: {row.clinic_name}\n"
        "Market: Armenia\n"
        f"Pricing: {tier_text}\n"
        "Access period: 30 days\n"
        f"Price: {_format_price(amount, currency)} / month\n"
        f"Recipient: {recipient}\n"
        f"Card / payment number: {card}\n"
        f"Bank details: {bank}\n\n"
        "After payment, reply to this email with the payment receipt. "
        "Your clinic will only be activated after an administrator verifies the payment.\n\n"
        "Teta2"
    )


@router.get("/plans")
async def market_plans():
    return {
        "name": "Teta2",
        "period_days": 30,
        "funding_limit": FUNDING_LIMIT,
        "markets": MARKETS,
    }


@router.post(
    "/admin/access-requests/{request_id}/send-payment",
    dependencies=[Depends(require_platform_admin)],
)
async def send_market_payment_instructions(
    request_id: uuid.UUID,
    body: MarketPaymentDecision,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if row.status not in {"SUBMITTED", "PAYMENT_REQUESTED", "PAYMENT_REVIEW"}:
        raise AppError(
            "ACCESS_REQUEST_STATE_INVALID",
            "Payment instructions cannot be sent in this state.",
            409,
        )

    market = _market_for_request(row)
    if market not in MARKETS:
        raise AppError(
            "ACCESS_REQUEST_MARKET_UNSUPPORTED",
            "The clinic country could not be mapped to Armenia or Russia. Correct the request country before sending a payment email.",
            409,
        )

    settings = await platform_settings(session)
    if not settings.payment_card.strip() and not settings.payment_bank_details.strip():
        raise AppError(
            "PAYMENT_DETAILS_REQUIRED",
            "Configure payment details before sending payment instructions.",
            409,
        )

    position = await _funding_position(session, row, market)
    tier = "FUNDING" if position <= FUNDING_LIMIT else "STANDARD"
    config = MARKETS[market]
    amount = int(config["funding_price"] if tier == "FUNDING" else config["standard_price"])
    currency = str(config["currency"])
    subject = str(config["payment_subject"])

    await send_logged_email(
        session,
        recipient=row.email,
        subject=subject,
        body=_email_body(
            row,
            market=market,
            tier=tier,
            amount=amount,
            currency=currency,
            recipient=settings.payment_recipient,
            payment_card=settings.payment_card,
            bank_details=settings.payment_bank_details,
        ),
        kind=f"PAYMENT_INSTRUCTIONS_{market}_{tier}",
        access_request_id=row.id,
    )
    now = datetime.now(UTC)
    row.status = "PAYMENT_REQUESTED"
    row.admin_note = body.note or row.admin_note
    row.payment_instructions_sent_at = now
    row.updated_at = now
    await session.commit()
    return {
        "id": str(row.id),
        "status": row.status,
        "market": market,
        "market_name": config["name"],
        "pricing_tier": tier,
        "funding_position": position,
        "funding_limit": FUNDING_LIMIT,
        "price_amount": amount,
        "price_currency": currency,
        "email_subject": subject,
    }
