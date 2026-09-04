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
      reviewRequired: tooth.review_required === true
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

/** Resolve the detector instance that originally produced the finding. */
export function detectorForFindingGroup(
  group: Pick<ToothFindingGroup, "toothCode" | "findings" | "provenanceBoxes">,
  detections: VisionToothDetection[]
): VisionToothDetection | null {
  const instanceIds = Array.from(new Set(
    group.findings
      .map((finding) => finding.provenance?.tooth_detection_instance_id)
      .filter((value): value is number =>
        typeof value === "number" && Number.isInteger(value) && value >= 0
      )
  ));

  if (instanceIds.length === 1) {
    const exact = detections.find((detection) => detection.instanceId === instanceIds[0]);
    if (exact) return exact;
  }

  const sameTooth = group.toothCode
    ? detections.filter((detection) => detection.toothCode === group.toothCode)
    : [];
  if (sameTooth.length === 1) return sameTooth[0];

  const reference = unionBoundingBoxes(group.provenanceBoxes);
  const candidates = sameTooth.length > 1 ? sameTooth : detections;
  if (reference && candidates.length > 0) {
    const ranked = candidates
      .map((detection) => ({
        detection,
        overlap: intersectionOverUnion(reference, detection.boundingBox)
      }))
      .sort((left, right) => right.overlap - left.overlap);
    if (ranked[0]?.overlap > 0) return ranked[0].detection;
  }

  return null;
}

function splitDetectionsByJaw(
  detections: VisionToothDetection[]
): { upper: VisionToothDetection[]; lower: VisionToothDetection[] } {
  if (detections.length < 2) return { upper: detections, lower: [] };
  const centers = detections.map((detection) => boxCenter(detection.boundingBox)[1]);
  let low = Math.min(...centers);
  let high = Math.max(...centers);

  for (let iteration = 0; iteration < 8; iteration += 1) {
    const lowerCluster: number[] = [];
    const upperCluster: number[] = [];
    for (const y of centers) {
      if (Math.abs(y - low) <= Math.abs(y - high)) upperCluster.push(y);
      else lowerCluster.push(y);
    }
    if (upperCluster.length) low = upperCluster.reduce((sum, value) => sum + value, 0) / upperCluster.length;
    if (lowerCluster.length) high = lowerCluster.reduce((sum, value) => sum + value, 0) / lowerCluster.length;
  }

  const divider = (low + high) / 2;
  return {
    upper: detections.filter((detection) => boxCenter(detection.boundingBox)[1] <= divider),
    lower: detections.filter((detection) => boxCenter(detection.boundingBox)[1] > divider)
  };
}

/**
 * Locate a tooth by FDI anatomy before trusting the model's FDI association.
 * Panoramic radiographs have a stable order: incisors are nearest the midline and
 * third molars are the most distal detections in each quadrant. This corrects
 * cases where a valid detector box was assigned to a neighboring FDI number.
 */
export function anatomicalDetectorForTooth(
  toothCode: string,
  detections: VisionToothDetection[],
  imageWidth: number
): VisionToothDetection | null {
  if (!isResolvedFdi(toothCode) || detections.length === 0 || imageWidth <= 0) return null;
  const quadrant = Number(toothCode[0]);
  const toothPosition = Number(toothCode[1]);
  const { upper, lower } = splitDetectionsByJaw(detections);
  const jaw = quadrant <= 2 ? upper : lower;
  const imageLeft = quadrant === 1 || quadrant === 4;
  const midline = imageWidth / 2;
  const quadrantCandidates = jaw.filter((detection) => {
    const x = boxCenter(detection.boundingBox)[0];
    return imageLeft ? x < midline : x >= midline;
  });

  if (quadrantCandidates.length === 0) return null;
  const ordered = [...quadrantCandidates].sort((left, right) => {
    const lx = boxCenter(left.boundingBox)[0];
    const rx = boxCenter(right.boundingBox)[0];
    // Position 1 is closest to the midline; position 8 is most distal.
    return imageLeft ? rx - lx : lx - rx;
  });

  const direct = ordered.find((detection) => detection.toothCode === toothCode) ?? null;
  const directRank = direct ? ordered.indexOf(direct) + 1 : null;

  // Terminal molars are especially reliable anatomically. If a finding exists for
  // an 8, place it on the most distal detected tooth in that quadrant even when the
  // FDI classifier attached the finding to the neighboring molar box.
  if (toothPosition === 8) return ordered[ordered.length - 1] ?? direct;

  // Keep a direct FDI match when its location is anatomically plausible.
  if (direct && directRank !== null && Math.abs(directRank - toothPosition) <= 1) {
    return direct;
  }

  // Use positional anatomy only when enough teeth are present to support that rank.
  const ranked = ordered[toothPosition - 1] ?? null;
  if (ranked) return ranked;
  return direct ?? null;
}

