from datetime import UTC, datetime

from app.radar.collector import CollectedSignal, parse_public_telegram, parse_web_document
from app.radar.intelligence import RadarSemanticItem, classification_from_semantic


def test_public_web_parser_produces_stable_readable_blocks():
    html = """
    <html><head><title>Yerevan dental discussion</title></head><body>
      <p>Երևանում լավ ատամնաբույժ կասե՞ք իմպլանտի համար</p>
      <p>Երևանում լավ ատամնաբույժ կասե՞ք իմպլանտի համար</p>
      <article>Does anyone know the price for veneers in Yerevan?</article>
    </body></html>
    """
    items = parse_web_document(html, "https://example.com/dental", max_items=20)
    assert len(items) == 2
    assert items[0].context_text == "Yerevan dental discussion"
    assert items[0].external_signal_id


def test_public_telegram_parser_extracts_messages_and_source_links():
    html = """
    <div class="tgme_widget_message" data-post="clinicarmenia/42">
      <a class="tgme_widget_message_owner_name"><span>Anna</span></a>
      <div class="tgme_widget_message_text">Ատամս ցավում է, Երևանում ո՞ւր գնամ</div>
      <time datetime="2026-08-19T04:00:00+00:00"></time>
    </div>
    """
    items = parse_public_telegram(html, "https://t.me/clinicarmenia", max_items=20)
    assert len(items) == 1
    assert items[0].external_signal_id == "clinicarmenia/42"
    assert items[0].source_url == "https://t.me/clinicarmenia/42"
    assert "Ատամս" in items[0].text


def test_semantic_ai_output_is_scored_by_server_policy_not_model_probability():
    item = RadarSemanticItem(
        item_id="item_0",
        language="hy",
        location="Yerevan",
        treatment="IMPLANT",
        intent="ACTIVE_RESEARCH",
        urgency_label="MEDIUM",
        dental_relevance=1,
        treatment_intent=1,
        urgency=0.5,
        recommendation_intent=1,
        classifier_confidence=0.95,
    )
    now = datetime.now(UTC)
    result = classification_from_semantic(item, observed_at=now, published_at=now)
    assert result.candidate is True
    assert result.opportunity_score >= 90
    assert result.evidence["semantic_classifier"] == "groq"
    assert result.location_match == 1.0


def test_collected_signal_contains_only_collection_contract_fields():
    signal = CollectedSignal(
        external_signal_id="1",
        signal_type="COMMENT",
        text="Need a dentist in Yerevan",
        context_text="Dental post",
        source_url="https://example.com/post/1",
        author_external_id="public-user",
        author_display="Public User",
        author_profile_url=None,
        observed_at=datetime.now(UTC),
        published_at=None,
    )
    assert not hasattr(signal, "password")
    assert not hasattr(signal, "session")
