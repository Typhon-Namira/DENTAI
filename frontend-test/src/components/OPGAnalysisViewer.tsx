import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
import { api, errorMessage } from "../api/client";
import type { XRay } from "../api/types";
import {
  findingModelScore,
  formatModelScore,
  isStandardPanoramicSideConsistent,
  normalizeBoundingBoxToImage,
  observedImageSide,
  type FindingFilter,
  type ToothFindingGroup
} from "../utils/opg";
import { StatusBadge } from "./StatusBadge";

const DISPLAYABLE_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const FILTERS: Array<{ value: FindingFilter; label: string }> = [
  { value: "ALL", label: "Show all findings" },
  { value: "PENDING", label: "Pending only" },
  { value: "CONFIRMED", label: "Confirmed" },
  { value: "REJECTED", label: "Rejected" }
];

interface OPGAnalysisViewerProps {
  xray: XRay | null;
  groups: ToothFindingGroup[];
  filter: FindingFilter;
  selectedGroupKey: string | null;
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
  filter,
  selectedGroupKey,
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

  function selectFromKeyboard(event: KeyboardEvent<SVGGElement>, key: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelectedGroupChange(key);
    }
  }

  return (
    <section className="opg-workspace card">
      <div className="opg-toolbar">
        <div>
          <p className="eyebrow">Interactive OPG</p>
          <h3>Original radiograph with DENTAI overlays</h3>
        </div>
        <div className="viewer-controls" aria-label="Viewer controls">
          <label className="overlay-toggle">
            <input
              type="checkbox"
              checked={overlaysVisible}
              onChange={(event) => setOverlaysVisible(event.target.checked)}
            />
            Show AI overlays
          </label>
          <button
            className="button button-quiet"
            type="button"
            disabled={!selectedGroupKey}
            onClick={() => onSelectedGroupChange(null)}
          >
            Reset selected tooth
          </button>
        </div>
      </div>

      <div className="finding-filters" aria-label="Finding review filters">
        {FILTERS.map((option) => (
          <button
            className={filter === option.value ? "active" : ""}
            key={option.value}
            type="button"
            onClick={() => onFilterChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="opg-layout">
        <div className="opg-viewer-shell">
          {!xray && (
            <div className="opg-placeholder">
              The X-ray referenced by this analysis is not present in the patient profile.
            </div>
          )}

          {xray && !displayable && (
            <div className="opg-placeholder dicom-state">
              <strong>DICOM study</strong>
              <span>{xray.original_filename}</span>
              <p>Interactive browser rendering is reserved for a future DICOM viewer.</p>
            </div>
          )}

          {xray && displayable && !imageUrl && !imageError && (
            <div className="opg-placeholder">Authorizing temporary X-ray access…</div>
          )}

          {imageError && <div className="opg-placeholder error-panel">{imageError}</div>}

          {imageUrl && (
            <div className="opg-image-stage">
              <img
                src={imageUrl}
                alt="Original OPG for the selected DENTAI analysis"
                onLoad={(event) => {
                  setImageSize({
                    width: event.currentTarget.naturalWidth,
                    height: event.currentTarget.naturalHeight
                  });
                  setImageError("");
                }}
                onError={() => setImageError("The temporary X-ray image URL could not be loaded.")}
              />
              {overlaysVisible && imageSize && (
                <svg
                  className="opg-overlay"
                  viewBox={"0 0 " + imageSize.width + " " + imageSize.height}
                  preserveAspectRatio="xMidYMid meet"
                  aria-label="DENTAI tooth detection overlay"
                >
                  {projectedGroups.map((group) => {
                    if (!group.projectedBoundingBox || !group.toothCode) return null;
                    const [x1, y1, x2, y2] = group.projectedBoundingBox;
                    const active = activeGroupKey === group.key;
                    const strokeWidth = Math.max(2, imageSize.width / 900);
                    const fontSize = Math.max(18, imageSize.width / 85);
                    return (
                      <g
                        className={"tooth-overlay" + (active ? " active" : "")}
                        key={group.key}
                        role="button"
                        tabIndex={0}
                        aria-label={"Select tooth " + group.toothCode}
                        onClick={() => onSelectedGroupChange(group.key)}
                        onKeyDown={(event) => selectFromKeyboard(event, group.key)}
                        onMouseEnter={() => {
                          setHoveredGroupKey(group.key);
                          onSelectedGroupChange(group.key);
                        }}
                        onMouseLeave={() => setHoveredGroupKey(null)}
                      >
                        <rect
                          x={x1}
                          y={y1}
                          width={x2 - x1}
                          height={y2 - y1}
                          rx={strokeWidth * 2}
                          vectorEffect="non-scaling-stroke"
                        />
                        <text
                          x={x1 + strokeWidth * 3}
                          y={Math.max(y1 + fontSize, fontSize)}
                          fontSize={fontSize}
                        >
                          {group.toothCode}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}
            </div>
          )}
          <div className="opg-caption">
            <span>{xray?.original_filename ?? "No X-ray available"}</span>
            <span>
              {projectedGroups.filter((group) => group.projectedBoundingBox).length} tooth regions shown
            </span>
          </div>
          {debugOpg && imageSize && (
            <div className="opg-debug-panel">
              <strong>OPG coordinate debug</strong>
              <span>Image: {imageSize.width} × {imageSize.height}</span>
              {projectedGroups.map((group) => (
                <code key={group.key}>
                  {group.toothCode ?? group.key} · source={group.boundingBoxSource ?? "NONE"}
                  {" · raw="}{JSON.stringify(group.boundingBox)}
                  {" · projected="}{JSON.stringify(group.projectedBoundingBox)}
                  {group.toothCode && group.projectedBoundingBox
                    ? " · side=" + observedImageSide(
                        group.projectedBoundingBox,
                        imageSize.width
                      ) + " · standard=" + String(isStandardPanoramicSideConsistent(
                        group.toothCode,
                        group.projectedBoundingBox,
                        imageSize.width
                      ))
                    : ""}
                </code>
              ))}
            </div>
          )}
        </div>

        <aside className="tooth-inspector" aria-live="polite">
          {!selectedGroup ? (
            <div className="inspector-empty">
              <span>FDI</span>
              <h3>Select a tooth region</h3>
              <p>Choose an overlay or finding group to inspect its model evidence.</p>
            </div>
          ) : (
            <>
              <div className="selected-tooth-heading">
                <div>
                  <p className="eyebrow">Selected tooth</p>
                  <h2>{selectedGroup.toothCode ?? "Unassigned finding"}</h2>
                </div>
                <span className="count-badge">{selectedGroup.findings.length}</span>
              </div>
              <div className="finding-chip-row">
                {selectedGroup.findings.map((finding) => (
                  <span key={finding.id}>{finding.finding_type.replaceAll("_", " ")}</span>
                ))}
              </div>
              <p className="score-helper">
                Model score is supporting AI evidence and is not an independent diagnostic probability.
              </p>
              <div className="tooth-evidence-list">
                {selectedGroup.findings.map((finding) => {
                  const provenance = finding.provenance;
                  const score = findingModelScore(finding);
                  return (
                    <article key={finding.id}>
                      <div className="evidence-heading">
                        <strong>{finding.finding_type.replaceAll("_", " ")}</strong>
                        <StatusBadge value={finding.review_status} />
                      </div>
                      <p>{finding.description}</p>
                      <dl>
                        <div>
                          <dt>Model score</dt>
                          <dd title={score === null ? undefined : "Exact value: " + String(score)}>
                            {formatModelScore(score)}
                          </dd>
                        </div>
                        <div><dt>Review status</dt><dd>{finding.review_status}</dd></div>
                        <div>
                          <dt>Review required</dt>
                          <dd>{detailValue(provenance?.review_required)}</dd>
                        </div>
                        <div><dt>Uncertainty</dt><dd>{detailValue(provenance?.uncertainty)}</dd></div>
                        <div>
                          <dt>Uncertainty reason</dt>
                          <dd>{detailValue(provenance?.uncertainty_reason)}</dd>
                        </div>
                        <div>
                          <dt>Review reasons</dt>
                          <dd>{provenance?.review_reasons?.length
                            ? provenance.review_reasons.join(", ")
                            : "Not provided"}</dd>
                        </div>
                        <div><dt>Source model</dt><dd>{detailValue(provenance?.source_model)}</dd></div>
                        <div><dt>Model version</dt><dd>{detailValue(provenance?.model_version)}</dd></div>
                      </dl>
                    </article>
                  );
                })}
              </div>
            </>
          )}
        </aside>
      </div>

      {projectedGroups.some((group) => !group.projectedBoundingBox) && (
        <p className="overlay-note">
          Findings without a valid bounding box remain available in the finding panel.
        </p>
      )}
    </section>
  );
}
