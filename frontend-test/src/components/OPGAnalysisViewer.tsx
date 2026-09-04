import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { GroqClinicalSummary, ReviewDecision, XRay } from "../api/types";
import {
  normalizeBoundingBoxToImage,
  type FindingFilter,
  type ToothFindingGroup
} from "../utils/opg";
import {
  groupFindingConfidence,
  groupFindingTone,
  primaryFinding
} from "../utils/findingVisuals";
import {
  explanationForGroup,
  humanizeFindingType
} from "../utils/clinicalSummary";

const DISPLAYABLE_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

interface OPGAnalysisViewerProps {
  xray: XRay | null;
  groups: ToothFindingGroup[];
  clinicalSummary: GroqClinicalSummary | null;
  filter: FindingFilter;
  selectedGroupKey: string | null;
  canReview: boolean;
  decisions: Record<string, ReviewDecision | "">;
  pendingCount: number;
  decidedCount: number;
  reviewing: boolean;
  reviewError: string;
  reviewDone: string;
  canSubmitReview: boolean;
  onSubmitReview: () => void;
  onDecisionChange: (findingId: string, decision: ReviewDecision | "") => void;
  onFilterChange: (filter: FindingFilter) => void;
  onSelectedGroupChange: (key: string | null) => void;
}

interface ImageSize {
  width: number;
  height: number;
}

