import type { DentalFinding } from "../api/types";
import type { ToothFindingGroup } from "./opg";

export type FindingTone = "RESTORATIVE" | "PATHOLOGY";

const RESTORATIVE_FINDINGS = new Set([
  "FILLING",
  "CROWN",
  "RESTORATION",
  "RESTORED",
  "IMPLANT",
  "BRIDGE",
  "ROOT_CANAL_TREATMENT",
  "ROOT_CANAL_FILLING",
  "ENDODONTIC_TREATMENT"
]);

export function findingTone(findingType: string): FindingTone {
  return RESTORATIVE_FINDINGS.has(findingType.trim().toUpperCase())
    ? "RESTORATIVE"
    : "PATHOLOGY";
}

export function groupFindingTone(group: Pick<ToothFindingGroup, "findings">): FindingTone {
  return group.findings.some((finding) => findingTone(finding.finding_type) === "PATHOLOGY")
    ? "PATHOLOGY"
    : "RESTORATIVE";
}

function finiteConfidence(finding: DentalFinding): number | null {
  return typeof finding.confidence === "number" && Number.isFinite(finding.confidence)
    ? Math.max(0, Math.min(1, finding.confidence))
    : null;
}

export function groupFindingConfidence(
  group: Pick<ToothFindingGroup, "findings">
): number {
  const tone = groupFindingTone(group);
  const relevant = group.findings.filter((finding) =>
    tone === "PATHOLOGY" ? findingTone(finding.finding_type) === "PATHOLOGY" : true
  );
  const values = relevant
    .map(finiteConfidence)
    .filter((value): value is number => value !== null);

  return values.length > 0 ? Math.max(...values) : 0.5;
}

export function primaryFinding(
  group: Pick<ToothFindingGroup, "findings">
): DentalFinding | null {
  if (group.findings.length === 0) return null;
  const tone = groupFindingTone(group);
  const candidates = tone === "PATHOLOGY"
    ? group.findings.filter((finding) => findingTone(finding.finding_type) === "PATHOLOGY")
    : group.findings;

  return [...candidates].sort(
    (left, right) => (finiteConfidence(right) ?? -1) - (finiteConfidence(left) ?? -1)
  )[0] ?? group.findings[0];
}
