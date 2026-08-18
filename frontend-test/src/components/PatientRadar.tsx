import { useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../api/client";
import type {
  RadarDashboard,
  RadarOpportunity,
  RadarOpportunityDetail,
  RadarOpportunityFilters,
  RadarSource,
  Role
} from "../api/types";

const EMPTY_DASHBOARD: RadarDashboard = {
  hot: 0,
  warm: 0,
  research: 0,
  ignored: 0,
  sources_monitored: 0,
  new_signals_24h: 0,
  new_opportunities_24h: 0,
  generated_at: ""
};

const TREATMENTS = [
  "IMPLANT",
  "VENEER",
  "CROWN",
  "ROOT_CANAL",
  "FILLING",
  "BRACES",
  "WHITENING",
  "CLEANING",
  "WISDOM_TOOTH",
  "COSMETIC_DENTISTRY"
];

function humanize(value: string | null | undefined): string {
  return value ? value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) : "—";
}

function dateTime(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function tierClass(tier: string): string {
  return "radar-tier radar-tier-" + tier.toLowerCase();
}

function PlatformMark({ platform }: { platform: string }) {
  const label = platform === "INSTAGRAM" ? "IG" : platform === "FACEBOOK" ? "FB" : platform === "TELEGRAM" ? "TG" : "WEB";
  return <span className={"radar-platform radar-platform-" + platform.toLowerCase()}>{label}</span>;
}

function Metric({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <article className={"radar-metric " + (accent ? "radar-metric-" + accent : "")}>
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <i aria-hidden="true" />
    </article>
  );
}

function SignalTimeline({ detail }: { detail: RadarOpportunityDetail }) {
  return (
    <div className="radar-signal-timeline">
      {detail.signals.map((signal, index) => (
        <article key={signal.id}>
          <span className="radar-timeline-node">{index + 1}</span>
          <div>
            <div className="radar-signal-meta">
              <PlatformMark platform={signal.platform} />
              <span>{humanize(signal.signal_type)}</span>
              <span>{dateTime(signal.published_at || signal.observed_at)}</span>
              <span className={tierClass(signal.tier)}>{signal.opportunity_score}</span>
            </div>
            {signal.context_text && <p className="radar-context">Context: {signal.context_text}</p>}
            <blockquote>{signal.text}</blockquote>
            <div className="radar-tags">
              <span>{humanize(signal.intent)}</span>
              {signal.treatment && <span>{humanize(signal.treatment)}</span>}
              {signal.location && <span>{signal.location}</span>}
              <span>{humanize(signal.urgency_label)} urgency</span>
            </div>
            <a href={signal.source_url} target="_blank" rel="noreferrer">Open original evidence ↗</a>
          </div>
        </article>
      ))}
    </div>
  );
}

export function PatientRadar({ role }: { role: Role }) {
  const [dashboard, setDashboard] = useState<RadarDashboard>(EMPTY_DASHBOARD);
  const [sources, setSources] = useState<RadarSource[]>([]);
  const [opportunities, setOpportunities] = useState<RadarOpportunity[]>([]);
  const [filters, setFilters] = useState<RadarOpportunityFilters>({ status: "NEW", minScore: 50 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RadarOpportunityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");

  const canManage = role === "DIRECTOR" || role === "MANAGER";
  const sourceHighlights = useMemo(
    () => [...sources].sort((a, b) => b.source_score - a.source_score).slice(0, 6),
    [sources]
  );

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([
      api.radarDashboard(controller.signal),
      api.radarSources(controller.signal),
      api.radarOpportunities(filters, controller.signal)
    ])
      .then(([summary, sourceItems, page]) => {
        setDashboard(summary);
        setSources(sourceItems);
        setOpportunities(page.items);
        if (selectedId && !page.items.some((item) => item.id === selectedId)) {
          setSelectedId(null);
          setDetail(null);
        }
      })
      .catch((reason) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(errorMessage(reason));
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [filters.tier, filters.platform, filters.language, filters.location, filters.treatment, filters.status, filters.minScore]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    const controller = new AbortController();
    setDetailLoading(true);
    api.radarOpportunity(selectedId, controller.signal)
      .then(setDetail)
      .catch((reason) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(errorMessage(reason));
        }
      })
      .finally(() => setDetailLoading(false));
    return () => controller.abort();
  }, [selectedId]);

  async function updateStatus(status: "NEW" | "REVIEWED" | "ARCHIVED") {
    if (!selectedId) return;
    setError("");
    try {
      const updated = await api.updateRadarOpportunity(selectedId, status);
      setDetail((current) => current ? { ...current, opportunity: updated } : current);
      setOpportunities((current) => current.filter((item) => item.id !== selectedId));
      setSelectedId(null);
      setDetail(null);
      const nextDashboard = await api.radarDashboard();
      setDashboard(nextDashboard);
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  return (
    <div className="radar-workspace">
      <section className="radar-hero">
        <div>
          <p className="eyebrow">Armenia intent intelligence</p>
          <h1>Patient Radar</h1>
          <p>Read-only discovery of evidence-linked dental intent across authorized online sources.</p>
        </div>
        <div className="radar-live-badge"><i /> Intelligence live</div>
      </section>

      {error && <div className="error-panel" role="alert">{error}</div>}
      {loading && <div className="loading-bar" aria-label="Loading patient radar" />}

      <section className="radar-metrics" aria-label="Patient Radar summary">
        <Metric label="Hot opportunities" value={dashboard.hot} accent="hot" />
        <Metric label="Warm opportunities" value={dashboard.warm} accent="warm" />
        <Metric label="Research signals" value={dashboard.research} />
        <Metric label="Sources monitored" value={dashboard.sources_monitored} />
        <Metric label="New signals · 24h" value={dashboard.new_signals_24h} />
      </section>

      <section className="radar-control-bar">
        <div className="radar-filter-group">
          <label>
            <span>Tier</span>
            <select value={filters.tier ?? ""} onChange={(event) => setFilters((value) => ({ ...value, tier: event.target.value || undefined }))}>
              <option value="">All ≥ score</option>
              <option value="HOT">Hot</option>
              <option value="WARM">Warm</option>
              <option value="RESEARCH">Research</option>
            </select>
          </label>
          <label>
            <span>Platform</span>
            <select value={filters.platform ?? ""} onChange={(event) => setFilters((value) => ({ ...value, platform: event.target.value || undefined }))}>
              <option value="">All platforms</option>
              <option value="INSTAGRAM">Instagram</option>
              <option value="FACEBOOK">Facebook</option>
              <option value="TELEGRAM">Telegram</option>
              <option value="WEB">Public web</option>
            </select>
          </label>
          <label>
            <span>Language</span>
            <select value={filters.language ?? ""} onChange={(event) => setFilters((value) => ({ ...value, language: event.target.value || undefined }))}>
              <option value="">All languages</option>
              <option value="hy">Armenian</option>
              <option value="ru">Russian</option>
              <option value="en">English</option>
              <option value="mixed">Mixed</option>
            </select>
          </label>
          <label>
            <span>Treatment</span>
            <select value={filters.treatment ?? ""} onChange={(event) => setFilters((value) => ({ ...value, treatment: event.target.value || undefined }))}>
              <option value="">All dental needs</option>
              {TREATMENTS.map((item) => <option value={item} key={item}>{humanize(item)}</option>)}
            </select>
          </label>
          <label className="radar-min-score">
            <span>Minimum score · {filters.minScore ?? 50}</span>
            <input type="range" min="0" max="100" step="5" value={filters.minScore ?? 50} onChange={(event) => setFilters((value) => ({ ...value, minScore: Number(event.target.value) }))} />
          </label>
        </div>
      </section>

      <div className="radar-main-grid">
        <section className="radar-opportunity-panel">
          <div className="section-heading">
            <div><p className="eyebrow">Prioritized queue</p><h2>Patient opportunities</h2></div>
            <span className="count-badge">{opportunities.length}</span>
          </div>
          <div className="radar-opportunity-list">
            {opportunities.map((item) => (
              <button
                type="button"
                className={item.id === selectedId ? "selected" : ""}
                key={item.id}
                onClick={() => setSelectedId(item.id)}
              >
                <div className="radar-score-ring" style={{ "--score": item.opportunity_score } as React.CSSProperties}>
                  <strong>{item.opportunity_score}</strong><small>/100</small>
                </div>
                <div className="radar-opportunity-copy">
                  <div className="radar-row-meta">
                    <PlatformMark platform={item.platform} />
                    <span className={tierClass(item.tier)}>{item.tier}</span>
                    <span>{item.language.toUpperCase()}</span>
                    <span>{dateTime(item.last_seen_at)}</span>
                  </div>
                  <h3>{item.author_display || "Public-source opportunity"}</h3>
                  <p>{item.explanation}</p>
                  <div className="radar-tags">
                    {item.treatment && <span>{humanize(item.treatment)}</span>}
                    <span>{humanize(item.intent)}</span>
                    {item.location && <span>{item.location}</span>}
                    <span>{item.signal_count} signal{item.signal_count === 1 ? "" : "s"}</span>
                  </div>
                </div>
                <span className="radar-open-arrow">›</span>
              </button>
            ))}
            {!loading && opportunities.length === 0 && (
              <div className="radar-empty">
                <span>⌁</span>
                <h3>No matching opportunities</h3>
                <p>New evidence-linked signals will appear here when they meet the selected filters.</p>
              </div>
            )}
          </div>
        </section>

        <aside className="radar-source-panel">
          <div className="section-heading compact-heading">
            <div><p className="eyebrow">Source graph</p><h3>Highest-value sources</h3></div>
          </div>
          <div className="radar-source-list">
            {sourceHighlights.map((source) => (
              <article key={source.id}>
                <PlatformMark platform={source.platform} />
                <div><strong>{source.name}</strong><small>{source.priority} · every {source.monitoring_interval_minutes} min</small></div>
                <span>{source.source_score}</span>
              </article>
            ))}
            {!loading && sourceHighlights.length === 0 && <div className="empty-inline">No sources registered yet.</div>}
          </div>
          <div className="radar-safety-note">
            <strong>Read-only intelligence</strong>
            <p>No likes, follows, comments, replies, DMs, sharing, posting, CAPTCHA bypass, or automated outreach.</p>
          </div>
        </aside>
      </div>

      {selectedId && (
        <div className="radar-detail-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setSelectedId(null);
        }}>
          <section className="radar-detail-sheet" role="dialog" aria-modal="true" aria-label="Patient opportunity evidence">
            <header>
              <div><p className="eyebrow">Evidence-linked opportunity</p><h2>{detail?.opportunity.author_display || "Patient opportunity"}</h2></div>
              <button type="button" onClick={() => setSelectedId(null)} aria-label="Close">×</button>
            </header>
            {detailLoading || !detail ? <div className="page-loader">Loading opportunity evidence…</div> : (
              <>
                <div className="radar-detail-summary">
                  <div className="radar-score-ring large" style={{ "--score": detail.opportunity.opportunity_score } as React.CSSProperties}>
                    <strong>{detail.opportunity.opportunity_score}</strong><small>/100</small>
                  </div>
                  <div>
                    <div className="radar-row-meta">
                      <PlatformMark platform={detail.opportunity.platform} />
                      <span className={tierClass(detail.opportunity.tier)}>{detail.opportunity.tier}</span>
                      <span>{humanize(detail.opportunity.urgency)} urgency</span>
                    </div>
                    <h3>{detail.opportunity.explanation}</h3>
                    <p>Observed from {dateTime(detail.opportunity.first_seen_at)} to {dateTime(detail.opportunity.last_seen_at)} across {detail.opportunity.signal_count} evidence signal{detail.opportunity.signal_count === 1 ? "" : "s"}.</p>
                  </div>
                </div>
                <div className="radar-detail-facts">
                  <span><small>Intent</small><strong>{humanize(detail.opportunity.intent)}</strong></span>
                  <span><small>Treatment</small><strong>{humanize(detail.opportunity.treatment)}</strong></span>
                  <span><small>Location</small><strong>{detail.opportunity.location || "Not explicit"}</strong></span>
                  <span><small>Language</small><strong>{detail.opportunity.language.toUpperCase()}</strong></span>
                </div>
                <div className="radar-score-disclaimer">
                  Opportunity score ranks observable intent evidence using the configured DENTAI Radar policy. It is not a calibrated probability that a person will become a clinic patient.
                </div>
                <div className="section-heading compact-heading"><div><p className="eyebrow">Intent timeline</p><h3>Verifiable evidence</h3></div></div>
                <SignalTimeline detail={detail} />
                {canManage && (
                  <footer className="radar-detail-actions">
                    <button className="button button-secondary" type="button" onClick={() => void updateStatus("ARCHIVED")}>Archive</button>
                    <button className="button button-accent" type="button" onClick={() => void updateStatus("REVIEWED")}>Mark reviewed</button>
                  </footer>
                )}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
