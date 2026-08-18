from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

RULES_PATH = Path("config/patient_radar_rules.json")

_ARMENIAN_RE = re.compile(r"[\u0530-\u058f]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
_LATIN_RE = re.compile(r"[a-zA-Z]")
_SPACE_RE = re.compile(r"\s+")

DENTAL_TERMS = (
    "ատամ",
    "ատամնաբույժ",
    "ատամնաբուժ",
    "зуб",
    "зубы",
    "зубной",
    "стоматолог",
    "стоматология",
    "dentist",
    "dental",
    "tooth",
    "teeth",
)

PAIN_TERMS = (
    "ցավ",
    "ցավում",
    "սարսափելի",
    "ուռել",
    "ուռուցք",
    "боль",
    "болит",
    "болят",
    "опух",
    "swollen",
    "swelling",
    "hurts",
    "hurt",
    "pain",
    "ache",
)

EMERGENCY_TERMS = (
    "շտապ",
    "անհապաղ",
    "չեմ դիմանում",
    "срочно",
    "невыносим",
    "urgent",
    "emergency",
    "unbearable",
)

RECOMMENDATION_TERMS = (
    "խորհուրդ",
    "կասե՞ք",
    "կասեք",
    "ով ա լավ",
    "ով է լավ",
    "рекомендуйте",
    "посоветуйте",
    "кто хороший",
    "recommend",
    "recommendation",
    "who is good",
    "good dentist",
)

PRICE_TERMS = (
    "գին",
    "արժի",
    "արժեք",
    "որքան",
    "ինչքա՞ն",
    "цена",
    "стоит",
    "сколько",
    "price",
    "cost",
    "how much",
)

LOCATION_TERMS: dict[str, tuple[str, ...]] = {
    "Yerevan": ("yerevan", "երևան", "երեւան", "ереван"),
    "Gyumri": ("gyumri", "գյումրի", "гюмри"),
    "Vanadzor": ("vanadzor", "վանաձոր", "ванадзор"),
    "Armenia": ("armenia", "հայաստան", "армения"),
}

TREATMENT_TERMS: dict[str, tuple[str, ...]] = {
    "IMPLANT": ("իմպլանտ", "имплант", "implant"),
    "VENEER": ("վինիր", "վենիր", "винир", "veneer"),
    "CROWN": ("պսակ", "коронк", "crown"),
    "ROOT_CANAL": (
        "արմատախողովակ",
        "արմատի խողովակ",
        "корневой канал",
        "лечение канал",
        "root canal",
    ),
    "FILLING": ("պլոմբ", "լցոն", "пломб", "filling"),
    "BRACES": ("բրեկետ", "брекет", "braces"),
    "WHITENING": ("սպիտակեց", "отбелив", "whitening", "bleaching"),
    "CLEANING": (
        "ատամների մաքր",
        "профчист",
        "чистка зуб",
        "dental cleaning",
        "teeth cleaning",
    ),
    "WISDOM_TOOTH": (
        "իմաստության ատամ",
        "зуб мудрости",
        "wisdom tooth",
        "wisdom teeth",
    ),
    "COSMETIC_DENTISTRY": (
        "ժպիտ",
        "էսթետիկ ատամ",
        "эстетическая стомат",
        "улыбк",
        "cosmetic dentistry",
        "smile makeover",
    ),
}


@dataclass(frozen=True)
class RadarClassification:
    language: str
    location: str | None
    treatment: str | None
    intent: str
    urgency_label: str
    dental_relevance: float
    treatment_intent: float
    location_match: float
    urgency: float
    recency: float
    recommendation_intent: float
    classifier_confidence: float
    opportunity_score: int
    tier: str
    candidate: bool
    evidence: dict[str, Any]
    rule_set: str
    rule_version: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(value: str | None) -> str:
    return _SPACE_RE.sub(" ", (value or "").strip().casefold())


def _matches(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in text]


@lru_cache(maxsize=1)
def load_rules() -> dict[str, Any]:
    with RULES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def detect_language(text: str) -> str:
    counts = {
        "hy": len(_ARMENIAN_RE.findall(text)),
        "ru": len(_CYRILLIC_RE.findall(text)),
        "en": len(_LATIN_RE.findall(text)),
    }
    active = [name for name, count in counts.items() if count >= 3]
    if len(active) > 1:
        ordered = sorted(active, key=lambda name: counts[name], reverse=True)
        if counts[ordered[1]] >= max(3, counts[ordered[0]] * 0.20):
            return "mixed"
    if not active:
        return "unknown"
    return max(active, key=lambda name: counts[name])


def detect_location(text: str) -> tuple[str | None, list[str]]:
    for location, terms in LOCATION_TERMS.items():
        hits = _matches(text, terms)
        if hits:
            return location, hits
    return None, []


def detect_treatment(text: str) -> tuple[str | None, list[str]]:
    for treatment, terms in TREATMENT_TERMS.items():
        hits = _matches(text, terms)
        if hits:
            return treatment, hits
    return None, []


def recency_score(observed_at: datetime, published_at: datetime | None) -> float:
    published = published_at or observed_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    age_hours = max(0.0, (observed_at - published).total_seconds() / 3600)
    if age_hours <= 6:
        return 1.0
    if age_hours <= 24:
        return 0.90
    if age_hours <= 72:
        return 0.75
    if age_hours <= 168:
        return 0.55
    if age_hours <= 720:
        return 0.30
    return 0.10


def _round_unit(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 4)


def classify_signal(
    text: str,
    *,
    context_text: str | None = None,
    observed_at: datetime | None = None,
    published_at: datetime | None = None,
) -> RadarClassification:
    if not text.strip():
        raise ValueError("signal text cannot be empty")

    rules = load_rules()
    observed = observed_at or datetime.now(UTC)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)

    combined = _normalize(" ".join(part for part in (context_text, text) if part))
    dental_hits = _matches(combined, DENTAL_TERMS)
    pain_hits = _matches(combined, PAIN_TERMS)
    emergency_hits = _matches(combined, EMERGENCY_TERMS)
    recommendation_hits = _matches(combined, RECOMMENDATION_TERMS)
    price_hits = _matches(combined, PRICE_TERMS)
    location, location_hits = detect_location(combined)
    treatment, treatment_hits = detect_treatment(combined)

    dental_relevance = 0.0
    if dental_hits:
        dental_relevance = 0.90
    if treatment_hits:
        dental_relevance = max(dental_relevance, 0.90)
    if dental_hits and (treatment_hits or pain_hits):
        dental_relevance = 1.0
    elif pain_hits and ("ատամ" in combined or "зуб" in combined or "tooth" in combined):
        dental_relevance = max(dental_relevance, 0.90)
    elif pain_hits:
        dental_relevance = max(dental_relevance, 0.25)

    recommendation = 1.0 if recommendation_hits else 0.0
    price_inquiry = bool(price_hits)
    treatment_intent = 0.0
    if treatment_hits:
        treatment_intent = 0.78
    if treatment_hits and (recommendation_hits or price_hits):
        treatment_intent = 1.0
    elif dental_relevance >= 0.9 and (recommendation_hits or price_hits):
        treatment_intent = 0.88
    elif dental_relevance >= 0.9 and pain_hits:
        treatment_intent = 0.70
    elif dental_relevance >= 0.9:
        treatment_intent = 0.50

    if emergency_hits and dental_relevance >= 0.5:
        urgency = 1.0
        urgency_label = "VERY_HIGH"
    elif pain_hits and dental_relevance >= 0.5:
        urgency = 0.85
        urgency_label = "HIGH"
    elif dental_relevance >= 0.9 and treatment_intent >= 0.75:
        urgency = 0.50
        urgency_label = "MEDIUM"
    else:
        urgency = 0.20 if dental_relevance >= 0.5 else 0.0
        urgency_label = "LOW"

    if location in {"Yerevan", "Gyumri", "Vanadzor", "Armenia"}:
        location_match = 1.0
    elif location is None:
        location_match = 0.50
    else:
        location_match = 0.0

    if recommendation_hits and price_hits:
        intent = "ACTIVE_RESEARCH"
    elif recommendation_hits:
        intent = "RECOMMENDATION"
    elif price_hits and dental_relevance >= 0.5:
        intent = "PRICE_INQUIRY"
    elif emergency_hits and dental_relevance >= 0.5:
        intent = "URGENT_NEED"
    elif pain_hits and dental_relevance >= 0.5:
        intent = "CARE_NEED"
    elif dental_relevance >= 0.9:
        intent = "EMERGING"
    else:
        intent = "UNRELATED"

    language = detect_language(text)
    dimensions = sum(
        bool(value)
        for value in (
            dental_hits,
            treatment_hits,
            pain_hits,
            recommendation_hits,
            price_hits,
            location_hits,
        )
    )
    classifier_confidence = min(0.96, 0.50 + dimensions * 0.075)
    if dental_relevance < 0.5:
        classifier_confidence = min(classifier_confidence, 0.70)

    component_values = {
        "dental_relevance": _round_unit(dental_relevance),
        "treatment_intent": _round_unit(treatment_intent),
        "location_match": _round_unit(location_match),
        "urgency": _round_unit(urgency),
        "recency": _round_unit(recency_score(observed, published_at)),
        "recommendation_intent": _round_unit(recommendation),
        "classifier_confidence": _round_unit(classifier_confidence),
    }
    weighted = sum(
        component_values[name] * float(weight)
        for name, weight in rules["score_weights"].items()
    )
    if not math.isfinite(weighted):
        weighted = 0.0
    score = int(round(min(1.0, max(0.0, weighted)) * 100))

    if score >= int(rules["tiers"]["HOT"]):
        tier = "HOT"
    elif score >= int(rules["tiers"]["WARM"]):
        tier = "WARM"
    elif score >= int(rules["tiers"]["RESEARCH"]):
        tier = "RESEARCH"
    else:
        tier = "IGNORE"

    candidate = dental_relevance >= float(rules["candidate_relevance_threshold"])
    evidence = {
        "dental_terms": dental_hits,
        "pain_terms": pain_hits,
        "emergency_terms": emergency_hits,
        "recommendation_terms": recommendation_hits,
        "price_terms": price_hits,
        "treatment_terms": treatment_hits,
        "location_terms": location_hits,
        "price_inquiry": price_inquiry,
        "components": component_values,
    }
    return RadarClassification(
        language=language,
        location=location,
        treatment=treatment,
        intent=intent,
        urgency_label=urgency_label,
        dental_relevance=component_values["dental_relevance"],
        treatment_intent=component_values["treatment_intent"],
        location_match=component_values["location_match"],
        urgency=component_values["urgency"],
        recency=component_values["recency"],
        recommendation_intent=component_values["recommendation_intent"],
        classifier_confidence=component_values["classifier_confidence"],
        opportunity_score=score,
        tier=tier,
        candidate=candidate,
        evidence=evidence,
        rule_set=rules["rule_set"],
        rule_version=rules["version"],
    )


