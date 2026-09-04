import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { GroqClinicalSummary, ReviewDecision, XRay } from "../api/types";
import {
  boundingBoxForFindingGroup,
  normalizeBoundingBoxToImage,
  type BoundingBox,
  type FindingFilter,
  type ToothFindingGroup,
  type VisionToothDetection
} from "../utils/opg";
import {
  groupFindingConfidence,
  groupFindingTone,
  primaryFinding
} from "../utils/findingVisuals";
import {
  explanationForGroup,
  localizedFindingType
} from "../utils/clinicalSummary";

const DISPLAYABLE_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

interface OPGAnalysisViewerProps {
  xray: XRay | null;
  groups: ToothFindingGroup[];
  detections: VisionToothDetection[];
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

interface LabelRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

function rectanglesOverlap(left: LabelRect, right: LabelRect, gap = 5): boolean {
  return !(
    left.x + left.width + gap <= right.x ||
    right.x + right.width + gap <= left.x ||
    left.y + left.height + gap <= right.y ||
    right.y + right.height + gap <= left.y
  );
}

function placeToothLabels(
  regions: Array<{ key: string; box: BoundingBox }>,
  imageWidth: number,
  imageHeight: number
): Map<string, LabelRect> {
  const fontSize = Math.max(13, imageWidth / 110);
  const labelWidth = Math.max(34, fontSize * 2.15);
  const labelHeight = fontSize + 9;
  const placed: LabelRect[] = [];
  const result = new Map<string, LabelRect>();

  const ordered = [...regions].sort((left, right) => {
    const ly = (left.box[1] + left.box[3]) / 2;
    const ry = (right.box[1] + right.box[3]) / 2;
    return Math.abs(ly - ry) > imageHeight * 0.04
      ? ly - ry
      : ((left.box[0] + left.box[2]) / 2) - ((right.box[0] + right.box[2]) / 2);
  });

  for (const region of ordered) {
    const [x1, y1, x2] = region.box;
    const centerX = (x1 + x2) / 2;
    const candidates: LabelRect[] = [];
    for (let lane = 0; lane < 5; lane += 1) {
      const verticalOffset = 8 + lane * (labelHeight + 5);
      candidates.push({
        x: Math.max(4, Math.min(imageWidth - labelWidth - 4, centerX - labelWidth / 2)),
        y: Math.max(4, y1 - labelHeight - verticalOffset),
        width: labelWidth,
        height: labelHeight
      });
    }
    for (let lane = 0; lane < 3; lane += 1) {
      const horizontalOffset = lane * (labelWidth * 0.45);
      candidates.push({
        x: Math.max(4, Math.min(imageWidth - labelWidth - 4, centerX - labelWidth / 2 + horizontalOffset)),
        y: Math.min(imageHeight - labelHeight - 4, y1 + 6),
        width: labelWidth,
        height: labelHeight
      });
    }

    const chosen = candidates.find((candidate) =>
      !placed.some((existing) => rectanglesOverlap(candidate, existing))
    ) ?? candidates[0];
    placed.push(chosen);
    result.set(region.key, chosen);
  }
  return result;
}

function containsArmenian(value: string): boolean {
  return /[\u0530-\u058F]/.test(value);
}

function textMatchesLanguage(value: string | null | undefined, armenian: boolean): boolean {
  if (!value) return false;
  return armenian ? containsArmenian(value) : !containsArmenian(value);
}

export function OPGAnalysisViewer({
  xray,
  groups,
  detections,
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
  const language = armenian ? "hy" : "en";

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
      const exactBox = boundingBoxForFindingGroup(
        group,
        detections,
        imageSize.width,
        imageSize.height
      );
      if (!exactBox) return [];
      const projected = normalizeBoundingBoxToImage(exactBox, imageSize.width, imageSize.height);
      if (!projected) return [];
      return [{
        key: group.key,
        group,
        box: projected,
        tone: groupFindingTone(group),
        confidence: groupFindingConfidence(group),
        primary: primaryFinding(group)
      }];
    });
  }, [groups, detections, imageSize]);

  const labelLayouts = useMemo(
    () => imageSize ? placeToothLabels(projectedRegions, imageSize.width, imageSize.height) : new Map<string, LabelRect>(),
    [projectedRegions, imageSize]
  );

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
        fill: "rgba(34, 197, 94, 0.105)",
        stroke: "rgba(74, 222, 128, 0.94)",
        glow: "rgba(34, 197, 94, 0.46)",
        confidence: "rgba(220, 252, 231, 0.28)"
      };
    }
    const strength = Math.max(0.2, Math.min(1, confidence));
    return {
      fill: `rgba(239, 68, 68, ${0.045 + strength * 0.17})`,
      stroke: `rgba(248, 80, 80, ${0.58 + strength * 0.40})`,
      glow: `rgba(239, 68, 68, ${0.12 + strength * 0.46})`,
      confidence: `rgba(255, 230, 230, ${0.12 + strength * 0.20})`
    };
  }

  const modalHeadline = selectedGroup
    ? localizedFindingType(primaryFinding(selectedGroup)?.finding_type ?? "", language)
    : "";
  const modalTypes = selectedGroup
    ? selectedGroup.findings.map((finding) => localizedFindingType(finding.finding_type, language))
    : [];
  const localizedClinicalExplanation = selectedGroup
    ? (
        textMatchesLanguage(selectedExplanation?.clinical_explanation, armenian)
          ? selectedExplanation!.clinical_explanation
          : armenian
            ? `DENTAI-ն ${selectedGroup.toothCode ?? "?"} ատամի շրջանում նշել է ${modalTypes.join(", ")}։ Այս արդյունքը պետք է համադրել կլինիկական զննման և բժշկի գնահատման հետ։`
            : `DENTAI identified ${modalTypes.join(", ")} in the region of tooth ${selectedGroup.toothCode ?? "?"}. Correlate this finding with the clinical examination and clinician assessment.`
      )
    : "";
  const localizedReviewExplanation = selectedGroup
    ? (
        textMatchesLanguage(selectedExplanation?.review_explanation, armenian)
          ? selectedExplanation!.review_explanation
          : armenian
            ? "Այս արդյունքը օժանդակ AI դիտարկում է և վերջնական ախտորոշում չէ մինչև բժշկի վերանայումը։"
            : "This is an AI-assisted observation and is not a final diagnosis until reviewed by the clinician."
      )
    : "";

  return (
    <section className="opg-workspace medical-opg card findings-only-opg">
      <div className="medical-opg-header">
        <div>
          <p className="eyebrow">{armenian ? "Ինտերակտիվ OPG" : "Interactive OPG"}</p>
          <h3>{armenian ? "DENTAI-ի կլինիկական արդյունքները ռենտգենի վրա" : "DENTAI clinical findings on the radiograph"}</h3>
          <p>{armenian ? "Կանաչ՝ բուժված կամ վերականգնված ատամներ · կարմիր՝ պաթոլոգիկ արդյունքներ · կարմիրի ուժգնությունը արտացոլում է մոդելի վստահությունը։" : "Green = treated or restored teeth · red = pathological findings · red intensity reflects model confidence."}</p>
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
              alt={armenian ? "Ընտրված DENTAI վերլուծության OPG" : "OPG for the selected DENTAI analysis"}
              onLoad={(event) => {
                setImageSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight });
                setImageError("");
              }}
              onError={() => setImageError(armenian ? "Ռենտգենի պատկերը չհաջողվեց բեռնել։" : "The radiograph could not be loaded.")}
            />
            <div className="stage-vignette" aria-hidden="true" />

            {overlaysVisible && imageSize && (
              <svg className="opg-overlay medical-overlay finding-only-overlay" viewBox={`0 0 ${imageSize.width} ${imageSize.height}`} preserveAspectRatio="xMidYMid meet" aria-label={armenian ? "DENTAI կլինիկական արդյունքների շերտ" : "DENTAI clinical finding overlay"}>
                {projectedRegions.map((region) => {
                  const [x1, y1, x2, y2] = region.box;
                  const width = x2 - x1;
                  const height = y2 - y1;
                  const active = activeGroupKey === region.group.key;
                  const colors = regionColors(region.tone, region.confidence);
                  const confidenceLabel = `${Math.round(region.confidence * 100)}%`;
                  const label = region.group.toothCode ?? "?";
                  const labelRect = labelLayouts.get(region.key);
                  const fontSize = Math.max(13, imageSize.width / 110);
                  const confidenceSize = Math.max(16, Math.min(width * 0.32, imageSize.width / 52));
                  const connectorX = labelRect ? labelRect.x + labelRect.width / 2 : (x1 + x2) / 2;
                  const connectorY = labelRect ? labelRect.y + labelRect.height : y1;
                  const boxCenterX = (x1 + x2) / 2;
                  return (
                    <g
                      className={`clinical-finding-region ${region.tone === "RESTORATIVE" ? "restorative" : "pathology"}${active ? " active" : ""}`}
                      key={region.key}
                      role="button"
                      tabIndex={0}
                      aria-label={`${armenian ? "Ատամ" : "Tooth"} ${label}: ${region.primary ? localizedFindingType(region.primary.finding_type, language) : (armenian ? "արդյունք" : "finding")}`}
                      onClick={() => onSelectedGroupChange(region.group.key)}
                      onKeyDown={(event) => selectFromKeyboard(event, region.group.key)}
                      onMouseEnter={() => setHoveredGroupKey(region.group.key)}
                      onMouseLeave={() => setHoveredGroupKey(null)}
                    >
                      {region.tone === "PATHOLOGY" && (
                        <rect
                          className="finding-confidence-pulse"
                          x={x1 - 2}
                          y={y1 - 2}
                          width={width + 4}
                          height={height + 4}
                          rx={Math.max(5, width * 0.08)}
                          fill="none"
                          stroke={colors.glow}
                          strokeWidth="1.4"
                          vectorEffect="non-scaling-stroke"
                          opacity={0.18 + region.confidence * 0.48}
                        />
                      )}
                      <rect
                        className="finding-region-box"
                        x={x1}
                        y={y1}
                        width={width}
                        height={height}
                        rx={Math.max(5, width * 0.08)}
                        fill={colors.fill}
                        stroke={colors.stroke}
                        strokeWidth={active ? 2.6 : 1.7}
                        vectorEffect="non-scaling-stroke"
                        style={{ filter: `drop-shadow(0 0 ${active ? 11 : 5}px ${colors.glow})` }}
                      />
                      <text
                        className="finding-confidence-watermark"
                        x={(x1 + x2) / 2}
                        y={(y1 + y2) / 2 + confidenceSize * 0.34}
                        textAnchor="middle"
                        fontSize={confidenceSize}
                        fill={colors.confidence}
                        fontWeight="800"
                      >{confidenceLabel}</text>
                      {labelRect && (
                        <g className="finding-tooth-label" pointerEvents="none">
                          <line x1={connectorX} y1={connectorY} x2={boxCenterX} y2={Math.max(y1 - 2, connectorY)} stroke={colors.stroke} strokeWidth="1" vectorEffect="non-scaling-stroke" opacity="0.72" />
                          <rect x={labelRect.x} y={labelRect.y} width={labelRect.width} height={labelRect.height} rx={labelRect.height / 2} fill="rgba(8, 13, 25, 0.91)" stroke={colors.stroke} strokeWidth="1" vectorEffect="non-scaling-stroke" />
                          <text x={labelRect.x + labelRect.width / 2} y={labelRect.y + labelRect.height / 2 + fontSize * 0.28} textAnchor="middle" fontSize={fontSize * 0.82} fill="#fff" fontWeight="850">{label}</text>
                        </g>
                      )}
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
          <section className="finding-dialog" role="dialog" aria-modal="true" aria-label={`${armenian ? "Ատամ" : "Tooth"} ${selectedGroup.toothCode ?? "?"}`} lang={language}>
            <button className="finding-dialog-close" type="button" onClick={() => onSelectedGroupChange(null)} aria-label={armenian ? "Փակել" : "Close"}>×</button>
            <div className={`finding-dialog-visual ${groupFindingTone(selectedGroup) === "RESTORATIVE" ? "restorative" : "pathology"}`}>
              {imageUrl && <img src={imageUrl} alt={armenian ? "Ռենտգենի ընտրված շրջան" : "Selected radiographic region"} style={{ objectPosition: focusPosition }} />}
              <div className="finding-visual-shade" />
              <div className="finding-visual-target" aria-hidden="true"><i /><i /><span>{selectedGroup.toothCode ?? "?"}</span></div>
              <div className="finding-visual-label"><span>✦</span><strong>{armenian ? "DENTAI կլինիկական կենտրոնացում" : "DENTAI clinical focus"}</strong></div>
            </div>
            <div className="finding-dialog-content">
              <header className="finding-dialog-heading">
                <div>
                  <p className="eyebrow">{armenian ? "Ընտրված ատամ" : "Selected tooth"} · FDI {selectedGroup.toothCode ?? "?"}</p>
                  <h2>{modalHeadline}</h2>
                </div>
                <span className="finding-count-badge">{Math.round(groupFindingConfidence(selectedGroup) * 100)}%</span>
              </header>

              <div className="finding-chip-row premium-finding-chips">
                {selectedGroup.findings.map((finding) => <span key={finding.id}>{localizedFindingType(finding.finding_type, language)}</span>)}
              </div>

              <div className="clinical-story-grid">
                <article className="clinical-story-card primary-story">
                  <span className="story-icon">◉</span>
                  <div><small>{armenian ? "Ինչ է նկատել համակարգը" : "What the system observed"}</small><p>{localizedClinicalExplanation}</p></div>
                </article>
                <article className="clinical-story-card">
                  <span className="story-icon">✓</span>
                  <div><small>{armenian ? "Բժշկի գնահատում" : "Clinician assessment"}</small><p>{localizedReviewExplanation}</p></div>
                </article>
              </div>

              <div className="finding-confidence-list">
                {selectedGroup.findings.map((finding) => (
                  <div key={finding.id}>
                    <span>{localizedFindingType(finding.finding_type, language)}</span>
                    <strong>{typeof finding.confidence === "number" ? `${Math.round(finding.confidence * 100)}%` : "—"}</strong>
                    <small>{armenian
                      ? finding.review_status === "CONFIRMED" ? "Հաստատված" : finding.review_status === "REJECTED" ? "Մերժված" : "Սպասող"
                      : finding.review_status.replaceAll("_", " ")}</small>
                  </div>
                ))}
              </div>

              {canReview && selectedGroup.findings.some((finding) => finding.review_status === "PENDING") && (
                <section className="micro-review-card">
                  <div><strong>{armenian ? "Բժշկի որոշում" : "Clinician decision"}</strong><small>{armenian ? "Յուրաքանչյուր արդյունք հաստատեք կամ մերժեք։" : "Confirm or reject each finding."}</small></div>
                  <div className="micro-review-items">
                    {selectedGroup.findings.filter((finding) => finding.review_status === "PENDING").map((finding) => (
                      <div key={finding.id} className="micro-review-item">
                        <span>{localizedFindingType(finding.finding_type, language)}</span>
                        <div className="decision-segmented" role="group" aria-label={armenian ? "Բժշկի որոշում" : "Clinician decision"}>
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
