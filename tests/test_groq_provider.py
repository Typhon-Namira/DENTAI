import json
from copy import deepcopy

import pytest

import ai_engine.groq.provider as groq_module
from ai_engine.groq.provider import (
    GroqClinicalSummary,
    GroqEvidenceBindingError,
    GroqFindingEvidence,
    GroqToothExplanation,
    MAX_GROQ_CONCURRENCY,
    MAX_GROQ_TEETH_PER_BATCH,
    batch_tooth_evidence,
    build_groq_request_payload,
    build_product_finding_evidence,
    group_evidence_by_tooth,
    safe_failure_reason,
    summarize_product_findings,
    validate_summary_against_evidence,
)


def raw_finding(
    tooth: str | None = "37",
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
    by_tooth: dict[str, list[str]] = {}
    for item in evidence:
        by_tooth.setdefault(item.tooth_fdi, []).append(item.evidence_id)
    return GroqClinicalSummary(
        doctor_summary="DENTAI evidence is available for clinician review.",
        tooth_explanations=[
            GroqToothExplanation(
                tooth_fdi=tooth,
                evidence_ids=evidence_ids,
                headline=f"Tooth {tooth} — DENTAI finding",
                clinical_explanation="DENTAI identified the supplied finding.",
                review_explanation="Clinician verification is required.",
            )
            for tooth, evidence_ids in by_tooth.items()
        ],
        important_changes=[],
        monitoring_points=["Verify the highlighted tooth region."],
        questions_for_doctor=["Does the highlighted region match the supplied tooth number?"],
        patient_message_draft="A clinician will review the radiographic findings.",
    )


def production_findings() -> list[dict]:
    return [
        raw_finding("16", "CROWN", 0.9231),
        raw_finding("16", "ROOT_CANAL_TREATMENT", 0.6951),
        raw_finding("24", "FILLING", 0.6287),
        raw_finding("36", "CROWN", 0.9516),
        raw_finding("36", "ROOT_CANAL_TREATMENT", 0.8945),
        raw_finding("36", "FILLING", 0.8732),
        raw_finding("37", "FILLING", 0.8945),
        raw_finding("47", "FILLING", 0.6951),
        raw_finding("44", "FILLING", 0.3206733167171478),
    ]


def test_strict_output_schema_contains_ids_and_no_canonical_evidence_values():
    schema = GroqClinicalSummary.model_json_schema()
    tooth = schema["$defs"]["GroqToothExplanation"]["properties"]
    assert set(tooth) == {
        "tooth_fdi",
        "evidence_ids",
        "headline",
        "clinical_explanation",
        "review_explanation",
    }
    assert "confidence_explanation" not in tooth
    assert "model_score" not in json.dumps(schema)
    object_schemas = [schema, *schema.get("$defs", {}).values()]
    for object_schema in object_schemas:
        if object_schema.get("type") == "object":
            assert object_schema["additionalProperties"] is False
            assert set(object_schema["required"]) == set(object_schema["properties"])


def test_one_evidence_id_validates():
    evidence = build_product_finding_evidence([raw_finding()])
    summary = valid_summary(evidence)
    assert validate_summary_against_evidence(summary, evidence) is summary
    assert summary.tooth_explanations[0].evidence_ids == ["finding_0"]


def test_multiple_findings_on_one_tooth_validate_by_ids_only():
    evidence = build_product_finding_evidence(
        [
            raw_finding("37", "FILLING", 0.8945),
            raw_finding("37", "ROOT_CANAL_TREATMENT", 0.9516),
        ]
    )
    summary = valid_summary(evidence)
    assert validate_summary_against_evidence(summary, evidence) is summary
    assert summary.tooth_explanations[0].evidence_ids == ["finding_0", "finding_1"]


def test_realistic_multi_tooth_fixture_covers_every_visible_evidence_once():
    findings = production_findings()
    before = deepcopy(findings)
    evidence = build_product_finding_evidence(findings)
    summary = valid_summary(evidence)
    validate_summary_against_evidence(summary, evidence)

    assert len(evidence) == 8
    assert {item.tooth_fdi for item in evidence} == {"16", "24", "36", "37", "47"}
    assert [item.evidence_id for item in evidence] == [f"finding_{index}" for index in range(8)]
    assert all(item.tooth_fdi != "44" for item in evidence)
    assert findings == before


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_id",
        "duplicate_id",
        "omitted_id",
        "wrong_tooth",
        "omitted_tooth",
    ],
)
def test_invalid_id_coverage_rejects_complete_narrative(mutation: str):
    evidence = build_product_finding_evidence(
        [raw_finding("37", "FILLING"), raw_finding("47", "FILLING")]
    )
    summary = valid_summary(evidence)
    if mutation == "unknown_id":
        summary.tooth_explanations[0].evidence_ids[0] = "finding_99"
    elif mutation == "duplicate_id":
        summary.tooth_explanations[1].evidence_ids[0] = "finding_0"
    elif mutation == "omitted_id":
        summary.tooth_explanations[0].evidence_ids = []
    elif mutation == "wrong_tooth":
        summary.tooth_explanations[0].evidence_ids[0] = "finding_1"
        summary.tooth_explanations[1].evidence_ids[0] = "finding_0"
    else:
        summary.tooth_explanations.pop()

    with pytest.raises(GroqEvidenceBindingError):
        validate_summary_against_evidence(summary, evidence)


