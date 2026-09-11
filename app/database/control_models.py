import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
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
    subscription_plan: Mapped[str | None] = mapped_column(String(40), nullable=True)
    subscription_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AccessRequest(Base):
    __tablename__ = "platform_access_requests"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_name: Mapped[str] = mapped_column(String(200), index=True)
    country: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(300))
    website: Mapped[str | None] = mapped_column(String(300))
    contact_name: Mapped[str] = mapped_column(String(160))
    contact_role: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), index=True)
    phone: Mapped[str] = mapped_column(String(50))
    dentists_count: Mapped[int] = mapped_column(Integer, default=1)
    branches_count: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="SUBMITTED", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text)
    payment_reference: Mapped[str | None] = mapped_column(String(200))
    payment_proof_note: Mapped[str | None] = mapped_column(Text)
    payment_instructions_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    payment_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_clinic_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformSettings(Base):
    __tablename__ = "platform_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    plan_name: Mapped[str] = mapped_column(String(80), default="Teta2 Care")
    subscription_days: Mapped[int] = mapped_column(Integer, default=30)
    price_amount: Mapped[int] = mapped_column(Integer, default=99000)
    price_currency: Mapped[str] = mapped_column(String(12), default="AMD")
    payment_recipient: Mapped[str] = mapped_column(String(200), default="Teta2")
    payment_card: Mapped[str] = mapped_column(String(100), default="")
    payment_bank_details: Mapped[str] = mapped_column(Text, default="")
    payment_email_subject: Mapped[str] = mapped_column(
        String(240), default="Teta2 Care access request — payment instructions"
    )
    payment_email_intro: Mapped[str] = mapped_column(
        Text,
        default=(
            "Your Teta2 Care access request has been approved. "
            "Please complete the subscription payment using the details below and reply to this email with your payment receipt."
        ),
    )
    activation_email_subject: Mapped[str] = mapped_column(
        String(240), default="Your Teta2 Care dashboard is ready"
    )
    activation_email_intro: Mapped[str] = mapped_column(
        Text,
        default=(
            "Your payment has been verified and your Teta2 Care dashboard has been activated for 30 days."
        ),
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformEmailLog(Base):
    __tablename__ = "platform_email_log"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    access_request_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)
    recipient: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class PlatformVisit(Base):
    __tablename__ = "platform_visits"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    path: Mapped[str] = mapped_column(String(300), index=True)
    method: Mapped[str] = mapped_column(String(12))
    status_code: Mapped[int] = mapped_column(Integer)
    visitor_hash: Mapped[str | None] = mapped_column(String(80), index=True)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
