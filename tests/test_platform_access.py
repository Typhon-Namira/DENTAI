from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.clinic_resolution.service import ClinicResolver
from app.core.errors import AppError
from app.database.base import Base
from app.database.control_models import AccessRequest, ClinicRegistry, PlatformCommercialConfig
from app.platform import service


async def control_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    control_tables = [
        table for table in Base.metadata.sorted_tables if table.info.get("plane") == "control"
    ]
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all, tables=control_tables)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def test_control_models_are_marked_for_control_plane():
    expected = {
        "clinic_registry",
        "platform_commercial_config",
        "platform_access_requests",
        "platform_subscription_terms",
        "platform_email_logs",
        "platform_admin_audit",
    }
    actual = {
        table.name for table in Base.metadata.sorted_tables if table.info.get("plane") == "control"
    }
    assert expected <= actual
    assert "patients" not in actual


def test_subscription_expiry_is_enforced_only_for_paid_tenants():
    resolver = ClinicResolver()
    legacy = ClinicRegistry(
        slug="legacy",
        name="Legacy",
        is_active=True,
        encrypted_database_url="plain:sqlite+aiosqlite:///legacy.db",
        subscription_enforced=False,
    )
    resolver._validate_access(legacy, enforce_subscription=True)

    expired = ClinicRegistry(
        slug="expired",
        name="Expired",
        is_active=True,
        encrypted_database_url="plain:sqlite+aiosqlite:///expired.db",
        subscription_enforced=True,
        access_expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    with pytest.raises(AppError) as caught:
        resolver._validate_access(expired, enforce_subscription=True)
    assert caught.value.code == "SUBSCRIPTION_EXPIRED"


@pytest.mark.asyncio
async def test_payment_email_freezes_quote_and_uses_single_care_plan(monkeypatch):
    engine, factory = await control_factory()
    monkeypatch.setattr(service.settings, "app_env", "test")
    try:
        async with factory() as session:
            session.add(
                PlatformCommercialConfig(
                    id=1,
                    plan_name="Teta2 Care",
                    price_amount=123456,
                    currency="AMD",
                    bank_name="Example Bank",
                    card_holder="Teta2",
                    card_number="0000 0000 0000 0000",
                )
            )
            request = AccessRequest(
                status="SUBMITTED",
                plan_name="Teta2 Care",
                clinic_name="Example Dental",
                country="Armenia",
                city="Yerevan",
                contact_name="Ani Dentist",
                contact_email="ani@example.com",
                contact_phone="+37400000000",
                preferred_language="en",
            )
            session.add(request)
            await session.flush()

            await service.send_payment_request(session, request)
            await session.flush()

            assert request.status == "PAYMENT_REQUEST_SENT"
            assert request.plan_name == "Teta2 Care"
            assert float(request.quoted_price_amount or 0) == 123456
            assert request.quoted_currency == "AMD"
            assert request.payment_reference and request.payment_reference.startswith("T2-")
    finally:
        await engine.dispose()


def test_admin_token_round_trip(monkeypatch):
    monkeypatch.setattr(service.settings, "app_secret", "test-platform-secret-that-is-long-enough")
    monkeypatch.setattr(service.settings, "platform_admin_token_minutes", 60)
    token = service.issue_admin_token("platform-admin")
    assert service.validate_admin_token(token) == "platform-admin"
