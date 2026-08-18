from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.radar.engine import (
    RadarClassification,
    classify_signal,
    content_dedupe_key,
    person_fingerprint,
    source_rank,
)
from app.radar.models import RadarOpportunity, RadarSignal, RadarSource

PLATFORMS = {"INSTAGRAM", "FACEBOOK", "TELEGRAM", "WEB"}
SOURCE_TYPES = {
    "PAGE",
    "PROFILE",
    "GROUP",
    "CHANNEL",
    "COMMUNITY",
    "POST_FEED",
    "WEB_SOURCE",
}
OPPORTUNITY_STATUSES = {"NEW", "REVIEWED", "ARCHIVED"}


@dataclass(frozen=True)
class IngestResult:
    signal: RadarSignal
    opportunity: RadarOpportunity | None
    duplicate: bool


def normalize_platform(value: str) -> str:
    platform = value.strip().upper()
    if platform not in PLATFORMS:
        raise AppError("RADAR_PLATFORM_INVALID", f"Unsupported Radar platform: {platform}", 422)
    return platform


def normalize_source_type(value: str) -> str:
    source_type = value.strip().upper()
    if source_type not in SOURCE_TYPES:
        raise AppError("RADAR_SOURCE_TYPE_INVALID", "Unsupported Radar source type.", 422)
    return source_type


def opportunity_explanation(classification: RadarClassification) -> str:
    parts: list[str] = []
    if classification.treatment:
        parts.append(classification.treatment.replace("_", " ").title())
    if classification.intent != "UNRELATED":
        parts.append(classification.intent.replace("_", " ").title())
    if classification.location:
        parts.append(classification.location)
    if classification.urgency_label in {"HIGH", "VERY_HIGH"}:
        parts.append(f"{classification.urgency_label.replace('_', ' ').title()} urgency")
    if not parts:
        parts.append("Dental relevance signal")
    return " · ".join(parts)


async def create_source(
    db: AsyncSession,
    *,
    platform: str,
    external_source_id: str,
    source_type: str,
    name: str,
    source_url: str,
    handle: str | None,
    language_hints: list[str],
    location_hint: str | None,
    armenia_relevance: float,
    engagement_score: float,
    dental_signal_probability: float,
    source_metadata: dict[str, Any],
) -> RadarSource:
    normalized_platform = normalize_platform(platform)
    normalized_type = normalize_source_type(source_type)
    existing = await db.scalar(
        select(RadarSource).where(
            RadarSource.platform == normalized_platform,
            RadarSource.external_source_id == external_source_id.strip(),
        )
    )
    if existing:
        raise AppError("RADAR_SOURCE_EXISTS", "This Radar source is already registered.", 409)

    score, priority, interval = source_rank(
        armenia_relevance,
        engagement_score,
        dental_signal_probability,
    )
    now = datetime.now(UTC)
    source = RadarSource(
        platform=normalized_platform,
        external_source_id=external_source_id.strip(),
        source_type=normalized_type,
        name=name.strip(),
        handle=handle.strip() if handle else None,
        source_url=source_url.strip(),
        language_hints=[item.strip().lower() for item in language_hints if item.strip()],
        location_hint=location_hint.strip() if location_hint else None,
        armenia_relevance=max(0.0, min(100.0, armenia_relevance)),
        engagement_score=max(0.0, min(100.0, engagement_score)),
        dental_signal_probability=max(0.0, min(100.0, dental_signal_probability)),
        source_score=score,
        priority=priority,
        monitoring_interval_minutes=interval,
        next_check_at=now,
        source_metadata=source_metadata,
    )
    db.add(source)
    await db.flush()
    return source


async def update_source(
    db: AsyncSession,
    source: RadarSource,
    *,
    is_active: bool | None = None,
    armenia_relevance: float | None = None,
    engagement_score: float | None = None,
    dental_signal_probability: float | None = None,
) -> RadarSource:
    if is_active is not None:
        source.is_active = is_active
    if armenia_relevance is not None:
        source.armenia_relevance = max(0.0, min(100.0, armenia_relevance))
    if engagement_score is not None:
        source.engagement_score = max(0.0, min(100.0, engagement_score))
    if dental_signal_probability is not None:
        source.dental_signal_probability = max(0.0, min(100.0, dental_signal_probability))

    score, priority, interval = source_rank(
        source.armenia_relevance,
        source.engagement_score,
        source.dental_signal_probability,
        active=source.is_active,
    )
    source.source_score = score
    source.priority = priority
    source.monitoring_interval_minutes = interval
    source.next_check_at = datetime.now(UTC) + timedelta(minutes=interval)
    await db.flush()
    return source


