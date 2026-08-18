import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { GroqClinicalSummary, ReviewDecision, XRay } from "../api/types";
import {
  findingModelScore,
  formatModelScore,
  isStandardPanoramicSideConsistent,
  normalizeBoundingBoxToImage,
  observedImageSide,
  type FindingFilter,
  type ToothFindingGroup
} from "../utils/opg";
import {
  explanationForGroup,
  humanizeFindingType,
  technicalDetailsForFinding
} from "../utils/clinicalSummary";

const DISPLAYABLE_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const FILTERS: Array<{ value: FindingFilter; label: string }> = [
  { value: "ALL", label: "All" },
  { value: "PENDING", label: "Pending" },
  { value: "CONFIRMED", label: "Confirmed" },
  { value: "REJECTED", label: "Rejected" }
];

interface OPGAnalysisViewerProps {
  xray: XRay | null;
  groups: ToothFindingGroup[];
  clinicalSummary: GroqClinicalSummary | null;
  filter: FindingFilter;
  selectedGroupKey: string | null;
  canReview: boolean;
  decisions: Record<string, ReviewDecision | "">;
  onDecisionChange: (findingId: string, decision: ReviewDecision | "") => void;
  onFilterChange: (filter: FindingFilter) => void;
  onSelectedGroupChange: (key: string | null) => void;
}

interface ImageSize {
  width: number;
  height: number;
}

function detailValue(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Not provided";
  return String(value);
}

