import type {
  AIAnalysis,
  DentalFinding,
  FindingProvenance,
  FindingReview,
  XRay
} from "../api/types";

export type FindingFilter = "ALL" | FindingReview;
export type BoundingBox = [number, number, number, number];

export interface ToothFindingGroup {
  key: string;
  toothCode: string | null;
  findings: DentalFinding[];
  boundingBox: BoundingBox | null;
}

export function extractBoundingBox(
  provenance: FindingProvenance | null
): BoundingBox | null {
  const value = provenance?.bounding_box;
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

export function groupFindingsByTooth(findings: DentalFinding[]): ToothFindingGroup[] {
  const grouped = new Map<string, DentalFinding[]>();

  for (const finding of findings) {
    const key = finding.tooth_code ? "tooth:" + finding.tooth_code : "unassigned:" + finding.id;
    grouped.set(key, [...(grouped.get(key) ?? []), finding]);
  }

  return Array.from(grouped, ([key, groupedFindings]) => {
    const boxes = groupedFindings
      .map((finding) => extractBoundingBox(finding.provenance))
      .filter((box): box is BoundingBox => box !== null);
    return {
      key,
      toothCode: groupedFindings[0]?.tooth_code ?? null,
      findings: groupedFindings,
      boundingBox: unionBoundingBoxes(boxes)
    };
  }).sort((left, right) =>
    (left.toothCode ?? left.key).localeCompare(right.toothCode ?? right.key, undefined, {
      numeric: true
    })
  );
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