def source_rank(
    armenia_relevance: float,
    engagement: float,
    dental_signal_probability: float,
    *,
    active: bool = True,
    new_content: bool = False,
) -> tuple[int, str, int]:
    rules = load_rules()
    normalized = [
        min(100.0, max(0.0, float(value)))
        for value in (armenia_relevance, engagement, dental_signal_probability)
    ]
    score = int(round(normalized[0] * 0.40 + normalized[1] * 0.25 + normalized[2] * 0.35))
    if not active:
        priority = "INACTIVE"
    elif score >= int(rules["source_priority"]["HIGH"]):
        priority = "HIGH"
    elif score >= int(rules["source_priority"]["MEDIUM"]):
        priority = "MEDIUM"
    else:
        priority = "LOW"
    interval = int(rules["monitoring_minutes"][priority])
    if new_content and active:
        interval = min(interval, int(rules["monitoring_minutes"]["HIGH"]))
    return score, priority, interval


def content_dedupe_key(
    platform: str,
    source_external_id: str,
    author_external_id: str | None,
    external_signal_id: str | None,
    text: str,
) -> str:
    canonical = "|".join(
        (
            platform.strip().upper(),
            source_external_id.strip(),
            (author_external_id or "anonymous").strip(),
            (external_signal_id or "").strip(),
            _normalize(text),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def person_fingerprint(clinic_id: str, platform: str, author_external_id: str | None) -> str:
    if not author_external_id:
        return "anonymous:" + hashlib.sha256(platform.encode("utf-8")).hexdigest()[:20]
    canonical = f"{clinic_id}|{platform.strip().upper()}|{author_external_id.strip().casefold()}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
