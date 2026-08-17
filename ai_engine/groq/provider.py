import json
import math

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

PRODUCT_MODEL_SCORE_THRESHOLD = 0.60
logger = structlog.get_logger(__name__)


class StrictGroqModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GroqFindingEvidence(StrictGroqModel):
    evidence_id: str = Field(pattern=r"^finding_[0-9]+$")
    tooth_fdi: str = Field(pattern=r"^[1-4][1-8]$")
    finding_type: str = Field(min_length=1)
    model_score: float = Field(ge=0, le=1)
    review_required: bool
    uncertainty: str = Field(min_length=1)
    uncertainty_reason: str | None
    review_reasons: list[str]
    source_model: str = Field(min_length=1)
    model_version: str = Field(min_length=1)


class GroqToothExplanation(StrictGroqModel):
    tooth_fdi: str = Field(pattern=r"^[1-4][1-8]$")
    evidence_ids: list[str]
    headline: str = Field(min_length=1)
    clinical_explanation: str = Field(min_length=1)
    review_explanation: str = Field(min_length=1)


class GroqClinicalSummary(StrictGroqModel):
    doctor_summary: str = Field(min_length=1)
    tooth_explanations: list[GroqToothExplanation]
    important_changes: list[str]
    monitoring_points: list[str]
    questions_for_doctor: list[str]
    patient_message_draft: str


class GroqEvidenceBindingError(ValueError):
    """Groq narrative references do not exactly cover canonical DENTAI evidence."""


SYSTEM_PROMPT = """You are not a dental diagnostic model.
You do not analyze radiographs.
You do not perform clinical inference.
You are a controlled clinical-language renderer.

Rewrite only the supplied DENTAI evidence into clear human-readable language.
Every factual clinical statement must be directly supported by a supplied field.
If the evidence does not support a statement, omit it.

Never add findings, diagnoses, treatment recommendations, urgency, anatomical claims,
or interpretations that are absent from the supplied DENTAI evidence.

Create exactly one tooth_explanations item for each distinct tooth_fdi. Reference every
finding for that tooth exactly once using only its evidence_id. Do not echo model_score,
finding_type, review_required, uncertainty, review reasons, or model provenance in the
response. Do not omit, duplicate, merge, or invent evidence IDs.

Do not classify model_score as high, moderate, or low confidence, and do not describe it
as a diagnostic or disease probability. Numeric score language is rendered separately by
the DENTAI application. You may translate supplied uncertainty and review reasons into
cautious plain language, but do not broaden their meaning. If
FDI_LOW_CONFIDENCE_OR_UNRESOLVED is supplied, explain only that DENTAI marked additional
uncertainty around tooth-number assignment and that the highlighted region should be
verified by the clinician.

Explain only whether DENTAI marked review_required. Never claim that clinician review is
pending, confirmed, or rejected; mutable review state is not supplied to you.
Return only the requested structured JSON."""


def build_product_finding_evidence(findings: list[dict]) -> list[GroqFindingEvidence]:
    """Build deidentified narrative input without mutating DENTAI findings."""
    evidence: list[GroqFindingEvidence] = []
    for finding in findings:
        score = finding.get("confidence")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or score < PRODUCT_MODEL_SCORE_THRESHOLD
        ):
            continue

        provenance = finding.get("provenance")
        if not isinstance(provenance, dict):
            raise TypeError("product-visible finding provenance is required")
        review_required = provenance.get("review_required")
        if not isinstance(review_required, bool):
            raise TypeError("product-visible finding review_required must be boolean")

        evidence.append(
            GroqFindingEvidence(
                evidence_id=f"finding_{len(evidence)}",
                tooth_fdi=finding["tooth_code"],
                finding_type=finding["finding_type"],
                model_score=score,
                review_required=review_required,
                uncertainty=provenance["uncertainty"],
                uncertainty_reason=provenance.get("uncertainty_reason"),
                review_reasons=provenance["review_reasons"],
                source_model=provenance["source_model"],
                model_version=provenance["model_version"],
            )
        )
    return evidence


