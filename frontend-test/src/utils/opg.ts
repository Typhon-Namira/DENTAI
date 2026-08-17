import type {
  AIAnalysis,
  AIAnalysisStructuredResult,
  DentalFinding,
  FindingProvenance,
  FindingReview,
  XRay
} from "../api/types";

export type FindingFilter = "ALL" | FindingReview;
export type BoundingBox = [number, number, number, number];
export type PanoramicSide = "LEFT" | "RIGHT";
export type BoundingBoxSource = "VISION_EVIDENCE" | "FINDING_PROVENANCE";

export const MODEL_SCORE_DISPLAY_THRESHOLD = 0.60;

export function isFindingProductVisible(finding: DentalFinding): boolean {
  return (
    typeof finding.confidence === "number" &&
    Number.isFinite(finding.confidence) &&
    finding.confidence >= MODEL_SCORE_DISPLAY_THRESHOLD
  );
}

export interface ToothFindingGroup {
  key: string;
  toothCode: string | null;
  findings: DentalFinding[];
  boundingBox: BoundingBox | null;
  boundingBoxSource: BoundingBoxSource | null;
  provenanceBoxes: BoundingBox[];
  geometryAmbiguous: boolean;
}

export interface VisionToothGeometry {
  boxes: Map<string, BoundingBox>;
  ambiguousToothCodes: Set<string>;
}

export function extractBoundingBox(
  provenance: FindingProvenance | null
): BoundingBox | null {
  return parseBoundingBox(provenance?.bounding_box);
}

export function parseBoundingBox(value: unknown): BoundingBox | null {
  if (!Array.isArray(value) || value.length !== 4) return null;
  if (!value.every((coordinate) => typeof coordinate === "number" && Number.isFinite(coordinate))) {
    return null;
  }
  const [x1, y1, x2, y2] = value;
  if (x2 <= x1 || y2 <= y1) return null;
  return [x1, y1, x2, y2];
}

function unionBoundingBoxes(boxes: BoundingBox[]): BoundingBox | null {
  if (boxes.length === 0) return null;
  return [
    Math.min(...boxes.map((box) => box[0])),
    Math.min(...boxes.map((box) => box[1])),
    Math.max(...boxes.map((box) => box[2])),
    Math.max(...boxes.map((box) => box[3]))
  ];
}

export function extractVisionToothGeometry(
  structuredResult: AIAnalysisStructuredResult | null
): VisionToothGeometry {
  const boxesByTooth = new Map<string, BoundingBox[]>();
  const teeth = structuredResult?.vision_evidence?.teeth;
  if (!Array.isArray(teeth)) {
    return { boxes: new Map(), ambiguousToothCodes: new Set() };
  }

  for (const value of teeth) {
    if (!value || typeof value !== "object") continue;
    const tooth = value as {
      fdi?: unknown;
      tooth_detection?: { bbox_xyxy?: unknown };
    };
    const toothCode =
      typeof tooth.fdi === "string" || typeof tooth.fdi === "number"
        ? String(tooth.fdi)
        : null;
    const box = parseBoundingBox(tooth.tooth_detection?.bbox_xyxy);
    if (!toothCode || !box) continue;
    boxesByTooth.set(toothCode, [...(boxesByTooth.get(toothCode) ?? []), box]);
  }

  const boxes = new Map<string, BoundingBox>();
  const ambiguousToothCodes = new Set<string>();
  for (const [toothCode, toothBoxes] of boxesByTooth) {
    if (toothBoxes.length === 1) {
      boxes.set(toothCode, toothBoxes[0]);
    } else {
      ambiguousToothCodes.add(toothCode);
    }
  }
  return { boxes, ambiguousToothCodes };
}

export function extractVisionToothBoxes(
  structuredResult: AIAnalysisStructuredResult | null
): Map<string, BoundingBox> {
  return extractVisionToothGeometry(structuredResult).boxes;
}

export function findingGroupKey(finding: DentalFinding): string {
  if (finding.tooth_code) return "tooth:" + finding.tooth_code;

  const instanceId = finding.provenance?.tooth_detection_instance_id;
  if (
    typeof instanceId === "number" &&
    Number.isInteger(instanceId) &&
    instanceId >= 0
  ) {
    return "unresolved-instance:" + instanceId;
  }

  return "unassigned:" + finding.id;
}

