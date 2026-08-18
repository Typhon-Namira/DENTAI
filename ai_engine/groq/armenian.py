import re

import httpx

from ai_engine.groq.provider import (
    SYSTEM_PROMPT,
    GroqClinicalSummary,
    GroqClinicalSummaryProvider,
    GroqFindingEvidence,
    build_groq_request_payload,
    validate_summary_against_evidence,
)

ARMENIAN_LANGUAGE_INSTRUCTION = """
LANGUAGE REQUIREMENT — NATURAL EASTERN ARMENIAN ONLY

Every narrative string in the JSON response must be written in fluent, idiomatic Eastern
Armenian using Armenian script. Do not answer in English. Do not use Latin-script dental
terms, translated-English sentence structure, mixed Armenian/English prose, or robotic
word-for-word translation.

The only values that may remain non-Armenian are machine identifiers that are required by
the schema, such as tooth_fdi and evidence_ids. Do not repeat those identifiers inside
narrative prose unless clinically necessary to identify the tooth, and use only the numeric
FDI tooth number when doing so.

VOICE AND QUALITY
- Write as an experienced Armenian dental clinician explaining a radiographic observation
  clearly to another clinician.
- Use natural Eastern Armenian syntax, short coherent sentences, and standard dental
  vocabulary that would sound normal in a real Armenian dental clinic.
- Prefer direct human wording over bureaucratic or literal translation.
- Avoid repetitive phrases such as repeatedly saying that the AI "detected" something.
  Vary the wording naturally while preserving exactly the same evidence.
- Keep the headline brief and clinically meaningful.
- The clinical_explanation should explain what the supplied DENTAI evidence indicates in
  plain professional Armenian, without introducing any new interpretation.
- The review_explanation should clearly state what still requires clinician confirmation,
  especially when review_required or uncertainty is present.
- Monitoring points must be practical and readable, but must not invent treatment,
  urgency, disease progression, or a future disease-occurrence date.
- The patient_message_draft must be warm, calm, understandable Eastern Armenian, with no
  technical AI jargon, no model score, no frightening language, and no claim of a final
  diagnosis.

SAFETY
Preserve exactly the supplied DENTAI evidence. Do not add, remove, strengthen, weaken, or
reinterpret findings. Do not invent diagnosis, treatment, certainty, timing, urgency, tooth
identity, score meaning, or clinical facts. Model scores are supporting AI evidence only
and are not independent diagnostic probabilities.

Return only the required JSON object. All narrative fields must satisfy these Armenian
language and clinical-writing requirements.
"""

_ARMENIAN = re.compile(r"[\u0531-\u058F]")
_LATIN = re.compile(r"[A-Za-z]")


class GroqArmenianLanguageError(ValueError):
    """Groq narrative was not returned as Armenian-only clinical language."""


def _narrative_strings(summary: GroqClinicalSummary) -> list[str]:
    values = [
        summary.doctor_summary,
        summary.patient_message_draft,
        *summary.important_changes,
        *summary.monitoring_points,
        *summary.questions_for_doctor,
    ]
    for explanation in summary.tooth_explanations:
        values.extend(
            [
                explanation.headline,
                explanation.clinical_explanation,
                explanation.review_explanation,
            ]
        )
    return [value.strip() for value in values if value.strip()]


def validate_armenian_summary(summary: GroqClinicalSummary) -> GroqClinicalSummary:
    """Reject English or mixed-script Groq prose before it reaches the product UI."""
    for value in _narrative_strings(summary):
        if _LATIN.search(value) or not _ARMENIAN.search(value):
            raise GroqArmenianLanguageError("Groq narrative must be Eastern Armenian only")
    return summary


class ArmenianGroqClinicalSummaryProvider(GroqClinicalSummaryProvider):
    """Evidence-bound Groq renderer that accepts only natural Eastern Armenian prose."""

    async def summarize(
        self,
        evidence: list[GroqFindingEvidence],
    ) -> GroqClinicalSummary:
        payload = build_groq_request_payload(self.model, evidence)
        payload["messages"][0]["content"] = (
            SYSTEM_PROMPT.rstrip() + "\n\n" + ARMENIAN_LANGUAGE_INSTRUCTION.strip()
        )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        summary = GroqClinicalSummary.model_validate_json(content)
        summary = validate_summary_against_evidence(summary, evidence)
        return validate_armenian_summary(summary)
