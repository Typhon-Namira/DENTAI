"""Validate the configured SMTP transport without sending an email."""

import smtplib

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    required = {
        "SMTP_HOST": settings.smtp_host,
        "SMTP_USERNAME": settings.smtp_username,
        "SMTP_PASSWORD": settings.smtp_password,
        "SMTP_FROM_EMAIL": settings.smtp_from_email,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"SMTP configuration is incomplete: {', '.join(missing)}")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.ehlo()
        if settings.smtp_use_tls:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(settings.smtp_username, settings.smtp_password)
        code, _ = smtp.noop()
        if code >= 400:
            raise RuntimeError(f"SMTP NOOP failed with status {code}")

    print("SMTP preflight passed", flush=True)


if __name__ == "__main__":
    main()
