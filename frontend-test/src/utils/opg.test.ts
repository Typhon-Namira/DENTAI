import { describe, expect, it } from "vitest";
import type {
  AIAnalysis,
  AIAnalysisStructuredResult,
  DentalFinding,
  XRay
} from "../api/types";
import {
  expectedPanoramicSide,
  extractBoundingBox,
  extractVisionToothBoxes,
  filterFindings,
  groupFindingsByTooth,
  isFindingProductVisible,
  isStandardPanoramicSideConsistent,
  MODEL_SCORE_DISPLAY_THRESHOLD,
  normalizeBoundingBoxToImage,
  resolveSelectedGroupKey,
  xrayForAnalysis
} from "./opg";

function finding(
  id: string,
  toothCode: string | null,
  status: DentalFinding["review_status"],
  boundingBox?: unknown,
  confidence: number | null = 0.8732
): DentalFinding {
  return {
    id,
    patient_id: "patient",
    analysis_id: "analysis",
    tooth_code: toothCode,
    finding_type: "FILLING",
    description: "Model-generated finding",
    source: "AI",
    confidence,
    provenance: boundingBox === undefined ? null : { bounding_box: boundingBox as never },
    review_status: status,
    confirmed_by: null,
    confirmed_at: null,
    created_at: "2026-08-17T00:00:00Z"
  };
}

function structuredTeeth(
  teeth: Array<{ fdi: string; box: unknown }>
): AIAnalysisStructuredResult {
  return {
    vision_evidence: {
      teeth: teeth.map((tooth) => ({
        fdi: tooth.fdi,
        tooth_detection: { bbox_xyxy: tooth.box }
      }))
    }
  };
}