async def ingest_signal(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    source: RadarSource,
    external_signal_id: str | None,
    signal_type: str,
    text: str,
    context_text: str | None,
    source_url: str,
    author_external_id: str | None,
    author_display: str | None,
    author_profile_url: str | None,
    observed_at: datetime,
    published_at: datetime | None,
) -> IngestResult:
    if not source.is_active:
        raise AppError("RADAR_SOURCE_INACTIVE", "Radar source is inactive.", 409)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=UTC)
    if published_at is not None and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)

    dedupe_key = content_dedupe_key(
        source.platform,
        source.external_source_id,
        author_external_id,
        external_signal_id,
        text,
    )
    existing = await db.scalar(
        select(RadarSignal).where(
            RadarSignal.source_id == source.id,
            RadarSignal.dedupe_key == dedupe_key,
        )
    )
    if existing:
        opportunity = None
        if existing.opportunity_id:
            opportunity = await db.get(RadarOpportunity, existing.opportunity_id)
        return IngestResult(existing, opportunity, True)

    classification = classify_signal(
        text,
        context_text=context_text,
        observed_at=observed_at,
        published_at=published_at,
    )
    if author_external_id:
        person_key = person_fingerprint(str(clinic_id), source.platform, author_external_id)
    else:
        person_key = f"anonymous:{dedupe_key[:54]}"

    opportunity: RadarOpportunity | None = None
    if classification.candidate:
        opportunity = await db.scalar(
            select(RadarOpportunity).where(
                RadarOpportunity.platform == source.platform,
                RadarOpportunity.person_key == person_key,
            )
        )
        explanation = opportunity_explanation(classification)
        if opportunity is None:
            opportunity = RadarOpportunity(
                platform=source.platform,
                person_key=person_key,
                author_display=author_display.strip() if author_display else None,
                author_profile_url=author_profile_url.strip() if author_profile_url else None,
                language=classification.language,
                location=classification.location,
                treatment=classification.treatment,
                intent=classification.intent,
                urgency=classification.urgency_label,
                opportunity_score=classification.opportunity_score,
                tier=classification.tier,
                status="NEW",
                first_seen_at=published_at or observed_at,
                last_seen_at=published_at or observed_at,
                signal_count=1,
                explanation=explanation,
                evidence_summary={
                    "latest_source_id": str(source.id),
                    "latest_url": source_url,
                    "score_components": classification.evidence.get("components", {}),
                },
                scoring_rule_set=classification.rule_set,
                scoring_rule_version=classification.rule_version,
            )
            db.add(opportunity)
            await db.flush()
        else:
            opportunity.signal_count += 1
            opportunity.last_seen_at = max(
                opportunity.last_seen_at,
                published_at or observed_at,
            )
            if classification.opportunity_score >= opportunity.opportunity_score:
                opportunity.opportunity_score = classification.opportunity_score
                opportunity.tier = classification.tier
                opportunity.language = classification.language
                opportunity.location = classification.location or opportunity.location
                opportunity.treatment = classification.treatment or opportunity.treatment
                opportunity.intent = classification.intent
                opportunity.urgency = classification.urgency_label
                opportunity.explanation = explanation
                opportunity.evidence_summary = {
                    "latest_source_id": str(source.id),
                    "latest_url": source_url,
                    "score_components": classification.evidence.get("components", {}),
                }
            if author_display and not opportunity.author_display:
                opportunity.author_display = author_display.strip()
            if author_profile_url and not opportunity.author_profile_url:
                opportunity.author_profile_url = author_profile_url.strip()

    signal = RadarSignal(
        source_id=source.id,
        opportunity_id=opportunity.id if opportunity else None,
        platform=source.platform,
        external_signal_id=external_signal_id.strip() if external_signal_id else None,
        dedupe_key=dedupe_key,
        signal_type=signal_type.strip().upper(),
        text=text.strip(),
        context_text=context_text.strip() if context_text else None,
        source_url=source_url.strip(),
        author_display=author_display.strip() if author_display else None,
        person_key=person_key,
        language=classification.language,
        location=classification.location,
        treatment=classification.treatment,
        intent=classification.intent,
        urgency_label=classification.urgency_label,
        dental_relevance=classification.dental_relevance,
        treatment_intent=classification.treatment_intent,
        location_match=classification.location_match,
        urgency_score=classification.urgency,
        recency_score=classification.recency,
        recommendation_intent=classification.recommendation_intent,
        classifier_confidence=classification.classifier_confidence,
        opportunity_score=classification.opportunity_score,
        tier=classification.tier,
        is_candidate=classification.candidate,
        evidence={
            **classification.evidence,
            "rule_set": classification.rule_set,
            "rule_version": classification.rule_version,
        },
        observed_at=observed_at,
        published_at=published_at,
    )
    db.add(signal)

    _, source.priority, source.monitoring_interval_minutes = source_rank(
        source.armenia_relevance,
        source.engagement_score,
        source.dental_signal_probability,
        active=True,
        new_content=True,
    )
    source.last_content_at = published_at or observed_at
    source.last_polled_at = observed_at
    source.next_check_at = observed_at + timedelta(minutes=source.monitoring_interval_minutes)
    await db.flush()
    return IngestResult(signal, opportunity, False)


