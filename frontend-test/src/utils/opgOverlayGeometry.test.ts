import { describe, expect, it } from "vitest";
import type { DentalFinding } from "../api/types";
import {
  boundingBoxForFindingGroup,
  geometryCorrectedFdiForDetection,
  groupFindingsByTooth,
  type VisionToothDetection
} from "./opg";

function detection(
  key: string,
  instanceId: number,
  toothCode: string | null,
  boundingBox: [number, number, number, number]
): VisionToothDetection {
  return {
    key,
    instanceId,
    toothCode,
    boundingBox,
    confidence: 0.95,
    reviewRequired: false
  };
}

function finding(toothCode: string): DentalFinding {
  return {
    id: `finding-${toothCode}`,
    patient_id: "patient",
    analysis_id: "analysis",
    tooth_code: toothCode,
    finding_type: "CARIES",
    description: "test",
    source: "AI",
    confidence: 0.9,
    provenance: null,
    review_status: "PENDING",
    confirmed_by: null,
    confirmed_at: null,
    created_at: "2026-09-04T00:00:00Z"
  };
}

const detections: VisionToothDetection[] = [
  // Deliberately jaw-swapped FDI labels. Geometry must repair the quadrant.
  detection("upper-left", 1, "46", [150, 210, 250, 420]),
  detection("lower-left", 2, "16", [160, 610, 260, 830]),
  detection("upper-right", 3, "35", [850, 220, 950, 430]),
  detection("lower-right", 4, "25", [840, 600, 940, 820])
];

describe("OPG physical jaw geometry", () => {
  it("repairs upper/lower quadrant swaps without moving detector boxes", () => {
    expect(geometryCorrectedFdiForDetection(detections[0], detections, 1200)).toBe("16");
    expect(geometryCorrectedFdiForDetection(detections[1], detections, 1200)).toBe("46");
    expect(geometryCorrectedFdiForDetection(detections[2], detections, 1200)).toBe("25");
    expect(geometryCorrectedFdiForDetection(detections[3], detections, 1200)).toBe("35");
  });

  it("places a lower-jaw finding on the lower detector, never the upper mislabeled detector", () => {
    const group35 = groupFindingsByTooth([finding("35")])[0];
    const box = boundingBoxForFindingGroup(group35, detections, 1200, 900);

    expect(box).not.toBeNull();
    expect(box![1]).toBeGreaterThan(500);
    expect((box![0] + box![2]) / 2).toBeCloseTo(890, 0);
  });

  it("places the mirrored lower-right-patient finding on the physical lower jaw", () => {
    const group46 = groupFindingsByTooth([finding("46")])[0];
    const box = boundingBoxForFindingGroup(group46, detections, 1200, 900);

    expect(box).not.toBeNull();
    expect(box![1]).toBeGreaterThan(500);
    expect((box![0] + box![2]) / 2).toBeCloseTo(210, 0);
  });

  it("withholds unresolved tooth codes instead of displaying a misleading overlay", () => {
    const unresolved = detection("unknown", 5, null, [400, 300, 480, 500]);
    expect(geometryCorrectedFdiForDetection(unresolved, [...detections, unresolved], 1200)).toBeNull();
  });
});
