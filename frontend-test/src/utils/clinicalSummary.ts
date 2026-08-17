import type {
  DentalFinding,
  GroqClinicalSummary,
  GroqFindingEvidence,
  GroqToothExplanation
} from "../api/types";
import type { ToothFindingGroup } from "./opg";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringArray(value: unknown): string[] | null {
  if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) return null;
  return value;
}

function parseEvidence(value: unknown): GroqFindingEvidence | null {
  if (!isRecord(value)) return null;
  const reviewReasons = stringArray(value.review_reasons);
  if (
    typeof value.evidence_id !== "string" ||
    typeof value.tooth_fdi !== "string" ||
    typeof value.finding_type !== "string" ||
    typeof value.model_score !== "number" ||
    !Number.isFinite(value.model_score) ||
    "review_status" in value ||
    typeof value.review_required !== "boolean" ||
    typeof value.uncertainty !== "string" ||
    !(typeof value.uncertainty_reason === "string" || value.uncertainty_reason === null) ||
    reviewReasons === null ||
    typeof value.source_model !== "string" ||
    typeof value.model_version !== "string"
  ) {
    return null;
  }
  return {
    evidence_id: value.evidence_id,
    tooth_fdi: value.tooth_fdi,
    finding_type: value.finding_type,
    model_score: value.model_score,
    review_required: value.review_required,
    uncertainty: value.uncertainty,
    uncertainty_reason: value.uncertainty_reason,
    review_reasons: reviewReasons,
    source_model: value.source_model,
    model_version: value.model_version
  };
}

function parseCanonicalEvidence(value: unknown): Record<string, GroqFindingEvidence> | null {
  if (!isRecord(value)) return null;
  const result: Record<string, GroqFindingEvidence> = {};
  for (const [evidenceId, rawEvidence] of Object.entries(value)) {
    const evidence = parseEvidence(rawEvidence);
    if (!evidence || evidence.evidence_id !== evidenceId) return null;
    result[evidenceId] = evidence;
  }
  return result;
}

function parseToothExplanation(value: unknown): GroqToothExplanation | null {
  if (!isRecord(value)) return null;
  const evidenceIds = stringArray(value.evidence_ids);
  if (
    evidenceIds === null ||
    typeof value.tooth_fdi !== "string" ||
    typeof value.headline !== "string" ||
    typeof value.clinical_explanation !== "string" ||
    typeof value.review_explanation !== "string"
  ) {
    return null;
  }
  return {
    tooth_fdi: value.tooth_fdi,
    evidence_ids: evidenceIds,
    headline: value.headline,
    clinical_explanation: value.clinical_explanation,
    review_explanation: value.review_explanation
  };
}

export function parseClinicalSummary(value: unknown): GroqClinicalSummary | null {
  if (!isRecord(value) || value.status === "UNAVAILABLE") return null;
  if (
    value.status !== undefined &&
    value.status !== "AVAILABLE" &&
    value.status !== "PARTIAL"
  ) {
    return null;
  }

  const importantChanges = stringArray(value.important_changes);
  const monitoringPoints = stringArray(value.monitoring_points);
  const questionsForDoctor = stringArray(value.questions_for_doctor);
  const canonicalEvidence = parseCanonicalEvidence(value.canonical_evidence);
  const declaredFailures = value.failed_tooth_fdis === undefined
    ? []
    : stringArray(value.failed_tooth_fdis);
  if (
    typeof value.doctor_summary !== "string" ||
    !Array.isArray(value.tooth_explanations) ||
    importantChanges === null ||
    monitoringPoints === null ||
    questionsForDoctor === null ||
    typeof value.patient_message_draft !== "string" ||
    canonicalEvidence === null ||
    declaredFailures === null
  ) {
    return null;
  }

  const parsedExplanations = value.tooth_explanations
    .map(parseToothExplanation)
    .filter((item): item is GroqToothExplanation => item !== null);
  const explanationCounts = new Map<string, number>();
  for (const explanation of parsedExplanations) {
    explanationCounts.set(
      explanation.tooth_fdi,
      (explanationCounts.get(explanation.tooth_fdi) ?? 0) + 1
    );
  }

  const validExplanations: GroqToothExplanation[] = [];
  for (const explanation of parsedExplanations) {
    if (explanationCounts.get(explanation.tooth_fdi) !== 1) continue;

    const expectedIds = Object.values(canonicalEvidence)
      .filter((item) => item.tooth_fdi === explanation.tooth_fdi)
      .map((item) => item.evidence_id);
    const returnedIds = explanation.evidence_ids;
    const returnedSet = new Set(returnedIds);
    if (
      expectedIds.length === 0 ||
      returnedIds.length !== returnedSet.size ||
      returnedIds.some((evidenceId) => {
        const evidence = canonicalEvidence[evidenceId];
        return !evidence || evidence.tooth_fdi !== explanation.tooth_fdi;
      }) ||
      returnedSet.size !== expectedIds.length ||
      expectedIds.some((evidenceId) => !returnedSet.has(evidenceId))
    ) {
      continue;
    }
    validExplanations.push(explanation);
  }

  if (validExplanations.length === 0) return null;

  const eligibleTeeth = new Set(
    Object.values(canonicalEvidence).map((item) => item.tooth_fdi)
  );
  const explainedTeeth = new Set(validExplanations.map((item) => item.tooth_fdi));
  const failedToothFdis = Array.from(new Set([
    ...declaredFailures,
    ...Array.from(eligibleTeeth).filter((tooth) => !explainedTeeth.has(tooth))
  ])).sort();
  const status = explainedTeeth.size === eligibleTeeth.size ? "AVAILABLE" : "PARTIAL";

  return {
    status,
    doctor_summary: value.doctor_summary,
    tooth_explanations: validExplanations,
    important_changes: importantChanges,
    monitoring_points: monitoringPoints,
    questions_for_doctor: questionsForDoctor,
    patient_message_draft: value.patient_message_draft,
    canonical_evidence: canonicalEvidence,
    failed_tooth_fdis: status === "AVAILABLE" ? [] : failedToothFdis
  };
}

