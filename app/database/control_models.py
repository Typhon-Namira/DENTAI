import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, utc_now

CONTROL_TABLE_INFO = {"info": {"plane": "control"}}


class ClinicRegistry(Base):
    __tablename__ = "clinic_registry"
    __table_args__ = CONTROL_TABLE_INFO

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    encrypted_database_url: Mapped[str] = mapped_column(Text)
    allowed_origins: Mapped[list] = mapped_column(JSON, default=list)
    feature_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    subscription_enforced: Mapped[bool] = mapped_column(Boolean, default=False)
    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformCommercialConfig(Base):
    __tablename__ = "platform_commercial_config"
    __table_args__ = CONTROL_TABLE_INFO

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    plan_name: Mapped[str] = mapped_column(String(80), default="Teta2 Care")
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=99000)
    currency: Mapped[str] = mapped_column(String(12), default="AMD")
    bank_name: Mapped[str | None] = mapped_column(String(160))
    card_holder: Mapped[str | None] = mapped_column(String(200))
    card_number: Mapped[str | None] = mapped_column(String(64))
    payment_instructions: Mapped[str | None] = mapped_column(Text)
    support_email: Mapped[str | None] = mapped_column(String(320))
    sender_name: Mapped[str] = mapped_column(String(120), default="Teta2 Care")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AccessRequest(Base):
    __tablename__ = "platform_access_requests"
    __table_args__ = CONTROL_TABLE_INFO

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(40), default="SUBMITTED", index=True)
    plan_name: Mapped[str] = mapped_column(String(80), default="Teta2 Care")
    clinic_name: Mapped[str] = mapped_column(String(200))
    legal_name: Mapped[str | None] = mapped_column(String(240))
    country: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(500))
    contact_name: Mapped[str] = mapped_column(String(200))
    contact_role: Mapped[str | None] = mapped_column(String(160))
    contact_email: Mapped[str] = mapped_column(String(320), index=True)
    contact_phone: Mapped[str] = mapped_column(String(50))
    dentist_count: Mapped[int | None] = mapped_column(Integer)
    monthly_patient_volume: Mapped[int | None] = mapped_column(Integer)
    preferred_language: Mapped[str] = mapped_column(String(16), default="en")
    notes: Mapped[str | None] = mapped_column(Text)

    quoted_price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    quoted_currency: Mapped[str | None] = mapped_column(String(12))
    payment_reference: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    payment_notes: Mapped[str | None] = mapped_column(Text)
    receipt_reference: Mapped[str | None] = mapped_column(String(500))
    review_note: Mapped[str | None] = mapped_column(Text)

    payment_email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clinic_registry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinic_registry.id", ondelete="SET NULL"), index=True
    )
    issued_username: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SubscriptionTerm(Base):
    __tablename__ = "platform_subscription_terms"
    __table_args__ = CONTROL_TABLE_INFO

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clinic_registry.id", ondelete="CASCADE"), index=True
    )
    access_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_access_requests.id", ondelete="SET NULL"), index=True
    )
    plan_name: Mapped[str] = mapped_column(String(80), default="Teta2 Care")
    price_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(12))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    kind: Mapped[str] = mapped_column(String(30), default="INITIAL")
    payment_reference: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PlatformEmailLog(Base):
    __tablename__ = "platform_email_logs"
    __table_args__ = CONTROL_TABLE_INFO

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    access_request_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_access_requests.id", ondelete="SET NULL"), index=True
    )
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clinic_registry.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[str] = mapped_column(String(60), index=True)
    recipient: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)
    safe_error: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformAdminAudit(Base):
    __tablename__ = "platform_admin_audit"
    __table_args__ = CONTROL_TABLE_INFO

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(100), index=True)
    access_request_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