function tightenDetectorBox(
  detector: VisionToothDetection,
  toothCode: string,
  detections: VisionToothDetection[],
  imageWidth: number
): BoundingBox {
  const [rawX1, rawY1, rawX2, rawY2] = detector.boundingBox;
  const [cx, cy] = boxCenter(detector.boundingBox);
  const quadrant = Number(toothCode[0]);
  const upperJaw = quadrant <= 2;
  const imageLeft = quadrant === 1 || quadrant === 4;
  const { upper, lower } = splitDetectionsByJaw(detections);
  const jaw = upperJaw ? upper : lower;
  const sameQuadrant = jaw
    .filter((item) => {
      const x = boxCenter(item.boundingBox)[0];
      return imageLeft ? x < imageWidth / 2 : x >= imageWidth / 2;
    })
    .sort((left, right) => boxCenter(left.boundingBox)[0] - boxCenter(right.boundingBox)[0]);

  const index = sameQuadrant.findIndex((item) => item.key === detector.key);
  const previous = index > 0 ? sameQuadrant[index - 1] : null;
  const next = index >= 0 && index < sameQuadrant.length - 1 ? sameQuadrant[index + 1] : null;
  const previousCenter = previous ? boxCenter(previous.boundingBox)[0] : null;
  const nextCenter = next ? boxCenter(next.boundingBox)[0] : null;

  // Neighbor midpoints prevent adjacent tooth rectangles from visually invading
  // each other, while the detector still determines the actual tooth center/height.
  const leftBoundary = previousCenter === null ? rawX1 : (previousCenter + cx) / 2;
  const rightBoundary = nextCenter === null ? rawX2 : (nextCenter + cx) / 2;
  const x1 = Math.max(rawX1, leftBoundary + 1);
  const x2 = Math.min(rawX2, rightBoundary - 1);
  const width = Math.max(1, x2 - x1);
  const height = Math.max(1, rawY2 - rawY1);
  const horizontalInset = Math.min(width * 0.035, 4);
  const verticalInset = Math.min(height * 0.02, 3);

  const tightened: BoundingBox = [
    x1 + horizontalInset,
    rawY1 + verticalInset,
    x2 - horizontalInset,
    rawY2 - verticalInset
  ];
  if (tightened[2] <= tightened[0] || tightened[3] <= tightened[1]) {
    return detector.boundingBox;
  }
  // Keep the anatomical center unchanged; only remove obvious inter-tooth overlap.
  const tightenedCenter = boxCenter(tightened);
  if (Math.abs(tightenedCenter[1] - cy) > height * 0.05) return detector.boundingBox;
  return tightened;
}

export function boundingBoxForFindingGroup(
  group: ToothFindingGroup,
  detections: VisionToothDetection[],
  imageWidth?: number,
  _imageHeight?: number
): BoundingBox | null {
  if (group.toothCode && imageWidth && imageWidth > 0) {
    const anatomical = anatomicalDetectorForTooth(group.toothCode, detections, imageWidth);
    if (anatomical) {
      return tightenDetectorBox(anatomical, group.toothCode, detections, imageWidth);
    }
  }

  const detector = detectorForFindingGroup(group, detections);
  if (detector) return detector.boundingBox;
  if (group.boundingBox) return group.boundingBox;
  return unionBoundingBoxes(group.provenanceBoxes);
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
