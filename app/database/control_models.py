import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, utc_now


class ClinicRegistry(Base):
    __tablename__ = "clinic_registry"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    encrypted_database_url: Mapped[str] = mapped_column(Text)
    allowed_origins: Mapped[list] = mapped_column(JSON, default=list)
    feature_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    subscription_plan: Mapped[str] = mapped_column(String(40), default="TETA2_CARE")
    subscription_status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    subscription_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscription_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    renewal_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformAccessRequest(Base):
    __tablename__ = "platform_access_requests"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_name: Mapped[str] = mapped_column(String(200), index=True)
    requested_slug: Mapped[str] = mapped_column(String(80), index=True)
    country: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(String(300))
    website: Mapped[str | None] = mapped_column(String(300))
    director_name: Mapped[str] = mapped_column(String(200))
    work_email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str] = mapped_column(String(80))
    branch_count: Mapped[int] = mapped_column(Integer, default=1)
    dentist_count: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(String(40), default="TETA2_CARE")
    status: Mapped[str] = mapped_column(String(40), default="SUBMITTED", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text)
    payment_reference: Mapped[str | None] = mapped_column(String(300))
    payment_proof_note: Mapped[str | None] = mapped_column(Text)
    payment_instructions_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformBillingSettings(Base):
    __tablename__ = "platform_billing_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    plan_name: Mapped[str] = mapped_column(String(40), default="Teta2 Care")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(12), default="AMD")
    bank_name: Mapped[str] = mapped_column(String(200), default="")
    cardholder_name: Mapped[str] = mapped_column(String(200), default="")
    card_number: Mapped[str] = mapped_column(String(100), default="")
    payment_note: Mapped[str] = mapped_column(Text, default="")
    support_email: Mapped[str] = mapped_column(String(320), default="")
    login_url: Mapped[str] = mapped_column(String(500), default="https://www.teta2.com")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformAdminEvent(Base):
    __tablename__ = "platform_admin_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(120))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
