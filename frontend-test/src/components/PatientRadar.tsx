import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
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

interface RuntimeSourceState {
  state: string;
  collector: string | null;
  last_error_code: string | null;
  last_error: string | null;
  last_signal_count: number;
  last_new_signal_count: number;
  consecutive_failures: number;
  last_success_at: string | null;
  last_duration_ms: number | null;
  source_revision: string | null;
  claimed_by: string | null;
}

interface RadarRuntime {
  worker_expected: boolean;
  active_sources: number;
  due_sources: number;
  unhealthy_sources: number;
  action_required_sources: number;
  last_success_at: string | null;
  llm_semantic_refinement: boolean;
  collectors: Record<string, { ready?: boolean; mode?: string; detail?: string }>;
  sources: Record<string, RuntimeSourceState>;
}

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

const PLATFORMS = ["INSTAGRAM", "FACEBOOK", "TELEGRAM", "WEB"] as const;

function humanize(value: string | null | undefined): string {
  return value
    ? value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
    : "—";
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

function RuntimePill({ state }: { state: string }) {
  const normalized = state.toLowerCase().replaceAll("_", "-");
  return <span className={"radar-runtime-pill state-" + normalized}>{humanize(state)}</span>;
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

function ConnectionMatrix({ runtime }: { runtime: RadarRuntime | null }) {
  return (
    <div className="radar-collector-grid">
      {PLATFORMS.map((platform) => {
        const status = runtime?.collectors?.[platform];
        const ready = Boolean(status?.ready);
        return (
          <article key={platform} className={ready ? "ready" : "attention"}>
            <div className="collector-icon"><PlatformMark platform={platform} /></div>
            <div>
              <strong>{humanize(platform)}</strong>
              <span>{status?.detail ?? "Checking collector…"}</span>
            </div>
            <i aria-label={ready ? "Ready" : "Action required"}>{ready ? "●" : "○"}</i>
          </article>
        );
      })}
    </div>
  );
}

export function PatientRadar({ role }: { role: Role }) {
  const [dashboard, setDashboard] = useState<RadarDashboard>(EMPTY_DASHBOARD);
  const [runtime, setRuntime] = useState<RadarRuntime | null>(null);
  const [sources, setSources] = useState<RadarSource[]>([]);
  const [opportunities, setOpportunities] = useState<RadarOpportunity[]>([]);
  const [filters, setFilters] = useState<RadarOpportunityFilters>({ status: "NEW", minScore: 50 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RadarOpportunityDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [busySourceId, setBusySourceId] = useState<string | null>(null);
  const [showAddSource, setShowAddSource] = useState(false);
  const [sourceForm, setSourceForm] = useState({ platform: "WEB", name: "", sourceUrl: "" });

  const canManage = role === "DIRECTOR" || role === "MANAGER";
  const sourceHighlights = useMemo(
    () => [...sources].sort((a, b) => b.source_score - a.source_score),
    [sources]
  );

  async function refresh(signal?: AbortSignal) {
    const [summary, runtimeInfo, sourceItems, page] = await Promise.all([
      api.radarDashboard(signal),
      api.radarRuntime(signal),
      api.radarSources(signal),
      api.radarOpportunities(filters, signal)
    ]);
    setDashboard(summary);
    setRuntime(runtimeInfo as RadarRuntime);
    setSources(sourceItems);
    setOpportunities(page.items);
  }

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    refresh(controller.signal)
      .catch((reason) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) setError(errorMessage(reason));
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
        if (!(reason instanceof DOMException && reason.name === "AbortError")) setError(errorMessage(reason));
      })
      .finally(() => setDetailLoading(false));
    return () => controller.abort();
  }, [selectedId]);

  async function updateStatus(status: "NEW" | "REVIEWED" | "ARCHIVED") {
    if (!selectedId) return;
    setError("");
    try {
      await api.updateRadarOpportunity(selectedId, status);
      setSelectedId(null);
      setDetail(null);
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  async function runSource(sourceId: string) {
    setBusySourceId(sourceId);
    setError("");
    try {
      const result = await api.runRadarSource(sourceId);
      if (result.error_code) setError(result.error_code + ": " + (result.error || "Source needs attention."));
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusySourceId(null);
    }
  }

  async function toggleSource(source: RadarSource) {
    setBusySourceId(source.id);
    try {
      await api.updateRadarSource(source.id, { is_active: !source.is_active });
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusySourceId(null);
    }
  }

  async function addSource(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const sourceType = sourceForm.platform === "TELEGRAM" ? "CHANNEL" : sourceForm.platform === "WEB" ? "WEB_SOURCE" : "PAGE";
      const created = await api.createRadarSource({
        platform: sourceForm.platform,
        source_type: sourceType,
        name: sourceForm.name,
        source_url: sourceForm.sourceUrl,
        location_hint: "Armenia",
        armenia_relevance: 75,
        engagement_score: 50,
        dental_signal_probability: 50
      });
      setSourceForm({ platform: "WEB", name: "", sourceUrl: "" });
      setShowAddSource(false);
      await refresh();
      await runSource(created.id);
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  return (
    <div className="radar-workspace">
      <section className="radar-hero radar-hero-operational">
        <div>
          <p className="eyebrow">Armenia intent intelligence</p>
          <h1>Patient Radar</h1>
          <p>Continuous, read-only discovery of evidence-linked dental demand across authorized sources.</p>
        </div>
        <div className="radar-hero-actions">
          <div className={runtime?.unhealthy_sources || runtime?.action_required_sources ? "radar-live-badge warning" : "radar-live-badge"}>
            <i /> {runtime?.worker_expected ? "Monitoring active" : "Ready for sources"}
          </div>
          {canManage && <button type="button" className="button button-accent" onClick={() => setShowAddSource(true)}>+ Add source</button>}
        </div>
      </section>

      {error && <div className="error-panel" role="alert">{error}</div>}
      {loading && <div className="loading-bar" aria-label="Loading patient radar" />}

      <section className="radar-operations-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Operational engine</p>
            <h2>Collection & intelligence</h2>
          </div>
          <div className="radar-engine-summary">
            <span><b>{runtime?.active_sources ?? 0}</b> active</span>
            <span><b>{runtime?.due_sources ?? 0}</b> due</span>
            <span className={(runtime?.action_required_sources ?? 0) > 0 ? "attention" : ""}><b>{runtime?.action_required_sources ?? 0}</b> action required</span>
            <span><b>{runtime?.llm_semantic_refinement ? "AI" : "Rules"}</b> semantic mode</span>
          </div>
        </div>
        <ConnectionMatrix runtime={runtime} />
      </section>

      <section className="radar-metrics" aria-label="Patient Radar summary">
        <Metric label="Hot opportunities" value={dashboard.hot} accent="hot" />
        <Metric label="Warm opportunities" value={dashboard.warm} accent="warm" />
        <Metric label="Research signals" value={dashboard.research} />
        <Metric label="Sources monitored" value={dashboard.sources_monitored} />
        <Metric label="New signals · 24h" value={dashboard.new_signals_24h} />
      </section>

      <section className="radar-source-ops">
        <div className="section-heading">
          <div><p className="eyebrow">Adaptive monitoring</p><h2>Source operations</h2></div>
          <small>High-value sources are checked more frequently. New content temporarily increases cadence.</small>
        </div>
        <div className="radar-source-table">
          {sourceHighlights.map((source) => {
            const state = runtime?.sources?.[source.id];
            return (
              <article key={source.id}>
                <div className="source-main">
                  <PlatformMark platform={source.platform} />
                  <div>
                    <strong>{source.name}</strong>
                    <a href={source.source_url} target="_blank" rel="noreferrer">{source.handle || source.source_url}</a>
                  </div>
                </div>
                <div className="source-score"><small>Source score</small><strong>{source.source_score}</strong></div>
                <div className="source-cadence"><small>Cadence</small><strong>{source.priority}</strong><span>{source.monitoring_interval_minutes} min</span></div>
                <div className="source-runtime">
                  <RuntimePill state={state?.state || (source.is_active ? "IDLE" : "PAUSED")} />
                  <small>{state?.last_success_at ? "Last success " + dateTime(state.last_success_at) : "Not polled yet"}</small>
                  {state?.last_error_code && <em>{state.last_error_code}</em>}
                </div>
                {canManage && (
                  <div className="source-actions">
                    <button type="button" className="button button-secondary" disabled={busySourceId === source.id || !source.is_active} onClick={() => void runSource(source.id)}>
                      {busySourceId === source.id ? "Running…" : "Run now"}
                    </button>
                    <button type="button" className="radar-icon-button" disabled={busySourceId === source.id} onClick={() => void toggleSource(source)} title={source.is_active ? "Pause source" : "Resume source"}>
                      {source.is_active ? "Ⅱ" : "▶"}
                    </button>
                  </div>
                )}
              </article>
            );
          })}
          {!loading && sourceHighlights.length === 0 && (
            <div className="radar-empty compact">
              <span>⌁</span><h3>No sources yet</h3><p>Add a public web or Telegram source to start immediately. Instagram and Facebook use an authorized session collector.</p>
            </div>
          )}
        </div>
      </section>

      <section className="radar-control-bar">
        <div className="radar-filter-group">
          <label><span>Tier</span><select value={filters.tier ?? ""} onChange={(e) => setFilters((v) => ({ ...v, tier: e.target.value || undefined }))}><option value="">All ≥ score</option><option value="HOT">Hot</option><option value="WARM">Warm</option><option value="RESEARCH">Research</option></select></label>
          <label><span>Platform</span><select value={filters.platform ?? ""} onChange={(e) => setFilters((v) => ({ ...v, platform: e.target.value || undefined }))}><option value="">All platforms</option>{PLATFORMS.map((item) => <option value={item} key={item}>{humanize(item)}</option>)}</select></label>
          <label><span>Language</span><select value={filters.language ?? ""} onChange={(e) => setFilters((v) => ({ ...v, language: e.target.value || undefined }))}><option value="">All languages</option><option value="hy">Armenian</option><option value="ru">Russian</option><option value="en">English</option><option value="mixed">Mixed</option></select></label>
          <label><span>Treatment</span><select value={filters.treatment ?? ""} onChange={(e) => setFilters((v) => ({ ...v, treatment: e.target.value || undefined }))}><option value="">All dental needs</option>{TREATMENTS.map((item) => <option value={item} key={item}>{humanize(item)}</option>)}</select></label>
          <label className="radar-min-score"><span>Minimum score · {filters.minScore ?? 50}</span><input type="range" min="0" max="100" step="5" value={filters.minScore ?? 50} onChange={(e) => setFilters((v) => ({ ...v, minScore: Number(e.target.value) }))} /></label>
        </div>
      </section>

      <div className="radar-main-grid radar-main-grid-wide">
        <section className="radar-opportunity-panel">
          <div className="section-heading"><div><p className="eyebrow">Prioritized queue</p><h2>Patient opportunities</h2></div><span className="count-badge">{opportunities.length}</span></div>
          <div className="radar-opportunity-list">
            {opportunities.map((item) => {
              const trend = Number(item.evidence_summary?.score_trend ?? 0);
              return (
                <button type="button" className={item.id === selectedId ? "selected" : ""} key={item.id} onClick={() => setSelectedId(item.id)}>
                  <div className="radar-score-ring" style={{ "--score": item.opportunity_score } as React.CSSProperties}><strong>{item.opportunity_score}</strong><small>/100</small></div>
                  <div className="radar-opportunity-copy">
                    <div className="radar-row-meta"><PlatformMark platform={item.platform} /><span className={tierClass(item.tier)}>{item.tier}</span><span>{item.language.toUpperCase()}</span><span>{dateTime(item.last_seen_at)}</span></div>
                    <h3>{item.author_display || "Public-source opportunity"}</h3>
                    <p>{item.explanation}</p>
                    <div className="radar-tags">{item.treatment && <span>{humanize(item.treatment)}</span>}<span>{humanize(item.intent)}</span>{item.location && <span>{item.location}</span>}<span>{item.signal_count} signals</span>{trend !== 0 && <span className={trend > 0 ? "trend-up" : "trend-down"}>{trend > 0 ? "↑" : "↓"} {Math.abs(trend)} intent</span>}</div>
                  </div>
                  <span className="radar-open-arrow">›</span>
                </button>
              );
            })}
            {!loading && opportunities.length === 0 && <div className="radar-empty"><span>⌁</span><h3>No matching opportunities</h3><p>New evidence-linked signals will appear when monitored sources match the selected filters.</p></div>}
          </div>
        </section>

        <aside className="radar-insight-panel">
          <p className="eyebrow">How Radar works</p>
          <h3>Fast filter → semantic AI → deterministic score</h3>
          <p>Collected text is deduplicated, interpreted with context, and ranked using the versioned DENTAI opportunity policy. The score is a prioritization signal, not a conversion probability.</p>
          <div className="radar-pipeline">
            <span>Collect</span><i>→</i><span>Deduplicate</span><i>→</i><span>Understand</span><i>→</i><span>Score</span><i>→</i><span>Review</span>
          </div>
          <div className="radar-safety-note"><strong>Read-only intelligence</strong><p>No likes, follows, comments, replies, DMs, sharing, posting, CAPTCHA bypass, or automatic outreach.</p></div>
        </aside>
      </div>

      {showAddSource && (
        <div className="radar-detail-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setShowAddSource(false); }}>
          <form className="radar-source-dialog" onSubmit={(e) => void addSource(e)}>
            <header><div><p className="eyebrow">Monitoring source</p><h2>Add source</h2></div><button type="button" onClick={() => setShowAddSource(false)} aria-label="Close">×</button></header>
            <label><span>Platform</span><select value={sourceForm.platform} onChange={(e) => setSourceForm((v) => ({ ...v, platform: e.target.value }))}>{PLATFORMS.map((item) => <option value={item} key={item}>{humanize(item)}</option>)}</select></label>
            <label><span>Display name</span><input required value={sourceForm.name} onChange={(e) => setSourceForm((v) => ({ ...v, name: e.target.value }))} placeholder="Armenian beauty creator" /></label>
            <label><span>Source URL</span><input required type="url" value={sourceForm.sourceUrl} onChange={(e) => setSourceForm((v) => ({ ...v, sourceUrl: e.target.value }))} placeholder="https://…" /></label>
            <div className="radar-dialog-note">Web and public Telegram sources can run immediately. Instagram/Facebook and protected sources require the authorized session collector; DENTAI never stores platform passwords in the clinical database.</div>
            <footer><button type="button" className="button button-secondary" onClick={() => setShowAddSource(false)}>Cancel</button><button className="button button-accent" type="submit">Add & run</button></footer>
          </form>
        </div>
      )}

      {selectedId && (
        <div className="radar-detail-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelectedId(null); }}>
          <section className="radar-detail-sheet" role="dialog" aria-modal="true" aria-label="Patient opportunity evidence">
            <header><div><p className="eyebrow">Evidence-linked opportunity</p><h2>{detail?.opportunity.author_display || "Patient opportunity"}</h2></div><button type="button" onClick={() => setSelectedId(null)} aria-label="Close">×</button></header>
            {detailLoading || !detail ? <div className="page-loader">Loading opportunity evidence…</div> : (
              <>
                <div className="radar-detail-summary">
                  <div className="radar-score-ring large" style={{ "--score": detail.opportunity.opportunity_score } as React.CSSProperties}><strong>{detail.opportunity.opportunity_score}</strong><small>/100</small></div>
                  <div><div className="radar-row-meta"><PlatformMark platform={detail.opportunity.platform} /><span className={tierClass(detail.opportunity.tier)}>{detail.opportunity.tier}</span><span>{humanize(detail.opportunity.urgency)} urgency</span></div><h3>{detail.opportunity.explanation}</h3><p>Observed from {dateTime(detail.opportunity.first_seen_at)} to {dateTime(detail.opportunity.last_seen_at)} across {detail.opportunity.signal_count} evidence signals.</p></div>
                </div>
                <div className="radar-detail-facts"><span><small>Intent</small><strong>{humanize(detail.opportunity.intent)}</strong></span><span><small>Treatment</small><strong>{humanize(detail.opportunity.treatment)}</strong></span><span><small>Location</small><strong>{detail.opportunity.location || "Not explicit"}</strong></span><span><small>Language</small><strong>{detail.opportunity.language.toUpperCase()}</strong></span></div>
                <div className="radar-score-disclaimer">Opportunity score ranks observable intent evidence using the configured DENTAI Radar policy. It is not a calibrated probability that a person will become a clinic patient.</div>
                <div className="section-heading compact-heading"><div><p className="eyebrow">Intent timeline</p><h3>Verifiable evidence</h3></div></div>
                <SignalTimeline detail={detail} />
                {canManage && <footer className="radar-detail-actions"><button className="button button-secondary" type="button" onClick={() => void updateStatus("ARCHIVED")}>Archive</button><button className="button button-accent" type="button" onClick={() => void updateStatus("REVIEWED")}>Mark reviewed</button></footer>}
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
