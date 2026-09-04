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
  extractVisionToothDetections,
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
  const armenian = document.documentElement.lang === "hy";

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
  const toothDetections = useMemo(
    () => extractVisionToothDetections(analysis?.structured_result ?? null),
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
        <h3>{armenian ? "Վերլուծություն ընտրված չէ" : "No analysis selected"}</h3>
        <p>{armenian ? "Ընտրեք վերբեռնված ռենտգենը և գործարկեք DENTAI V5-ը կամ բացեք առկա վերլուծությունը։" : "Select an uploaded X-ray and run DENTAI V5, or choose an existing analysis."}</p>
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
      setReviewDone(armenian ? "Վերանայման որոշումները պահպանվել են։" : "Review decisions saved.");
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
            <p className="eyebrow">DENTAI V5 · {armenian ? "Կլինիկական վերանայում" : "Clinical review"}</p>
            <h2>{armenian ? "AI-ով աջակցվող ռենտգենային վերանայում" : "AI-assisted radiographic review"}</h2>
            <p>{displayDate(analysis.completed_at ?? analysis.requested_at)} · {toothDetections.length} {armenian ? "հայտնաբերված ատամ" : "detected teeth"} · {productVisibleFindings.length} {armenian ? "տեսանելի արդյունք" : "visible findings"}</p>
          </div>
        </div>
        <StatusBadge value={analysis.status} />
      </header>

      {analysis.status === "FAILED" && (
        <div className="error-panel" role="alert">
          {armenian ? "Վերլուծությունը ձախողվել է" : "Analysis failed"}{analysis.error_code ? `: ${analysis.error_code}` : "."}
        </div>
      )}

      {summaryPresentation.showPanel && clinicalSummary && (
        <section className="clinical-briefing" lang={armenian ? "hy" : "en"}>
          <div className="briefing-orbit" aria-hidden="true">
            <span>AI</span><i /><i />
          </div>
          <div className="briefing-copy">
            <p className="eyebrow">{armenian ? "Կլինիկական ամփոփում" : "Clinical summary"}</p>
            <h3>{clinicalSummary.doctor_summary}</h3>
            <p className="briefing-safety">{armenian ? "DENTAI-ի կառուցվածքային տվյալների բացատրություն է և չի փոխարինում բժշկի գնահատմանը։" : "Interpretation of DENTAI structured evidence; it does not replace clinician assessment."}</p>
          </div>
          <div className="briefing-signals">
            {clinicalSummary.important_changes[0] && (
              <article>
                <span className="signal-icon">◉</span>
                <div><small>{armenian ? "Հիմնական դիտարկում" : "Key observation"}</small><strong>{clinicalSummary.important_changes[0]}</strong></div>
              </article>
            )}
            {clinicalSummary.monitoring_points[0] && (
              <article>
                <span className="signal-icon">⌁</span>
                <div><small>{armenian ? "Հսկողություն" : "Monitoring"}</small><strong>{clinicalSummary.monitoring_points[0]}</strong></div>
              </article>
            )}
            {clinicalSummary.questions_for_doctor[0] && (
              <article>
                <span className="signal-icon">?</span>
                <div><small>{armenian ? "Բժշկի համար" : "For the clinician"}</small><strong>{clinicalSummary.questions_for_doctor[0]}</strong></div>
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
        detections={toothDetections}
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
            <strong>{armenian ? "Բժշկի հաստատում" : "Clinician confirmation"}</strong>
            <p>{armenian ? "Յուրաքանչյուր արդյունքի համար ընտրեք «Հաստատել» կամ «Մերժել»։" : "Confirm or reject each pending finding before saving the review."}</p>
          </div>
          {reviewError && <span className="review-inline-error" role="alert">{reviewError}</span>}
          {reviewDone && <span className="review-inline-success" role="status">{reviewDone}</span>}
          <button
            className="button button-accent"
            type="button"
            disabled={!canSubmit || reviewing}
            onClick={() => void submitReview()}
          >
            {reviewing ? (armenian ? "Պահպանվում է…" : "Saving…") : (armenian ? "Պահպանել վերանայումը" : "Save review")}
          </button>
        </section>
      )}

      <details className="finding-library-fold card">
        <summary>
          <span>{armenian ? "Բոլոր տեսանելի արդյունքները" : "All visible findings"}</span>
          <small>{armenian ? `Մոդելի գնահատական ≥ ${MODEL_SCORE_DISPLAY_THRESHOLD.toFixed(2)} · փակ է լռելյայն` : `Model score ≥ ${MODEL_SCORE_DISPLAY_THRESHOLD.toFixed(2)} · hidden by default`}</small>
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
        <summary>{armenian ? "Տեխնիկական վերլուծության տվյալներ" : "Technical analysis data"}</summary>
        <div className="technical-mini-grid">
          <span><small>Analysis ID</small><strong>{analysis.id}</strong></span>
          <span><small>{armenian ? "Մատակարար" : "Provider"}</small><strong>{analysis.provider}</strong></span>
          <span><small>{armenian ? "Մոդելի տարբերակ" : "Model version"}</small><strong>{analysis.model_version}</strong></span>
          <span><small>{armenian ? "Վերանայում" : "Review"}</small><strong>{analysis.review_status.replaceAll("_", " ")}</strong></span>
        </div>
        <details className="raw-json nested-raw-json"><summary>Raw JSON</summary><pre>{JSON.stringify({ analysis, xray, findings }, null, 2)}</pre></details>
      </details>
    </section>
  );
}
