import { describe, expect, it } from "vitest";
import type {
  DentalFinding,
  GroqClinicalSummary,
  GroqFindingEvidence
} from "../api/types";
import {
  explanationForGroup,
  modelScoreLanguage,
  parseClinicalSummary,
  reviewStatusLanguage,
  technicalDetailsForFinding
} from "./clinicalSummary";
import { groupFindingsByTooth } from "./opg";

function finding(
  id: string,
  toothCode: string,
  findingType: string,
  score: number,
  reviewStatus: DentalFinding["review_status"] = "PENDING"
): DentalFinding {
  return {
    id,
    patient_id: "patient",
    analysis_id: "analysis",
    tooth_code: toothCode,
    finding_type: findingType,
    description: "Deterministic DENTAI finding",
    source: "AI",
    confidence: score,
    provenance: {
      source_model: "DENTAI Unified V5",
      model_version: "dentai-unified-v5",
      raw_score: score,
      uncertainty: "LOW_CONFIDENCE",
      uncertainty_reason: "FDI_LOW_CONFIDENCE_OR_UNRESOLVED",
      review_required: true,
      review_reasons: ["FDI_LOW_CONFIDENCE_OR_UNRESOLVED"],
      bounding_box: [10, 20, 30, 40]
    },
    review_status: reviewStatus,
    confirmed_by: null,
    confirmed_at: null,
    created_at: "2026-08-17T00:00:00Z"
  };
}

function evidence(
  id: string,
  toothCode: string,
  findingType: string,
  score: number
): GroqFindingEvidence {
  return {
    evidence_id: id,
    tooth_fdi: toothCode,
    finding_type: findingType,
    model_score: score,
    review_required: true,
    uncertainty: "LOW_CONFIDENCE",
    uncertainty_reason: "FDI_LOW_CONFIDENCE_OR_UNRESOLVED",
    review_reasons: ["FDI_LOW_CONFIDENCE_OR_UNRESOLVED"],
    source_model: "DENTAI Unified V5",
    model_version: "dentai-unified-v5"
  };
}

function summary(items: GroqFindingEvidence[]): GroqClinicalSummary {
  const byTooth = new Map<string, string[]>();
  for (const item of items) {
    byTooth.set(item.tooth_fdi, [...(byTooth.get(item.tooth_fdi) ?? []), item.evidence_id]);
  }
  return {
    doctor_summary: "AI-assisted explanation of supplied DENTAI evidence.",
    tooth_explanations: Array.from(byTooth, ([toothFdi, evidenceIds]) => ({
      tooth_fdi: toothFdi,
      evidence_ids: evidenceIds,
      headline: "Existing restoration detected",
      clinical_explanation: "DENTAI identified features consistent with the supplied finding.",
      review_explanation: "DENTAI marked this AI-generated finding for clinician review."
    })),
    important_changes: [],
    monitoring_points: [],
    questions_for_doctor: [],
    patient_message_draft: "",
    canonical_evidence: Object.fromEntries(items.map((item) => [item.evidence_id, item]))
  };
}

