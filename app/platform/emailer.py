import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import get_settings


@dataclass(frozen=True)
class EmailDelivery:
    sent: bool
    detail: str


def smtp_configured() -> bool:
    settings = get_settings()
    return bool(settings.smtp_host and settings.smtp_from_email)


def _send_sync(*, to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from_email:
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
        if settings.smtp_starttls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password or "")
        client.send_message(message)


async def deliver_email(*, to: str, subject: str, body: str) -> EmailDelivery:
    if not smtp_configured():
        return EmailDelivery(False, "SMTP_NOT_CONFIGURED")
    try:
        await asyncio.to_thread(_send_sync, to=to, subject=subject, body=body)
    except (OSError, smtplib.SMTPException) as exc:
        return EmailDelivery(False, f"SMTP_ERROR:{type(exc).__name__}")
    return EmailDelivery(True, "SENT")


def payment_instructions_email(
    *,
    clinic_name: str,
    director_name: str,
    price: str,
    currency: str,
    bank_name: str,
    cardholder_name: str,
    card_number: str,
    payment_note: str,
    request_id: str,
    support_email: str,
) -> tuple[str, str]:
    subject = "Teta2 Care access request — payment instructions"
    body = f"""Hello {director_name},

Your access request for {clinic_name} has passed the first review stage.

Teta2 Care is provided as one fixed 30-day subscription. After payment is verified, your clinic dashboard will be activated for 30 days. Renewal adds another 30 days without deleting or resetting your existing clinical data.

Subscription: Teta2 Care
Price: {price} {currency}
Bank: {bank_name or '—'}
Cardholder: {cardholder_name or '—'}
Card / payment number: {card_number or '—'}
Payment note: {payment_note or 'Please include your clinic name and request ID.'}
Request ID: {request_id}

After transferring the payment, reply to this email with the payment receipt and keep the Request ID in the subject or message. Payment verification is performed before access credentials are issued.

If you need assistance, contact {support_email or 'the Teta2 Care team'}.

Teta2 Care
Clinical follow-up platform
"""
    return subject, body


def credentials_email(
    *,
    clinic_name: str,
    clinic_slug: str,
    username: str,
    temporary_password: str,
    login_url: str,
    expires_at: str,
) -> tuple[str, str]:
    subject = "Teta2 Care dashboard access activated"
    body = f"""Hello,

Your Teta2 Care dashboard for {clinic_name} is now active for 30 days.

Login URL: {login_url}
Clinic ID / slug: {clinic_slug}
Username: {username}
Temporary password: {temporary_password}
Access valid until: {expires_at}

Please store these credentials securely. Your clinic data remains preserved when the subscription expires; renewing the subscription extends access by another 30 days without deleting previous records.

Teta2 Care
Clinical follow-up platform
"""
    return subject, body


def renewal_email(
    *, clinic_name: str, login_url: str, expires_at: str
) -> tuple[str, str]:
    subject = "Teta2 Care subscription renewed"
    body = f"""Hello,

The Teta2 Care subscription for {clinic_name} has been renewed for another 30 days.

Dashboard: {login_url}
Access valid until: {expires_at}

All existing clinic, patient, imaging, follow-up, conversation and appointment data remains unchanged.

Teta2 Care
Clinical follow-up platform
"""
    return subject, body
