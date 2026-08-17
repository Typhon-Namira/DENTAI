import { describe, expect, it } from "vitest";
import type { AIAnalysis, DentalFinding, XRay } from "../api/types";
import {
  extractBoundingBox,
  filterFindings,
  groupFindingsByTooth,
  resolveSelectedGroupKey,
  xrayForAnalysis
} from "./opg";

function finding(
  id: string,
  toothCode: string | null,
  status: DentalFinding["review_status"],
  boundingBox?: unknown
): DentalFinding {
  return {
    id,
    patient_id: "patient",
    analysis_id: "analysis",
    tooth_code: toothCode,
    finding_type: "FILLING",
    description: "Model-generated finding",
    source: "AI",
    confidence: 0.8732,
    provenance: boundingBox === undefined ? null : { bounding_box: boundingBox as never },
    review_status: status,
    confirmed_by: null,
    confirmed_at: null,
    created_at: "2026-08-17T00:00:00Z"
  };
}

describe("OPG finding utilities", () => {
  it("groups multiple findings for one tooth into one overlay region", () => {
    const groups = groupFindingsByTooth([
      finding("a", "36", "PENDING", [10, 20, 50, 80]),
      finding("b", "36", "PENDING", [12, 18, 48, 82]),
      finding("c", "11", "CONFIRMED", [100, 20, 130, 70])
    ]);
    const tooth36 = groups.find((group) => group.toothCode === "36");
    expect(tooth36?.findings).toHaveLength(2);
    expect(tooth36?.boundingBox).toEqual([10, 18, 50, 82]);
  });

  it("extracts valid xyxy bounding boxes", () => {
    expect(extractBoundingBox({ bounding_box: [1, 2, 30, 40] })).toEqual([1, 2, 30, 40]);
  });

  it("ignores malformed bounding boxes without hiding the finding", () => {
    expect(extractBoundingBox({ bounding_box: [1, 2, 3] as never })).toBeNull();
    expect(extractBoundingBox({ bounding_box: [5, 5, 2, 2] })).toBeNull();
    const groups = groupFindingsByTooth([finding("a", "36", "PENDING", ["x", 2, 3, 4])]);
    expect(groups[0]?.findings).toHaveLength(1);
    expect(groups[0]?.boundingBox).toBeNull();
  });

  it("keeps a valid selected tooth and resets missing selections deterministically", () => {
    const groups = groupFindingsByTooth([
      finding("a", "11", "PENDING", [1, 1, 2, 2]),
      finding("b", "36", "PENDING", [3, 3, 4, 4])
    ]);
    expect(resolveSelectedGroupKey(groups, "tooth:36")).toBe("tooth:36");
    expect(resolveSelectedGroupKey(groups, "tooth:99")).toBe("tooth:11");
  });

  it("uses the historical analysis xray_id rather than current selection", () => {
    const xrays = [
      { id: "current" },
      { id: "historical" }
    ] as XRay[];
    const analysis = { xray_id: "historical" } as AIAnalysis;
    expect(xrayForAnalysis(analysis, xrays)?.id).toBe("historical");
  });

  it("filters findings by review status", () => {
    const findings = [
      finding("a", "11", "PENDING"),
      finding("b", "12", "CONFIRMED"),
      finding("c", "13", "REJECTED")
    ];
    expect(filterFindings(findings, "ALL")).toHaveLength(3);
    expect(filterFindings(findings, "PENDING").map((item) => item.id)).toEqual(["a"]);
    expect(filterFindings(findings, "CONFIRMED").map((item) => item.id)).toEqual(["b"]);
    expect(filterFindings(findings, "REJECTED").map((item) => item.id)).toEqual(["c"]);
  });
});
