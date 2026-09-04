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

export function isResolvedFdi(value: unknown): value is string {
  return typeof value === "string" && /^[1-4][1-8]$/.test(value);
}

export function isFindingProductVisible(finding: DentalFinding): boolean {
  return (
    isResolvedFdi(finding.tooth_code) &&
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

export interface VisionToothDetection {
  key: string;
  instanceId: number | null;
  toothCode: string | null;
  boundingBox: BoundingBox;
  confidence: number | null;
  reviewRequired: boolean;
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

function boxArea(box: BoundingBox): number {
  return Math.max(0, box[2] - box[0]) * Math.max(0, box[3] - box[1]);
}

function intersectionArea(left: BoundingBox, right: BoundingBox): number {
  const width = Math.max(0, Math.min(left[2], right[2]) - Math.max(left[0], right[0]));
  const height = Math.max(0, Math.min(left[3], right[3]) - Math.max(left[1], right[1]));
  return width * height;
}

function intersectionOverUnion(left: BoundingBox, right: BoundingBox): number {
  const intersection = intersectionArea(left, right);
  if (intersection <= 0) return 0;
  const union = boxArea(left) + boxArea(right) - intersection;
  return union > 0 ? intersection / union : 0;
}

function boxCenter(box: BoundingBox): [number, number] {
  return [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2];
}

export function extractVisionToothDetections(
  structuredResult: AIAnalysisStructuredResult | null
): VisionToothDetection[] {
  const teeth = structuredResult?.vision_evidence?.teeth;
  if (!Array.isArray(teeth)) return [];

  return teeth.flatMap((value, index) => {
    if (!value || typeof value !== "object") return [];
    const tooth = value as {
      fdi?: unknown;
      review_required?: unknown;
      fdi_review_required?: unknown;
      tooth_detection?: {
        instance_id?: unknown;
        bbox_xyxy?: unknown;
        confidence?: unknown;
      };
    };
    const boundingBox = parseBoundingBox(tooth.tooth_detection?.bbox_xyxy);
    if (!boundingBox) return [];
    const toothCode =
      typeof tooth.fdi === "string" || typeof tooth.fdi === "number"
        ? String(tooth.fdi)
        : null;
    const rawInstanceId = tooth.tooth_detection?.instance_id;
    const instanceId = typeof rawInstanceId === "number" && Number.isInteger(rawInstanceId)
      ? rawInstanceId
      : null;
    const confidence = tooth.tooth_detection?.confidence;
    return [{
      key: `detected:${instanceId ?? index}`,
      instanceId,
      toothCode,
      boundingBox,
      confidence: typeof confidence === "number" && Number.isFinite(confidence) ? confidence : null,
      reviewRequired: tooth.review_required === true || tooth.fdi_review_required === true
    }];
  });
}

export function extractVisionToothGeometry(
  structuredResult: AIAnalysisStructuredResult | null
): VisionToothGeometry {
  const boxesByTooth = new Map<string, BoundingBox[]>();
  for (const detection of extractVisionToothDetections(structuredResult)) {
    if (!detection.toothCode) continue;
    boxesByTooth.set(
      detection.toothCode,
      [...(boxesByTooth.get(detection.toothCode) ?? []), detection.boundingBox]
    );
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

function jawDivider(detections: VisionToothDetection[]): number | null {
  if (detections.length < 2) return null;
  const ys = detections.map((detection) => boxCenter(detection.boundingBox)[1]);
  let upperMean = Math.min(...ys);
  let lowerMean = Math.max(...ys);

  for (let iteration = 0; iteration < 10; iteration += 1) {
    const upper: number[] = [];
    const lower: number[] = [];
    for (const y of ys) {
      if (Math.abs(y - upperMean) <= Math.abs(y - lowerMean)) upper.push(y);
      else lower.push(y);
    }
    if (upper.length > 0) {
      upperMean = upper.reduce((sum, value) => sum + value, 0) / upper.length;
    }
    if (lower.length > 0) {
      lowerMean = lower.reduce((sum, value) => sum + value, 0) / lower.length;
    }
  }

  if (!Number.isFinite(upperMean) || !Number.isFinite(lowerMean) || upperMean >= lowerMean) {
    return null;
  }
  return (upperMean + lowerMean) / 2;
}

function viewerSideForDetection(
  detection: VisionToothDetection,
  imageWidth: number
): PanoramicSide | null {
  if (imageWidth <= 0) return null;
  const [cx] = boxCenter(detection.boundingBox);
  const midpoint = imageWidth / 2;
  const deadZone = imageWidth * 0.04;

  if (cx < midpoint - deadZone) return "LEFT";
  if (cx > midpoint + deadZone) return "RIGHT";

  if (isResolvedFdi(detection.toothCode)) {
    return expectedPanoramicSide(detection.toothCode);
  }
  return cx < midpoint ? "LEFT" : "RIGHT";
}

/**
 * Correct only the quadrant digit from the physical position of the detector.
 * The second FDI digit (tooth position within a quadrant) remains model-derived.
 * This fixes the known class of errors where a lower-jaw FDI is attached to an
 * upper-jaw detector (or vice versa) while preserving the detector's exact box.
 */
export function geometryCorrectedFdiForDetection(
  detection: VisionToothDetection,
  detections: VisionToothDetection[],
  imageWidth: number
): string | null {
  if (!isResolvedFdi(detection.toothCode) || imageWidth <= 0) return null;
  const divider = jawDivider(detections);
  if (divider === null) return null;

  const [, cy] = boxCenter(detection.boundingBox);
  const upperJaw = cy <= divider;
  const side = viewerSideForDetection(detection, imageWidth);
  if (!side) return null;

  const quadrant = upperJaw
    ? (side === "LEFT" ? "1" : "2")
    : (side === "LEFT" ? "4" : "3");
  return quadrant + detection.toothCode[1];
}

/**
 * Match a finding to a detector only after correcting detector jaw/side geometry.
 * A lower-jaw finding can therefore never be drawn over an upper-jaw detector.
 * Ambiguous or missing geometry is deliberately withheld rather than guessed.
 */
export function detectorForFindingGroup(
  group: Pick<ToothFindingGroup, "toothCode" | "findings" | "provenanceBoxes">,
  detections: VisionToothDetection[],
  imageWidth?: number
): VisionToothDetection | null {
  if (!isResolvedFdi(group.toothCode) || !imageWidth || imageWidth <= 0) return null;

  const candidates = detections.filter(
    (detection) => geometryCorrectedFdiForDetection(detection, detections, imageWidth) === group.toothCode
  );
  if (candidates.length === 0) return null;
  if (candidates.length === 1) return candidates[0];

  const instanceIds = Array.from(new Set(
    group.findings
      .map((finding) => finding.provenance?.tooth_detection_instance_id)
      .filter((value): value is number =>
        typeof value === "number" && Number.isInteger(value) && value >= 0
      )
  ));
  if (instanceIds.length === 1) {
    const exact = candidates.find((detection) => detection.instanceId === instanceIds[0]);
    if (exact) return exact;
  }

  const reference = unionBoundingBoxes(group.provenanceBoxes);
  if (!reference) return null;

  const ranked = candidates
    .map((detection) => ({
      detection,
      overlap: intersectionOverUnion(reference, detection.boundingBox)
    }))
    .sort((left, right) => right.overlap - left.overlap);

  const best = ranked[0];
  const second = ranked[1];
  if (!best || best.overlap < 0.05) return null;
  if (second && best.overlap - second.overlap < 0.05) return null;
  return best.detection;
}

function insetDetectorBox(box: BoundingBox): BoundingBox {
  const [x1, y1, x2, y2] = box;
  const width = x2 - x1;
  const height = y2 - y1;
  const insetX = Math.min(4, width * 0.025);
  const insetY = Math.min(3, height * 0.015);
  const tightened: BoundingBox = [
    x1 + insetX,
    y1 + insetY,
    x2 - insetX,
    y2 - insetY
  ];
  return tightened[2] > tightened[0] && tightened[3] > tightened[1]
    ? tightened
    : box;
}

export function boundingBoxForFindingGroup(
  group: ToothFindingGroup,
  detections: VisionToothDetection[],
  imageWidth?: number,
  _imageHeight?: number
): BoundingBox | null {
  if (!isResolvedFdi(group.toothCode) || !imageWidth || imageWidth <= 0) return null;
  const detector = detectorForFindingGroup(group, detections, imageWidth);
  return detector ? insetDetectorBox(detector.boundingBox) : null;
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
  if (!requestedKey) return null;
  return groups.some((group) => group.key === requestedKey) ? requestedKey : null;
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