def test_request_contains_deidentified_canonical_input_but_output_schema_only_uses_ids():
    evidence = build_product_finding_evidence([raw_finding()])
    payload = build_groq_request_payload("openai/gpt-oss-20b", evidence)
    finding_payload = json.loads(payload["messages"][1]["content"])["findings"][0]
    assert finding_payload["model_score"] == 0.8945
    assert finding_payload["source_model"] == "DENTAI Unified V5"
    assert "patient" not in payload["messages"][1]["content"]
    assert "source_image_id" not in payload["messages"][1]["content"]
    assert "bounding_box" not in payload["messages"][1]["content"]
    output_properties = payload["response_format"]["json_schema"]["schema"]["$defs"][
        "GroqToothExplanation"
    ]["properties"]
    assert "evidence_ids" in output_properties
    assert "model_score" not in output_properties
    assert payload["temperature"] == 0


@pytest.mark.asyncio
async def test_canonical_values_are_attached_server_side_not_returned_by_groq():
    evidence = build_product_finding_evidence([raw_finding()])

    class Provider:
        model = "openai/gpt-oss-20b"

        async def summarize(self, received):
            assert received == evidence
            return valid_summary(received)

    result = await summarize_product_findings(Provider(), [raw_finding()])
    canonical = result["canonical_evidence"]["finding_0"]
    assert canonical == evidence[0].model_dump(mode="json")
    assert "model_score" not in result["tooth_explanations"][0]
    assert "finding_type" not in result["tooth_explanations"][0]


@pytest.mark.asyncio
async def test_groq_failure_logs_safe_diagnostics_and_returns_unavailable(monkeypatch):
    events = []

    class CapturingLogger:
        def warning(self, event, **values):
            events.append((event, values))

    class UnavailableProvider:
        model = "openai/gpt-oss-20b"

        async def summarize(self, evidence):
            raise TimeoutError("sensitive response must not be logged")

    monkeypatch.setattr(groq_module, "logger", CapturingLogger())
    result = await summarize_product_findings(UnavailableProvider(), [raw_finding()])
    assert result["status"] == "UNAVAILABLE"
    assert result["failed_tooth_fdis"] == ["37"]
    assert events == [
        (
            "groq_clinical_summary_batch_unavailable",
            {
                "exception_class": "TimeoutError",
                "reason": "timeout",
                "batch_tooth_count": 1,
                "evidence_count": 1,
                "model": "openai/gpt-oss-20b",
                "retry_mode": "batch",
                "tooth_fdis": ["37"],
            },
        )
    ]
    assert "sensitive response" not in repr(events)


@pytest.mark.asyncio
async def test_missing_groq_provider_leaves_narrative_absent():
    assert await summarize_product_findings(None, [raw_finding()]) is None


def test_safe_failure_categories_do_not_include_exception_messages():
    error = GroqEvidenceBindingError("invented clinical response")
    assert safe_failure_reason(error) == "evidence_binding_error"


def test_unresolved_product_finding_is_excluded_from_tooth_specific_evidence() -> None:
    resolved = raw_finding("37", "FILLING", 0.8945)
    unresolved = raw_finding(None, "DEEP_CARIES", 0.9516)

    evidence = build_product_finding_evidence([resolved, unresolved])

    assert [(item.evidence_id, item.tooth_fdi) for item in evidence] == [("finding_0", "37")]
    assert unresolved["tooth_code"] is None
    assert unresolved["confidence"] == 0.9516


@pytest.mark.asyncio
async def test_mixed_resolved_and_unresolved_findings_keep_groq_summary_available() -> None:
    findings = [
        raw_finding("37", "FILLING", 0.8945),
        raw_finding(None, "DEEP_CARIES", 0.9516),
    ]

    class Provider:
        model = "openai/gpt-oss-20b"

        async def summarize(self, evidence):
            assert [item.tooth_fdi for item in evidence] == ["37"]
            return valid_summary(evidence)

    result = await summarize_product_findings(Provider(), findings)

    assert result["doctor_summary"]
    assert result.get("status") != "UNAVAILABLE"
    assert set(result["canonical_evidence"]) == {"finding_0"}


