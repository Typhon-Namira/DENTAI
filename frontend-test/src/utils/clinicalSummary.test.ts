import { describe, expect, it } from "vitest";
import type {
  DentalFinding,
  GroqClinicalSummary,
  GroqFindingEvidence
} from "../api/types";
import {
  clinicalSummaryPresentation,
  explanationForGroup,
  modelScoreLanguage,
  parseClinicalSummary,
  PARTIAL_CLINICAL_SUMMARY_NOTICE,
  reviewStatusLanguage,
  technicalDetailsForFinding
} from "./clinicalSummary";
import { groupFindingsByTooth } from "./opg";

function finding(
  id: string,
  toothCode: string | null,
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
    status: "AVAILABLE",
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
    canonical_evidence: Object.fromEntries(items.map((item) => [item.evidence_id, item])),
    failed_tooth_fdis: []
  };
}

describe("clinical summary utilities", () => {
  it("falls back when clinical_summary is missing or Groq is unavailable", () => {
    expect(parseClinicalSummary(undefined)).toBeNull();
    expect(parseClinicalSummary({ status: "UNAVAILABLE" })).toBeNull();
  });

  it("keeps AVAILABLE summaries complete without a partial warning", () => {
    const candidate = summary([
      evidence("finding_0", "37", "FILLING", 0.8945)
    ]);
    candidate.patient_message_draft = "Optional complete-coverage draft.";
    const parsed = parseClinicalSummary(candidate);
    const presentation = clinicalSummaryPresentation(parsed);

    expect(presentation.showPanel).toBe(true);
    expect(presentation.showPartialWarning).toBe(false);
    expect(presentation.partialWarning).toBeNull();
    expect(presentation.showPatientMessage).toBe(true);
  });

  it("shows a clear PARTIAL warning and hides the patient message draft", () => {
    const candidate = summary([
      evidence("finding_0", "37", "FILLING", 0.8945),
      evidence("finding_1", "47", "FILLING", 0.81)
    ]);
    candidate.status = "PARTIAL";
    candidate.failed_tooth_fdis = ["47"];
    candidate.patient_message_draft = "This incomplete draft must remain hidden.";
    candidate.tooth_explanations = candidate.tooth_explanations.filter(
      (item) => item.tooth_fdi === "37"
    );
    const parsed = parseClinicalSummary(candidate);
    const presentation = clinicalSummaryPresentation(parsed);

    expect(presentation.showPanel).toBe(true);
    expect(presentation.showPartialWarning).toBe(true);
    expect(presentation.partialWarning).toBe(PARTIAL_CLINICAL_SUMMARY_NOTICE);
    expect(presentation.partialWarning).toContain(
      "Findings without a validated AI-assisted explanation"
    );
    expect(presentation.showPatientMessage).toBe(false);
  });

  it("does not render a Groq summary panel for UNAVAILABLE summaries", () => {
    const parsed = parseClinicalSummary({ status: "UNAVAILABLE" });
    const presentation = clinicalSummaryPresentation(parsed);

    expect(parsed).toBeNull();
    expect(presentation).toEqual({
      showPanel: false,
      showPartialWarning: false,
      partialWarning: null,
      showPatientMessage: false
    });
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

  it("keeps tooth 46 explanation when tooth 44 is missing from a partial summary", () => {
    const tooth44 = evidence("finding_0", "44", "FILLING", 0.80);
    const tooth46 = evidence("finding_1", "46", "CROWN", 0.91);
    const candidate = summary([tooth44, tooth46]);
    candidate.status = "PARTIAL";
    candidate.failed_tooth_fdis = ["44"];
    candidate.tooth_explanations = candidate.tooth_explanations.filter(
      (item) => item.tooth_fdi === "46"
    );

    const parsed = parseClinicalSummary(candidate);
    const group44 = groupFindingsByTooth([
      finding("a", "44", "FILLING", 0.80)
    ])[0];
    const group46 = groupFindingsByTooth([
      finding("b", "46", "CROWN", 0.91)
    ])[0];

    expect(parsed?.status).toBe("PARTIAL");
    expect(explanationForGroup(parsed, group46)?.tooth_fdi).toBe("46");
    expect(explanationForGroup(parsed, group44)).toBeNull();
  });

  it.each(["unknown", "duplicate", "wrong_tooth", "missing"] as const)(
    "fails closed for malformed tooth 44 %s binding without corrupting tooth 46",
    (mutation) => {
      const items = [
        evidence("finding_0", "44", "FILLING", 0.80),
        evidence("finding_1", "44", "CROWN", 0.82),
        evidence("finding_2", "46", "FILLING", 0.91)
      ];
      const candidate = summary(items);
      const tooth44 = candidate.tooth_explanations.find(
        (item) => item.tooth_fdi === "44"
      )!;
      if (mutation === "unknown") tooth44.evidence_ids = ["finding_99", "finding_1"];
      if (mutation === "duplicate") tooth44.evidence_ids = ["finding_0", "finding_0"];
      if (mutation === "wrong_tooth") tooth44.tooth_fdi = "47";
      if (mutation === "missing") tooth44.evidence_ids = ["finding_0"];

      const parsed = parseClinicalSummary(candidate);
      const group44 = groupFindingsByTooth([
        finding("a", "44", "FILLING", 0.80),
        finding("b", "44", "CROWN", 0.82)
      ])[0];
      const group46 = groupFindingsByTooth([
        finding("c", "46", "FILLING", 0.91)
      ])[0];

      expect(parsed?.status).toBe("PARTIAL");
      expect(explanationForGroup(parsed, group44)).toBeNull();
      expect(explanationForGroup(parsed, group46)?.tooth_fdi).toBe("46");
    }
  );

  it("parses AVAILABLE, PARTIAL, and UNAVAILABLE shapes safely", () => {
    const item37 = evidence("finding_0", "37", "FILLING", 0.89);
    const available = summary([item37]);
    expect(parseClinicalSummary(available)?.status).toBe("AVAILABLE");

    const partial = summary([
      item37,
      evidence("finding_1", "47", "FILLING", 0.81)
    ]);
    partial.status = "PARTIAL";
    partial.failed_tooth_fdis = ["47"];
    partial.tooth_explanations = partial.tooth_explanations.filter(
      (item) => item.tooth_fdi === "37"
    );
    expect(parseClinicalSummary(partial)?.status).toBe("PARTIAL");
    expect(parseClinicalSummary({ status: "UNAVAILABLE" })).toBeNull();
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
      bounding_box: [10, 20, 30, 40],
      raw_fdi: null,
      fdi_confidence: null,
      fdi_was_changed: null,
      duplicate_cleanup_applied: null,
      fdi_review_required: null,
      tooth_detection_instance_id: null,
      quadrant_candidates: [],
      resolved_quadrant: null,
      side_constraint_applied: null,
      side_constraint_overrode_raw_quadrant: null
    });
  });

  it("keeps raw FDI only in technical details for an unresolved region", () => {
    const unresolved = finding("u", null, "FILLING", 0.8945);
    unresolved.provenance = {
      ...unresolved.provenance,
      raw_fdi: "37",
      fdi_confidence: 0.94,
      fdi_was_changed: true,
      fdi_review_required: true,
      tooth_detection_instance_id: 7,
      quadrant_candidates: ["1", "4"],
      resolved_quadrant: "4",
      side_constraint_applied: true,
      side_constraint_overrode_raw_quadrant: true
    };

    const group = groupFindingsByTooth([unresolved])[0];
    const technical = technicalDetailsForFinding(unresolved);

    expect(group.toothCode).toBeNull();
    expect(explanationForGroup(null, group)).toBeNull();
    expect(technical.raw_fdi).toBe("37");
    expect(technical.fdi_review_required).toBe(true);
    expect(technical.side_constraint_overrode_raw_quadrant).toBe(true);
  });
});
