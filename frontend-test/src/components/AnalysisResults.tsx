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
  extractVisionToothBoxes,
  filterFindings,
  findingModelScore,
  formatModelScore,
  groupFindingsByTooth,
  resolveSelectedGroupKey,
  type FindingFilter
} from "../utils/opg";
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

  const filteredFindings = useMemo(
    () => filterFindings(findings, filter),
    [findings, filter]
  );
  const visionBoxes = useMemo(
    () => extractVisionToothBoxes(analysis?.structured_result ?? null),
    [analysis?.structured_result]
  );
  const groups = useMemo(
    () => groupFindingsByTooth(filteredFindings, visionBoxes),
    [filteredFindings, visionBoxes]
  );
  const pending = useMemo(
    () => findings.filter((finding) => finding.review_status === "PENDING"),
    [findings]
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
    setSelectedGroupKey(
      finding.tooth_code ? "tooth:" + finding.tooth_code : "unassigned:" + finding.id
    );
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

      <OPGAnalysisViewer
        xray={xray}
        groups={groups}
        filter={filter}
        selectedGroupKey={selectedGroupKey}
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
          Model score is supporting AI evidence and is not an independent diagnostic probability.
          Exact backend values remain available in Raw JSON.
        </p>

        {groups.length === 0 ? (
          <div className="empty-inline">
            {findings.length === 0
              ? analysis.status === "COMPLETED"
                ? "No DentalFinding records were returned for this analysis."
                : "Findings will appear after processing completes."
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
                <span className="tooth-code">{group.toothCode ?? "Unassigned"}</span>
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
                    <span className="tooth-code">{finding.tooth_code ?? "—"}</span>
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
