import { describe, expect, it } from "vitest";
import type {
  DentalFinding,
  GroqClinicalSummary,
  GroqFindingEvidence
} from "../api/types";
import {
  explanationForGroup,
  parseClinicalSummary,
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
  score: number,
  reviewStatus: DentalFinding["review_status"] = "PENDING"
): GroqFindingEvidence {
  return {
    evidence_id: id,
    tooth_fdi: toothCode,
    finding_type: findingType,
    model_score: score,
    review_status: reviewStatus,
    review_required: true,
    uncertainty: "LOW_CONFIDENCE",
    uncertainty_reason: "FDI_LOW_CONFIDENCE_OR_UNRESOLVED",
    review_reasons: ["FDI_LOW_CONFIDENCE_OR_UNRESOLVED"],
    source_model: "DENTAI Unified V5",
    model_version: "dentai-unified-v5"
  };
}

function summary(items: GroqFindingEvidence[]): GroqClinicalSummary {
  return {
    doctor_summary: "AI-assisted explanation of supplied DENTAI evidence.",
    tooth_explanations: [{
      tooth_fdi: items[0].tooth_fdi,
      evidence: items,
      headline: "Existing restoration detected",
      clinical_explanation: "DENTAI identified features consistent with the supplied finding.",
      confidence_explanation: "The model score is supporting AI evidence.",
      review_explanation: "Clinician review is required."
    }],
    important_changes: [],
    monitoring_points: [],
    questions_for_doctor: [],
    patient_message_draft: ""
  };
}

describe("clinical summary utilities", () => {
  it("falls back when clinical_summary is missing or Groq is unavailable", () => {
    expect(parseClinicalSummary(undefined)).toBeNull();
    expect(parseClinicalSummary({ status: "UNAVAILABLE" })).toBeNull();
  });

  it("matches a one-finding explanation only to its exact DENTAI tooth evidence", () => {
    const dentaiFinding = finding("a", "37", "FILLING", 0.8945);
    const group = groupFindingsByTooth([dentaiFinding])[0];
    const parsed = parseClinicalSummary(summary([
      evidence("finding_0", "37", "FILLING", 0.8945)
    ]));
    expect(explanationForGroup(parsed, group)?.headline).toBe("Existing restoration detected");
  });

  it("supports multiple findings on one tooth without merging their identities", () => {
    const findings = [
      finding("a", "37", "FILLING", 0.8945),
      finding("b", "37", "ROOT_CANAL_TREATMENT", 0.9516)
    ];
    const group = groupFindingsByTooth(findings)[0];
    const parsed = parseClinicalSummary(summary([
      evidence("finding_0", "37", "FILLING", 0.8945),
      evidence("finding_1", "37", "ROOT_CANAL_TREATMENT", 0.9516)
    ]));
    expect(explanationForGroup(parsed, group)?.evidence).toHaveLength(2);
  });

  it("rejects a narrative that invents a tooth or finding", () => {
    const group = groupFindingsByTooth([
      finding("a", "37", "FILLING", 0.8945)
    ])[0];
    expect(explanationForGroup(summary([
      evidence("finding_0", "36", "CARIES", 0.8945)
    ]), group)).toBeNull();
  });

  it("falls back after review status changes so stale narrative is not shown", () => {
    const group = groupFindingsByTooth([
      finding("a", "37", "FILLING", 0.8945, "CONFIRMED")
    ])[0];
    expect(explanationForGroup(summary([
      evidence("finding_0", "37", "FILLING", 0.8945, "PENDING")
    ]), group)).toBeNull();
  });

  it("preserves exact machine evidence in technical details", () => {
    const details = technicalDetailsForFinding(
      finding("a", "37", "FILLING", 0.8945)
    );
    expect(details).toEqual({
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
