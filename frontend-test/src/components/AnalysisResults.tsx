import { useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../api/client";
import type {
  AIAnalysis,
  DentalFinding,
  ReviewDecision,
  Role
} from "../api/types";
import { StatusBadge } from "./StatusBadge";

interface AnalysisResultsProps {
  analysis: AIAnalysis | null;
  findings: DentalFinding[];
  role: Role;
  onReviewed: () => Promise<void> | void;
}

function displayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function confidence(value: number | null): string {
  return value === null ? "Not provided" : String(value);
}

export function AnalysisResults({ analysis, findings, role, onReviewed }: AnalysisResultsProps) {
  const [decisions, setDecisions] = useState<Record<string, ReviewDecision | "">>({});
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewDone, setReviewDone] = useState("");

  useEffect(() => {
    setDecisions({});
    setReviewError("");
    setReviewDone("");
  }, [analysis?.id]);

  const pending = useMemo(
    () => findings.filter((finding) => finding.review_status === "PENDING"),
    [findings]
  );
  const canSubmit = pending.length > 0 && pending.every((finding) => decisions[finding.id]);

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

  return (
    <section className="results-stack">
      <div className="card result-summary">
        <div className="section-heading">
          <div>
            <p className="eyebrow">DENTAI V5 result</p>
            <h3>Analysis overview</h3>
          </div>
          <StatusBadge value={analysis.status} />
        </div>

        <dl className="metadata-grid">
          <div><dt>Analysis ID</dt><dd>{analysis.id}</dd></div>
          <div><dt>Provider</dt><dd>{analysis.provider}</dd></div>
          <div><dt>Model</dt><dd>{analysis.model_name}</dd></div>
          <div><dt>Model version</dt><dd>{analysis.model_version}</dd></div>
          <div><dt>Schema version</dt><dd>{analysis.analysis_schema_version}</dd></div>
          <div><dt>Review</dt><dd>{analysis.review_status.replaceAll("_", " ")}</dd></div>
          <div><dt>Requested</dt><dd>{displayDate(analysis.requested_at)}</dd></div>
          <div><dt>Processing started</dt><dd>{displayDate(analysis.processing_started_at)}</dd></div>
          <div><dt>Completed</dt><dd>{displayDate(analysis.completed_at)}</dd></div>
          <div><dt>Failed</dt><dd>{displayDate(analysis.failed_at)}</dd></div>
        </dl>

        {analysis.status === "FAILED" && (
          <div className="error-panel" role="alert">
            Analysis failed{analysis.error_code ? ": " + analysis.error_code : "."}
          </div>
        )}
      </div>

      <div className="card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Product view</p>
            <h3>Dental findings</h3>
          </div>
          <span className="count-badge">{findings.length}</span>
        </div>

        {findings.length === 0 ? (
          <div className="empty-inline">
            {analysis.status === "COMPLETED"
              ? "No DentalFinding records were returned for this analysis."
              : "Findings will appear after processing completes."}
          </div>
        ) : (
          <div className="finding-list">
            {findings.map((finding) => (
              <article className="finding-card" key={finding.id}>
                <div className="finding-topline">
                  <span className="tooth-code">{finding.tooth_code || "General"}</span>
                  <StatusBadge value={finding.review_status} />
                </div>
                <h4>{finding.finding_type.replaceAll("_", " ")}</h4>
                <p>{finding.description}</p>
                <dl className="finding-meta">
                  <div><dt>Confidence</dt><dd>{confidence(finding.confidence)}</dd></div>
                  <div><dt>Source</dt><dd>{finding.source}</dd></div>
                  <div><dt>Created</dt><dd>{displayDate(finding.created_at)}</dd></div>
                </dl>
                {finding.review_status === "PENDING" && (
                  <p className="review-required">Requires clinician review</p>
                )}
                {role === "DOCTOR" && finding.review_status === "PENDING" && (
                  <label className="decision-field">
                    Review decision
                    <select
                      value={decisions[finding.id] ?? ""}
                      onChange={(event) =>
                        setDecisions((current) => ({
                          ...current,
                          [finding.id]: event.target.value as ReviewDecision | ""
                        }))
                      }
                    >
                      <option value="">Choose a decision…</option>
                      <option value="CONFIRMED">Confirm finding</option>
                      <option value="REJECTED">Reject finding</option>
                    </select>
                  </label>
                )}
              </article>
            ))}
          </div>
        )}

        {role === "DOCTOR" && pending.length > 0 && (
          <div className="review-panel">
            <p className="muted">
              Select an explicit decision for every pending finding. Nothing is auto-confirmed.
            </p>
            {reviewError && <div className="error-panel" role="alert">{reviewError}</div>}
            {reviewDone && <div className="success-panel" role="status">{reviewDone}</div>}
            <button
              className="button button-primary"
              type="button"
              disabled={!canSubmit || reviewing}
              onClick={() => void submitReview()}
            >
              {reviewing ? "Saving review…" : "Submit clinician review"}
            </button>
          </div>
        )}
      </div>

      <details className="card raw-json">
        <summary>Raw JSON</summary>
        <pre>{JSON.stringify({ analysis, findings }, null, 2)}</pre>
      </details>
    </section>
  );
}