describe("clinical summary utilities", () => {
  it("falls back when clinical_summary is missing or Groq is unavailable", () => {
    expect(parseClinicalSummary(undefined)).toBeNull();
    expect(parseClinicalSummary({ status: "UNAVAILABLE" })).toBeNull();
  });

  it("matches one evidence ID to canonical DENTAI data", () => {
    const group = groupFindingsByTooth([
      finding("a", "37", "FILLING", 0.8945)
    ])[0];
    const parsed = parseClinicalSummary(summary([
      evidence("finding_0", "37", "FILLING", 0.8945)
    ]));
    expect(explanationForGroup(parsed, group)?.headline).toBe("Existing restoration detected");
  });

  it("supports multiple findings on one tooth and multiple teeth", () => {
    const items = [
      evidence("finding_0", "16", "CROWN", 0.9231),
      evidence("finding_1", "16", "ROOT_CANAL_TREATMENT", 0.6951),
      evidence("finding_2", "37", "FILLING", 0.8945)
    ];
    const parsed = parseClinicalSummary(summary(items));
    const tooth16 = groupFindingsByTooth([
      finding("a", "16", "CROWN", 0.9231),
      finding("b", "16", "ROOT_CANAL_TREATMENT", 0.6951)
    ])[0];
    expect(explanationForGroup(parsed, tooth16)?.evidence_ids)
      .toEqual(["finding_0", "finding_1"]);
  });

  it.each(["PENDING", "CONFIRMED", "REJECTED"] as const)(
    "keeps the same Groq explanation when live review status is %s",
    (reviewStatus) => {
      const group = groupFindingsByTooth([
        finding("a", "37", "FILLING", 0.8945, reviewStatus)
      ])[0];
      const parsed = parseClinicalSummary(summary([
        evidence("finding_0", "37", "FILLING", 0.8945)
      ]));
      expect(explanationForGroup(parsed, group)?.headline)
        .toBe("Existing restoration detected");
    }
  );

  it("rejects unknown, duplicate, omitted, or wrong-tooth evidence IDs", () => {
    const base = summary([
      evidence("finding_0", "37", "FILLING", 0.8945),
      evidence("finding_1", "47", "FILLING", 0.6951)
    ]);
    const invalid = [
      { ...base, tooth_explanations: [
        { ...base.tooth_explanations[0], evidence_ids: ["finding_99"] },
        base.tooth_explanations[1]
      ] },
      { ...base, tooth_explanations: [
        base.tooth_explanations[0],
        { ...base.tooth_explanations[1], evidence_ids: ["finding_0"] }
      ] },
      { ...base, tooth_explanations: [base.tooth_explanations[0]] },
      { ...base, tooth_explanations: [
        { ...base.tooth_explanations[0], evidence_ids: ["finding_1"] },
        { ...base.tooth_explanations[1], evidence_ids: ["finding_0"] }
      ] }
    ];
    for (const candidate of invalid) {
      expect(parseClinicalSummary(candidate)).toBeNull();
    }
  });

  it("does not trust narrative IDs when canonical DENTAI values differ", () => {
    const parsed = parseClinicalSummary(summary([
      evidence("finding_0", "37", "CARIES", 0.8945)
    ]));
    const group = groupFindingsByTooth([
      finding("a", "37", "FILLING", 0.8945)
    ])[0];
    expect(explanationForGroup(parsed, group)).toBeNull();
  });

  it("renders current review language from DentalFinding state", () => {
    expect(reviewStatusLanguage("PENDING"))
      .toBe("This finding is awaiting clinician review.");
    expect(reviewStatusLanguage("CONFIRMED"))
      .toBe("This finding has been confirmed by the reviewing clinician.");
    expect(reviewStatusLanguage("REJECTED")).toContain("was rejected");
  });

  it("renders numeric model-score language deterministically without confidence labels", () => {
    const text = modelScoreLanguage(0.8945);
    expect(text).toBe(
      "Model score: 0.8945. This score represents supporting AI evidence and is not an " +
      "independent diagnostic probability."
    );
    expect(text).not.toMatch(/high confidence|moderate confidence|low confidence/i);
  });

  it("preserves technical details from canonical DentalFinding data", () => {
    expect(technicalDetailsForFinding(
      finding("a", "37", "FILLING", 0.8945)
    )).toEqual({
      confidence: 0.8945,
      raw_score: 0.8945,
      review_status: "PENDING",
      review_required: true,
      uncertainty: "LOW_CONFIDENCE",
      uncertainty_reason: "FDI_LOW_CONFIDENCE_OR_UNRESOLVED",
      review_reasons: ["FDI_LOW_CONFIDENCE_OR_UNRESOLVED"],
      source_model: "DENTAI Unified V5",
      model_version: "dentai-unified-v5",
      bounding_box: [10, 20, 30, 40]
    });
  });
});
