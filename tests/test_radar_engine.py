from datetime import UTC, datetime, timedelta

from app.radar.engine import (
    classify_signal,
    content_dedupe_key,
    detect_language,
    person_fingerprint,
    source_rank,
)


def test_direct_armenian_implant_recommendation_is_hot():
    result = classify_signal("Երևանում լավ ատամնաբույժ կասե՞ք իմպլանտի համար")

    assert result.candidate is True
    assert result.language == "hy"
    assert result.location == "Yerevan"
    assert result.treatment == "IMPLANT"
    assert result.intent == "RECOMMENDATION"
    assert result.tier == "HOT"
    assert result.opportunity_score >= 90


def test_indirect_armenian_dental_distress_is_detected_without_dentist_word():
    result = classify_signal("Ատամներս սարսափելի վիճակում են, արդեն ամաչում եմ ժպտալ")

    assert result.candidate is True
    assert result.dental_relevance >= 0.9
    assert result.treatment == "COSMETIC_DENTISTRY"
    assert result.intent in {"CARE_NEED", "EMERGING"}
    assert result.opportunity_score >= 50


def test_context_turns_ambiguous_price_question_into_veneer_signal():
    result = classify_signal(
        "Մոտավորապես ինչքա՞ն արժի",
        context_text="Երևանում վինիրների մասին քննարկում",
    )

    assert result.candidate is True
    assert result.location == "Yerevan"
    assert result.treatment == "VENEER"
    assert result.intent == "PRICE_INQUIRY"
    assert result.treatment_intent >= 0.75


def test_non_dental_pain_signal_is_not_promoted_to_high_value_opportunity():
    result = classify_signal("My back hurts after the gym")

    assert result.dental_relevance < 0.5
    assert result.tier == "IGNORE"


def test_mixed_language_detection_handles_real_market_content():
    assert detect_language("Երևանում good dentist please recommend") == "mixed"


def test_recency_decreases_old_signal_score():
    observed = datetime.now(UTC)
    fresh = classify_signal(
        "Yerevan good dentist recommendation for implant",
        observed_at=observed,
        published_at=observed - timedelta(hours=1),
    )
    old = classify_signal(
        "Yerevan good dentist recommendation for implant",
        observed_at=observed,
        published_at=observed - timedelta(days=90),
    )

    assert fresh.recency > old.recency
    assert fresh.opportunity_score > old.opportunity_score


def test_source_rank_controls_adaptive_monitoring():
    score, priority, interval = source_rank(98, 94, 91)
    assert score >= 90
    assert priority == "HIGH"
    assert interval == 5

    _, low_priority, low_interval = source_rank(40, 20, 20)
    assert low_priority == "LOW"
    assert low_interval == 180

    _, inactive_priority, inactive_interval = source_rank(98, 94, 91, active=False)
    assert inactive_priority == "INACTIVE"
    assert inactive_interval == 1440


def test_dedupe_key_is_stable_and_author_sensitive():
    first = content_dedupe_key("instagram", "page-1", "user-1", "comment-1", "Hello")
    same = content_dedupe_key("INSTAGRAM", "page-1", "user-1", "comment-1", " hello ")
    other_author = content_dedupe_key(
        "INSTAGRAM", "page-1", "user-2", "comment-1", "Hello"
    )

    assert first == same
    assert first != other_author


def test_person_fingerprint_is_tenant_scoped():
    first = person_fingerprint("clinic-a", "telegram", "public-user-42")
    same = person_fingerprint("clinic-a", "TELEGRAM", "PUBLIC-USER-42")
    other_clinic = person_fingerprint("clinic-b", "TELEGRAM", "public-user-42")

    assert first == same
    assert first != other_clinic
    assert "public-user-42" not in first
