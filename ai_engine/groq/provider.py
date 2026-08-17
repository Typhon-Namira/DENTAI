import json
import math

import httpx
from pydantic import BaseModel, ConfigDict, Field

PRODUCT_MODEL_SCORE_THRESHOLD = 0.60


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
    evidence: list[GroqFindingEvidence]
    headline: str = Field(min_length=1)
    clinical_explanation: str = Field(min_length=1)
    confidence_explanation: str = Field(min_length=1)
    review_explanation: str = Field(min_length=1)


class GroqClinicalSummary(StrictGroqModel):
    doctor_summary: str = Field(min_length=1)
    tooth_explanations: list[GroqToothExplanation]
    important_changes: list[str]
    monitoring_points: list[str]
    questions_for_doctor: list[str]
    patient_message_draft: str


SYSTEM_PROMPT = """You are not a dental diagnostic model.
You do not analyze radiographs.
You do not perform clinical inference.
You are a controlled clinical-language renderer.

Rewrite only the supplied DENTAI evidence into clear human-readable language.

Every factual clinical statement in your response must be directly supported by
a supplied evidence field.

If the evidence does not support a statement, omit it.

Never add findings, diagnoses, treatment recommendations, urgency, anatomical
claims, or interpretations that are absent from the supplied DENTAI evidence.

Create exactly one tooth_explanations item for each distinct tooth_fdi. Copy every
finding evidence object for that tooth into its evidence list without changing any
field. Do not omit, duplicate, merge, or invent evidence. Do not interpret model_score
as an independent diagnostic probability. Translate internal enum and reason-code names
into plain language instead of repeating raw code tokens. Explain only whether DENTAI
marked review_required. Never claim that clinician review is pending, confirmed, or rejected;
that mutable application state is not supplied to you. Dentist review remains required.
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


def validate_summary_against_evidence(
    summary: GroqClinicalSummary,
    evidence: list[GroqFindingEvidence],
) -> GroqClinicalSummary:
    """Reject the entire narrative if any DENTAI evidence identity changes."""
    expected = {item.evidence_id: item for item in evidence}
    expected_teeth = {item.tooth_fdi for item in evidence}
    returned_teeth: set[str] = set()
    seen: set[str] = set()

    for explanation in summary.tooth_explanations:
        if explanation.tooth_fdi in returned_teeth:
            raise ValueError("Groq returned duplicate tooth explanations")
        returned_teeth.add(explanation.tooth_fdi)
        if not explanation.evidence:
            raise ValueError("Groq returned a tooth explanation without evidence")

        for returned in explanation.evidence:
            original = expected.get(returned.evidence_id)
            if original is None:
                raise ValueError("Groq returned an unknown evidence_id")
            if returned.evidence_id in seen:
                raise ValueError("Groq returned duplicate finding evidence")
            if returned.tooth_fdi != explanation.tooth_fdi or returned != original:
                raise ValueError("Groq changed DENTAI finding evidence")
            seen.add(returned.evidence_id)

    if returned_teeth != expected_teeth or seen != set(expected):
        raise ValueError("Groq omitted or added DENTAI tooth evidence")
    return summary


def build_groq_request_payload(
    model: str,
    evidence: list[GroqFindingEvidence],
) -> dict:
    schema = GroqClinicalSummary.model_json_schema()
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
                "schema": schema,
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


async def summarize_product_findings(
    provider: GroqClinicalSummaryProvider | None,
    findings: list[dict],
) -> dict | None:
    """Keep narrative generation optional and isolated from DENTAI completion."""
    if provider is None:
        return None
    try:
        evidence = build_product_finding_evidence(findings)
        if not evidence:
            return None
        summary = await provider.summarize(evidence)
        return summary.model_dump(mode="json")
    except Exception:
        # Groq is optional; no narrative failure may change the DENTAI result.
        return {"status": "UNAVAILABLE"}
