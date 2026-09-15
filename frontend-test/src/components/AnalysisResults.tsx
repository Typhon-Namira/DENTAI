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
  isResolvedFdi,
  resolveSelectedGroupKey,
  type FindingFilter
} from "../utils/opg";
import { parseClinicalSummary } from "../utils/clinicalSummary";
import { dashboardText, type DashboardLang } from "../product/dashboardI18n";
import { OPGAnalysisViewer } from "./OPGAnalysisViewer";

interface AnalysisResultsProps {
  analysis: AIAnalysis | null;
  xray: XRay | null;
  findings: DentalFinding[];
  role: Role;
  onReviewed: () => Promise<unknown> | void;
  lang: DashboardLang;
}

const copy = {
  en: { none: "No analysis selected", choose: "Select an X-ray and run Teta2 AI.", saved: "Review saved.", failed: "Analysis failed" },
  hy: { none: "Վերլուծություն ընտրված չէ", choose: "Ընտրեք ռենտգեն պատկերը և գործարկեք Teta2 ԱԲ-ն։", saved: "Վերանայումը պահպանվել է։", failed: "Վերլուծությունը ձախողվել է" },
  ru: { none: "Анализ не выбран", choose: "Выберите рентгеновский снимок и запустите Teta2 ИИ.", saved: "Результаты проверки сохранены.", failed: "Не удалось выполнить анализ" }
} as const;

export function AnalysisResults({ analysis, xray, findings, role, onReviewed, lang }: AnalysisResultsProps) {
  const [decisions, setDecisions] = useState<Record<string, ReviewDecision | "">>({});
  const [reviewing, setReviewing] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewDone, setReviewDone] = useState("");
  const [filter, setFilter] = useState<FindingFilter>("ALL");
  const [selectedGroupKey, setSelectedGroupKey] = useState<string | null>(null);
  const text = copy[lang];

  const clinicalSummary = useMemo(() => parseClinicalSummary(analysis?.structured_result?.clinical_summary), [analysis?.structured_result]);
  const resolvedFindings = useMemo(() => findings.filter((finding) => isResolvedFdi(finding.tooth_code)), [findings]);
  const filteredFindings = useMemo(() => filterFindings(resolvedFindings, filter), [resolvedFindings, filter]);
  const toothDetections = useMemo(() => extractVisionToothDetections(analysis?.structured_result ?? null), [analysis?.structured_result]);
  const visionGeometry = useMemo(() => extractVisionToothGeometry(analysis?.structured_result ?? null), [analysis?.structured_result]);
  const groups = useMemo(() => groupFindingsByTooth(filteredFindings, visionGeometry.boxes, visionGeometry.ambiguousToothCodes), [filteredFindings, visionGeometry]);
  const pending = useMemo(() => resolvedFindings.filter((finding) => finding.review_status === "PENDING"), [resolvedFindings]);
  const decidedCount = pending.filter((finding) => decisions[finding.id]).length;
  const canSubmit = pending.length > 0 && decidedCount === pending.length;
  const canReview = role === "DIRECTOR" || role === "MANAGER" || role === "DOCTOR";

  useEffect(() => {
    setDecisions({}); setReviewError(""); setReviewDone(""); setFilter("ALL"); setSelectedGroupKey(null);
  }, [analysis?.id]);

  useEffect(() => { setSelectedGroupKey((current) => resolveSelectedGroupKey(groups, current)); }, [groups]);

  if (!analysis) return <section className="card empty-state"><span className="empty-icon" aria-hidden="true">◎</span><h3>{text.none}</h3><p>{text.choose}</p></section>;

  async function submitReview() {
    if (!canSubmit || !analysis) return;
    setReviewing(true); setReviewError(""); setReviewDone("");
    try {
      await api.reviewAnalysis(analysis.id, { decisions: pending.map((finding) => ({ finding_id: finding.id, decision: decisions[finding.id] as ReviewDecision })) });
      setReviewDone(text.saved);
      await onReviewed();
    } catch (reason) { setReviewError(errorMessage(reason)); }
    finally { setReviewing(false); }
  }

  if (analysis.status === "FAILED") return <section className="card error-panel" role="alert">{text.failed}{analysis.error_code ? `: ${analysis.error_code}` : "."}</section>;

  return <OPGAnalysisViewer
    xray={xray}
    groups={groups}
    detections={toothDetections}
    clinicalSummary={clinicalSummary}
    filter={filter}
    selectedGroupKey={selectedGroupKey}
    canReview={canReview}
    decisions={decisions}
    pendingCount={pending.length}
    decidedCount={decidedCount}
    reviewing={reviewing}
    reviewError={reviewError}
    reviewDone={reviewDone}
    canSubmitReview={canSubmit}
    onSubmitReview={() => void submitReview()}
    onDecisionChange={(findingId, decision) => setDecisions((current) => ({ ...current, [findingId]: decision }))}
    onFilterChange={setFilter}
    onSelectedGroupChange={setSelectedGroupKey}
    lang={lang}
    reviewLabel={dashboardText(lang, "review")}
  />;
}
