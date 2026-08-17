import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin, utc_now


class Role(StrEnum):
    DIRECTOR = "DIRECTOR"
    MANAGER = "MANAGER"
    DOCTOR = "DOCTOR"


class AIStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewStatus(StrEnum):
    UNREVIEWED = "UNREVIEWED"
    REVIEWED = "REVIEWED"


class FindingReview(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class WhatsAppOutreachStatus(StrEnum):
    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    CLAIMED = "CLAIMED"
    SENDING = "SENDING"
    SEND_UNKNOWN = "SEND_UNKNOWN"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Branch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "branches"
    name: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    token_version: Mapped[int] = mapped_column(Integer, default=1)


class UserBranchScope(UUIDMixin, Base):
    __tablename__ = "user_branch_scopes"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), index=True
    )
    __table_args__ = (UniqueConstraint("user_id", "branch_id"),)


class ManagerProfile(UUIDMixin, Base):
    __tablename__ = "manager_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    operational_notes: Mapped[str | None] = mapped_column(Text)


class DoctorProfile(UUIDMixin, Base):
    __tablename__ = "doctor_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    specialty: Mapped[str] = mapped_column(String(160))
    license_identifier: Mapped[str | None] = mapped_column(String(120))
    professional_title: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(40))
    operational_notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Patient(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "patients"
    patient_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(30))
    phone: Mapped[str | None] = mapped_column(String(40))
    whatsapp_phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(320))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class PatientDoctorAssignment(UUIDMixin, Base):
    __tablename__ = "patient_doctor_assignments"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Visit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "visits"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str] = mapped_column(Text)
    clinical_notes: Mapped[str | None] = mapped_column(Text)


class XRay(UUIDMixin, Base):
    __tablename__ = "xrays"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE")
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AIAnalysis(UUIDMixin, Base):
    __tablename__ = "ai_analyses"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    xray_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("xrays.id"))
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[AIStatus] = mapped_column(Enum(AIStatus), default=AIStatus.QUEUED, index=True)
    provider: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(50))
    analysis_schema_version: Mapped[str] = mapped_column(String(40), default="legacy-1.0")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    worker_id: Mapped[str | None] = mapped_column(String(160))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    structured_result: Mapped[dict | None] = mapped_column(JSON)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.UNREVIEWED
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DentalFinding(UUIDMixin, Base):
    __tablename__ = "dental_findings"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_analyses.id"))
    tooth_code: Mapped[str | None] = mapped_column(String(20))
    finding_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    review_status: Mapped[FindingReview] = mapped_column(
        Enum(FindingReview), default=FindingReview.PENDING
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WhatsAppOutreach(UUIDMixin, Base):
    __tablename__ = "whatsapp_outreach"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_analyses.id"), index=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("dental_findings.id"))
    source_finding_ids: Mapped[list] = mapped_column(JSON, default=list)
    followup_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("followups.id"))
    tooth_fdi: Mapped[str] = mapped_column(String(20))
    finding_type: Mapped[str] = mapped_column(String(500))
    recommended_window: Mapped[str] = mapped_column(String(80))
    target_followup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    message: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), default="hy-AM")
    status: Mapped[WhatsAppOutreachStatus] = mapped_column(
        Enum(WhatsAppOutreachStatus), default=WhatsAppOutreachStatus.SCHEDULED, index=True
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    timing_reason: Mapped[str] = mapped_column(Text)
    timing_policy_rule_id: Mapped[str] = mapped_column(String(500))
    timing_policy_version: Mapped[str] = mapped_column(String(40))
    clinic_timezone: Mapped[str] = mapped_column(String(80), default="Asia/Yerevan")
    include_image: Mapped[bool] = mapped_column(Boolean, default=False)
    safe_error: Mapped[str | None] = mapped_column(String(120))
    worker_id: Mapped[str | None] = mapped_column(String(160))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatch_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ToothRecord(UUIDMixin, Base):
    __tablename__ = "tooth_records"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    tooth_code: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    __table_args__ = (UniqueConstraint("patient_id", "tooth_code"),)


class FutureRiskProfile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "future_risk_profiles"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    generated_from_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ai_analyses.id")
    )
    risk_items: Mapped[list] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(20))
    doctor_review_status: Mapped[str] = mapped_column(String(30), default="PENDING")


class CareTimelineItem(UUIDMixin, Base):
    __tablename__ = "care_timeline_items"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(60))
    recommended_date: Mapped[date | None] = mapped_column(Date)
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(20))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FollowUp(UUIDMixin, Base):
    __tablename__ = "followups"
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    priority: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Package(UUIDMixin, Base):
    __tablename__ = "packages"
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    analysis_limit: Mapped[int | None] = mapped_column(Integer)
    storage_limit: Mapped[int | None] = mapped_column(BigInteger)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Usage(UUIDMixin, Base):
    __tablename__ = "usage"
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    ai_analyses_used: Mapped[int] = mapped_column(Integer, default=0)
    storage_bytes_used: Mapped[int] = mapped_column(BigInteger, default=0)


class PurchaseSubscription(UUIDMixin, Base):
    __tablename__ = "purchase_subscriptions"
    package_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("packages.id"))
    status: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshSession(UUIDMixin, Base):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("branches.id"))
    audit_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