export function OPGAnalysisViewer({
  xray,
  groups,
  clinicalSummary,
  filter,
  selectedGroupKey,
  canReview,
  decisions,
  onDecisionChange,
  onFilterChange,
  onSelectedGroupChange
}: OPGAnalysisViewerProps) {
  const [imageUrl, setImageUrl] = useState("");
  const [imageSize, setImageSize] = useState<ImageSize | null>(null);
  const [imageError, setImageError] = useState("");
  const [overlaysVisible, setOverlaysVisible] = useState(true);
  const [hoveredGroupKey, setHoveredGroupKey] = useState<string | null>(null);

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
  const debugOpg = new URLSearchParams(window.location.search).get("debugOpg") === "1";
  const projectedGroups = useMemo(
    () => groups.map((group) => ({
      ...group,
      projectedBoundingBox:
        group.boundingBox && imageSize
          ? normalizeBoundingBoxToImage(group.boundingBox, imageSize.width, imageSize.height)
          : null
    })),
    [groups, imageSize]
  );
  const selectedProjected = useMemo(
    () => projectedGroups.find((group) => group.key === selectedGroupKey) ?? null,
    [projectedGroups, selectedGroupKey]
  );
  const focusPosition = useMemo(() => {
    if (!selectedProjected?.projectedBoundingBox || !imageSize) return "50% 50%";
    const [x1, y1, x2, y2] = selectedProjected.projectedBoundingBox;
    const x = (((x1 + x2) / 2) / imageSize.width) * 100;
    const y = (((y1 + y2) / 2) / imageSize.height) * 100;
    return `${x}% ${y}%`;
  }, [selectedProjected, imageSize]);

  useEffect(() => {
    let active = true;
    setImageUrl("");
    setImageSize(null);
    setImageError("");

    if (!xray || !DISPLAYABLE_IMAGE_TYPES.has(xray.mime_type)) {
      return () => {
        active = false;
      };
    }

    api.xrayDownload(xray.id)
      .then((download) => {
        if (active) setImageUrl(download.url);
      })
      .catch((reason) => {
        if (active) setImageError(errorMessage(reason));
      });

    return () => {
      active = false;
    };
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

  return (
    <section className="opg-workspace medical-opg card">
      <div className="medical-opg-header">
        <div>
          <p className="eyebrow">Interactive OPG</p>
          <h3>AI findings on the original radiograph</h3>
          <p>Tap a luminous region to open the clinical explanation.</p>
        </div>
        <div className="medical-viewer-actions">
          <label className="medical-switch">
            <input type="checkbox" checked={overlaysVisible} onChange={(event) => setOverlaysVisible(event.target.checked)} />
            <span aria-hidden="true" />
            AI overlay
          </label>
          <div className="finding-filter-pills" aria-label="Finding review filters">
            {FILTERS.map((option) => (
              <button className={filter === option.value ? "active" : ""} key={option.value} type="button" onClick={() => onFilterChange(option.value)}>
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="opg-cinematic-shell">
        {!xray && <div className="opg-placeholder">The X-ray referenced by this analysis is not present in the patient profile.</div>}
        {xray && !displayable && (
          <div className="opg-placeholder dicom-state"><strong>DICOM study</strong><span>{xray.original_filename}</span><p>Interactive browser rendering is reserved for a future DICOM viewer.</p></div>
        )}
        {xray && displayable && !imageUrl && !imageError && <div className="opg-placeholder">Authorizing temporary X-ray access…</div>}
        {imageError && <div className="opg-placeholder error-panel">{imageError}</div>}

        {imageUrl && (
          <div className="opg-image-stage cinematic-stage">
            <img
              src={imageUrl}
              alt="Original OPG for the selected DENTAI analysis"
              onLoad={(event) => {
                setImageSize({ width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight });
                setImageError("");
              }}
              onError={() => setImageError("The temporary X-ray image URL could not be loaded.")}
            />
            <div className="stage-vignette" aria-hidden="true" />
            {overlaysVisible && imageSize && (
              <svg className="opg-overlay medical-overlay" viewBox={`0 0 ${imageSize.width} ${imageSize.height}`} preserveAspectRatio="xMidYMid meet" aria-label="DENTAI tooth detection overlay">
                <defs>
                  <filter id="dentaiGlow" x="-80%" y="-80%" width="260%" height="260%">
                    <feGaussianBlur stdDeviation="8" result="blur" />
                    <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>
                {projectedGroups.map((group) => {
                  if (!group.projectedBoundingBox || !group.toothCode) return null;
                  const [x1, y1, x2, y2] = group.projectedBoundingBox;
                  const cx = (x1 + x2) / 2;
                  const cy = (y1 + y2) / 2;
                  const rx = Math.max((x2 - x1) * 0.62, imageSize.width / 90);
                  const ry = Math.max((y2 - y1) * 0.62, imageSize.height / 45);
                  const active = activeGroupKey === group.key;
                  const nodeRadius = Math.max(5, imageSize.width / 320);
                  const fontSize = Math.max(16, imageSize.width / 95);
                  return (
                    <g
                      className={`medical-finding-hotspot${active ? " active" : ""}`}
                      key={group.key}
                      role="button"
                      tabIndex={0}
                      aria-label={`Open tooth ${group.toothCode} finding`}
                      onClick={() => onSelectedGroupChange(group.key)}
                      onKeyDown={(event) => selectFromKeyboard(event, group.key)}
                      onMouseEnter={() => setHoveredGroupKey(group.key)}
                      onMouseLeave={() => setHoveredGroupKey(null)}
                    >
                      <ellipse className="hotspot-aura hotspot-aura-outer" cx={cx} cy={cy} rx={rx * 1.16} ry={ry * 1.16} filter="url(#dentaiGlow)" />
                      <ellipse className="hotspot-aura hotspot-aura-inner" cx={cx} cy={cy} rx={rx} ry={ry} />
                      <circle className="hotspot-node" cx={cx + rx * 0.68} cy={cy - ry * 0.68} r={nodeRadius} />
                      <text className="hotspot-label" x={cx + rx * 0.68 + nodeRadius * 1.7} y={cy - ry * 0.68 + fontSize * 0.34} fontSize={fontSize}>{group.toothCode}</text>
                    </g>
                  );
                })}
              </svg>
            )}
            <div className="opg-stage-guide"><span className="guide-pulse" />Click a highlighted tooth for the clinical view</div>
          </div>
        )}

        <div className="opg-caption medical-caption">
          <span>{xray?.original_filename ?? "No X-ray available"}</span>
          <span>{projectedGroups.filter((group) => group.projectedBoundingBox && group.toothCode).length} interactive regions</span>
        </div>
      </div>

      {debugOpg && imageSize && (
        <details className="opg-debug-panel"><summary>OPG coordinate debug</summary><span>Image: {imageSize.width} × {imageSize.height}</span>{projectedGroups.map((group) => (
          <code key={group.key}>{group.toothCode ?? group.key} · source={group.boundingBoxSource ?? "NONE"}{" · canonical="}{group.geometryAmbiguous ? "AMBIGUOUS_DUPLICATE_FDI" : "UNAMBIGUOUS"}{" · raw="}{JSON.stringify(group.boundingBox)}{" · projected="}{JSON.stringify(group.projectedBoundingBox)}{group.toothCode && group.projectedBoundingBox ? ` · side=${observedImageSide(group.projectedBoundingBox, imageSize.width)} · standard=${String(isStandardPanoramicSideConsistent(group.toothCode, group.projectedBoundingBox, imageSize.width))}` : ""}</code>
        ))}</details>
      )}

      {selectedGroup && (
        <div className="finding-dialog-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.currentTarget === event.target) onSelectedGroupChange(null);
        }}>
          <section className="finding-dialog" role="dialog" aria-modal="true" aria-label={`Tooth ${selectedGroup.toothCode} AI finding`} lang="hy">
            <button className="finding-dialog-close" type="button" onClick={() => onSelectedGroupChange(null)} aria-label="Close">×</button>

            <div className="finding-dialog-visual">
              {imageUrl && <img src={imageUrl} alt="Focused radiographic region" style={{ objectPosition: focusPosition }} />}
              <div className="finding-visual-shade" />
              <div className="finding-visual-target" aria-hidden="true"><i /><i /><span>{selectedGroup.toothCode}</span></div>
              <div className="finding-visual-label"><span>✦</span><strong>DENTAI clinical focus</strong></div>
            </div>

            <div className="finding-dialog-content">
              <header className="finding-dialog-heading">
                <div>
                  <p className="eyebrow">Ընտրված ատամ · FDI {selectedGroup.toothCode}</p>
                  <h2>{selectedExplanation?.headline ?? humanizeFindingType(selectedGroup.findings[0]?.finding_type ?? "")}</h2>
                </div>
                <span className="finding-count-badge">{selectedGroup.findings.length} դիտարկում</span>
              </header>

              <div className="finding-chip-row premium-finding-chips">
                {selectedGroup.findings.map((finding) => <span key={finding.id}>{humanizeFindingType(finding.finding_type)}</span>)}
              </div>

              <div className="clinical-story-grid">
                <article className="clinical-story-card primary-story">
                  <span className="story-icon">◉</span>
                  <div><small>Ինչ է նկատել համակարգը</small><p>{selectedExplanation?.clinical_explanation ?? `DENTAI-ն այս ատամի շրջանում նշել է ${selectedGroup.findings.map((finding) => humanizeFindingType(finding.finding_type)).join(", ")}։ Արդյունքը պետք է համադրել կլինիկական զննման հետ։`}</p></div>
                </article>
                <article className="clinical-story-card">
                  <span className="story-icon">✓</span>
                  <div><small>Բժշկի գնահատում</small><p>{selectedExplanation?.review_explanation ?? "Այս դիտարկումը նախատեսված է բժշկի վերանայման համար և ինքնուրույն վերջնական ախտորոշում չէ։"}</p></div>
                </article>
                {clinicalSummary?.monitoring_points[0] && (
                  <article className="clinical-story-card">
                    <span className="story-icon">⌁</span>
                    <div><small>Հսկողության կետ</small><p>{clinicalSummary.monitoring_points[0]}</p></div>
                  </article>
                )}
              </div>

              {canReview && selectedGroup.findings.some((finding) => finding.review_status === "PENDING") && (
                <section className="micro-review-card">
                  <div><strong>Բժշկի որոշում</strong><small>Փոքր, հստակ հաստատում յուրաքանչյուր արդյունքի համար</small></div>
                  <div className="micro-review-items">
                    {selectedGroup.findings.filter((finding) => finding.review_status === "PENDING").map((finding) => (
                      <div key={finding.id} className="micro-review-item">
                        <span>{humanizeFindingType(finding.finding_type)}</span>
                        <div className="decision-segmented" role="group" aria-label="Clinician decision">
                          <button className={decisions[finding.id] === "CONFIRMED" ? "selected confirm" : ""} type="button" onClick={() => onDecisionChange(finding.id, "CONFIRMED")}>Հաստատել</button>
                          <button className={decisions[finding.id] === "REJECTED" ? "selected reject" : ""} type="button" onClick={() => onDecisionChange(finding.id, "REJECTED")}>Մերժել</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <details className="technical-details premium-technical-details">
                <summary>Տեխնիկական տվյալներ</summary>
                <div className="technical-finding-stack">
                  {selectedGroup.findings.map((finding) => {
                    const score = findingModelScore(finding);
                    const technical = technicalDetailsForFinding(finding);
                    return (
                      <article key={finding.id}>
                        <h4>{humanizeFindingType(finding.finding_type)}</h4>
                        <dl>
                          <div><dt>Model score</dt><dd>{formatModelScore(score)}</dd></div>
                          <div><dt>Review status</dt><dd>{technical.review_status}</dd></div>
                          <div><dt>Review required</dt><dd>{detailValue(technical.review_required)}</dd></div>
                          <div><dt>Uncertainty</dt><dd>{detailValue(technical.uncertainty)}</dd></div>
                          <div><dt>Source model</dt><dd>{detailValue(technical.source_model)}</dd></div>
                          <div><dt>Model version</dt><dd>{detailValue(technical.model_version)}</dd></div>
                          <div><dt>Bounding box</dt><dd>{technical.bounding_box ? JSON.stringify(technical.bounding_box) : "Not provided"}</dd></div>
                        </dl>
                      </article>
                    );
                  })}
                </div>
              </details>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