function findingFingerprint(finding: DentalFinding): string | null {
  const provenance = finding.provenance;
  if (
    !finding.tooth_code ||
    typeof finding.confidence !== "number" ||
    !Number.isFinite(finding.confidence) ||
    !provenance ||
    typeof provenance.review_required !== "boolean" ||
    typeof provenance.uncertainty !== "string" ||
    !(
      typeof provenance.uncertainty_reason === "string" ||
      provenance.uncertainty_reason === null
    ) ||
    !Array.isArray(provenance.review_reasons) ||
    !provenance.review_reasons.every((item) => typeof item === "string") ||
    typeof provenance.source_model !== "string" ||
    typeof provenance.model_version !== "string"
  ) {
    return null;
  }
  return JSON.stringify({
    tooth_fdi: finding.tooth_code,
    finding_type: finding.finding_type,
    model_score: finding.confidence,
    review_required: provenance.review_required,
    uncertainty: provenance.uncertainty,
    uncertainty_reason: provenance.uncertainty_reason,
    review_reasons: provenance.review_reasons,
    source_model: provenance.source_model,
    model_version: provenance.model_version
  });
}

function evidenceFingerprint(evidence: GroqFindingEvidence): string {
  const { evidence_id: _, ...identity } = evidence;
  return JSON.stringify(identity);
}

export function explanationForGroup(
  summary: GroqClinicalSummary | null,
  group: ToothFindingGroup | null
): GroqToothExplanation | null {
  if (!summary || !group?.toothCode) return null;
  const matches = summary.tooth_explanations.filter(
    (item) => item.tooth_fdi === group.toothCode
  );
  if (matches.length !== 1) return null;

  const findingEvidence = group.findings.map(findingFingerprint);
  if (findingEvidence.some((item) => item === null)) return null;
  const returnedEvidence = matches[0].evidence_ids.map(
    (evidenceId) => summary.canonical_evidence[evidenceId]
  );
  if (returnedEvidence.some((item) => item === undefined)) return null;

  const expected = (findingEvidence as string[]).sort();
  const returned = (returnedEvidence as GroqFindingEvidence[])
    .map(evidenceFingerprint)
    .sort();
  if (expected.length !== returned.length) return null;
  return expected.every((item, index) => item === returned[index]) ? matches[0] : null;
}

export function reviewStatusLanguage(
  status: DentalFinding["review_status"]
): string {
  if (status === "CONFIRMED") {
    return "This finding has been confirmed by the reviewing clinician.";
  }
  if (status === "REJECTED") {
    return (
      "This finding was rejected by the reviewing clinician and is not treated as a " +
      "confirmed finding."
    );
  }
  return "This finding is awaiting clinician review.";
}

export function modelScoreLanguage(score: number | null): string {
  if (typeof score !== "number" || !Number.isFinite(score)) {
    return "Model score was not provided.";
  }
  return (
    "Model score: " + score.toFixed(4) +
    ". This score represents supporting AI evidence and is not an independent " +
    "diagnostic probability."
  );
}

export function technicalDetailsForFinding(finding: DentalFinding) {
  return {
    confidence: finding.confidence,
    raw_score: finding.provenance?.raw_score ?? null,
    review_status: finding.review_status,
    review_required: finding.provenance?.review_required ?? null,
    uncertainty: finding.provenance?.uncertainty ?? null,
    uncertainty_reason: finding.provenance?.uncertainty_reason ?? null,
    review_reasons: finding.provenance?.review_reasons ?? [],
    source_model: finding.provenance?.source_model ?? null,
    model_version: finding.provenance?.model_version ?? null,
    bounding_box: finding.provenance?.bounding_box ?? null,
    raw_fdi: finding.provenance?.raw_fdi ?? null,
    fdi_confidence: finding.provenance?.fdi_confidence ?? null,
    fdi_was_changed: finding.provenance?.fdi_was_changed ?? null,
    duplicate_cleanup_applied:
      finding.provenance?.duplicate_cleanup_applied ?? null,
    fdi_review_required: finding.provenance?.fdi_review_required ?? null,
    tooth_detection_instance_id:
      finding.provenance?.tooth_detection_instance_id ?? null,
    quadrant_candidates: finding.provenance?.quadrant_candidates ?? [],
    resolved_quadrant: finding.provenance?.resolved_quadrant ?? null,
    side_constraint_applied:
      finding.provenance?.side_constraint_applied ?? null,
    side_constraint_overrode_raw_quadrant:
      finding.provenance?.side_constraint_overrode_raw_quadrant ?? null
  };
}

export function humanizeFindingType(value: string): string {
  const words = value.toLowerCase().replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
