import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin, utc_now


class ClinicCareSettings(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "clinic_care_settings"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"), unique=True, index=True
    )
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Yerevan")
    working_days: Mapped[list] = mapped_column(JSON, default=lambda: [0, 1, 2, 3, 4, 5])
    day_start: Mapped[str] = mapped_column(String(5), default="09:00")
    day_end: Mapped[str] = mapped_column(String(5), default="18:00")
    appointment_minutes: Mapped[int] = mapped_column(Integer, default=30)
    slot_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    min_booking_notice_minutes: Mapped[int] = mapped_column(Integer, default=60)
    booking_horizon_days: Mapped[int] = mapped_column(Integer, default=30)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=0)
    preferred_times: Mapped[list] = mapped_column(JSON, default=list)
    blocked_windows: Mapped[list] = mapped_column(JSON, default=list)
    auto_followup_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_outreach_after_review: Mapped[bool] = mapped_column(Boolean, default=True)
    attach_tooth_image: Mapped[bool] = mapped_column(Boolean, default=True)
    default_language: Mapped[str] = mapped_column(String(16), default="en")
    booking_instructions: Mapped[str | None] = mapped_column(Text)


class CarePlan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "care_plans"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_analyses.id", ondelete="CASCADE"), unique=True, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="READY_FOR_REVIEW", index=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    summary: Mapped[str | None] = mapped_column(Text)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CarePlanItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "care_plan_items"

    care_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_plans.id", ondelete="CASCADE"), index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dental_findings.id", ondelete="CASCADE"), unique=True, index=True
    )
    tooth_fdi: Mapped[str] = mapped_column(String(20), index=True)
    finding_type: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float | None]
    recommended_window: Mapped[str] = mapped_column(String(80))
    target_followup_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(40), default="AWAITING_REVIEW", index=True)
    rationale: Mapped[str] = mapped_column(Text)
    message_preview: Mapped[str | None] = mapped_column(Text)
    appointment_required: Mapped[bool] = mapped_column(Boolean, default=True)
    image_required: Mapped[bool] = mapped_column(Boolean, default=True)


class CareConversation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "care_conversations"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    care_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("care_plans.id", ondelete="SET NULL"), index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    whatsapp_phone: Mapped[str] = mapped_column(String(40), index=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    booking_context: Mapped[dict] = mapped_column(JSON, default=dict)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class CareConversationMessage(UUIDMixin, Base):
    __tablename__ = "care_conversation_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("care_conversations.id", ondelete="CASCADE"), index=True
    )
    care_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("care_plan_items.id", ondelete="SET NULL"), index=True
    )
    direction: Mapped[str] = mapped_column(String(16), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="WHATSAPP")
    body: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(16), default="en")
    status: Mapped[str] = mapped_column(String(32), default="RECORDED", index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(200), index=True)
    message_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class CareAppointment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "care_appointments"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"), index=True)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), index=True)
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("care_conversations.id", ondelete="SET NULL"), index=True
    )
    care_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("care_plan_items.id", ondelete="SET NULL"), index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(80), default="Asia/Yerevan")
    status: Mapped[str] = mapped_column(String(40), default="PROPOSED", index=True)
    source: Mapped[str] = mapped_column(String(20), default="AI")
    tooth_fdi: Mapped[str | None] = mapped_column(String(20))
    finding_type: Mapped[str | None] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    doctor_note: Mapped[str | None] = mapped_column(Text)
    patient_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reschedule_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("branch_id", "starts_at", "patient_id", name="uq_care_appointment_patient_slot"),
    )