async def dashboard_summary(db: AsyncSession) -> dict[str, Any]:
    tier_rows = (
        await db.execute(
            select(RadarOpportunity.tier, func.count(RadarOpportunity.id))
            .where(RadarOpportunity.status != "ARCHIVED")
            .group_by(RadarOpportunity.tier)
        )
    ).all()
    counts = {tier: int(count) for tier, count in tier_rows}
    active_sources = int(
        await db.scalar(
            select(func.count(RadarSource.id)).where(RadarSource.is_active.is_(True))
        )
        or 0
    )
    now = datetime.now(UTC)
    start = now - timedelta(days=1)
    new_signals = int(
        await db.scalar(select(func.count(RadarSignal.id)).where(RadarSignal.observed_at >= start))
        or 0
    )
    opportunities_24h = int(
        await db.scalar(
            select(func.count(RadarOpportunity.id)).where(RadarOpportunity.created_at >= start)
        )
        or 0
    )
    return {
        "hot": counts.get("HOT", 0),
        "warm": counts.get("WARM", 0),
        "research": counts.get("RESEARCH", 0),
        "ignored": counts.get("IGNORE", 0),
        "sources_monitored": active_sources,
        "new_signals_24h": new_signals,
        "new_opportunities_24h": opportunities_24h,
        "generated_at": now,
    }


async def list_opportunities(
    db: AsyncSession,
    *,
    tier: str | None,
    platform: str | None,
    language: str | None,
    location: str | None,
    treatment: str | None,
    status: str | None,
    min_score: int,
    limit: int,
    offset: int,
) -> tuple[list[RadarOpportunity], int]:
    filters = [RadarOpportunity.opportunity_score >= min_score]
    if tier:
        filters.append(RadarOpportunity.tier == tier.strip().upper())
    if platform:
        filters.append(RadarOpportunity.platform == normalize_platform(platform))
    if language:
        filters.append(RadarOpportunity.language == language.strip().lower())
    if location:
        filters.append(RadarOpportunity.location == location.strip())
    if treatment:
        filters.append(RadarOpportunity.treatment == treatment.strip().upper())
    if status:
        normalized_status = status.strip().upper()
        if normalized_status not in OPPORTUNITY_STATUSES:
            raise AppError("RADAR_STATUS_INVALID", "Unsupported opportunity status.", 422)
        filters.append(RadarOpportunity.status == normalized_status)

    total = int(
        await db.scalar(select(func.count(RadarOpportunity.id)).where(and_(*filters))) or 0
    )
    rows = (
        await db.scalars(
            select(RadarOpportunity)
            .where(and_(*filters))
            .order_by(
                RadarOpportunity.opportunity_score.desc(),
                RadarOpportunity.last_seen_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return list(rows), total


async def opportunity_signals(
    db: AsyncSession,
    opportunity_id: uuid.UUID,
    *,
    limit: int = 100,
) -> tuple[RadarOpportunity, list[RadarSignal]]:
    opportunity = await db.get(RadarOpportunity, opportunity_id)
    if not opportunity:
        raise AppError("RADAR_OPPORTUNITY_NOT_FOUND", "Patient opportunity was not found.", 404)
    signals = (
        await db.scalars(
            select(RadarSignal)
            .where(RadarSignal.opportunity_id == opportunity_id)
            .order_by(RadarSignal.published_at.asc(), RadarSignal.observed_at.asc())
            .limit(limit)
        )
    ).all()
    return opportunity, list(signals)


async def due_sources(db: AsyncSession, *, limit: int = 50) -> list[RadarSource]:
    now = datetime.now(UTC)
    return list(
        (
            await db.scalars(
                select(RadarSource)
                .where(
                    RadarSource.is_active.is_(True),
                    or_(RadarSource.next_check_at.is_(None), RadarSource.next_check_at <= now),
                )
                .order_by(RadarSource.priority.asc(), RadarSource.next_check_at.asc())
                .limit(limit)
            )
        ).all()
    )