export function groupFindingsByTooth(
  findings: DentalFinding[],
  visionBoxes: Map<string, BoundingBox> = new Map(),
  ambiguousVisionToothCodes: Set<string> = new Set()
): ToothFindingGroup[] {
  const grouped = new Map<string, DentalFinding[]>();

  for (const finding of findings) {
    const key = findingGroupKey(finding);
    grouped.set(key, [...(grouped.get(key) ?? []), finding]);
  }

  return Array.from(grouped, ([key, groupedFindings]) => {
    const toothCode = groupedFindings[0]?.tooth_code ?? null;
    const provenanceBoxes = groupedFindings
      .map((finding) => extractBoundingBox(finding.provenance))
      .filter((box): box is BoundingBox => box !== null);
    const geometryAmbiguous = toothCode
      ? ambiguousVisionToothCodes.has(toothCode)
      : false;
    const visionBox = toothCode && !geometryAmbiguous
      ? visionBoxes.get(toothCode) ?? null
      : null;
    const boundingBoxSource: BoundingBoxSource | null = geometryAmbiguous
      ? null
      : visionBox
        ? "VISION_EVIDENCE"
        : provenanceBoxes.length
          ? "FINDING_PROVENANCE"
          : null;
    return {
      key,
      toothCode,
      findings: groupedFindings,
      boundingBox: geometryAmbiguous
        ? null
        : visionBox ?? unionBoundingBoxes(provenanceBoxes),
      boundingBoxSource,
      provenanceBoxes,
      geometryAmbiguous
    };
  }).sort((left, right) =>
    (left.toothCode ?? left.key).localeCompare(right.toothCode ?? right.key, undefined, {
      numeric: true
    })
  );
}

export function normalizeBoundingBoxToImage(
  box: BoundingBox,
  imageWidth: number,
  imageHeight: number
): BoundingBox | null {
  if (imageWidth <= 0 || imageHeight <= 0) return null;
  const normalized = box.every((coordinate) => coordinate >= 0 && coordinate <= 1);
  const projected: BoundingBox = normalized
    ? [
        box[0] * imageWidth,
        box[1] * imageHeight,
        box[2] * imageWidth,
        box[3] * imageHeight
      ]
    : box;
  if (
    projected[0] < 0 ||
    projected[1] < 0 ||
    projected[2] > imageWidth ||
    projected[3] > imageHeight
  ) {
    return null;
  }
  return projected;
}

export function expectedPanoramicSide(toothCode: string): PanoramicSide | null {
  const quadrant = toothCode.charAt(0);
  if (quadrant === "1" || quadrant === "4") return "LEFT";
  if (quadrant === "2" || quadrant === "3") return "RIGHT";
  return null;
}

export function observedImageSide(
  box: BoundingBox,
  imageWidth: number
): PanoramicSide | null {
  if (imageWidth <= 0) return null;
  return (box[0] + box[2]) / 2 < imageWidth / 2 ? "LEFT" : "RIGHT";
}

export function isStandardPanoramicSideConsistent(
  toothCode: string,
  box: BoundingBox,
  imageWidth: number
): boolean | null {
  const expected = expectedPanoramicSide(toothCode);
  const observed = observedImageSide(box, imageWidth);
  return expected && observed ? expected === observed : null;
}

export function filterFindings(
  findings: DentalFinding[],
  filter: FindingFilter
): DentalFinding[] {
  if (filter === "ALL") return findings;
  return findings.filter((finding) => finding.review_status === filter);
}

export function resolveSelectedGroupKey(
  groups: ToothFindingGroup[],
  requestedKey: string | null
): string | null {
  if (requestedKey && groups.some((group) => group.key === requestedKey)) return requestedKey;
  return groups.find((group) => group.boundingBox)?.key ?? groups[0]?.key ?? null;
}

export function xrayForAnalysis(
  analysis: Pick<AIAnalysis, "xray_id"> | null,
  xrays: XRay[]
): XRay | null {
  if (!analysis) return null;
  return xrays.find((xray) => xray.id === analysis.xray_id) ?? null;
}

export function findingModelScore(finding: DentalFinding): number | null {
  const rawScore = finding.provenance?.raw_score;
  if (typeof rawScore === "number" && Number.isFinite(rawScore)) return rawScore;
  return typeof finding.confidence === "number" && Number.isFinite(finding.confidence)
    ? finding.confidence
    : null;
}

export function formatModelScore(value: number | null): string {
  return value === null ? "Not provided" : value.toFixed(4);
}
