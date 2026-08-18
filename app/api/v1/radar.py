from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import select

from app.auth.dependencies import AuthContext, current_context, roles
from app.core.errors import AppError
from app.database.models import Role
from app.radar.engine import classify_signal, source_rank
from app.radar.models import RadarOpportunity, RadarSignal, RadarSource
from app.radar.service import (
    OPPORTUNITY_STATUSES,
    create_source,
    dashboard_summary,
    due_sources,
    ingest_signal,
    list_opportunities,
    opportunity_signals,
    update_source,
)

router = APIRouter(prefix="/radar", tags=["patient-radar"])


class RadarSourceCreate(BaseModel):
    platform: str
    external_source_id: str = Field(min_length=1, max_length=300)
    source_type: str
    name: str = Field(min_length=1, max_length=300)
    handle: str | None = Field(default=None, max_length=300)
    source_url: HttpUrl
    language_hints: list[str] = Field(default_factory=list, max_length=8)
    location_hint: str | None = Field(default=None, max_length=160)
    armenia_relevance: float = Field(default=50, ge=0, le=100)
    engagement_score: float = Field(default=50, ge=0, le=100)
    dental_signal_probability: float = Field(default=50, ge=0, le=100)
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class RadarSourcePatch(BaseModel):
    is_active: bool | None = None
    armenia_relevance: float | None = Field(default=None, ge=0, le=100)
    engagement_score: float | None = Field(default=None, ge=0, le=100)
    dental_signal_probability: float | None = Field(default=None, ge=0, le=100)


class RadarSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    external_source_id: str
    source_type: str
    name: str
    handle: str | None
    source_url: str
    language_hints: list
    location_hint: str | None
    armenia_relevance: float
    engagement_score: float
    dental_signal_probability: float
    source_score: int
    priority: str
    monitoring_interval_minutes: int
    is_active: bool
    last_polled_at: datetime | None
    last_content_at: datetime | None
    next_check_at: datetime | None
    source_metadata: dict
    created_at: datetime
    updated_at: datetime


class RadarSignalIn(BaseModel):
    external_signal_id: str | None = Field(default=None, max_length=400)
    signal_type: str = Field(default="COMMENT", min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=20_000)
    context_text: str | None = Field(default=None, max_length=30_000)
    source_url: HttpUrl
    author_external_id: str | None = Field(default=None, max_length=500)
    author_display: str | None = Field(default=None, max_length=300)
    author_profile_url: HttpUrl | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None


class RadarBatchIngest(BaseModel):
    source_id: uuid.UUID
    signals: list[RadarSignalIn] = Field(min_length=1, max_length=500)


class RadarSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    opportunity_id: uuid.UUID | None
    platform: str
    external_signal_id: str | None
    signal_type: str
    text: str
    context_text: str | None
    source_url: str
    author_display: str | None
    language: str
    location: str | None
    treatment: str | None
    intent: str
    urgency_label: str
    dental_relevance: float
    treatment_intent: float
    location_match: float
    urgency_score: float
    recency_score: float
    recommendation_intent: float
    classifier_confidence: float
    opportunity_score: int
    tier: str
    is_candidate: bool
    evidence: dict
    observed_at: datetime
    published_at: datetime | None


class RadarOpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    author_display: str | None
    author_profile_url: str | None
    language: str
    location: str | None
    treatment: str | None
    intent: str
    urgency: str
    opportunity_score: int
    tier: str
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    signal_count: int
    explanation: str
    evidence_summary: dict
    scoring_rule_set: str
    scoring_rule_version: str
    created_at: datetime
    updated_at: datetime


class RadarOpportunityPage(BaseModel):
    items: list[RadarOpportunityOut]
    total: int
    limit: int
    offset: int


class RadarOpportunityDetail(BaseModel):
    opportunity: RadarOpportunityOut
    signals: list[RadarSignalOut]


class RadarOpportunityStatusPatch(BaseModel):
    status: str


class RadarDashboardOut(BaseModel):
    hot: int
    warm: int
    research: int
    ignored: int
    sources_monitored: int
    new_signals_24h: int
    new_opportunities_24h: int
    generated_at: datetime