class RecordingProvider:
    model = "openai/gpt-oss-20b"

    def __init__(
        self,
        *,
        fail_batches: set[frozenset[str]] | None = None,
        fail_single_teeth: set[str] | None = None,
        invalid_batches: dict[frozenset[str], str] | None = None,
    ):
        self.fail_batches = fail_batches or set()
        self.fail_single_teeth = fail_single_teeth or set()
        self.invalid_batches = invalid_batches or {}
        self.calls: list[list[GroqFindingEvidence]] = []
        self.active = 0
        self.max_active = 0

    async def summarize(
        self,
        received: list[GroqFindingEvidence],
    ) -> GroqClinicalSummary:
        self.calls.append(received)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            teeth = frozenset(item.tooth_fdi for item in received)
            if teeth in self.fail_batches or (
                len(teeth) == 1 and next(iter(teeth)) in self.fail_single_teeth
            ):
                raise TimeoutError("narrative content must not be logged")

            summary = valid_summary(received)
            mutation = self.invalid_batches.get(teeth)
            if mutation == "unknown":
                summary.tooth_explanations[0].evidence_ids[0] = "finding_999"
            elif mutation == "duplicate":
                summary.tooth_explanations[0].evidence_ids.append(
                    summary.tooth_explanations[0].evidence_ids[0]
                )
            elif mutation == "wrong_tooth":
                summary.tooth_explanations[0].tooth_fdi = "48"
            elif mutation == "missing":
                summary.tooth_explanations[0].evidence_ids.pop()
            return validate_summary_against_evidence(summary, received)
        finally:
            self.active -= 1


def findings_for_teeth(*teeth: str) -> list[dict]:
    return [raw_finding(tooth, "FILLING", 0.70 + index / 100) for index, tooth in enumerate(teeth)]


@pytest.mark.asyncio
async def test_one_to_three_teeth_use_one_batch():
    provider = RecordingProvider()
    result = await summarize_product_findings(
        provider,
        findings_for_teeth("16", "24", "36"),
    )

    assert MAX_GROQ_TEETH_PER_BATCH == 3
    assert len(provider.calls) == 1
    assert {item.tooth_fdi for item in provider.calls[0]} == {"16", "24", "36"}
    assert result["status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_large_analysis_creates_bounded_multi_tooth_batches():
    provider = RecordingProvider()
    teeth = ("16", "24", "26", "27", "35", "46", "47")
    result = await summarize_product_findings(provider, findings_for_teeth(*teeth))

    assert [len({item.tooth_fdi for item in call}) for call in provider.calls] == [3, 3, 1]
    assert result["status"] == "AVAILABLE"
    assert {item["tooth_fdi"] for item in result["tooth_explanations"]} == set(teeth)
    assert MAX_GROQ_CONCURRENCY == 2
    assert provider.max_active <= MAX_GROQ_CONCURRENCY


@pytest.mark.asyncio
async def test_failed_batch_retries_teeth_and_preserves_partial_success():
    provider = RecordingProvider(
        fail_batches={frozenset({"27", "35", "44"})},
        fail_single_teeth={"35"},
    )
    teeth = ("16", "24", "26", "27", "35", "44", "46", "47")
    result = await summarize_product_findings(provider, findings_for_teeth(*teeth))

    explained = {item["tooth_fdi"] for item in result["tooth_explanations"]}
    assert result["status"] == "PARTIAL"
    assert result["failed_tooth_fdis"] == ["35"]
    assert explained == set(teeth) - {"35"}
    assert [item.tooth_fdi for call in provider.calls for item in call].count("35") == 2


@pytest.mark.asyncio
async def test_all_batches_fail_without_losing_canonical_evidence():
    class AlwaysUnavailable:
        model = "openai/gpt-oss-20b"

        async def summarize(self, _received):
            raise TimeoutError("unavailable")

    result = await summarize_product_findings(
        AlwaysUnavailable(),
        findings_for_teeth("16", "24", "36", "37"),
    )

    assert result["status"] == "UNAVAILABLE"
    assert result["tooth_explanations"] == []
    assert result["failed_tooth_fdis"] == ["16", "24", "36", "37"]
    assert len(result["canonical_evidence"]) == 4


@pytest.mark.asyncio
async def test_multi_tooth_failure_can_recover_completely_with_single_tooth_retries():
    provider = RecordingProvider(
        fail_batches={frozenset({"16", "24", "36"})},
    )
    result = await summarize_product_findings(
        provider,
        findings_for_teeth("16", "24", "36"),
    )

    assert result["status"] == "AVAILABLE"
    assert len(provider.calls) == 4
    assert all(len({item.tooth_fdi for item in call}) == 1 for call in provider.calls[1:])


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["unknown", "duplicate", "wrong_tooth", "missing"])
async def test_invalid_batch_isolated_and_only_failed_single_tooth_falls_back(
    mutation: str,
):
    invalid_batch = frozenset({"16", "24", "36"})
    provider = RecordingProvider(
        invalid_batches={
            invalid_batch: mutation,
            frozenset({"24"}): mutation,
        }
    )
    result = await summarize_product_findings(
        provider,
        findings_for_teeth("16", "24", "36", "46"),
    )

    assert result["status"] == "PARTIAL"
    assert result["failed_tooth_fdis"] == ["24"]
    assert {item["tooth_fdi"] for item in result["tooth_explanations"]} == {
        "16",
        "36",
        "46",
    }


