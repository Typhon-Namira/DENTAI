import { describe, expect, it } from "vitest";
import type { DentalFinding } from "../api/types";
import type { ToothFindingGroup } from "./opg";
import {
  findingTone,
  groupFindingConfidence,
  groupFindingTone,
  primaryFinding
} from "./findingVisuals";

function finding(type: string, confidence: number): DentalFinding {
  return {
    id: `${type}-${confidence}`,
    patient_id: "patient",
    analysis_id: "analysis",
    tooth_code: "16",
    finding_type: type,
    description: type,
    source: "AI",
    confidence,
    provenance: null,
    review_status: "PENDING",
    confirmed_by: null,
    confirmed_at: null,
    created_at: "2026-09-04T00:00:00Z"
  };
}

function group(findings: DentalFinding[]): ToothFindingGroup {
  return {
    key: "tooth:16",
    toothCode: "16",
    findings,
    boundingBox: [10, 10, 40, 60],
    boundingBoxSource: "VISION_EVIDENCE",
    provenanceBoxes: [],
    geometryAmbiguous: false
  };
}

describe("OPG finding visual classification", () => {
  it("renders fillings and crowns as restorative", () => {
    expect(findingTone("FILLING")).toBe("RESTORATIVE");
    expect(findingTone("CROWN")).toBe("RESTORATIVE");
    expect(findingTone("ROOT_CANAL_TREATMENT")).toBe("RESTORATIVE");
  });

  it("renders caries and other disease findings as pathology", () => {
    expect(findingTone("CARIES")).toBe("PATHOLOGY");
    expect(findingTone("DEEP_CARIES")).toBe("PATHOLOGY");
    expect(findingTone("IMPACTED")).toBe("PATHOLOGY");
  });

  it("lets pathology override a restorative finding on the same tooth", () => {
    expect(groupFindingTone(group([
      finding("FILLING", 0.95),
      finding("CARIES", 0.72)
    ]))).toBe("PATHOLOGY");
  });

  it("uses the strongest pathology confidence to drive red intensity", () => {
    const value = group([
      finding("FILLING", 0.99),
      finding("CARIES", 0.61),
      finding("DEEP_CARIES", 0.88)
    ]);
    expect(groupFindingConfidence(value)).toBe(0.88);
    expect(primaryFinding(value)?.finding_type).toBe("DEEP_CARIES");
  });
});
