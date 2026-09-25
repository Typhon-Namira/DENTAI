import {
  Activity,
  Archive,
  BarChart3,
  Building2,
  Check,
  CircleDollarSign,
  Clock3,
  CreditCard,
  Database,
  FileImage,
  Gift,
  HeartPulse,
  KeyRound,
  LockKeyhole,
  Mail,
  MessageCircle,
  Pencil,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Trash2,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { API_BASE_URL } from "../api/client";
import "./platform-admin-control-center.css";

const ADMIN_SESSION_KEY = "teta2-platform-admin-session";

type ClinicStats = {
  patients: number;
  opgs: number;
  ai_analyses: number;
  followups_total: number;
  followups_completed: number;
  followups_pending: number;
  care_items_total: number;
  care_items_completed: number;
  care_items_pending: number;
  ai_conversations: number;
  conversation_messages: number;
  database_status: string;
};

type Clinic = {
  id: string;
  slug: string;
  name: string;
  registry_active: boolean;
  subscription_plan: string;
  subscription_state: string;
  subscription_source: string;
  category: "FREE" | "PAID" | "GIFT" | "LEGACY";
  operational_state: string;
  subscription_starts_at?: string | null;
  subscription_expires_at?: string | null;
  days_remaining?: number | null;
  free_trial_started_at?: string | null;
  upgrade_requested_at?: string | null;
  gift_granted_at?: string | null;
  gift_note?: string | null;
  created_at: string;
  updated_at: string;
  stats: ClinicStats;
};

type Payment = {
  id: string;
  clinic_id?: string | null;
  clinic_name: string;
  market?: string | null;
  amount?: number | null;
  currency?: string | null;
  accounted: boolean;
  reference?: string | null;
  proof_note?: string | null;
  verified_at: string;
  created_at: string;
};

type TrafficPage = {
  path: string;
  visits_total: number;
  visits_24h: number;
  visits_30d: number;
  unique_30d: number;
};

type AuditRow = {
  id: string;
  action: string;
  target_type: string;
  target_id?: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

type Dashboard = {
  generated_at: string;
  clinics: Clinic[];
  summary: Record<string, number>;
  payments: {
    items: Payment[];
    verified_count: number;
    accounted_count: number;
    unpriced_legacy_count: number;
    revenue_by_currency: Record<string, number>;
  };
  traffic: {
    pages: TrafficPage[];
    totals: Record<string, number>;
  };
  recent_audit: AuditRow[];
};

type PlatformOverview = {
  health: {
    api: string;
    control_database: string;
    smtp_configured: boolean;
    tenant_auto_provisioning_configured: boolean;
    ai_provider: string;
    groq_configured: boolean;
    whatsapp_configured: boolean;
    radar_enabled: boolean;
    storage_provider: string;
  };
  metrics: Record<string, number>;
  request_statuses: Record<string, number>;
  top_routes: Array<[string, number]>;
  recent_emails: Array<{
    id: string;
    kind: string;
    recipient: string;
    subject: string;
    status: string;
    error?: string | null;
    created_at: string;
  }>;
};

type AccessRequest = {
  id: string;
  clinic_name: string;
  country: string;
  city: string;
  address?: string | null;
  website?: string | null;
  contact_name: string;
  contact_role: string;
  email: string;
  phone: string;
  dentists_count: number;
  branches_count: number;
  notes?: string | null;
  status: string;
  admin_note?: string | null;
  payment_reference?: string | null;
  payment_proof_note?: string | null;
  payment_amount?: number | null;
  payment_currency?: string | null;
  payment_instructions_sent_at?: string | null;
  payment_verified_at?: string | null;
  activated_clinic_id?: string | null;
  created_at: string;
  updated_at?: string;
};

type PlatformSettings = {
  plan_name: string;
  subscription_days: number;
  price_amount: number;
  price_currency: string;
  payment_recipient: string;
  payment_card: string;
  payment_bank_details: string;
  payment_email_subject: string;
  payment_email_intro: string;
  activation_email_subject: string;
  activation_email_intro: string;
};

type AdminTab =
  | "overview"
  | "free"
  | "paid"
  | "gifts"
  | "clinics"
  | "payments"
  | "requests"
  | "traffic"
  | "health"
  | "audit"
  | "settings";

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

async function requestJson<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body?.error?.message || body?.detail || "Request failed");
  }
  return body as T;
}

function number(value: number | undefined) {
  return Number(value || 0).toLocaleString("en-US");
}

function date(value: string | null | undefined) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "—"
    : new Intl.DateTimeFormat("en-US", { year: "numeric", month: "short", day: "2-digit" }).format(parsed);
}

function dateTime(value: string | null | undefined) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "—"
    : new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(parsed);
}

function money(value: number | null | undefined, currency: string | null | undefined) {
  if (value == null || !currency) return "Not recorded";
  return `${value.toLocaleString("en-US")} ${currency}`;
}

