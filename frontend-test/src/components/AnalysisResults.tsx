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
  extractVisionToothGeometry,
  filterFindings,
  findingGroupKey,
  findingModelScore,
  formatModelScore,
  groupFindingsByTooth,
  isFindingProductVisible,
  MODEL_SCORE_DISPLAY_THRESHOLD,
  resolveSelectedGroupKey,
  type FindingFilter
} from "../utils/opg";
import { parseClinicalSummary } from "../utils/clinicalSummary";
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
  const canSubmit = pending.length > 0 && pending.every((finding) => decisions[finding.id]);

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
      setReviewDone("Review decisions submitted.");
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
    <section className="analysis-workspace">
      <header className="analysis-hero-header">
        <div>
          <p className="eyebrow">DENTAI V5 analysis</p>
          <h2>{analysis.model_name}</h2>
          <p>
            Original OPG with model-generated tooth regions and clinician-review evidence.
          </p>
        </div>
        <StatusBadge value={analysis.status} />
      </header>

      <div className="analysis-metadata card">
        <dl className="metadata-grid">
          <div><dt>Analysis ID</dt><dd>{analysis.id}</dd></div>
          <div><dt>Provider</dt><dd>{analysis.provider}</dd></div>
          <div><dt>Model version</dt><dd>{analysis.model_version}</dd></div>
          <div><dt>Schema version</dt><dd>{analysis.analysis_schema_version}</dd></div>
          <div><dt>Review</dt><dd>{analysis.review_status.replaceAll("_", " ")}</dd></div>
          <div><dt>Requested</dt><dd>{displayDate(analysis.requested_at)}</dd></div>
          <div><dt>Processing started</dt><dd>{displayDate(analysis.processing_started_at)}</dd></div>
          <div><dt>Completed</dt><dd>{displayDate(analysis.completed_at)}</dd></div>
        </dl>
        {analysis.status === "FAILED" && (
          <div className="error-panel" role="alert">
            Analysis failed{analysis.error_code ? ": " + analysis.error_code : "."}
          </div>
        )}
      </div>

      {clinicalSummary && (
        <section className="card clinical-summary-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">AI-assisted clinical summary</p>
              <h3>DENTAI evidence in clinical language</h3>
            </div>
          </div>
          <p className="clinical-summary-disclaimer">
            AI-assisted explanatory text based only on DENTAI structured evidence.
            This is not a diagnosis and requires clinician review.
          </p>
          <p className="doctor-summary">{clinicalSummary.doctor_summary}</p>
          <div className="clinical-summary-lists">
            {clinicalSummary.important_changes.length > 0 && (
              <div>
                <h4>Important changes</h4>
                <ul>{clinicalSummary.important_changes.map((item) => (
                  <li key={item}>{item}</li>
                ))}</ul>
              </div>
            )}
            {clinicalSummary.monitoring_points.length > 0 && (
              <div>
                <h4>Monitoring points</h4>
                <ul>{clinicalSummary.monitoring_points.map((item) => (
                  <li key={item}>{item}</li>
                ))}</ul>
              </div>
            )}
            {clinicalSummary.questions_for_doctor.length > 0 && (
              <div>
                <h4>Questions for the doctor</h4>
                <ul>{clinicalSummary.questions_for_doctor.map((item) => (
                  <li key={item}>{item}</li>
                ))}</ul>
              </div>
            )}
          </div>
          {clinicalSummary.patient_message_draft && (
            <details className="patient-message-draft">
              <summary>Optional patient message draft</summary>
              <p>{clinicalSummary.patient_message_draft}</p>
            </details>
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

      <section className="card findings-review-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Findings / clinician review</p>
            <h3>Finding groups</h3>
          </div>
          <span className="count-badge">{filteredFindings.length}</span>
        </div>
        <p className="score-helper">
          Product view shows AI findings with a model score of{" "}
          {MODEL_SCORE_DISPLAY_THRESHOLD.toFixed(2)} or higher.
        </p>
        <p className="score-helper">
          Model score is supporting AI evidence and is not an independent diagnostic probability.
          Exact backend values remain available in Raw JSON.
        </p>

        {groups.length === 0 ? (
          <div className="empty-inline">
            {findings.length === 0
              ? analysis.status === "COMPLETED"
                ? "No DentalFinding records were returned for this analysis."
                : "Findings will appear after processing completes."
              : productVisibleFindings.length === 0
                ? "No findings meet the product display threshold."
                : "No findings match the selected review filter."}
          </div>
        ) : (
          <div className="finding-group-grid">
            {groups.map((group) => (
              <button
                className={"finding-group-card" + (
                  selectedGroupKey === group.key ? " selected" : ""
                )}
                key={group.key}
                type="button"
                onClick={() => setSelectedGroupKey(group.key)}
                onMouseEnter={() => setSelectedGroupKey(group.key)}
              >
                <span className="tooth-code">{group.toothCode ?? "Finding region"}</span>
                <span className="group-findings">
                  <strong>{group.findings.map((finding) =>
                    finding.finding_type.replaceAll("_", " ")
                  ).join(" · ")}</strong>
                  <small>
                    {group.findings.map((finding) =>
                      formatModelScore(findingModelScore(finding))
                    ).join(" · ")}
                  </small>
                </span>
                <span className="group-statuses">
                  {Array.from(new Set(group.findings.map((finding) => finding.review_status)))
                    .map((status) => <StatusBadge key={status} value={status} />)}
                </span>
              </button>
            ))}
          </div>
        )}

        {role === "DOCTOR" && pending.length > 0 && (
          <div className="review-panel">
            <div>
              <p className="eyebrow">Required decisions</p>
              <h3>Review every pending finding</h3>
              <p className="muted">
                Each pending finding requires an explicit Confirm or Reject decision.
                Nothing is auto-confirmed.
              </p>
            </div>
            <div className="clinical-review-list">
              {pending.map((finding) => (
                <article
                  className="clinical-review-row"
                  key={finding.id}
                  onMouseEnter={() => inspectFinding(finding)}
                >
                  <button type="button" onClick={() => inspectFinding(finding)}>
                    <span className="tooth-code">{finding.tooth_code ?? "Finding region"}</span>
                    <span>
                      <strong>{finding.finding_type.replaceAll("_", " ")}</strong>
                      <small>{finding.description}</small>
                    </span>
                  </button>
                  <label>
                    Decision
                    <select
                      value={decisions[finding.id] ?? ""}
                      onChange={(event) =>
                        setDecisions((current) => ({
                          ...current,
                          [finding.id]: event.target.value as ReviewDecision | ""
                        }))
                      }
                    >
                      <option value="">Choose…</option>
                      <option value="CONFIRMED">Confirm finding</option>
                      <option value="REJECTED">Reject finding</option>
                    </select>
                  </label>
                </article>
              ))}
            </div>
            {reviewError && <div className="error-panel" role="alert">{reviewError}</div>}
            {reviewDone && <div className="success-panel" role="status">{reviewDone}</div>}
            <button
              className="button button-primary"
              type="button"
              disabled={!canSubmit || reviewing}
              onClick={() => void submitReview()}
            >
              {reviewing ? "Submitting decisions…" : "Submit clinician review"}
            </button>
          </div>
        )}
      </section>

      <details className="card raw-json">
        <summary>Raw JSON</summary>
        <pre>{JSON.stringify({ analysis, xray, findings }, null, 2)}</pre>
      </details>
    </section>
  );
}
