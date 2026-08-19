from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import get_settings
from app.radar.engine import RadarClassification, classify_signal, load_rules, recency_score

logger = structlog.get_logger(__name__)

_ALLOWED_TREATMENTS = {
    "IMPLANT",
    "VENEER",
    "CROWN",
    "ROOT_CANAL",
    "FILLING",
    "BRACES",
    "WHITENING",
    "CLEANING",
    "WISDOM_TOOTH",
    "EMERGENCY_DENTAL_CARE",
    "COSMETIC_DENTISTRY",
}
_ALLOWED_INTENTS = {
    "RECOMMENDATION",
    "ACTIVE_RESEARCH",
    "PRICE_INQUIRY",
    "URGENT_NEED",
    "CARE_NEED",
    "EMERGING",
    "UNRELATED",
}
_ALLOWED_URGENCY = {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"}
_ALLOWED_LANGUAGES = {"hy", "ru", "en", "mixed", "unknown"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RadarSemanticItem(StrictModel):
    item_id: str = Field(pattern=r"^item_[0-9]+$")
    language: str
    location: str | None
    treatment: str | None
    intent: str
    urgency_label: str
    dental_relevance: float = Field(ge=0, le=1)
    treatment_intent: float = Field(ge=0, le=1)
    urgency: float = Field(ge=0, le=1)
    recommendation_intent: float = Field(ge=0, le=1)
    classifier_confidence: float = Field(ge=0, le=1)


class RadarSemanticBatch(StrictModel):
    items: list[RadarSemanticItem]


SYSTEM_PROMPT = """You are the semantic intent-classification stage of DENTAI Patient Radar.
You analyze only the supplied public/authorized text and nearby post/caption context.
Do not identify people, infer protected traits, infer medical diagnoses, or infer facts that are not in text.
Your job is only dental-service intent intelligence for Armenia.

For every input item return exactly one output item with the same item_id.
Supported languages: hy, ru, en, mixed, unknown.
Supported treatment values: IMPLANT, VENEER, CROWN, ROOT_CANAL, FILLING, BRACES,
WHITENING, CLEANING, WISDOM_TOOTH, EMERGENCY_DENTAL_CARE, COSMETIC_DENTISTRY, or null.
Supported intent values: RECOMMENDATION, ACTIVE_RESEARCH, PRICE_INQUIRY, URGENT_NEED,
CARE_NEED, EMERGING, UNRELATED.
Supported urgency_label values: LOW, MEDIUM, HIGH, VERY_HIGH.

Use context when a short comment is ambiguous. Example: 'how much?' under a veneer post can be a price inquiry.
Understand colloquial Eastern Armenian, Russian, English, transliteration, and mixed-language Armenian-market text.
Be conservative: dental_relevance must be low for unrelated pain, beauty, shopping, or general health content.
Do not output a conversion probability. Scores are semantic component strengths only.
Return only strict JSON matching the schema."""


def _location_match(location: str | None) -> float:
    if location in {"Yerevan", "Gyumri", "Vanadzor", "Armenia"}:
        return 1.0
    if location is None:
        return 0.5
    return 0.0


def _tier(score: int, rules: dict[str, Any]) -> str:
    if score >= int(rules["tiers"]["HOT"]):
        return "HOT"
    if score >= int(rules["tiers"]["WARM"]):
        return "WARM"
    if score >= int(rules["tiers"]["RESEARCH"]):
        return "RESEARCH"
    return "IGNORE"


def classification_from_semantic(
    item: RadarSemanticItem,
    *,
    observed_at: datetime,
    published_at: datetime | None,
) -> RadarClassification:
    rules = load_rules()
    location = item.location.strip()[:160] if item.location else None
    treatment = item.treatment.strip().upper() if item.treatment else None
    intent = item.intent.strip().upper()
    urgency_label = item.urgency_label.strip().upper()
    language = item.language.strip().lower()
    if treatment not in _ALLOWED_TREATMENTS:
        treatment = None
    if intent not in _ALLOWED_INTENTS:
        intent = "UNRELATED"
    if urgency_label not in _ALLOWED_URGENCY:
        urgency_label = "LOW"
    if language not in _ALLOWED_LANGUAGES:
        language = "unknown"

    components = {
        "dental_relevance": round(float(item.dental_relevance), 4),
        "treatment_intent": round(float(item.treatment_intent), 4),
        "location_match": round(_location_match(location), 4),
        "urgency": round(float(item.urgency), 4),
        "recency": round(recency_score(observed_at, published_at), 4),
        "recommendation_intent": round(float(item.recommendation_intent), 4),
        "classifier_confidence": round(float(item.classifier_confidence), 4),
    }
    weighted = sum(
        components[name] * float(weight) for name, weight in rules["score_weights"].items()
    )
    score = int(round(max(0.0, min(1.0, weighted)) * 100))
    candidate = components["dental_relevance"] >= float(rules["candidate_relevance_threshold"])
    return RadarClassification(
        language=language,
        location=location,
        treatment=treatment,
        intent=intent,
        urgency_label=urgency_label,
        dental_relevance=components["dental_relevance"],
        treatment_intent=components["treatment_intent"],
        location_match=components["location_match"],
        urgency=components["urgency"],
        recency=components["recency"],
        recommendation_intent=components["recommendation_intent"],
        classifier_confidence=components["classifier_confidence"],
        opportunity_score=score,
        tier=_tier(score, rules),
        candidate=candidate,
        evidence={
            "components": components,
            "semantic_classifier": "groq",
            "semantic_item_id": item.item_id,
        },
        rule_set=rules["rule_set"],
        rule_version=rules["version"],
    )


def _request_payload(model: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"items": items}, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "dentai_radar_semantic_batch",
                "schema": RadarSemanticBatch.model_json_schema(),
                "strict": True,
            },
        },
        "temperature": 0,
    }


