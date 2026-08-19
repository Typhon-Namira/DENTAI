from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.radar.collector import CollectedSignal
from app.radar.engine import RadarClassification, classify_signal, content_dedupe_key
from app.radar.intelligence import classify_collected_batch
from app.radar.models import RadarSignal, RadarSource


@dataclass(frozen=True)
class FunnelResult:
    signals: list[CollectedSignal]
    classifications: list[RadarClassification]
    duplicates_skipped: int
    semantic_candidates: int
    cheap_rejected: int


async def _dedupe_new(
    db: AsyncSession,
    source: RadarSource,
    signals: list[CollectedSignal],
) -> tuple[list[CollectedSignal], int]:
    keys: list[str] = []
    unique: list[CollectedSignal] = []
    seen: set[str] = set()
    for item in signals:
        key = content_dedupe_key(
            source.platform,
            source.external_source_id,
            item.author_external_id,
            item.external_signal_id,
            item.text,
        )
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
        unique.append(item)
    if not keys:
        return [], len(signals)
    existing = set(
        (
            await db.scalars(
                select(RadarSignal.dedupe_key).where(
                    RadarSignal.source_id == source.id,
                    RadarSignal.dedupe_key.in_(keys),
                )
            )
        ).all()
    )
    new_items: list[CollectedSignal] = []
    for item, key in zip(unique, keys, strict=True):
        if key not in existing:
            new_items.append(item)
    return new_items, len(signals) - len(new_items)


def _needs_semantic(item: CollectedSignal, heuristic: RadarClassification) -> bool:
    threshold = get_settings().radar_semantic_min_relevance
    if heuristic.dental_relevance >= threshold:
        return True
    # Short comments such as "how much?" can only make sense with dental context.
    if item.context_text and heuristic.intent in {"PRICE_INQUIRY", "RECOMMENDATION"}:
        return True
    return False


async def run_funnel(
    db: AsyncSession,
    *,
    source: RadarSource,
    collected: list[CollectedSignal],
) -> FunnelResult:
    """Deduplicate and cheaply reject before any paid semantic request."""
    new_items, duplicate_count = await _dedupe_new(db, source, collected)
    heuristics = [
        classify_signal(
            item.text,
            context_text=item.context_text,
            observed_at=item.observed_at,
            published_at=item.published_at,
        )
        for item in new_items
    ]
    semantic_positions = [
        index
        for index, (item, heuristic) in enumerate(zip(new_items, heuristics, strict=True))
        if _needs_semantic(item, heuristic)
    ]
    if semantic_positions and get_settings().radar_llm_enabled:
        semantic_items = [new_items[index] for index in semantic_positions]
        refined = await classify_collected_batch(semantic_items)
        for position, classification in zip(semantic_positions, refined, strict=True):
            heuristics[position] = classification
    return FunnelResult(
        signals=new_items,
        classifications=heuristics,
        duplicates_skipped=duplicate_count,
        semantic_candidates=len(semantic_positions),
        cheap_rejected=max(0, len(new_items) - len(semantic_positions)),
    )