class RadarPreviewIn(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    context_text: str | None = Field(default=None, max_length=30_000)
    published_at: datetime | None = None


class RadarIngestItemOut(BaseModel):
    duplicate: bool
    signal: RadarSignalOut
    opportunity: RadarOpportunityOut | None


@router.get("/dashboard", response_model=RadarDashboardOut)
async def radar_dashboard(
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    return await dashboard_summary(ctx.session)


@router.get("/sources", response_model=list[RadarSourceOut])
async def radar_sources(
    ctx: Annotated[AuthContext, Depends(current_context)],
    active: bool | None = None,
    platform: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
):
    query = select(RadarSource)
    if active is not None:
        query = query.where(RadarSource.is_active.is_(active))
    if platform:
        query = query.where(RadarSource.platform == platform.strip().upper())
    query = query.order_by(RadarSource.source_score.desc(), RadarSource.name.asc()).limit(limit)
    return list((await ctx.session.scalars(query)).all())


@router.post("/sources", response_model=RadarSourceOut, status_code=201)
async def radar_source_create(
    payload: RadarSourceCreate,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    source = await create_source(
        ctx.session,
        platform=payload.platform,
        external_source_id=payload.external_source_id,
        source_type=payload.source_type,
        name=payload.name,
        source_url=str(payload.source_url),
        handle=payload.handle,
        language_hints=payload.language_hints,
        location_hint=payload.location_hint,
        armenia_relevance=payload.armenia_relevance,
        engagement_score=payload.engagement_score,
        dental_signal_probability=payload.dental_signal_probability,
        source_metadata=payload.source_metadata,
    )
    await ctx.session.commit()
    await ctx.session.refresh(source)
    return source


@router.patch("/sources/{source_id}", response_model=RadarSourceOut)
async def radar_source_patch(
    source_id: uuid.UUID,
    payload: RadarSourcePatch,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    source = await ctx.session.get(RadarSource, source_id)
    if not source:
        raise AppError("RADAR_SOURCE_NOT_FOUND", "Radar source was not found.", 404)
    await update_source(
        ctx.session,
        source,
        is_active=payload.is_active,
        armenia_relevance=payload.armenia_relevance,
        engagement_score=payload.engagement_score,
        dental_signal_probability=payload.dental_signal_probability,
    )
    await ctx.session.commit()
    await ctx.session.refresh(source)
    return source


@router.get("/sources/due", response_model=list[RadarSourceOut])
async def radar_due_sources(
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    return await due_sources(ctx.session, limit=limit)


@router.post("/sources/{source_id}/polled", response_model=RadarSourceOut)
async def radar_source_polled(
    source_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    source = await ctx.session.get(RadarSource, source_id)
    if not source:
        raise AppError("RADAR_SOURCE_NOT_FOUND", "Radar source was not found.", 404)
    now = datetime.now(UTC)
    _, priority, interval = source_rank(
        source.armenia_relevance,
        source.engagement_score,
        source.dental_signal_probability,
        active=source.is_active,
    )
    source.priority = priority
    source.monitoring_interval_minutes = interval
    source.last_polled_at = now
    source.next_check_at = now + timedelta(minutes=interval)
    await ctx.session.commit()
    await ctx.session.refresh(source)
    return source


@router.post("/ingest", response_model=list[RadarIngestItemOut])
async def radar_ingest(
    payload: RadarBatchIngest,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    source = await ctx.session.get(RadarSource, payload.source_id)
    if not source:
        raise AppError("RADAR_SOURCE_NOT_FOUND", "Radar source was not found.", 404)

    results: list[RadarIngestItemOut] = []
    for item in payload.signals:
        result = await ingest_signal(
            ctx.session,
            clinic_id=ctx.clinic.id,
            source=source,
            external_signal_id=item.external_signal_id,
            signal_type=item.signal_type,
            text=item.text,
            context_text=item.context_text,
            source_url=str(item.source_url),
            author_external_id=item.author_external_id,
            author_display=item.author_display,
            author_profile_url=str(item.author_profile_url) if item.author_profile_url else None,
            observed_at=item.observed_at,
            published_at=item.published_at,
        )
        results.append(
            RadarIngestItemOut(
                duplicate=result.duplicate,
                signal=RadarSignalOut.model_validate(result.signal),
                opportunity=(
                    RadarOpportunityOut.model_validate(result.opportunity)
                    if result.opportunity
                    else None
                ),
            )
        )
    await ctx.session.commit()
    return results


@router.post("/classify-preview")
async def radar_classify_preview(
    payload: RadarPreviewIn,
    _: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    return classify_signal(
        payload.text,
        context_text=payload.context_text,
        published_at=payload.published_at,
    ).as_dict()


@router.get("/opportunities", response_model=RadarOpportunityPage)
async def radar_opportunities(
    ctx: Annotated[AuthContext, Depends(current_context)],
    tier: str | None = None,
    platform: str | None = None,
    language: str | None = None,
    location: str | None = None,
    treatment: str | None = None,
    status: str | None = "NEW",
    min_score: Annotated[int, Query(ge=0, le=100)] = 50,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items, total = await list_opportunities(
        ctx.session,
        tier=tier,
        platform=platform,
        language=language,
        location=location,
        treatment=treatment,
        status=status,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )
    return RadarOpportunityPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/opportunities/{opportunity_id}", response_model=RadarOpportunityDetail)
async def radar_opportunity_detail(
    opportunity_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    opportunity, signals = await opportunity_signals(ctx.session, opportunity_id)
    return RadarOpportunityDetail(opportunity=opportunity, signals=signals)


@router.patch("/opportunities/{opportunity_id}", response_model=RadarOpportunityOut)
async def radar_opportunity_status(
    opportunity_id: uuid.UUID,
    payload: RadarOpportunityStatusPatch,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    opportunity = await ctx.session.get(RadarOpportunity, opportunity_id)
    if not opportunity:
        raise AppError("RADAR_OPPORTUNITY_NOT_FOUND", "Patient opportunity was not found.", 404)
    status = payload.status.strip().upper()
    if status not in OPPORTUNITY_STATUSES:
        raise AppError("RADAR_STATUS_INVALID", "Unsupported opportunity status.", 422)
    opportunity.status = status
    await ctx.session.commit()
    await ctx.session.refresh(opportunity)
    return opportunity
