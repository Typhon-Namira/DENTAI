from copy import deepcopy

import pytest

from ai_engine.groq.provider import (
    PRODUCT_MODEL_SCORE_THRESHOLD,
    GroqClinicalSummary,
    GroqFindingEvidence,
    GroqToothExplanation,
    build_groq_request_payload,
    build_product_finding_evidence,
    summarize_product_findings,
    validate_summary_against_evidence,
)


def raw_finding(
    tooth: str = "37",
    finding_type: str = "FILLING",
    score: float | None = 0.8945,
) -> dict:
    return {
        "tooth_code": tooth,
        "finding_type": finding_type,
        "description": "DENTAI evidence",
        "confidence": score,
        "provenance": {
            "source_model": "DENTAI Unified V5",
            "model_version": "dentai-unified-v5",
            "raw_score": score,
            "uncertainty": "LOW_CONFIDENCE",
            "uncertainty_reason": "FDI_LOW_CONFIDENCE_OR_UNRESOLVED",
            "bounding_box": [10.0, 20.0, 30.0, 40.0],
            "review_required": True,
            "review_reasons": ["FDI_LOW_CONFIDENCE_OR_UNRESOLVED"],
        },
    }


def valid_summary(evidence: list[GroqFindingEvidence]) -> GroqClinicalSummary:
    by_tooth: dict[str, list[GroqFindingEvidence]] = {}
    for item in evidence:
        by_tooth.setdefault(item.tooth_fdi, []).append(item)
    return GroqClinicalSummary(
        doctor_summary="DENTAI evidence is available for clinician review.",
        tooth_explanations=[
            GroqToothExplanation(
                tooth_fdi=tooth,
                evidence=items,
                headline=f"Tooth {tooth} — DENTAI finding",
                clinical_explanation="DENTAI identified the supplied finding.",
                confidence_explanation="The model score is supporting AI evidence.",
                review_explanation="Clinician review is required.",
            )
            for tooth, items in by_tooth.items()
        ],
        important_changes=[],
        monitoring_points=["Verify the highlighted tooth region."],
        questions_for_doctor=["Does the highlighted region match the supplied tooth number?"],
        patient_message_draft="A clinician will review the radiographic findings.",
    )


def test_strict_schema_forbids_extra_properties_and_requires_every_field():
    schema = GroqClinicalSummary.model_json_schema()
    object_schemas = [schema, *schema.get("$defs", {}).values()]
    for object_schema in object_schemas:
        if object_schema.get("type") != "object":
            continue
        assert object_schema["additionalProperties"] is False
        assert set(object_schema["required"]) == set(object_schema["properties"])


def test_one_tooth_one_finding_validates_exact_evidence():
    evidence = build_product_finding_evidence([raw_finding()])
    summary = valid_summary(evidence)
    assert validate_summary_against_evidence(summary, evidence) is summary
    assert summary.tooth_explanations[0].evidence == evidence


def test_one_tooth_multiple_findings_remain_distinct():
    evidence = build_product_finding_evidence(
        [
            raw_finding(finding_type="FILLING", score=0.8945),
            raw_finding(finding_type="ROOT_CANAL_TREATMENT", score=0.9516),
        ]
    )
    summary = valid_summary(evidence)
    validated = validate_summary_against_evidence(summary, evidence)
    assert len(validated.tooth_explanations) == 1
    assert [item.finding_type for item in validated.tooth_explanations[0].evidence] == [
        "FILLING",
        "ROOT_CANAL_TREATMENT",
    ]


def test_low_scores_are_excluded_without_mutating_raw_findings():
    findings = [
        raw_finding(tooth="37", score=PRODUCT_MODEL_SCORE_THRESHOLD),
        raw_finding(tooth="44", score=0.3206733167171478),
    ]
    before = deepcopy(findings)
    evidence = build_product_finding_evidence(findings)
    assert [(item.evidence_id, item.tooth_fdi) for item in evidence] == [
        ("finding_0", "37")
    ]
    assert findings == before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("evidence_id", "finding_99"),
        ("tooth_fdi", "36"),
        ("finding_type", "CARIES"),
        ("model_score", 0.7),
        ("review_status", "CONFIRMED"),
    ],
)
def test_changed_or_invented_evidence_rejects_entire_summary(field: str, value: object):
    evidence = build_product_finding_evidence([raw_finding()])
    payload = evidence[0].model_dump()
    payload[field] = value
    summary = valid_summary(evidence)
    summary.tooth_explanations[0].evidence[0] = GroqFindingEvidence.model_validate(payload)
    with pytest.raises(ValueError):
        validate_summary_against_evidence(summary, evidence)


def test_request_contains_only_deidentified_structured_dentai_evidence():
    evidence = build_product_finding_evidence([raw_finding()])
    payload = build_groq_request_payload("openai/gpt-oss-20b", evidence)
    user_content = payload["messages"][1]["content"]
    assert "patient" not in user_content
    assert "source_image_id" not in user_content
    assert "bounding_box" not in user_content
    assert payload["model"] == "openai/gpt-oss-20b"
    assert payload["temperature"] == 0
    assert payload["response_format"]["json_schema"]["strict"] is True


@pytest.mark.asyncio
async def test_groq_unavailable_returns_narrative_fallback_without_raising():
    class UnavailableProvider:
        async def summarize(self, evidence):
            raise TimeoutError("Groq unavailable")

    findings = [raw_finding()]
    before = deepcopy(findings)
    result = await summarize_product_findings(UnavailableProvider(), findings)
    assert result == {"status": "UNAVAILABLE"}
    assert findings == before


@pytest.mark.asyncio
async def test_missing_groq_provider_leaves_narrative_absent():
    assert await summarize_product_findings(None, [raw_finding()]) is None
