import asyncio
import json
import math

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

PRODUCT_MODEL_SCORE_THRESHOLD = 0.60
MAX_GROQ_TEETH_PER_BATCH = 3
MAX_GROQ_CONCURRENCY = 2
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
        tooth_code = finding.get("tooth_code")
        if tooth_code is None:
            # Groq remains tooth-specific and must never promote raw_fdi to authority.
            continue
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
                tooth_fdi=tooth_code,
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


def group_evidence_by_tooth(
    evidence: list[GroqFindingEvidence],
) -> list[list[GroqFindingEvidence]]:
    grouped: dict[str, list[GroqFindingEvidence]] = {}
    for item in evidence:
        grouped.setdefault(item.tooth_fdi, []).append(item)
    return list(grouped.values())


def batch_tooth_evidence(
    tooth_groups: list[list[GroqFindingEvidence]],
) -> list[list[GroqFindingEvidence]]:
    return [
        [item for group in tooth_groups[index : index + MAX_GROQ_TEETH_PER_BATCH] for item in group]
        for index in range(0, len(tooth_groups), MAX_GROQ_TEETH_PER_BATCH)
    ]


def _auth_failure(error: Exception) -> bool:
    return isinstance(error, httpx.HTTPStatusError) and error.response.status_code in {401, 403}


def _unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


async def _attempt_summary(
    provider: GroqClinicalSummaryProvider,
    evidence: list[GroqFindingEvidence],
    semaphore: asyncio.Semaphore,
    *,
    retry_mode: str,
) -> tuple[GroqClinicalSummary | None, Exception | None]:
    try:
        async with semaphore:
            return await provider.summarize(evidence), None
    except Exception as error:
        logger.warning(
            "groq_clinical_summary_batch_unavailable",
            exception_class=type(error).__name__,
            reason=safe_failure_reason(error),
            batch_tooth_count=len({item.tooth_fdi for item in evidence}),
            evidence_count=len(evidence),
            model=getattr(provider, "model", "unknown"),
            retry_mode=retry_mode,
            tooth_fdis=sorted({item.tooth_fdi for item in evidence}),
        )
        return None, error


async def _render_batch(
    provider: GroqClinicalSummaryProvider,
    evidence: list[GroqFindingEvidence],
    semaphore: asyncio.Semaphore,
) -> tuple[list[GroqClinicalSummary], list[str]]:
    tooth_groups = group_evidence_by_tooth(evidence)
    tooth_fdis = [group[0].tooth_fdi for group in tooth_groups]
    summary, error = await _attempt_summary(
        provider,
        evidence,
        semaphore,
        retry_mode="batch",
    )
    if summary is not None:
        return [summary], []

    if len(tooth_groups) == 1 or error is None or _auth_failure(error):
        return [], tooth_fdis

    retries = await asyncio.gather(
        *(
            _attempt_summary(
                provider,
                group,
                semaphore,
                retry_mode="single_tooth",
            )
            for group in tooth_groups
        )
    )
    successful: list[GroqClinicalSummary] = []
    failed: list[str] = []
    for group, (retry_summary, _) in zip(tooth_groups, retries, strict=True):
        if retry_summary is None:
            failed.append(group[0].tooth_fdi)
        else:
            successful.append(retry_summary)
    return successful, failed


def _aggregate_summaries(
    summaries: list[GroqClinicalSummary],
    evidence: list[GroqFindingEvidence],
    failed_tooth_fdis: list[str],
) -> dict:
    explanations = [
        explanation for summary in summaries for explanation in summary.tooth_explanations
    ]
    successful_teeth = {explanation.tooth_fdi for explanation in explanations}
    eligible_teeth = {item.tooth_fdi for item in evidence}
    failed_teeth = sorted((eligible_teeth - successful_teeth) | set(failed_tooth_fdis))

    if not successful_teeth:
        status = "UNAVAILABLE"
    elif successful_teeth == eligible_teeth:
        status = "AVAILABLE"
        failed_teeth = []
    else:
        status = "PARTIAL"

    result = {
        "status": status,
        "doctor_summary": " ".join(
            _unique_strings([summary.doctor_summary for summary in summaries])
        ),
        "tooth_explanations": [explanation.model_dump(mode="json") for explanation in explanations],
        "important_changes": _unique_strings(
            [item for summary in summaries for item in summary.important_changes]
        ),
        "monitoring_points": _unique_strings(
            [item for summary in summaries for item in summary.monitoring_points]
        ),
        "questions_for_doctor": _unique_strings(
            [item for summary in summaries for item in summary.questions_for_doctor]
        ),
        "patient_message_draft": " ".join(
            _unique_strings([summary.patient_message_draft for summary in summaries])
        ),
        "canonical_evidence": {
            key: item.model_dump(mode="json")
            for key, item in canonical_evidence_map(evidence).items()
        },
    }
    if failed_teeth:
        result["failed_tooth_fdis"] = failed_teeth
    return result


async def summarize_product_findings(
    provider: GroqClinicalSummaryProvider | None,
    findings: list[dict],
) -> dict | None:
    """Render deidentified DENTAI evidence in bounded, independently validated batches."""
    if provider is None:
        return None

    try:
        evidence = build_product_finding_evidence(findings)
    except Exception as error:
        logger.warning(
            "groq_clinical_summary_batch_unavailable",
            exception_class=type(error).__name__,
            reason=safe_failure_reason(error),
            batch_tooth_count=0,
            evidence_count=0,
            model=getattr(provider, "model", "unknown"),
            retry_mode="batch",
            tooth_fdis=[],
        )
        return {"status": "UNAVAILABLE"}

    if not evidence:
        return None

    batches = batch_tooth_evidence(group_evidence_by_tooth(evidence))
    semaphore = asyncio.Semaphore(MAX_GROQ_CONCURRENCY)
    rendered = await asyncio.gather(
        *(_render_batch(provider, batch, semaphore) for batch in batches)
    )
    summaries = [summary for batch_summaries, _ in rendered for summary in batch_summaries]
    failed_tooth_fdis = [
        tooth_fdi for _, batch_failures in rendered for tooth_fdi in batch_failures
    ]
    return _aggregate_summaries(summaries, evidence, failed_tooth_fdis)