def canonical_evidence_map(
    evidence: list[GroqFindingEvidence],
) -> dict[str, GroqFindingEvidence]:
    return {item.evidence_id: item for item in evidence}


def validate_summary_against_evidence(
    summary: GroqClinicalSummary,
    evidence: list[GroqFindingEvidence],
) -> GroqClinicalSummary:
    """Validate complete ID coverage without trusting Groq to copy canonical values."""
    expected = canonical_evidence_map(evidence)
    expected_teeth = {item.tooth_fdi for item in evidence}
    returned_teeth: set[str] = set()
    seen: set[str] = set()

    for explanation in summary.tooth_explanations:
        if explanation.tooth_fdi in returned_teeth:
            raise GroqEvidenceBindingError("duplicate tooth explanation")
        returned_teeth.add(explanation.tooth_fdi)
        if not explanation.evidence_ids:
            raise GroqEvidenceBindingError("tooth explanation has no evidence IDs")

        for evidence_id in explanation.evidence_ids:
            original = expected.get(evidence_id)
            if original is None:
                raise GroqEvidenceBindingError("unknown evidence ID")
            if evidence_id in seen:
                raise GroqEvidenceBindingError("duplicate evidence ID")
            if original.tooth_fdi != explanation.tooth_fdi:
                raise GroqEvidenceBindingError("wrong tooth and evidence association")
            seen.add(evidence_id)

    if returned_teeth != expected_teeth:
        raise GroqEvidenceBindingError("missing or unknown tooth explanation")
    if seen != set(expected):
        raise GroqEvidenceBindingError("evidence ID coverage is incomplete")
    return summary


def build_groq_request_payload(
    model: str,
    evidence: list[GroqFindingEvidence],
) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"findings": [item.model_dump(mode="json") for item in evidence]}
                ),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "dentai_clinical_summary",
                "schema": GroqClinicalSummary.model_json_schema(),
                "strict": True,
            },
        },
        "temperature": 0,
    }


class GroqClinicalSummaryProvider:
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str, timeout_seconds: int = 20):
        self.api_key, self.model, self.timeout_seconds = api_key, model, timeout_seconds

    async def summarize(
        self,
        evidence: list[GroqFindingEvidence],
    ) -> GroqClinicalSummary:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=build_groq_request_payload(self.model, evidence),
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        summary = GroqClinicalSummary.model_validate_json(content)
        return validate_summary_against_evidence(summary, evidence)


def safe_failure_reason(error: Exception) -> str:
    if isinstance(error, (httpx.TimeoutException, TimeoutError)):
        return "timeout"
    if isinstance(error, httpx.HTTPStatusError):
        return "http_status_error"
    if isinstance(error, httpx.HTTPError):
        return "transport_error"
    if isinstance(error, GroqEvidenceBindingError):
        return "evidence_binding_error"
    if isinstance(error, ValidationError):
        return "structured_response_validation_error"
    if isinstance(error, (KeyError, IndexError, TypeError, json.JSONDecodeError)):
        return "invalid_response_shape"
    return "unexpected_error"


async def summarize_product_findings(
    provider: GroqClinicalSummaryProvider | None,
    findings: list[dict],
) -> dict | None:
    """Keep narrative generation optional and isolated from DENTAI completion."""
    if provider is None:
        return None

    evidence: list[GroqFindingEvidence] = []
    try:
        evidence = build_product_finding_evidence(findings)
        if not evidence:
            return None
        summary = await provider.summarize(evidence)
        result = summary.model_dump(mode="json")
        result["canonical_evidence"] = {
            key: item.model_dump(mode="json")
            for key, item in canonical_evidence_map(evidence).items()
        }
        return result
    except Exception as error:
        logger.warning(
            "groq_clinical_summary_unavailable",
            exception_class=type(error).__name__,
            reason=safe_failure_reason(error),
            evidence_count=len(evidence),
            model=getattr(provider, "model", "unknown"),
        )
        return {"status": "UNAVAILABLE"}