describe("OPG finding utilities", () => {
  it("groups multiple findings for one tooth and unions only that tooth's fallback boxes", () => {
    const groups = groupFindingsByTooth([
      finding("a", "36", "PENDING", [1100, 20, 1150, 80]),
      finding("b", "36", "PENDING", [1112, 18, 1148, 82]),
      finding("c", "44", "CONFIRMED", [100, 20, 130, 70])
    ]);
    const tooth36 = groups.find((group) => group.toothCode === "36");
    expect(tooth36?.findings).toHaveLength(2);
    expect(tooth36?.boundingBox).toEqual([1100, 18, 1150, 82]);
    expect(tooth36?.boundingBoxSource).toBe("FINDING_PROVENANCE");
  });

  it("extracts valid xyxy bounding boxes and ignores malformed boxes", () => {
    expect(extractBoundingBox({ bounding_box: [1, 2, 30, 40] })).toEqual([1, 2, 30, 40]);
    expect(extractBoundingBox({ bounding_box: [1, 2, 3] as never })).toBeNull();
    expect(extractBoundingBox({ bounding_box: [5, 5, 2, 2] })).toBeNull();
    const groups = groupFindingsByTooth([finding("a", "44", "PENDING", ["x", 2, 3, 4])]);
    expect(groups[0]?.findings).toHaveLength(1);
    expect(groups[0]?.boundingBox).toBeNull();
  });

  it("normalizes fractional boxes and preserves valid original-image pixel boxes", () => {
    expect(normalizeBoundingBoxToImage([0.1, 0.2, 0.3, 0.4], 2000, 1000))
      .toEqual([200, 200, 600, 400]);
    expect(normalizeBoundingBoxToImage([100, 200, 300, 400], 2000, 1000))
      .toEqual([100, 200, 300, 400]);
    expect(normalizeBoundingBoxToImage([100, 200, 2300, 400], 2000, 1000)).toBeNull();
  });

  it("uses canonical vision evidence for tooth 44 instead of a wrong-side provenance box", () => {
    const findings = [
      finding("a", "44", "PENDING", [1500, 500, 1600, 800]),
      finding("b", "44", "PENDING", [1510, 510, 1610, 810])
    ];
    const visionBoxes = extractVisionToothBoxes(
      structuredTeeth([{ fdi: "44", box: [220, 500, 340, 820] }])
    );
    const tooth44 = groupFindingsByTooth(findings, visionBoxes)[0];
    expect(tooth44?.boundingBox).toEqual([220, 500, 340, 820]);
    expect(tooth44?.boundingBoxSource).toBe("VISION_EVIDENCE");
    expect(isStandardPanoramicSideConsistent("44", tooth44!.boundingBox!, 2000)).toBe(true);
  });

  it("does not reuse another tooth's canonical region", () => {
    const visionBoxes = extractVisionToothBoxes(
      structuredTeeth([{ fdi: "47", box: [100, 400, 240, 760] }])
    );
    const tooth44 = groupFindingsByTooth(
      [finding("a", "44", "PENDING", [260, 430, 350, 750])],
      visionBoxes
    )[0];
    expect(tooth44?.boundingBox).toEqual([260, 430, 350, 750]);
    expect(tooth44?.boundingBoxSource).toBe("FINDING_PROVENANCE");
  });

  it("documents standard panoramic orientation without transforming real boxes", () => {
    expect(expectedPanoramicSide("44")).toBe("LEFT");
    expect(expectedPanoramicSide("47")).toBe("LEFT");
    expect(expectedPanoramicSide("16")).toBe("LEFT");
    expect(expectedPanoramicSide("36")).toBe("RIGHT");
    expect(expectedPanoramicSide("37")).toBe("RIGHT");
    expect(expectedPanoramicSide("24")).toBe("RIGHT");
    expect(isStandardPanoramicSideConsistent("47", [100, 10, 200, 200], 2000)).toBe(true);
    expect(isStandardPanoramicSideConsistent("36", [1500, 10, 1600, 200], 2000)).toBe(true);
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
    const xrays = [{ id: "current" }, { id: "historical" }] as XRay[];
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

  it("includes the exact threshold and higher finite scores in the product view", () => {
    expect(MODEL_SCORE_DISPLAY_THRESHOLD).toBe(0.60);
    expect(isFindingProductVisible(finding("at", "11", "PENDING", undefined, 0.60)))
      .toBe(true);
    expect(isFindingProductVisible(finding("above", "12", "PENDING", undefined, 0.6001)))
      .toBe(true);
  });

  it("excludes below-threshold, null, non-finite, and malformed scores", () => {
    expect(isFindingProductVisible(finding("below", "11", "PENDING", undefined, 0.5999)))
      .toBe(false);
    expect(isFindingProductVisible(finding("low", "12", "PENDING", undefined, 0.3207)))
      .toBe(false);
    expect(isFindingProductVisible(finding("null", "13", "PENDING", undefined, null)))
      .toBe(false);
    expect(isFindingProductVisible(finding("nan", "14", "PENDING", undefined, Number.NaN)))
      .toBe(false);
    expect(isFindingProductVisible({
      ...finding("malformed", "15", "PENDING"),
      confidence: "0.9000" as unknown as number
    })).toBe(false);
  });

  it("does not create a tooth group or canonical overlay for a hidden tooth 44 finding", () => {
    const findings = [
      finding("tooth-44", "44", "PENDING", [1500, 500, 1600, 800], 0.3206733167171478),
      finding("tooth-47", "47", "PENDING", [100, 400, 240, 760], 0.6287)
    ];
    const productVisible = findings.filter(isFindingProductVisible);
    const visionBoxes = extractVisionToothBoxes(structuredTeeth([
      { fdi: "44", box: [220, 500, 340, 820] },
      { fdi: "47", box: [100, 400, 240, 760] }
    ]));
    const groups = groupFindingsByTooth(productVisible, visionBoxes);

    expect(groups.map((group) => group.toothCode)).toEqual(["47"]);
    expect(groups.some((group) => group.toothCode === "44")).toBe(false);
  });

  it("applies review-status filters after product visibility thresholding", () => {
    const findings = [
      finding("visible-pending", "11", "PENDING", undefined, 0.60),
      finding("hidden-pending", "12", "PENDING", undefined, 0.5999),
      finding("visible-confirmed", "13", "CONFIRMED", undefined, 0.9231),
      finding("hidden-rejected", "14", "REJECTED", undefined, 0.3207)
    ];
    const productVisible = findings.filter(isFindingProductVisible);

    expect(filterFindings(productVisible, "ALL").map((item) => item.id)).toEqual([
      "visible-pending",
      "visible-confirmed"
    ]);
    expect(filterFindings(productVisible, "PENDING").map((item) => item.id))
      .toEqual(["visible-pending"]);
    expect(filterFindings(productVisible, "CONFIRMED").map((item) => item.id))
      .toEqual(["visible-confirmed"]);
    expect(filterFindings(productVisible, "REJECTED")).toEqual([]);
  });
});
