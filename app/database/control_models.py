import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
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
    subscription_state: Mapped[str] = mapped_column(String(40), default="ACTIVE", index=True)
    subscription_source: Mapped[str] = mapped_column(String(24), default="LEGACY", index=True)
    subscription_starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    free_trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    upgrade_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gift_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gift_note: Mapped[str | None] = mapped_column(Text)
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
    payment_amount: Mapped[int | None] = mapped_column(Integer)
    payment_currency: Mapped[str | None] = mapped_column(String(12))
    payment_instructions_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
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


class PlatformAdminAudit(Base):
    __tablename__ = "platform_admin_audit"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(60), index=True)
    target_id: Mapped[str | None] = mapped_column(String(100), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class SalesManager(Base):
    __tablename__ = "platform_sales_managers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(120), default="Sales Manager")
    phone: Mapped[str | None] = mapped_column(String(50))
    photo_storage_key: Mapped[str | None] = mapped_column(String(500))
    photo_mime: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=1)
    encrypted_bank_card: Mapped[str | None] = mapped_column(Text)
    bank_card_last4: Mapped[str | None] = mapped_column(String(4))
    bank_account_holder: Mapped[str | None] = mapped_column(String(160))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_logout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SalesManagerSession(Base):
    __tablename__ = "platform_sales_manager_sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(String(500))


class SalesDailyReport(Base):
    __tablename__ = "platform_sales_daily_reports"
    __table_args__ = (
        UniqueConstraint("manager_id", "report_date", name="uq_sales_report_manager_date"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), index=True
    )
    report_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SalesReportClinic(Base):
    __tablename__ = "platform_sales_report_clinics"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_daily_reports.id", ondelete="CASCADE"), index=True
    )
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), index=True
    )
    clinic_name: Mapped[str] = mapped_column(String(200), index=True)
    country: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str | None] = mapped_column(String(300))
    website: Mapped[str | None] = mapped_column(String(300))
    contact_name: Mapped[str | None] = mapped_column(String(160))
    contact_role: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    negotiation_result: Mapped[str] = mapped_column(Text)
    outcome_status: Mapped[str] = mapped_column(String(40), default="CONTACTED", index=True)
    next_step: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    contacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    normalized_name: Mapped[str] = mapped_column(String(220), index=True)
    normalized_email: Mapped[str | None] = mapped_column(String(320), index=True)
    normalized_phone: Mapped[str | None] = mapped_column(String(60), index=True)
    normalized_website: Mapped[str | None] = mapped_column(String(240), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SalesManagerActivity(Base):
    __tablename__ = "platform_sales_manager_activity"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_sales_manager_sessions.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(60), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_hash: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class SalesReferralAttribution(Base):
    __tablename__ = "platform_sales_referral_attributions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    access_request_id: Mapped[uuid.UUID] = mapped_column(unique=True, index=True)
    clinic_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="SET NULL"), index=True
    )
    report_clinic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_sales_report_clinics.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="UNMATCHED", index=True)
    match_method: Mapped[str | None] = mapped_column(String(80))
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    match_details: Mapped[dict] = mapped_column(JSON, default=dict)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SalesSubscriptionPayment(Base):
    __tablename__ = "platform_sales_subscription_payments"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(index=True)
    access_request_id: Mapped[uuid.UUID | None] = mapped_column(unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(24), default="INITIAL", index=True)
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(12), index=True)
    reference: Mapped[str | None] = mapped_column(String(200))
    subscription_days: Mapped[int | None] = mapped_column(Integer)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SalesCommission(Base):
    __tablename__ = "platform_sales_commissions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="RESTRICT"), index=True
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_subscription_payments.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
    )
    attribution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_sales_referral_attributions.id", ondelete="SET NULL"), index=True
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(index=True)
    gross_amount: Mapped[int] = mapped_column(Integer)
    commission_rate_bps: Mapped[int] = mapped_column(Integer, default=3000)
    commission_amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(12), index=True)
    status: Mapped[str] = mapped_column(String(24), default="AVAILABLE", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class SalesWithdrawalRequest(Base):
    __tablename__ = "platform_sales_withdrawals"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(12), index=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    bank_card_last4: Mapped[str] = mapped_column(String(4))
    encrypted_bank_card_snapshot: Mapped[str] = mapped_column(Text)
    bank_account_holder: Mapped[str | None] = mapped_column(String(160))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    paid_reference: Mapped[str | None] = mapped_column(String(200))
    admin_note: Mapped[str | None] = mapped_column(Text)


class SalesGrowthIdea(Base):
    __tablename__ = "platform_sales_growth_ideas"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    expected_impact: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SalesScoreEvent(Base):
    __tablename__ = "platform_sales_score_events"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            "category",
            name="uq_sales_score_event_source_category",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="RESTRICT"), index=True
    )
    category: Mapped[str] = mapped_column(String(32), index=True)
    points: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )


class SalesEquityAward(Base):
    __tablename__ = "platform_sales_equity_awards"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    award_key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    manager_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_sales_managers.id", ondelete="RESTRICT"), index=True
    )
    points_at_award: Mapped[int] = mapped_column(Integer, default=1000)
    equity_percent_bps: Mapped[int] = mapped_column(Integer, default=300)
    status: Mapped[str] = mapped_column(String(32), default="PENDING_ADMIN_REVIEW", index=True)
    reached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    admin_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