export function OPGAnalysisViewer({
  xray,
  groups,
  clinicalSummary,
  filter,
  selectedGroupKey,
  canReview,
  decisions,
  pendingCount,
  decidedCount,
  reviewing,
  reviewError,
  reviewDone,
  canSubmitReview,
  onSubmitReview,
  onDecisionChange,
  onFilterChange,
  onSelectedGroupChange
}: OPGAnalysisViewerProps) {
  const [imageUrl, setImageUrl] = useState("");
  const [imageSize, setImageSize] = useState<ImageSize | null>(null);
  const [imageError, setImageError] = useState("");
  const [overlaysVisible, setOverlaysVisible] = useState(true);
  const [hoveredGroupKey, setHoveredGroupKey] = useState<string | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const armenian = document.documentElement.lang === "hy";

  const filters: Array<{ value: FindingFilter; label: string }> = armenian
    ? [
        { value: "ALL", label: "Բոլորը" },
        { value: "PENDING", label: "Սպասող" },
        { value: "CONFIRMED", label: "Հաստատված" },
        { value: "REJECTED", label: "Մերժված" }
      ]
    : [
        { value: "ALL", label: "All" },
        { value: "PENDING", label: "Pending" },
        { value: "CONFIRMED", label: "Confirmed" },
        { value: "REJECTED", label: "Rejected" }
      ];

  const selectedGroup = useMemo(
    () => groups.find((group) => group.key === selectedGroupKey) ?? null,
    [groups, selectedGroupKey]
  );
  const selectedExplanation = useMemo(
    () => explanationForGroup(clinicalSummary, selectedGroup),
    [clinicalSummary, selectedGroup]
  );
  const activeGroupKey = hoveredGroupKey ?? selectedGroupKey;
  const displayable = xray ? DISPLAYABLE_IMAGE_TYPES.has(xray.mime_type) : false;

  const projectedRegions = useMemo(() => {
    if (!imageSize) return [];
    return groups.flatMap((group) => {
      const sourceBoxes = group.boundingBox
        ? [group.boundingBox]
        : group.provenanceBoxes;
      return sourceBoxes.flatMap((box, index) => {
        const projected = normalizeBoundingBoxToImage(box, imageSize.width, imageSize.height);
        if (!projected) return [];
        return [{
          key: `${group.key}:${index}`,
          group,
          box: projected,
          tone: groupFindingTone(group),
          confidence: groupFindingConfidence(group),
          primary: primaryFinding(group)
        }];
      });
    });
  }, [groups, imageSize]);

  const selectedRegion = useMemo(
    () => projectedRegions.find((region) => region.group.key === selectedGroupKey) ?? null,
    [projectedRegions, selectedGroupKey]
  );

  const focusPosition = useMemo(() => {
    if (!selectedRegion || !imageSize) return "50% 50%";
    const [x1, y1, x2, y2] = selectedRegion.box;
    const x = (((x1 + x2) / 2) / imageSize.width) * 100;
    const y = (((y1 + y2) / 2) / imageSize.height) * 100;
    return `${x}% ${y}%`;
  }, [selectedRegion, imageSize]);

  useEffect(() => {
    let active = true;
    setImageUrl("");
    setImageSize(null);
    setImageError("");
    setReportOpen(false);

    if (!xray || !DISPLAYABLE_IMAGE_TYPES.has(xray.mime_type)) {
      return () => { active = false; };
    }

    api.xrayDownload(xray.id)
      .then((download) => {
        if (active) setImageUrl(download.url);
      })
      .catch((reason) => {
        if (active) setImageError(errorMessage(reason));
      });

    return () => { active = false; };
  }, [xray?.id, xray?.mime_type]);

  useEffect(() => {
    if (!selectedGroup) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") onSelectedGroupChange(null);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [selectedGroup, onSelectedGroupChange]);

  function selectFromKeyboard(event: KeyboardEvent<SVGGElement>, key: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelectedGroupChange(key);
    }
  }

  function regionColors(tone: "RESTORATIVE" | "PATHOLOGY", confidence: number) {
    if (tone === "RESTORATIVE") {
      return {
        fill: "rgba(34, 197, 94, 0.16)",
        stroke: "rgba(74, 222, 128, 0.96)",
        glow: "rgba(34, 197, 94, 0.72)",
        badge: "#22c55e"
      };
    }
    const strength = Math.max(0.2, Math.min(1, confidence));
    return {
      fill: `rgba(239, 68, 68, ${0.07 + strength * 0.24})`,
      stroke: `rgba(248, 80, 80, ${0.55 + strength * 0.45})`,
      glow: `rgba(239, 68, 68, ${0.18 + strength * 0.68})`,
      badge: `rgba(239, 68, 68, ${0.75 + strength * 0.25})`
    };
  }

  return (
    <section className="opg-workspace medical-opg card findings-only-opg">
      <div className="medical-opg-header">
        <div>
          <p className="eyebrow">{armenian ? "Ինտերակտիվ OPG" : "Interactive OPG"}</p>
          <h3>{armenian ? "DENTAI-ի կլինիկական արդյունքները ռենտգենի վրա" : "DENTAI clinical findings on the radiograph"}</h3>
          <p>{armenian ? "Կանաչ՝ վերականգնված/բուժված ատամներ · կարմիր՝ պաթոլոգիկ արդյունքներ · ավելի մուգ կարմիրը ցույց է տալիս ավելի բարձր վստահություն։" : "Green = restored/treated teeth · red = pathological findings · stronger red indicates higher model confidence."}</p>
        </div>
        <div className="medical-viewer-actions">
          {clinicalSummary && (
            <button className={`opg-report-button${reportOpen ? " active" : ""}`} type="button" onClick={() => setReportOpen((value) => !value)}>
              ✦ {armenian ? "AI զեկույց" : "AI report"}
            </button>
          )}
          <label className="medical-switch">
            <input type="checkbox" checked={overlaysVisible} onChange={(event) => setOverlaysVisible(event.target.checked)} />
            <span aria-hidden="true" />
            {armenian ? "AI շերտ" : "AI overlay"}
          </label>
          <div className="finding-filter-pills" aria-label="Finding review filters">
            {filters.map((option) => (
              <button className={filter === option.value ? "active" : ""} key={option.value} type="button" onClick={() => onFilterChange(option.value)}>
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="opg-cinematic-shell">
        {!xray && <div className="opg-placeholder">{armenian ? "Այս վերլուծության ռենտգենը հասանելի չէ։" : "The X-ray for this analysis is not available."}</div>}
        {xray && !displayable && <div className="opg-placeholder dicom-state"><strong>DICOM</strong><span>{xray.original_filename}</span></div>}
        {xray && displayable && !imageUrl && !imageError && <div className="opg-placeholder">{armenian ? "Բեռնվում է ռենտգենը…" : "Loading radiograph…"}</div>}
        {imageError && <div className="opg-placeholder error-panel">{imageError}</div>}

        {imageUrl && (
          <div className="opg-image-stage cinematic-stage finding-stage">
            <img
              src={imageUrl}
              alt="Original OPG for the selected DENTAI analysis"
              onLoad={(event) => {
                setImageSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight });
                setImageError("");
              }}
              onError={() => setImageError(armenian ? "Ռենտգենի պատկերը չհաջողվեց բեռնել։" : "The radiograph could not be loaded.")}
            />
            <div className="stage-vignette" aria-hidden="true" />

            {overlaysVisible && imageSize && (
              <svg className="opg-overlay medical-overlay finding-only-overlay" viewBox={`0 0 ${imageSize.width} ${imageSize.height}`} preserveAspectRatio="xMidYMid meet" aria-label="DENTAI clinical finding overlay">
                {projectedRegions.map((region) => {
                  const [x1, y1, x2, y2] = region.box;
                  const width = x2 - x1;
                  const height = y2 - y1;
                  const active = activeGroupKey === region.group.key;
                  const colors = regionColors(region.tone, region.confidence);
                  const confidenceLabel = `${Math.round(region.confidence * 100)}%`;
                  const label = region.group.toothCode ?? "?";
                  const pad = Math.max(2, imageSize.width / 700);
                  const fontSize = Math.max(13, imageSize.width / 105);
                  return (
                    <g
                      className={`clinical-finding-region ${region.tone === "RESTORATIVE" ? "restorative" : "pathology"}${active ? " active" : ""}`}
                      key={region.key}
                      role="button"
                      tabIndex={0}
                      aria-label={`${armenian ? "Ատամ" : "Tooth"} ${label}: ${region.primary ? humanizeFindingType(region.primary.finding_type) : "finding"}`}
                      onClick={() => onSelectedGroupChange(region.group.key)}
                      onKeyDown={(event) => selectFromKeyboard(event, region.group.key)}
                      onMouseEnter={() => setHoveredGroupKey(region.group.key)}
                      onMouseLeave={() => setHoveredGroupKey(null)}
                    >
                      {region.tone === "PATHOLOGY" && (
                        <rect
                          className="finding-confidence-pulse"
                          x={x1 - pad}
                          y={y1 - pad}
                          width={width + pad * 2}
                          height={height + pad * 2}
                          rx={Math.max(7, width * 0.12)}
                          fill="none"
                          stroke={colors.glow}
                          strokeWidth={Math.max(2, imageSize.width / 700)}
                          vectorEffect="non-scaling-stroke"
                          opacity={0.3 + region.confidence * 0.7}
                        />
                      )}
                      <rect
                        className="finding-region-box"
                        x={x1}
                        y={y1}
                        width={width}
                        height={height}
                        rx={Math.max(6, width * 0.1)}
                        fill={colors.fill}
                        stroke={colors.stroke}
                        strokeWidth={active ? 3 : 2}
                        vectorEffect="non-scaling-stroke"
                        style={{ filter: `drop-shadow(0 0 ${active ? 14 : 8}px ${colors.glow})` }}
                      />
                      <g className="finding-region-label" transform={`translate(${x1 + 5} ${Math.max(y1 + fontSize + 5, fontSize + 5)})`}>
                        <rect x="-3" y={-fontSize + 1} width={Math.max(48, fontSize * 4.1)} height={fontSize + 7} rx={(fontSize + 7) / 2} fill="rgba(7, 10, 22, 0.84)" stroke={colors.stroke} strokeWidth="1" vectorEffect="non-scaling-stroke" />
                        <circle cx={fontSize * 0.15} cy={-fontSize * 0.38} r={fontSize * 0.22} fill={colors.badge} />
                        <text x={fontSize * 0.55} y={-fontSize * 0.12} fontSize={fontSize * 0.78} fill="#fff" fontWeight="850">{label} · {confidenceLabel}</text>
                      </g>
                    </g>
                  );
                })}
              </svg>
            )}

            {clinicalSummary && reportOpen && (
              <aside className="opg-report-panel">
                <button type="button" onClick={() => setReportOpen(false)} aria-label={armenian ? "Փակել" : "Close"}>×</button>
                <span className="eyebrow">{armenian ? "AI կլինիկական զեկույց" : "AI clinical report"}</span>
                <h4>{clinicalSummary.doctor_summary}</h4>
                {clinicalSummary.important_changes[0] && <p><strong>{armenian ? "Հիմնական դիտարկում" : "Key observation"}</strong>{clinicalSummary.important_changes[0]}</p>}
                {clinicalSummary.monitoring_points[0] && <p><strong>{armenian ? "Հսկողություն" : "Monitoring"}</strong>{clinicalSummary.monitoring_points[0]}</p>}
                {clinicalSummary.questions_for_doctor[0] && <p><strong>{armenian ? "Բժշկի համար" : "For the clinician"}</strong>{clinicalSummary.questions_for_doctor[0]}</p>}
                <small>{armenian ? "AI-ի ամփոփումը չի փոխարինում բժշկի գնահատմանը։" : "AI summary does not replace clinician assessment."}</small>
              </aside>
            )}

            {canReview && pendingCount > 0 && (
              <div className="opg-review-dock">
                <span>{armenian ? "Վերանայում" : "Review"} {decidedCount}/{pendingCount}</span>
                {reviewError && <em>{reviewError}</em>}
                {reviewDone && <em className="success">{reviewDone}</em>}
                <button type="button" disabled={!canSubmitReview || reviewing} onClick={onSubmitReview}>
                  {reviewing ? (armenian ? "Պահպանվում է…" : "Saving…") : (armenian ? "Պահպանել" : "Save review")}
                </button>
              </div>
            )}

            <div className="opg-stage-guide finding-legend">
              <span><i className="legend-green" />{armenian ? "Բուժված / վերականգնված" : "Treated / restored"}</span>
              <span><i className="legend-red" />{armenian ? "Պաթոլոգիկ արդյունք" : "Pathological finding"}</span>
            </div>
          </div>
        )}

        <div className="opg-caption medical-caption">
          <span>{xray?.original_filename ?? (armenian ? "Ռենտգեն չկա" : "No X-ray available")}</span>
          <span>{projectedRegions.length} {armenian ? "կլինիկական շրջան" : "clinical regions"}</span>
        </div>
      </div>

      {selectedGroup && (
        <div className="finding-dialog-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.currentTarget === event.target) onSelectedGroupChange(null);
        }}>
          <section className="finding-dialog" role="dialog" aria-modal="true" aria-label={`${armenian ? "Ատամ" : "Tooth"} ${selectedGroup.toothCode ?? "?"}`} lang={armenian ? "hy" : "en"}>
            <button className="finding-dialog-close" type="button" onClick={() => onSelectedGroupChange(null)} aria-label={armenian ? "Փակել" : "Close"}>×</button>
            <div className={`finding-dialog-visual ${groupFindingTone(selectedGroup) === "RESTORATIVE" ? "restorative" : "pathology"}`}>
              {imageUrl && <img src={imageUrl} alt="Focused radiographic region" style={{ objectPosition: focusPosition }} />}
              <div className="finding-visual-shade" />
              <div className="finding-visual-target" aria-hidden="true"><i /><i /><span>{selectedGroup.toothCode ?? "?"}</span></div>
              <div className="finding-visual-label"><span>✦</span><strong>{armenian ? "DENTAI կլինիկական կենտրոնացում" : "DENTAI clinical focus"}</strong></div>
            </div>
            <div className="finding-dialog-content">
              <header className="finding-dialog-heading">
                <div>
                  <p className="eyebrow">{armenian ? "Ընտրված շրջան" : "Selected region"} · FDI {selectedGroup.toothCode ?? "?"}</p>
                  <h2>{selectedExplanation?.headline ?? humanizeFindingType(primaryFinding(selectedGroup)?.finding_type ?? "")}</h2>
                </div>
                <span className="finding-count-badge">{Math.round(groupFindingConfidence(selectedGroup) * 100)}%</span>
              </header>

              <div className="finding-chip-row premium-finding-chips">
                {selectedGroup.findings.map((finding) => <span key={finding.id}>{humanizeFindingType(finding.finding_type)}</span>)}
              </div>

              <div className="clinical-story-grid">
                <article className="clinical-story-card primary-story">
                  <span className="story-icon">◉</span>
                  <div><small>{armenian ? "Ինչ է նկատել համակարգը" : "What the system observed"}</small><p>{selectedExplanation?.clinical_explanation ?? selectedGroup.findings.map((finding) => finding.description).filter(Boolean).join(" ")}</p></div>
                </article>
                <article className="clinical-story-card">
                  <span className="story-icon">✓</span>
                  <div><small>{armenian ? "Բժշկի գնահատում" : "Clinician assessment"}</small><p>{selectedExplanation?.review_explanation ?? (armenian ? "Արդյունքը պետք է համադրել կլինիկական զննման հետ։" : "Correlate this result with the clinical examination.")}</p></div>
                </article>
              </div>

              <div className="finding-confidence-list">
                {selectedGroup.findings.map((finding) => (
                  <div key={finding.id}>
                    <span>{humanizeFindingType(finding.finding_type)}</span>
                    <strong>{typeof finding.confidence === "number" ? `${Math.round(finding.confidence * 100)}%` : "—"}</strong>
                    <small>{finding.review_status.replaceAll("_", " ")}</small>
                  </div>
                ))}
              </div>

              {canReview && selectedGroup.findings.some((finding) => finding.review_status === "PENDING") && (
                <section className="micro-review-card">
                  <div><strong>{armenian ? "Բժշկի որոշում" : "Clinician decision"}</strong><small>{armenian ? "Յուրաքանչյուր արդյունք հաստատեք կամ մերժեք։" : "Confirm or reject each finding."}</small></div>
                  <div className="micro-review-items">
                    {selectedGroup.findings.filter((finding) => finding.review_status === "PENDING").map((finding) => (
                      <div key={finding.id} className="micro-review-item">
                        <span>{humanizeFindingType(finding.finding_type)}</span>
                        <div className="decision-segmented" role="group" aria-label="Clinician decision">
                          <button className={decisions[finding.id] === "CONFIRMED" ? "selected confirm" : ""} type="button" onClick={() => onDecisionChange(finding.id, "CONFIRMED")}>{armenian ? "Հաստատել" : "Confirm"}</button>
                          <button className={decisions[finding.id] === "REJECTED" ? "selected reject" : ""} type="button" onClick={() => onDecisionChange(finding.id, "REJECTED")}>{armenian ? "Մերժել" : "Reject"}</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
