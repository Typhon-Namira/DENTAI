from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin, utc_now


class RadarSource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "radar_sources"

    platform: Mapped[str] = mapped_column(String(24), index=True)
    external_source_id: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(300))
    handle: Mapped[str | None] = mapped_column(String(300))
    source_url: Mapped[str] = mapped_column(String(1000))
    language_hints: Mapped[list] = mapped_column(JSON, default=list)
    location_hint: Mapped[str | None] = mapped_column(String(160))
    armenia_relevance: Mapped[float] = mapped_column(Float, default=50.0)
    engagement_score: Mapped[float] = mapped_column(Float, default=50.0)
    dental_signal_probability: Mapped[float] = mapped_column(Float, default=50.0)
    source_score: Mapped[int] = mapped_column(Integer, default=50)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    monitoring_interval_minutes: Mapped[int] = mapped_column(Integer, default=45)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_content_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    __table_args__ = (UniqueConstraint("platform", "external_source_id"),)


class RadarOpportunity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "radar_opportunities"

    platform: Mapped[str] = mapped_column(String(24), index=True)
    person_key: Mapped[str] = mapped_column(String(64), index=True)
    author_display: Mapped[str | None] = mapped_column(String(300))
    author_profile_url: Mapped[str | None] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(20), default="unknown", index=True)
    location: Mapped[str | None] = mapped_column(String(160), index=True)
    treatment: Mapped[str | None] = mapped_column(String(80), index=True)
    intent: Mapped[str] = mapped_column(String(80), index=True)
    urgency: Mapped[str] = mapped_column(String(30), index=True)
    opportunity_score: Mapped[int] = mapped_column(Integer, index=True)
    tier: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(30), default="NEW", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    signal_count: Mapped[int] = mapped_column(Integer, default=1)
    explanation: Mapped[str] = mapped_column(Text)
    evidence_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    scoring_rule_set: Mapped[str] = mapped_column(String(100))
    scoring_rule_version: Mapped[str] = mapped_column(String(40))

    __table_args__ = (UniqueConstraint("platform", "person_key"),)


class RadarSignal(UUIDMixin, Base):
    __tablename__ = "radar_signals"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("radar_sources.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("radar_opportunities.id", ondelete="SET NULL"), index=True
    )
    platform: Mapped[str] = mapped_column(String(24), index=True)
    external_signal_id: Mapped[str | None] = mapped_column(String(400))
    dedupe_key: Mapped[str] = mapped_column(String(64))
    signal_type: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    context_text: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1500))
    author_display: Mapped[str | None] = mapped_column(String(300))
    person_key: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(20), index=True)
    location: Mapped[str | None] = mapped_column(String(160), index=True)
    treatment: Mapped[str | None] = mapped_column(String(80), index=True)
    intent: Mapped[str] = mapped_column(String(80), index=True)
    urgency_label: Mapped[str] = mapped_column(String(30), index=True)
    dental_relevance: Mapped[float] = mapped_column(Float)
    treatment_intent: Mapped[float] = mapped_column(Float)
    location_match: Mapped[float] = mapped_column(Float)
    urgency_score: Mapped[float] = mapped_column(Float)
    recency_score: Mapped[float] = mapped_column(Float)
    recommendation_intent: Mapped[float] = mapped_column(Float)
    classifier_confidence: Mapped[float] = mapped_column(Float)
    opportunity_score: Mapped[int] = mapped_column(Integer, index=True)
    tier: Mapped[str] = mapped_column(String(20), index=True)
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (UniqueConstraint("source_id", "dedupe_key"),)