async def _classify_groq_batch(items: list[dict[str, Any]]) -> dict[str, RadarSemanticItem]:
    settings = get_settings()
    if not settings.groq_api_key:
        return {}
    try:
        async with httpx.AsyncClient(timeout=settings.groq_timeout_seconds) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json=_request_payload(settings.groq_model, items),
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = RadarSemanticBatch.model_validate_json(content)
    except (httpx.HTTPError, ValidationError, ValueError, KeyError, TypeError) as exc:
        await logger.awarning("radar_groq_batch_fallback", reason=type(exc).__name__)
        return {}

    expected = {str(item["item_id"]) for item in items}
    returned = [item.item_id for item in parsed.items]
    if set(returned) != expected or len(returned) != len(set(returned)):
        await logger.awarning("radar_groq_batch_binding_failed")
        return {}
    return {item.item_id: item for item in parsed.items}


async def classify_collected_batch(signals: list[Any]) -> list[RadarClassification]:
    """Batch semantic refinement with deterministic scoring and safe heuristic fallback."""
    heuristics = [
        classify_signal(
            signal.text,
            context_text=signal.context_text,
            observed_at=signal.observed_at,
            published_at=signal.published_at,
        )
        for signal in signals
    ]
    settings = get_settings()
    if not settings.radar_llm_enabled or not settings.groq_api_key or not signals:
        return heuristics

    results = list(heuristics)
    batch_size = max(1, min(64, settings.radar_llm_batch_size))
    for start in range(0, len(signals), batch_size):
        chunk = signals[start : start + batch_size]
        request_items = [
            {
                "item_id": f"item_{start + index}",
                "text": signal.text[:6000],
                "context": (signal.context_text or "")[:6000],
            }
            for index, signal in enumerate(chunk)
        ]
        semantic = await _classify_groq_batch(request_items)
        for index, signal in enumerate(chunk):
            item_id = f"item_{start + index}"
            refined = semantic.get(item_id)
            if refined is None:
                continue
            results[start + index] = classification_from_semantic(
                refined,
                observed_at=signal.observed_at,
                published_at=signal.published_at,
            )
    return results
