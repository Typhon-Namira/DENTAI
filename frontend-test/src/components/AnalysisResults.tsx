import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { api, errorMessage } from "../api/client";
import type {
  AIAnalysis,
  DentalFinding,
  ReviewDecision,
  Role,
  XRay
} from "../api/types";
import {
  extractVisionToothGeometry,
  filterFindings,
  findingGroupKey,
  groupFindingsByTooth,
  isFindingProductVisible,
  MODEL_SCORE_DISPLAY_THRESHOLD,
  resolveSelectedGroupKey,
  type FindingFilter
} from "../utils/opg";
import {
  clinicalSummaryPresentation,
  humanizeFindingType,
  parseClinicalSummary
} from "../utils/clinicalSummary";
import { OPGAnalysisViewer } from "./OPGAnalysisViewer";
import { StatusBadge } from "./StatusBadge";

interface AnalysisResultsProps {
  analysis: AIAnalysis | null;
  xray: XRay | null;
  findings: DentalFinding[];
  role: Role;
  onReviewed: () => Promise<void> | void;
}

function displayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
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

  const clinicalSummary = useMemo(
    () => parseClinicalSummary(analysis?.structured_result?.clinical_summary),
    [analysis?.structured_result]
  );
  const summaryPresentation = clinicalSummaryPresentation(clinicalSummary);
  const productVisibleFindings = useMemo(
    () => findings.filter(isFindingProductVisible),
    [findings]
  );
  const filteredFindings = useMemo(
    () => filterFindings(productVisibleFindings, filter),
    [productVisibleFindings, filter]
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
    () => productVisibleFindings.filter((finding) => finding.review_status === "PENDING"),
    [productVisibleFindings]
  );
  const decidedCount = pending.filter((finding) => decisions[finding.id]).length;
  const canSubmit = pending.length > 0 && decidedCount === pending.length;
  const reviewProgressStyle = {
    "--progress": `${Math.round((decidedCount / Math.max(pending.length, 1)) * 100)}%`
  } as CSSProperties;

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
        <h3>No analysis selected</h3>
        <p>Select an uploaded X-ray and run DENTAI V5, or choose an existing analysis.</p>
      </section>
    );
  }

  async function submitReview() {
    if (!analysis || !canSubmit) return;
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
      setReviewDone("Վերանայման որոշումները պահպանվել են։");
      await onReviewed();
    } catch (reason) {
      setReviewError(errorMessage(reason));
    } finally {
      setReviewing(false);
    }
  }

  function inspectFinding(finding: DentalFinding) {
    setFilter("ALL");
    setSelectedGroupKey(findingGroupKey(finding));
  }

  return (
    <section className="analysis-workspace pro-analysis-workspace">
      <header className="analysis-focus-header">
        <div>
          <span className="analysis-spark" aria-hidden="true">✦</span>
          <div>
            <p className="eyebrow">DENTAI V5 · Clinical review</p>
            <h2>AI-assisted radiographic review</h2>
            <p>{displayDate(analysis.completed_at ?? analysis.requested_at)} · {productVisibleFindings.length} product-visible findings</p>
          </div>
        </div>
        <StatusBadge value={analysis.status} />
      </header>

      {analysis.status === "FAILED" && (
        <div className="error-panel" role="alert">
          Analysis failed{analysis.error_code ? `: ${analysis.error_code}` : "."}
        </div>
      )}

      {summaryPresentation.showPanel && clinicalSummary && (
        <section className="clinical-briefing" lang="hy">
          <div className="briefing-orbit" aria-hidden="true">
            <span>AI</span><i /><i />
          </div>
          <div className="briefing-copy">
            <p className="eyebrow">Կլինիկական ամփոփում</p>
            <h3>{clinicalSummary.doctor_summary}</h3>
            <p className="briefing-safety">DENTAI-ի կառուցվածքային տվյալների բացատրություն է և չի փոխարինում բժշկի գնահատմանը։</p>
          </div>
          <div className="briefing-signals">
            {clinicalSummary.important_changes[0] && (
              <article>
                <span className="signal-icon">◉</span>
                <div><small>Հիմնական դիտարկում</small><strong>{clinicalSummary.important_changes[0]}</strong></div>
              </article>
            )}
            {clinicalSummary.monitoring_points[0] && (
              <article>
                <span className="signal-icon">⌁</span>
                <div><small>Հսկողություն</small><strong>{clinicalSummary.monitoring_points[0]}</strong></div>
              </article>
            )}
            {clinicalSummary.questions_for_doctor[0] && (
              <article>
                <span className="signal-icon">?</span>
                <div><small>Բժշկի համար</small><strong>{clinicalSummary.questions_for_doctor[0]}</strong></div>
              </article>
            )}
          </div>
          {summaryPresentation.showPartialWarning && (
            <p className="briefing-partial" role="status">{summaryPresentation.partialWarning}</p>
          )}
        </section>
      )}

      <OPGAnalysisViewer
        xray={xray}
        groups={groups}
        clinicalSummary={clinicalSummary}
        filter={filter}
        selectedGroupKey={selectedGroupKey}
        canReview={role === "DOCTOR"}
        decisions={decisions}
        onDecisionChange={(findingId, decision) =>
          setDecisions((current) => ({ ...current, [findingId]: decision }))
        }
        onFilterChange={setFilter}
        onSelectedGroupChange={setSelectedGroupKey}
      />

      {role === "DOCTOR" && pending.length > 0 && (
        <section className="compact-review-dock" aria-label="Clinician review">
          <div className="review-progress-ring" style={reviewProgressStyle}>
            <span>{decidedCount}/{pending.length}</span>
          </div>
          <div>
            <strong>Բժշկի հաստատում</strong>
            <p>Ընտրեք յուրաքանչյուր բացված արդյունքի «Հաստատել» կամ «Մերժել» տարբերակը։</p>
          </div>
          {reviewError && <span className="review-inline-error" role="alert">{reviewError}</span>}
          {reviewDone && <span className="review-inline-success" role="status">{reviewDone}</span>}
          <button
            className="button button-accent"
            type="button"
            disabled={!canSubmit || reviewing}
            onClick={() => void submitReview()}
          >
            {reviewing ? "Պահպանվում է…" : "Պահպանել վերանայումը"}
          </button>
        </section>
      )}

      <details className="finding-library-fold card">
        <summary>
          <span>All visible findings</span>
          <small>Model score ≥ {MODEL_SCORE_DISPLAY_THRESHOLD.toFixed(2)} · hidden by default</small>
        </summary>
        <div className="finding-library-list">
          {productVisibleFindings.map((finding) => (
            <button key={finding.id} type="button" onClick={() => inspectFinding(finding)}>
              <span className="tooth-code">{finding.tooth_code}</span>
              <span><strong>{humanizeFindingType(finding.finding_type)}</strong><small>{finding.review_status.replaceAll("_", " ")}</small></span>
              <span>›</span>
            </button>
          ))}
        </div>
      </details>

      <details className="technical-fold card">
        <summary>Technical analysis data</summary>
        <div className="technical-mini-grid">
          <span><small>Analysis ID</small><strong>{analysis.id}</strong></span>
          <span><small>Provider</small><strong>{analysis.provider}</strong></span>
          <span><small>Model version</small><strong>{analysis.model_version}</strong></span>
          <span><small>Review</small><strong>{analysis.review_status.replaceAll("_", " ")}</strong></span>
        </div>
        <details className="raw-json nested-raw-json"><summary>Raw JSON</summary><pre>{JSON.stringify({ analysis, xray, findings }, null, 2)}</pre></details>
      </details>
    </section>
  );
}