function label(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function metricCards(summary: Record<string, number>) {
  return [
    ["Clinics", summary.clinics_total, Building2],
    ["Patients", summary.patients, UsersRound],
    ["OPGs", summary.opgs, FileImage],
    ["AI analyses", summary.ai_analyses, Activity],
    ["AI conversations", summary.ai_conversations, MessageCircle],
    ["Follow-ups completed", summary.followups_completed, Check],
    ["Follow-ups pending", summary.followups_pending, Clock3],
    ["Verified payments", summary.payments_verified, CircleDollarSign],
  ] as const;
}

function StatusPill({ value }: { value: string }) {
  const key = value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  return <span className={`pa3-status pa3-status-${key}`}>{label(value)}</span>;
}

export function PlatformAdminControlCenter() {
  const [route, setRoute] = useState(window.location.pathname);
  const active = route === "/platform-admin";
  const [token, setToken] = useState(() => sessionStorage.getItem(ADMIN_SESSION_KEY) || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [platformOverview, setPlatformOverview] = useState<PlatformOverview | null>(null);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [tab, setTab] = useState<AdminTab>("overview");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [selectedClinic, setSelectedClinic] = useState<Clinic | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<AccessRequest | null>(null);
  const [editClinic, setEditClinic] = useState(false);
  const [giftClinic, setGiftClinic] = useState(false);
  const [archiveClinic, setArchiveClinic] = useState(false);
  const [renewClinic, setRenewClinic] = useState(false);

  useEffect(() => {
    const onRoute = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", onRoute);
    return () => window.removeEventListener("popstate", onRoute);
  }, []);

  useEffect(() => {
    if (!active) return;
    const previousLang = document.documentElement.lang;
    document.documentElement.lang = "en";
    document.body.classList.add("pa3-active");
    return () => {
      document.body.classList.remove("pa3-active");
      document.documentElement.lang = previousLang;
    };
  }, [active]);

  const load = useCallback(async (authToken: string) => {
    const [nextDashboard, nextOverview, nextRequests, nextSettings] = await Promise.all([
      requestJson<Dashboard>("/api/v1/platform/admin-control/dashboard", authToken),
      requestJson<PlatformOverview>("/api/v1/platform/admin/overview", authToken),
      requestJson<AccessRequest[]>("/api/v1/platform/admin/access-requests", authToken),
      requestJson<PlatformSettings>("/api/v1/platform/admin/settings", authToken),
    ]);
    setDashboard(nextDashboard);
    setPlatformOverview(nextOverview);
    setRequests(nextRequests);
    setSettings(nextSettings);
    setSelectedClinic((current) => current ? nextDashboard.clinics.find((clinic) => clinic.id === current.id) ?? null : null);
    setSelectedRequest((current) => current ? nextRequests.find((request) => request.id === current.id) ?? null : null);
    setAuthenticated(true);
    setError("");
  }, []);

  useEffect(() => {
    if (!active || !token || authenticated) return;
    void load(token).catch(() => {
      sessionStorage.removeItem(ADMIN_SESSION_KEY);
      setToken("");
      setAuthenticated(false);
    });
  }, [active, authenticated, load, token]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setLoginBusy(true);
    setError("");
    try {
      const session = await requestJson<{ access_token: string }>("/api/v1/platform/admin/login", undefined, {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      sessionStorage.setItem(ADMIN_SESSION_KEY, session.access_token);
      setToken(session.access_token);
      setPassword("");
      await load(session.access_token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Administrator authentication failed");
    } finally {
      setLoginBusy(false);
    }
  }

  function logout() {
    sessionStorage.removeItem(ADMIN_SESSION_KEY);
    setToken("");
    setAuthenticated(false);
    setDashboard(null);
    setPlatformOverview(null);
    setRequests([]);
    setSettings(null);
  }

  async function mutate<T>(path: string, init: RequestInit) {
    setBusy(path);
    setError("");
    try {
      const result = await requestJson<T>(path, token, init);
      await load(token);
      return result;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Administrative action failed");
      throw reason;
    } finally {
      setBusy("");
    }
  }

  const clinics = dashboard?.clinics ?? [];
  const filteredClinics = useMemo(() => {
    const query = search.trim().toLowerCase();
    return clinics.filter((clinic) => {
      if (tab === "free" && clinic.category !== "FREE") return false;
      if (tab === "paid" && clinic.category !== "PAID") return false;
      if (tab === "gifts" && clinic.category !== "GIFT") return false;
      if (!query) return true;
      return `${clinic.name} ${clinic.slug} ${clinic.subscription_plan} ${clinic.operational_state}`
        .toLowerCase()
        .includes(query);
    });
  }, [clinics, search, tab]);

  if (!active) return null;

  if (!authenticated) {
    return (
      <main className="pa3-root pa3-login-root">
        <section className="pa3-login-card">
          <div className="pa3-classified"><LockKeyhole /> INTERNAL · RESTRICTED</div>
          <div className="pa3-wordmark">Teta2 <span>CONTROL</span></div>
          <h1>Platform Operations Center</h1>
          <p>Authorized personnel only. Administrative access is logged and controls live clinic subscriptions, payments and platform operations.</p>
          <form onSubmit={login}>
            <label>Administrator email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required autoFocus /></label>
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
            {error && <div className="pa3-error">{error}</div>}
            <button className="pa3-primary" disabled={loginBusy}>{loginBusy ? "Authenticating…" : "Enter secure control center"}</button>
          </form>
          <div className="pa3-login-foot"><ShieldCheck /> Session-scoped administrator access</div>
        </section>
      </main>
    );
  }

  const nav: Array<[AdminTab, string, typeof Activity, number | undefined]> = [
    ["overview", "Overview", Activity, undefined],
    ["free", "Free clinics", Clock3, dashboard?.summary.clinics_free],
    ["paid", "Paid clinics", CreditCard, dashboard?.summary.clinics_paid],
    ["gifts", "Gifted clinics", Gift, dashboard?.summary.clinics_gifted],
    ["clinics", "All clinics", Building2, dashboard?.summary.clinics_total],
    ["payments", "Payments & revenue", CircleDollarSign, dashboard?.payments.verified_count],
    ["requests", "Access requests", Mail, dashboard?.summary.pending_requests],
    ["traffic", "Traffic", BarChart3, undefined],
    ["health", "System health", HeartPulse, platformOverview?.metrics.emails_failed_100],
    ["audit", "Audit log", ShieldCheck, undefined],
    ["settings", "Platform settings", KeyRound, undefined],
  ];

  return (
    <main className="pa3-root">
      <aside className="pa3-sidebar">
        <div className="pa3-side-brand"><strong>Teta2</strong><span>CONTROL</span></div>
        <div className="pa3-security-label"><LockKeyhole /> INTERNAL · RESTRICTED</div>
        <nav>
          {nav.map(([id, title, Icon, count]) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => { setTab(id); setSelectedClinic(null); setSelectedRequest(null); }}>
              <Icon /><span>{title}</span>{count != null ? <b>{count}</b> : null}
            </button>
          ))}
        </nav>
        <div className="pa3-side-foot">
          <span><Database /> Live control plane</span>
          <button onClick={logout}><X /> Sign out</button>
        </div>
      </aside>

      <section className="pa3-main">
        <header className="pa3-topbar">
          <div><small>PLATFORM OPERATIONS / INTERNAL</small><h1>{nav.find(([id]) => id === tab)?.[1]}</h1></div>
          <div className="pa3-top-actions">
            <span className="pa3-generated">Snapshot {dateTime(dashboard?.generated_at)}</span>
            <button title="Refresh live data" onClick={() => void load(token)}><RefreshCw /></button>
          </div>
        </header>
        {error && <div className="pa3-error pa3-page-error">{error}<button onClick={() => setError("")}><X /></button></div>}

        {tab === "overview" && <Overview dashboard={dashboard} onOpenClinic={setSelectedClinic} />}
        {["free", "paid", "gifts", "clinics"].includes(tab) && (
          <ClinicDirectory title={nav.find(([id]) => id === tab)?.[1] || "Clinics"} rows={filteredClinics} search={search} setSearch={setSearch} onOpen={setSelectedClinic} />
        )}
        {tab === "payments" && <Payments dashboard={dashboard} />}
        {tab === "requests" && <Requests rows={requests} selected={selectedRequest} setSelected={setSelectedRequest} token={token} busy={busy} mutate={mutate} />}
        {tab === "traffic" && <Traffic dashboard={dashboard} />}
        {tab === "health" && <SystemHealth overview={platformOverview} dashboard={dashboard} />}
        {tab === "audit" && <Audit dashboard={dashboard} />}
        {tab === "settings" && settings && <Settings value={settings} token={token} onSaved={() => load(token)} setError={setError} />}
      </section>

      {selectedClinic && (
        <ClinicDrawer
          clinic={selectedClinic}
          busy={busy}
          onClose={() => setSelectedClinic(null)}
          onEdit={() => setEditClinic(true)}
          onGift={() => setGiftClinic(true)}
          onRenew={() => setRenewClinic(true)}
          onArchive={() => setArchiveClinic(true)}
        />
      )}
      {editClinic && selectedClinic && <EditClinicModal clinic={selectedClinic} busy={busy} close={() => setEditClinic(false)} save={async (body) => { const updated = await mutate<Clinic>(`/api/v1/platform/admin-control/clinics/${selectedClinic.id}`, { method: "PATCH", body: JSON.stringify(body) }); setSelectedClinic(updated); setEditClinic(false); }} />}
      {giftClinic && selectedClinic && <GiftModal clinic={selectedClinic} busy={busy} close={() => setGiftClinic(false)} save={async (months, note) => { const updated = await mutate<Clinic>(`/api/v1/platform/admin-control/clinics/${selectedClinic.id}/gift`, { method: "POST", body: JSON.stringify({ months, note }) }); setSelectedClinic(updated); setGiftClinic(false); }} />}
      {renewClinic && selectedClinic && <RenewModal clinic={selectedClinic} busy={busy} close={() => setRenewClinic(false)} renew={async (days) => { await mutate(`/api/v1/platform/admin/clinics/${selectedClinic.id}/renew`, { method: "POST", body: JSON.stringify({ days }) }); setRenewClinic(false); }} />}
      {archiveClinic && selectedClinic && <ArchiveModal clinic={selectedClinic} busy={busy} close={() => setArchiveClinic(false)} archive={async (slug) => { await mutate(`/api/v1/platform/admin-control/clinics/${selectedClinic.id}/archive`, { method: "POST", body: JSON.stringify({ confirm_slug: slug, note: "Archived from internal control center" }) }); setArchiveClinic(false); setSelectedClinic(null); }} />}
    </main>
  );
}

function Overview({ dashboard, onOpenClinic }: { dashboard: Dashboard | null; onOpenClinic: (clinic: Clinic) => void }) {
  if (!dashboard) return <Loading />;
  const summary = dashboard.summary;
  return (
    <div className="pa3-stack">
      <section className="pa3-metric-grid">
        {metricCards(summary).map(([title, value, Icon]) => <article key={title}><span><Icon /></span><small>{title}</small><strong>{number(value)}</strong></article>)}
      </section>
      <section className="pa3-split pa3-accounting-row">
        <article className="pa3-panel">
          <PanelTitle eyebrow="ACCOUNT MIX" title="Clinic subscriptions" icon={Building2} />
          <div className="pa3-account-grid">
            <AccountStat label="Free" value={summary.clinics_free} className="free" />
            <AccountStat label="Paid" value={summary.clinics_paid} className="paid" />
            <AccountStat label="Gifted" value={summary.clinics_gifted} className="gift" />
            <AccountStat label="Legacy" value={summary.clinics_legacy} className="legacy" />
          </div>
        </article>
        <article className="pa3-panel">
          <PanelTitle eyebrow="REVENUE LEDGER" title="Verified revenue" icon={CircleDollarSign} />
          <div className="pa3-revenue-list">
            {Object.entries(dashboard.payments.revenue_by_currency).length ? Object.entries(dashboard.payments.revenue_by_currency).map(([currency, amount]) => <div key={currency}><span>{currency}</span><strong>{money(amount, currency)}</strong></div>) : <p>No priced verified payments recorded yet.</p>}
          </div>
          {dashboard.payments.unpriced_legacy_count > 0 && <div className="pa3-note">{dashboard.payments.unpriced_legacy_count} historical verified payment(s) have no stored amount and are excluded from revenue totals.</div>}
        </article>
      </section>
      <section className="pa3-panel">
        <PanelTitle eyebrow="CLINIC OPERATIONS" title="Per-clinic workload" icon={Database} />
        <ClinicTable rows={dashboard.clinics} onOpen={onOpenClinic} compact />
      </section>
    </div>
  );
}

function AccountStat({ label: title, value, className }: { label: string; value: number; className: string }) {
  return <div className={`pa3-account-stat ${className}`}><span>{title}</span><strong>{number(value)}</strong></div>;
}

function ClinicDirectory({ title, rows, search, setSearch, onOpen }: { title: string; rows: Clinic[]; search: string; setSearch: (value: string) => void; onOpen: (clinic: Clinic) => void }) {
  return (
    <section className="pa3-panel pa3-directory">
      <div className="pa3-directory-head"><div><small>ACCOUNT DIRECTORY</small><h2>{title}</h2><p>{rows.length} clinic account(s) in this view.</p></div><label><Search /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search clinic, slug or state" /></label></div>
      <ClinicTable rows={rows} onOpen={onOpen} />
    </section>
  );
}

function ClinicTable({ rows, onOpen, compact = false }: { rows: Clinic[]; onOpen: (clinic: Clinic) => void; compact?: boolean }) {
  return <div className="pa3-table-wrap"><table className="pa3-table"><thead><tr><th>Clinic</th><th>Account</th><th>Patients</th><th>OPGs</th><th>Follow-ups</th><th>AI conversations</th><th>Database</th><th>Access</th></tr></thead><tbody>{rows.map((clinic) => <tr key={clinic.id} onClick={() => onOpen(clinic)}><td><strong>{clinic.name}</strong><small>{clinic.slug}</small></td><td><span className={`pa3-account-tag ${clinic.category.toLowerCase()}`}>{clinic.category}</span><small>{clinic.operational_state}</small></td><td className="numeric">{number(clinic.stats.patients)}</td><td className="numeric">{number(clinic.stats.opgs)}</td><td><strong>{number(clinic.stats.followups_completed)} done</strong><small>{number(clinic.stats.followups_pending)} pending</small></td><td className="numeric">{number(clinic.stats.ai_conversations)}</td><td><StatusPill value={clinic.stats.database_status} /></td><td><strong>{clinic.subscription_expires_at ? date(clinic.subscription_expires_at) : "No expiry"}</strong>{!compact && <small>{clinic.days_remaining != null ? `${clinic.days_remaining} days left` : ""}</small>}</td></tr>)}</tbody></table>{!rows.length && <Empty message="No clinics match this view." />}</div>;
}

function Payments({ dashboard }: { dashboard: Dashboard | null }) {
  if (!dashboard) return <Loading />;
  return <div className="pa3-stack"><section className="pa3-metric-grid pa3-metric-grid-small"><article><span><CircleDollarSign /></span><small>Verified payments</small><strong>{number(dashboard.payments.verified_count)}</strong></article><article><span><Check /></span><small>Priced & accounted</small><strong>{number(dashboard.payments.accounted_count)}</strong></article><article><span><Clock3 /></span><small>Historical amount missing</small><strong>{number(dashboard.payments.unpriced_legacy_count)}</strong></article></section><section className="pa3-panel"><PanelTitle eyebrow="REAL PAYMENT LEDGER" title="Verified payments only" icon={CreditCard} /><div className="pa3-table-wrap"><table className="pa3-table"><thead><tr><th>Clinic</th><th>Market</th><th>Amount</th><th>Reference</th><th>Verified</th><th>Accounting</th></tr></thead><tbody>{dashboard.payments.items.map((payment) => <tr key={payment.id}><td><strong>{payment.clinic_name}</strong><small>{payment.clinic_id || "No linked clinic"}</small></td><td>{payment.market || "—"}</td><td><strong>{money(payment.amount, payment.currency)}</strong></td><td>{payment.reference || "—"}</td><td>{dateTime(payment.verified_at)}</td><td><StatusPill value={payment.accounted ? "ACCOUNTED" : "UNPRICED_LEGACY"} /></td></tr>)}</tbody></table>{!dashboard.payments.items.length && <Empty message="No verified real payments yet." />}</div></section></div>;
}

function Requests({ rows, selected, setSelected, token, busy, mutate }: { rows: AccessRequest[]; selected: AccessRequest | null; setSelected: (row: AccessRequest | null) => void; token: string; busy: string; mutate: <T>(path: string, init: RequestInit) => Promise<T> }) {
  const row = selected || rows[0] || null;
  const [editing, setEditing] = useState(false);
  return <div className="pa3-request-layout"><section className="pa3-request-list pa3-panel"><div className="pa3-panel-head-simple"><div><small>CLINIC PIPELINE</small><h2>Access requests</h2></div><b>{rows.length}</b></div>{rows.map((item) => <button key={item.id} className={row?.id === item.id ? "active" : ""} onClick={() => setSelected(item)}><div><strong>{item.clinic_name}</strong><StatusPill value={item.status} /></div><span>{item.contact_name} · {item.country}</span><small>{dateTime(item.created_at)}</small></button>)}</section>{row ? <section className="pa3-panel pa3-request-detail"><div className="pa3-request-title"><div><small>ACCESS REQUEST</small><h2>{row.clinic_name}</h2><p>{row.city}, {row.country}</p></div><button className="pa3-icon-button" onClick={() => setEditing(true)}><Pencil /></button></div><div className="pa3-detail-grid"><Info label="Contact" value={row.contact_name} sub={row.contact_role} /><Info label="Email" value={row.email} sub={row.phone} /><Info label="Clinic size" value={`${row.dentists_count} dentists`} sub={`${row.branches_count} branch(es)`} /><Info label="Submitted" value={date(row.created_at)} sub={row.website || "No website"} /></div>{row.notes && <div className="pa3-note"><strong>Applicant note</strong><p>{row.notes}</p></div>}<div className="pa3-action-row">{["SUBMITTED", "PAYMENT_REQUESTED", "PAYMENT_REVIEW"].includes(row.status) && <button className="pa3-secondary" disabled={!!busy} onClick={() => void mutate(`/api/v1/platform/admin-control/access-requests/${row.id}/send-payment`, { method: "POST", body: JSON.stringify({ note: "Payment instructions sent from control center" }) })}><Mail /> Send payment instructions</button>}{["PAYMENT_REQUESTED", "PAYMENT_REVIEW"].includes(row.status) && <button className="pa3-primary" disabled={!!busy} onClick={() => { const reference = window.prompt("Verified bank/payment reference", row.payment_reference || "")?.trim(); if (!reference) return; void mutate(`/api/v1/platform/admin-control/access-requests/${row.id}/activate`, { method: "POST", body: JSON.stringify({ reference, proof_note: "Payment verified in internal control center." }) }); }}><Check /> Verify payment & activate</button>}{!row.activated_clinic_id && row.status !== "REJECTED" && <button className="pa3-danger" disabled={!!busy} onClick={() => { const note = window.prompt("Reason for rejection (optional)", row.admin_note || "") ?? ""; if (window.confirm(`Reject access request for ${row.clinic_name}?`)) void mutate<AccessRequest>(`/api/v1/platform/admin/access-requests/${row.id}/reject`, { method: "POST", body: JSON.stringify({ note }) }); }}><X /> Reject request</button>}{!row.activated_clinic_id && <button className="pa3-danger" disabled={!!busy} onClick={() => { if (window.confirm(`Delete unactivated request for ${row.clinic_name}?`)) void mutate(`/api/v1/platform/admin-control/access-requests/${row.id}`, { method: "DELETE" }).then(() => setSelected(null)); }}><Trash2 /> Delete request</button>}</div>{editing && <EditRequestModal row={row} busy={busy} close={() => setEditing(false)} save={async (body) => { await mutate(`/api/v1/platform/admin-control/access-requests/${row.id}`, { method: "PATCH", body: JSON.stringify(body) }); setEditing(false); setSelected(null); }} />}</section> : <Empty message="No access request selected." />}</div>;
}

function SystemHealth({ overview, dashboard }: { overview: PlatformOverview | null; dashboard: Dashboard | null }) {
  if (!overview || !dashboard) return <Loading />;
  const offlineClinics = dashboard.clinics.filter((clinic) => clinic.stats.database_status !== "ONLINE");
  const healthRows: Array<[string, string]> = [
    ["API", overview.health.api],
    ["Control database", overview.health.control_database],
    ["Object storage", overview.health.storage_provider.toUpperCase()],
    ["AI provider", overview.health.ai_provider],
    ["SMTP", overview.health.smtp_configured ? "CONFIGURED" : "NOT CONFIGURED"],
    ["Tenant provisioning", overview.health.tenant_auto_provisioning_configured ? "CONFIGURED" : "NOT CONFIGURED"],
    ["Groq", overview.health.groq_configured ? "CONFIGURED" : "NOT CONFIGURED"],
    ["WhatsApp", overview.health.whatsapp_configured ? "CONFIGURED" : "NOT CONFIGURED"],
    ["Radar", overview.health.radar_enabled ? "ENABLED" : "DISABLED"],
  ];
  return <div className="pa3-stack">
    <section className="pa3-metric-grid pa3-metric-grid-small">
      <article><span><Building2 /></span><small>Active clinics</small><strong>{number(overview.metrics.clinics_active)}</strong></article>
      <article><span><Clock3 /></span><small>Expiring within 7 days</small><strong>{number(overview.metrics.clinics_expiring_7d)}</strong></article>
      <article><span><Mail /></span><small>Failed recent emails</small><strong>{number(overview.metrics.emails_failed_100)}</strong></article>
    </section>
    <section className="pa3-split">
      <article className="pa3-panel"><PanelTitle eyebrow="PLATFORM SERVICES" title="Configuration and core health" icon={HeartPulse} /><div className="pa3-health-grid">{healthRows.map(([name, value]) => <div key={name}><span>{name}</span><StatusPill value={value} /></div>)}</div></article>
      <article className="pa3-panel"><PanelTitle eyebrow="TENANT DATABASES" title="Clinic database availability" icon={Database} />{offlineClinics.length ? <div className="pa3-health-list">{offlineClinics.map((clinic) => <div key={clinic.id}><strong>{clinic.name}</strong><span>{clinic.slug}</span><StatusPill value={clinic.stats.database_status} /></div>)}</div> : <div className="pa3-health-ok"><Check /> All active tenant databases reported online.</div>}</article>
    </section>
    <section className="pa3-panel"><PanelTitle eyebrow="DELIVERY OPERATIONS" title="Recent email failures" icon={Mail} /><div className="pa3-table-wrap"><table className="pa3-table"><thead><tr><th>Type</th><th>Recipient</th><th>Subject</th><th>Status</th><th>Time</th></tr></thead><tbody>{overview.recent_emails.filter((email) => email.status === "FAILED").map((email) => <tr key={email.id}><td>{label(email.kind)}</td><td>{email.recipient}</td><td>{email.subject}</td><td><StatusPill value={email.status} /></td><td>{dateTime(email.created_at)}</td></tr>)}</tbody></table>{!overview.recent_emails.some((email) => email.status === "FAILED") && <Empty message="No recent email delivery failures." />}</div></section>
  </div>;
}

function Traffic({ dashboard }: { dashboard: Dashboard | null }) {
  if (!dashboard) return <Loading />;
  return <div className="pa3-stack"><section className="pa3-metric-grid pa3-metric-grid-small"><article><span><BarChart3 /></span><small>Tracked public visits · total</small><strong>{number(dashboard.traffic.totals.visits_total)}</strong></article><article><span><Activity /></span><small>Public visits · 30d</small><strong>{number(dashboard.traffic.totals.visits_30d)}</strong></article><article><span><Clock3 /></span><small>Public visits · 24h</small><strong>{number(dashboard.traffic.totals.visits_24h)}</strong></article></section><section className="pa3-panel"><PanelTitle eyebrow="PUBLIC SITE ANALYTICS" title="Page-by-page traffic" icon={BarChart3} /><div className="pa3-table-wrap"><table className="pa3-table"><thead><tr><th>Public page</th><th>Total visits</th><th>Last 30d</th><th>Unique · 30d</th><th>Last 24h</th></tr></thead><tbody>{dashboard.traffic.pages.map((page) => <tr key={page.path}><td><strong>{page.path === "/" ? "Homepage" : page.path}</strong><small>{page.path}</small></td><td className="numeric">{number(page.visits_total)}</td><td className="numeric">{number(page.visits_30d)}</td><td className="numeric">{number(page.unique_30d)}</td><td className="numeric">{number(page.visits_24h)}</td></tr>)}</tbody></table></div></section></div>;
}

function Audit({ dashboard }: { dashboard: Dashboard | null }) {
  if (!dashboard) return <Loading />;
  return <section className="pa3-panel"><PanelTitle eyebrow="ADMINISTRATIVE AUDIT" title="Recent privileged actions" icon={ShieldCheck} /><div className="pa3-timeline">{dashboard.recent_audit.map((row) => <article key={row.id}><span><ShieldCheck /></span><div><strong>{label(row.action)}</strong><p>{row.target_type} · {row.target_id || "platform"}</p><small>{dateTime(row.created_at)}</small></div><code>{JSON.stringify(row.details)}</code></article>)}{!dashboard.recent_audit.length && <Empty message="No control-center actions recorded yet." />}</div></section>;
}

function Settings({ value, token, onSaved, setError }: { value: PlatformSettings; token: string; onSaved: () => Promise<void>; setError: (message: string) => void }) {
  const [form, setForm] = useState(value);
  const [busy, setBusy] = useState(false);
  useEffect(() => setForm(value), [value]);
  const update = (key: keyof PlatformSettings, next: string | number) => setForm((current) => ({ ...current, [key]: next }));
  async function save() {
    setBusy(true); setError("");
    try {
      await requestJson("/api/v1/platform/admin/settings", token, { method: "PUT", body: JSON.stringify({ price_amount: form.price_amount, price_currency: form.price_currency, payment_recipient: form.payment_recipient, payment_card: form.payment_card, payment_bank_details: form.payment_bank_details, payment_email_subject: form.payment_email_subject, payment_email_intro: form.payment_email_intro, activation_email_subject: form.activation_email_subject, activation_email_intro: form.activation_email_intro }) });
      await onSaved();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save platform settings"); }
    finally { setBusy(false); }
  }
  return <section className="pa3-panel pa3-settings"><PanelTitle eyebrow="PLATFORM CONFIGURATION" title="Payment and activation settings" icon={KeyRound} /><div className="pa3-note">Market-specific Armenia and Russia prices are currently applied by the market pricing rules. This fallback price is used by legacy/default activation flows.</div><div className="pa3-settings-grid"><label>Fallback Premium price<input type="number" value={form.price_amount} onChange={(event) => update("price_amount", Number(event.target.value))} /></label><label>Currency<input value={form.price_currency} onChange={(event) => update("price_currency", event.target.value.toUpperCase())} /></label><label className="wide">Payment recipient<input value={form.payment_recipient} onChange={(event) => update("payment_recipient", event.target.value)} /></label><label className="wide">Card / payment number<input value={form.payment_card} onChange={(event) => update("payment_card", event.target.value)} /></label><label className="wide">Bank / transfer details<textarea rows={4} value={form.payment_bank_details} onChange={(event) => update("payment_bank_details", event.target.value)} /></label><label className="wide">Payment email subject<input value={form.payment_email_subject} onChange={(event) => update("payment_email_subject", event.target.value)} /></label><label className="wide">Payment email introduction<textarea rows={4} value={form.payment_email_intro} onChange={(event) => update("payment_email_intro", event.target.value)} /></label><label className="wide">Activation email subject<input value={form.activation_email_subject} onChange={(event) => update("activation_email_subject", event.target.value)} /></label><label className="wide">Activation email introduction<textarea rows={4} value={form.activation_email_intro} onChange={(event) => update("activation_email_intro", event.target.value)} /></label></div><button className="pa3-primary" disabled={busy} onClick={() => void save()}><Save /> {busy ? "Saving…" : "Save platform settings"}</button></section>;
}

function ClinicDrawer({ clinic, busy, onClose, onEdit, onGift, onRenew, onArchive }: { clinic: Clinic; busy: string; onClose: () => void; onEdit: () => void; onGift: () => void; onRenew: () => void; onArchive: () => void }) {
  return <div className="pa3-drawer-layer" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><aside className="pa3-drawer"><header><div><small>CLINIC CONTROL</small><h2>{clinic.name}</h2><p>{clinic.slug}</p></div><button onClick={onClose}><X /></button></header><div className="pa3-drawer-status"><span className={`pa3-account-tag ${clinic.category.toLowerCase()}`}>{clinic.category}</span><StatusPill value={clinic.operational_state} /><StatusPill value={clinic.stats.database_status} /></div><section><h3>Clinical operations</h3><div className="pa3-detail-grid"><Info label="Patients" value={number(clinic.stats.patients)} /><Info label="OPGs" value={number(clinic.stats.opgs)} /><Info label="AI analyses" value={number(clinic.stats.ai_analyses)} /><Info label="AI conversations" value={number(clinic.stats.ai_conversations)} /><Info label="Follow-ups completed" value={number(clinic.stats.followups_completed)} /><Info label="Follow-ups pending" value={number(clinic.stats.followups_pending)} /><Info label="AI messages" value={number(clinic.stats.conversation_messages)} /><Info label="Care items pending" value={number(clinic.stats.care_items_pending)} /></div></section><section><h3>Subscription</h3><div className="pa3-detail-grid"><Info label="Plan" value={clinic.subscription_plan} /><Info label="Source" value={clinic.subscription_source} /><Info label="Started" value={date(clinic.subscription_starts_at)} /><Info label="Expires" value={date(clinic.subscription_expires_at)} /><Info label="Days remaining" value={clinic.days_remaining == null ? "—" : String(clinic.days_remaining)} /><Info label="Gift note" value={clinic.gift_note || "—"} /></div></section><footer><button className="pa3-secondary" disabled={!!busy} onClick={onEdit}><Pencil /> Edit account</button><button className="pa3-primary" disabled={!!busy || clinic.operational_state === "ARCHIVED"} onClick={onRenew}><RefreshCw /> Renew subscription</button><button className="pa3-gift" disabled={!!busy} onClick={onGift}><Gift /> Grant Premium gift</button><button className="pa3-danger" disabled={!!busy} onClick={onArchive}><Archive /> Archive access</button></footer><p className="pa3-safety-note"><ShieldCheck /> Clinic archive disables access but deliberately preserves the tenant database and clinical history.</p></aside></div>;
}

function EditClinicModal({ clinic, busy, close, save }: { clinic: Clinic; busy: string; close: () => void; save: (body: Record<string, unknown>) => Promise<void> }) {
  const [name, setName] = useState(clinic.name);
  const [state, setState] = useState(clinic.subscription_state);
  const [active, setActive] = useState(clinic.registry_active);
  const [expiry, setExpiry] = useState(clinic.subscription_expires_at ? clinic.subscription_expires_at.slice(0, 10) : "");
  return <Modal title="Edit clinic account" close={close}><div className="pa3-modal-form"><label>Clinic name<input value={name} onChange={(event) => setName(event.target.value)} /></label><label>Subscription state<select value={state} onChange={(event) => setState(event.target.value)}><option>ACTIVE</option><option>PAYMENT_REVIEW</option><option>EXPIRED</option><option>SUSPENDED</option><option>ARCHIVED</option></select></label><label>Expiry date<input type="date" value={expiry} onChange={(event) => setExpiry(event.target.value)} /></label><label className="pa3-check"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /> Registry access enabled</label><button className="pa3-primary" disabled={!!busy} onClick={() => void save({ name, subscription_state: state, is_active: active, expires_at: expiry ? new Date(`${expiry}T23:59:59Z`).toISOString() : null })}><Save /> Save account</button></div></Modal>;
}

function GiftModal({ clinic, busy, close, save }: { clinic: Clinic; busy: string; close: () => void; save: (months: number, note: string) => Promise<void> }) {
  const [months, setMonths] = useState(3);
  const [note, setNote] = useState("");
  return <Modal title={`Gift Premium to ${clinic.name}`} close={close}><div className="pa3-modal-form"><div className="pa3-gift-callout"><Gift /><div><strong>Startup-funded access</strong><p>This account will be reported separately from paid revenue.</p></div></div><label>Gift duration (months)<input type="number" min="1" max="24" value={months} onChange={(event) => setMonths(Number(event.target.value))} /></label><label>Internal note<textarea rows={4} value={note} onChange={(event) => setNote(event.target.value)} placeholder="Reason, partnership, campaign or owner" /></label><button className="pa3-gift pa3-wide-button" disabled={!!busy} onClick={() => void save(months, note)}><Gift /> Grant {months} month{months === 1 ? "" : "s"} Premium</button></div></Modal>;
}

function RenewModal({ clinic, busy, close, renew }: { clinic: Clinic; busy: string; close: () => void; renew: (days: number) => Promise<void> }) {
  const [days, setDays] = useState(30);
  return <Modal title={`Renew ${clinic.name}`} close={close}><div className="pa3-modal-form"><div className="pa3-gift-callout"><RefreshCw /><div><strong>Extend Premium access</strong><p>The extension starts from the current expiry when it is still in the future, otherwise from today.</p></div></div><label>Extension (days)<input type="number" min="1" max="365" value={days} onChange={(event) => setDays(Number(event.target.value))} /></label><button className="pa3-primary pa3-wide-button" disabled={!!busy || days < 1 || days > 365} onClick={() => void renew(days)}><RefreshCw /> Renew for {days} days</button></div></Modal>;
}

function ArchiveModal({ clinic, busy, close, archive }: { clinic: Clinic; busy: string; close: () => void; archive: (slug: string) => Promise<void> }) {
  const [slug, setSlug] = useState("");
  return <Modal title="Archive clinic access" close={close}><div className="pa3-modal-form"><div className="pa3-danger-callout"><Archive /><div><strong>Access will be disabled.</strong><p>Clinical data is not deleted. This is intentional to prevent accidental loss of patient history.</p></div></div><p>Type <code>{clinic.slug}</code> to confirm.</p><input value={slug} onChange={(event) => setSlug(event.target.value)} placeholder={clinic.slug} /><button className="pa3-danger pa3-wide-button" disabled={!!busy || slug !== clinic.slug} onClick={() => void archive(slug)}><Archive /> Archive clinic</button></div></Modal>;
}

function EditRequestModal({ row, busy, close, save }: { row: AccessRequest; busy: string; close: () => void; save: (body: Record<string, unknown>) => Promise<void> }) {
  const [form, setForm] = useState({ clinic_name: row.clinic_name, country: row.country, city: row.city, address: row.address || "", website: row.website || "", contact_name: row.contact_name, contact_role: row.contact_role, email: row.email, phone: row.phone, admin_note: row.admin_note || "" });
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));
  return <Modal title="Edit access request" close={close}><div className="pa3-modal-form pa3-modal-grid">{Object.entries(form).map(([key, value]) => <label key={key} className={key === "admin_note" ? "wide" : ""}>{label(key)}{key === "admin_note" ? <textarea rows={3} value={value} onChange={(event) => update(key as keyof typeof form, event.target.value)} /> : <input value={value} onChange={(event) => update(key as keyof typeof form, event.target.value)} />}</label>)}<button className="pa3-primary wide" disabled={!!busy} onClick={() => void save(form)}><Save /> Save request</button></div></Modal>;
}

function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) {
  return <div className="pa3-modal-layer" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><section className="pa3-modal"><header><h2>{title}</h2><button onClick={close}><X /></button></header>{children}</section></div>;
}

function PanelTitle({ eyebrow, title, icon: Icon }: { eyebrow: string; title: string; icon: typeof Activity }) {
  return <div className="pa3-panel-title"><span><Icon /></span><div><small>{eyebrow}</small><h2>{title}</h2></div></div>;
}

function Info({ label: title, value, sub }: { label: string; value: string; sub?: string }) {
  return <div className="pa3-info"><small>{title}</small><strong>{value}</strong>{sub ? <span>{sub}</span> : null}</div>;
}

function Loading() {
  return <div className="pa3-loading"><RefreshCw className="spin" /> Loading secure platform data…</div>;
}

function Empty({ message }: { message: string }) {
  return <div className="pa3-empty"><Database /><span>{message}</span></div>;
}