def test_batching_keeps_all_findings_for_one_tooth_together():
    evidence = build_product_finding_evidence(
        [
            raw_finding("16", "CROWN", 0.92),
            raw_finding("16", "ROOT_CANAL_TREATMENT", 0.81),
            *findings_for_teeth("24", "36", "37"),
        ]
    )
    batches = batch_tooth_evidence(group_evidence_by_tooth(evidence))

    tooth_16_batches = [batch for batch in batches if any(item.tooth_fdi == "16" for item in batch)]
    assert len(tooth_16_batches) == 1
    assert [item.finding_type for item in tooth_16_batches[0] if item.tooth_fdi == "16"] == [
        "CROWN",
        "ROOT_CANAL_TREATMENT",
    ]


@pytest.mark.asyncio
async def test_unresolved_and_low_score_findings_do_not_create_batches_or_failures():
    unresolved = raw_finding(None, "DEEP_CARIES", 0.95)
    unresolved["provenance"]["raw_fdi"] = "37"
    low_score = raw_finding("44", "FILLING", 0.59)
    provider = RecordingProvider()

    result = await summarize_product_findings(
        provider,
        [unresolved, low_score, raw_finding("47", "FILLING", 0.80)],
    )

    assert result["status"] == "AVAILABLE"
    assert len(provider.calls) == 1
    assert [item.tooth_fdi for item in provider.calls[0]] == ["47"]
    assert set(result["canonical_evidence"]) == {"finding_0"}
    assert unresolved["provenance"]["raw_fdi"] == "37"


def test_groq_payload_excludes_image_patient_and_raw_fdi_data():
    finding = raw_finding("47", "FILLING", 0.80)
    finding["patient_name"] = "must not leave DENTAI"
    finding["image_url"] = "https://storage.invalid/opg"
    finding["provenance"]["raw_fdi"] = "37"
    evidence = build_product_finding_evidence([finding])
    payload_text = build_groq_request_payload(
        "openai/gpt-oss-20b",
        evidence,
    )["messages"][1]["content"]

    assert "patient_name" not in payload_text
    assert "image_url" not in payload_text
    assert "raw_fdi" not in payload_text
    assert "bounding_box" not in payload_text
    assert "source_image_id" not in payload_text



@pytest.mark.asyncio
async def test_authentication_failure_is_not_retried_per_tooth():
    class AuthenticationFailureProvider:
        model = "openai/gpt-oss-20b"

        def __init__(self):
            self.calls = 0

        async def summarize(self, _received):
            self.calls += 1
            request = groq_module.httpx.Request("POST", "https://api.groq.com")
            response = groq_module.httpx.Response(401, request=request)
            raise groq_module.httpx.HTTPStatusError(
                "unauthorized",
                request=request,
                response=response,
            )

    provider = AuthenticationFailureProvider()
    result = await summarize_product_findings(
        provider,
        findings_for_teeth("16", "24", "36"),
    )

    assert result["status"] == "UNAVAILABLE"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_production_sized_fixture_no_longer_uses_one_whole_analysis_request():
    provider = RecordingProvider()
    findings = production_findings()
    before = deepcopy(findings)

    result = await summarize_product_findings(provider, findings)

    assert result["status"] == "AVAILABLE"
    assert [len({item.tooth_fdi for item in call}) for call in provider.calls] == [3, 2]
    assert {item["tooth_fdi"] for item in result["tooth_explanations"]} == {
        "16",
        "24",
        "36",
        "37",
        "47",
    }
    assert findings == before
