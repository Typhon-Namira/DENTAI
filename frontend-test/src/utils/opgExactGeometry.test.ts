import { describe, expect, it } from "vitest";
import type { AIAnalysisStructuredResult, DentalFinding } from "../api/types";
import {
  boundingBoxForFindingGroup,
  extractVisionToothDetections,
  groupFindingsByTooth
} from "./opg";
import { localizedFindingType } from "./clinicalSummary";

function finding(instanceId: number, toothCode = "48"): DentalFinding {
  return {
    id: `finding-${instanceId}`,
    patient_id: "patient",
    analysis_id: "analysis",
    tooth_code: toothCode,
    finding_type: "IMPACTED",
    description: "Model finding",
    source: "AI",
    confidence: 0.93,
    provenance: {
      bounding_box: [500, 300, 650, 510],
      tooth_detection_instance_id: instanceId
    },
    review_status: "PENDING",
    confirmed_by: null,
    confirmed_at: null,
    created_at: "2026-09-04T00:00:00Z"
  };
}

describe("exact OPG finding geometry", () => {
  it("uses the detector instance that produced the finding instead of a broad fallback region", () => {
    const structured = {
      vision_evidence: {
        teeth: [
          { fdi: "48", tooth_detection: { instance_id: 7, bbox_xyxy: [80, 310, 165, 455], confidence: 0.97 } },
          { fdi: "48", tooth_detection: { instance_id: 8, bbox_xyxy: [500, 300, 650, 510], confidence: 0.88 } }
        ]
      }
    } as AIAnalysisStructuredResult;
    const detections = extractVisionToothDetections(structured);
    const group = groupFindingsByTooth([finding(7)], new Map(), new Set(["48"]))[0];

    expect(boundingBoxForFindingGroup(group, detections)).toEqual([80, 310, 165, 455]);
  });

  it("keeps finding labels bilingual", () => {
    expect(localizedFindingType("CROWN", "en")).toBe("Crown");
    expect(localizedFindingType("CROWN", "hy")).toBe("Պսակ");
    expect(localizedFindingType("DEEP_CARIES", "en")).toBe("Deep caries");
    expect(localizedFindingType("DEEP_CARIES", "hy")).toBe("Խորը կարիես");
  });
});
