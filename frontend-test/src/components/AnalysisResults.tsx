import { useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../api/client";
import type {
  AIAnalysis,
  DentalFinding,
  ReviewDecision,
  Role,
  XRay
} from "../api/types";
import {
  extractVisionToothDetections,
  extractVisionToothGeometry,
  filterFindings,
  groupFindingsByTooth,
  resolveSelectedGroupKey,
  type FindingFilter
} from "../utils/opg";
import { parseClinicalSummary } from "../utils/clinicalSummary";
import { OPGAnalysisViewer } from "./OPGAnalysisViewer";

interface AnalysisResultsProps {
  analysis: AIAnalysis | null;
  xray: XRay | null;
  findings: DentalFinding[];
  role: Role;
  onReviewed: () => Promise<void> | void;
}

export function AnalysisResults({
  analysis,
  xray,
  findings,
  role,
  onReviewed
}: AnalysisResultsProps) {
  const [decisions, setDecisions] = useState<Record<string, ReviewDecision | "">>({});
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewDone, setReviewDone] = useState("");
  const [filter, setFilter] = useState<FindingFilter>("ALL");
  const [selectedGroupKey, setSelectedGroupKey] = useState<string | null>(null);
  const armenian = document.documentElement.lang === "hy";

  const clinicalSummary = useMemo(
    () => parseClinicalSummary(analysis?.structured_result?.clinical_summary),
    [analysis?.structured_result]
  );
  const filteredFindings = useMemo(
    () => filterFindings(findings, filter),
    [findings, filter]
  );
  const toothDetections = useMemo(
    () => extractVisionToothDetections(analysis?.structured_result ?? null),
    [analysis?.structured_result]
  );
  const visionGeometry = useMemo(
    () => extractVisionToothGeometry(analysis?.structured_result ?? null),
    [analysis?.structured_result]
  );
  const groups = useMemo(
    () => groupFindingsByTooth(
      filteredFindings,
      visionGeometry.boxes,
      visionGeometry.ambiguousToothCodes
    ),
    [filteredFindings, visionGeometry]
  );
  const pending = useMemo(
    () => findings.filter((finding) => finding.review_status === "PENDING"),
    [findings]
  );
  const decidedCount = pending.filter((finding) => decisions[finding.id]).length;
  const canSubmit = pending.length > 0 && decidedCount === pending.length;

  useEffect(() => {
    setDecisions({});
    setReviewError("");
    setReviewDone("");
    setFilter("ALL");
    setSelectedGroupKey(null);
  }, [analysis?.id]);

  useEffect(() => {
    setSelectedGroupKey((current) => resolveSelectedGroupKey(groups, current));
  }, [groups]);

  if (!analysis) {
    return (
      <section className="card empty-state">
        <span className="empty-icon" aria-hidden="true">◎</span>
        <h3>{armenian ? "Վերլուծություն ընտրված չէ" : "No analysis selected"}</h3>
        <p>{armenian ? "Ընտրեք ռենտգենը և գործարկեք DENTAI V5-ը։" : "Select an X-ray and run DENTAI V5."}</p>
      </section>
    );
  }

  async function submitReview() {
    if (!canSubmit) return;
    setReviewing(true);
    setReviewError("");
    setReviewDone("");
    try {
      await api.reviewAnalysis(analysis.id, {
        decisions: pending.map((finding) => ({
          finding_id: finding.id,
          decision: decisions[finding.id] as ReviewDecision
        }))
      });
      setReviewDone(armenian ? "Վերանայումը պահպանվել է։" : "Review saved.");
      await onReviewed();
    } catch (reason) {
      setReviewError(errorMessage(reason));
    } finally {
      setReviewing(false);
    }
  }

  if (analysis.status === "FAILED") {
    return (
      <section className="card error-panel" role="alert">
        {armenian ? "Վերլուծությունը ձախողվել է" : "Analysis failed"}
        {analysis.error_code ? `: ${analysis.error_code}` : "."}
      </section>
    );
  }

  return (
    <OPGAnalysisViewer
      xray={xray}
      groups={groups}
      detections={toothDetections}
      clinicalSummary={clinicalSummary}
      filter={filter}
      selectedGroupKey={selectedGroupKey}
      canReview={role === "DOCTOR"}
      decisions={decisions}
      pendingCount={pending.length}
      decidedCount={decidedCount}
      reviewing={reviewing}
      reviewError={reviewError}
      reviewDone={reviewDone}
      canSubmitReview={canSubmit}
      onSubmitReview={() => void submitReview()}
      onDecisionChange={(findingId, decision) =>
        setDecisions((current) => ({ ...current, [findingId]: decision }))
      }
      onFilterChange={setFilter}
      onSelectedGroupChange={setSelectedGroupKey}
    />
  );
}