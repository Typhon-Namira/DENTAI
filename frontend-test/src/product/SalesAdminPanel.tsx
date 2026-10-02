import {
  Activity,
  BadgeCheck,
  Camera,
  Check,
  Clock3,
  CreditCard,
  KeyRound,
  Lightbulb,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Trophy,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { API_BASE_URL } from "../api/client";
import "./sales-admin.css";

type Balance = {
  currency: string;
  earned: number;
  pending_withdrawal: number;
  paid_out: number;
  available: number;
};

type ScoreCategory = {
  key: string;
  label: string;
  points: number;
  target: number;
  percent: number;
  completed: boolean;
};

type ScoreSummary = {
  total: number;
  target: number;
  percent: number;
  all_complete: boolean;
  categories: {
    reports: ScoreCategory;
    clinics: ScoreCategory;
    growth: ScoreCategory;
  };
  award?: {
    id: string;
    status: string;
    manager_id: string;
    reached_at: string;
    equity_percent: number;
    is_winner: boolean;
  } | null;
};

type Manager = {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  name: string;
  title: string;
  phone?: string | null;
  is_active: boolean;
  is_public: boolean;
  verified_at?: string | null;
  must_change_password: boolean;
  bank_card_last4?: string | null;
  bank_account_holder?: string | null;
  last_login_at?: string | null;
  last_logout_at?: string | null;
  created_at: string;
  updated_at: string;
  photo_url?: string | null;
  stats: {
    submitted_reports: number;
    reported_clinics: number;
    login_count: number;
    commission_events: number;
  };
  balances: Balance[];
  score: ScoreSummary;
};

type Withdrawal = {
  id: string;
  manager_id: string;
  manager_name: string;
  manager_email?: string | null;
  amount: number;
  currency: string;
  status: string;
  card_number: string;
  bank_card_last4: string;
  bank_account_holder?: string | null;
  requested_at: string;
  reviewed_at?: string | null;
  paid_at?: string | null;
  paid_reference?: string | null;
  admin_note?: string | null;
};

type Attribution = {
  id: string;
  access_request_id: string;
  clinic_id?: string | null;
  clinic_name?: string | null;
  manager_id?: string | null;
  manager_name?: string | null;
  report_clinic_id?: string | null;
  status: string;
  match_method?: string | null;
  match_score: number;
  match_details: Record<string, unknown>;
  created_at: string;
};

type ActivityDetail = {
  manager: Manager;
  stats: Manager["stats"];
  balances: Balance[];
  sessions: Array<{
    id: string;
    started_at: string;
    last_seen_at: string;
    ended_at?: string | null;
    ip_hash?: string | null;
    user_agent?: string | null;
  }>;
  activities: Array<{
    id: string;
    action: string;
    entity_type?: string | null;
    entity_id?: string | null;
    details: Record<string, unknown>;
    created_at: string;
    ip_hash?: string | null;
    user_agent?: string | null;
  }>;
  reports: Array<{
    id: string;
    report_date: string;
    status: string;
    summary?: string | null;
    submitted_at?: string | null;
    clinics: Array<{
      id: string;
      clinic_name: string;
      country: string;
      city: string;
      contact_name?: string | null;
      email?: string | null;
      phone?: string | null;
      website?: string | null;
      negotiation_result: string;
      outcome_status: string;
      next_step?: string | null;
      notes?: string | null;
      contacted_at: string;
    }>;
  }>;
};

type GrowthIdeaAdmin = {
  id: string;
  manager_id: string;
  manager_name: string;
  manager_email?: string | null;
  title: string;
  description: string;
  expected_impact?: string | null;
  status: string;
  admin_note?: string | null;
  submitted_at: string;
  reviewed_at?: string | null;
};

type EquityAwardAdmin = {
  id: string;
  manager_id: string;
  manager_name: string;
  manager_email?: string | null;
  status: string;
  points_at_award: number;
  equity_percent: number;
  reached_at: string;
  reviewed_at?: string | null;
  admin_note?: string | null;
  score: ScoreSummary;
};

type Mode = "managers" | "withdrawals" | "ideas" | "award";

function url(path: string) {
  return `${API_BASE_URL}${path}`;
}

async function json<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url(path), {
    ...init,
    headers: {
      "content-type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.error?.message || body?.detail || "Request failed");
  return body as T;
}

function money(value: number, currency: string) {
  return `${Number(value || 0).toLocaleString("en-US")} ${currency}`;
}

function when(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString("en-US");
}

function statusClass(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_");
}

export function SalesAdminPanel({ token, mode }: { token: string; mode: Mode }) {
  const [managers, setManagers] = useState<Manager[]>([]);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [attributions, setAttributions] = useState<Attribution[]>([]);
  const [ideas, setIdeas] = useState<GrowthIdeaAdmin[]>([]);
  const [award, setAward] = useState<EquityAwardAdmin | null>(null);
  const [selected, setSelected] = useState<Manager | null>(null);
  const [activity, setActivity] = useState<ActivityDetail | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [photoOpen, setPhotoOpen] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    const [nextManagers, nextWithdrawals, nextAttributions, nextIdeas, nextAward] = await Promise.all([
      json<Manager[]>("/api/v1/platform/admin-control/sales-managers", token),
      json<Withdrawal[]>("/api/v1/platform/admin-control/sales-withdrawals", token),
      json<Attribution[]>("/api/v1/platform/admin-control/sales-attributions", token),
      json<GrowthIdeaAdmin[]>("/api/v1/platform/admin-control/sales-growth-ideas", token),
      json<{award: EquityAwardAdmin | null}>("/api/v1/platform/admin-control/sales-equity-award", token),
    ]);
    setManagers(nextManagers);
    setWithdrawals(nextWithdrawals);
    setAttributions(nextAttributions);
    setIdeas(nextIdeas);
    setAward(nextAward.award);
    setSelected((current) => current ? nextManagers.find((row) => row.id === current.id) ?? null : null);
  }, [token]);

  useEffect(() => {
    void load().catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load sales operations"));
  }, [load]);

  useEffect(() => {
    if (!selected) {
      setActivity(null);
      return;
    }
    void json<ActivityDetail>(`/api/v1/platform/admin-control/sales-managers/${selected.id}/activity`, token)
      .then(setActivity)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load manager activity"));
  }, [selected, token]);

  async function mutate<T>(path: string, init: RequestInit) {
    setBusy(path);
    setError("");
    try {
      const result = await json<T>(path, token, init);
      await load();
      if (selected) {
        const next = await json<ActivityDetail>(`/api/v1/platform/admin-control/sales-managers/${selected.id}/activity`, token);
        setActivity(next);
      }
      return result;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Administrative action failed");
      throw reason;
    } finally {
      setBusy("");
    }
  }

  if (mode === "ideas") {
    return <GrowthIdeasAdmin rows={ideas} busy={busy} error={error} refresh={load} approve={async (row) => {
      const note = window.prompt("Approval note (optional)", row.admin_note || "") ?? "";
      await mutate(`/api/v1/platform/admin-control/sales-growth-ideas/${row.id}/approve`, {method:"POST",body:JSON.stringify({note})});
    }} reject={async (row) => {
      const note = window.prompt("Reason for rejection", row.admin_note || "") ?? "";
      if (!window.confirm(`Reject idea "${row.title}" from ${row.manager_name}?`)) return;
      await mutate(`/api/v1/platform/admin-control/sales-growth-ideas/${row.id}/reject`, {method:"POST",body:JSON.stringify({note})});
    }}/>;
  }

  if (mode === "award") {
    return <EquityAwardView award={award} busy={busy} error={error} refresh={load} confirm={async (row) => {
      const note = window.prompt("Legal / administrative confirmation note (optional)", row.admin_note || "") ?? "";
      await mutate(`/api/v1/platform/admin-control/sales-equity-award/${row.id}/confirm`, {method:"POST",body:JSON.stringify({note})});
    }}/>;
  }

  if (mode === "withdrawals") {
    return <WithdrawalsView rows={withdrawals} busy={busy} error={error} confirm={async (row) => {
      const reference = window.prompt("Manual payment reference", row.paid_reference || "")?.trim();
      if (!reference) return;
      const note = window.prompt("Internal payment note (optional)", row.admin_note || "") ?? "";
      await mutate(`/api/v1/platform/admin-control/sales-withdrawals/${row.id}/confirm`, {
        method: "POST",
        body: JSON.stringify({ reference, note }),
      });
    }} reject={async (row) => {
      const note = window.prompt("Reason for rejection", row.admin_note || "") ?? "";
      if (!window.confirm(`Reject withdrawal request for ${row.manager_name}?`)) return;
      await mutate(`/api/v1/platform/admin-control/sales-withdrawals/${row.id}/reject`, {
        method: "POST",
        body: JSON.stringify({ note }),
      });
    }} refresh={load}/>;
  }

  const pendingAttributions = attributions.filter((row) => ["AMBIGUOUS", "UNMATCHED"].includes(row.status));

  return <div className="sa-stack">
    {error && <div className="pa3-error pa3-page-error">{error}<button onClick={() => setError("")}><X/></button></div>}
    <section className="pa3-metric-grid pa3-metric-grid-small">
      <article><span><UsersRound/></span><small>Sales managers</small><strong>{managers.length}</strong></article>
      <article><span><ShieldCheck/></span><small>Active managers</small><strong>{managers.filter((row) => row.is_active).length}</strong></article>
      <article><span><CreditCard/></span><small>Pending payouts</small><strong>{withdrawals.filter((row) => row.status === "PENDING").length}</strong></article>
      <article><span><Activity/></span><small>Attribution review</small><strong>{pendingAttributions.length}</strong></article>
    </section>

    <section className="pa3-panel sa-directory">
      <div className="sa-toolbar"><div><small>SALES OPERATIONS</small><h2>Verified sales managers</h2><p>Create, edit, monitor and remove manager access. Historical activity is preserved.</p></div><div><button className="pa3-secondary" onClick={() => void load()}><RefreshCw/> Refresh</button><button className="pa3-primary" onClick={() => setCreateOpen(true)}><Plus/> Add sales manager</button></div></div>
      <div className="pa3-table-wrap"><table className="pa3-table"><thead><tr><th>Manager</th><th>Status</th><th>Score</th><th>Reports</th><th>Clinics</th><th>Logins</th><th>Balance</th><th>Last login</th></tr></thead><tbody>{managers.map((row) => <tr key={row.id} onClick={() => setSelected(row)}><td><div className="sa-manager-cell">{row.photo_url ? <img src={`${API_BASE_URL}${row.photo_url}`} alt=""/> : <span><UserRound/></span>}<div><strong>{row.name}</strong><small>{row.email} · @{row.username}</small></div></div></td><td><span className={`pa3-status pa3-status-${row.is_active ? "active" : "archived"}`}>{row.is_active ? "ACTIVE" : "REMOVED"}</span>{row.is_public && <small>Public verified card</small>}</td><td><strong>{row.score.total}/1000</strong><small>{Math.round(row.score.percent)}%</small></td><td className="numeric">{row.stats.submitted_reports}</td><td className="numeric">{row.stats.reported_clinics}</td><td className="numeric">{row.stats.login_count}</td><td>{row.balances.length ? row.balances.map((balance) => <small key={balance.currency}>{money(balance.available, balance.currency)}</small>) : "—"}</td><td>{when(row.last_login_at)}</td></tr>)}</tbody></table>{!managers.length && <div className="pa3-empty">No sales managers have been created.</div>}</div>
    </section>

    {pendingAttributions.length > 0 && <AttributionReview rows={pendingAttributions} managers={managers} busy={busy} confirm={async (row, managerId) => {
      await mutate(`/api/v1/platform/admin-control/sales-attributions/${row.id}/confirm`, {
        method: "POST",
        body: JSON.stringify({ manager_id: managerId }),
      });
    }}/>}

    {selected && <ManagerDrawer manager={selected} detail={activity} busy={busy} close={() => setSelected(null)} edit={() => setEditOpen(true)} photo={() => setPhotoOpen(true)} growth={async () => {
      const note = window.prompt("Describe the manager's verified startup-growth contribution (+10 points)")?.trim();
      if (!note) return;
      await mutate(`/api/v1/platform/admin-control/sales-managers/${selected.id}/growth-contribution`, {method:"POST",body:JSON.stringify({note})});
    }} reset={async () => {
      if (!window.confirm(`Reset password for ${selected.name} and email a new temporary password?`)) return;
      await mutate(`/api/v1/platform/admin-control/sales-managers/${selected.id}/reset-password`, { method: "POST", body: "{}" });
    }} remove={async () => {
      if (!window.confirm(`Remove ${selected.name} from active sales operations? Their historical reports, commissions and audit trail will be preserved.`)) return;
      await mutate(`/api/v1/platform/admin-control/sales-managers/${selected.id}`, { method: "DELETE" });
      setSelected(null);
    }}/>}
    {createOpen && <CreateManagerModal token={token} close={() => setCreateOpen(false)} onCreated={async () => { setCreateOpen(false); await load(); }} setError={setError}/>}
    {editOpen && selected && <EditManagerModal manager={selected} busy={busy} close={() => setEditOpen(false)} save={async (body) => {
      await mutate(`/api/v1/platform/admin-control/sales-managers/${selected.id}`, { method: "PATCH", body: JSON.stringify(body) });
      setEditOpen(false);
    }}/>}
    {photoOpen && selected && <ReplacePhotoModal token={token} manager={selected} close={() => setPhotoOpen(false)} saved={async () => { setPhotoOpen(false); await load(); }} setError={setError}/>}
  </div>;
}

function CreateManagerModal({ token, close, onCreated, setError }: { token: string; close: () => void; onCreated: () => Promise<void>; setError: (message: string) => void }) {
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", title: "Sales Manager", phone: "", username: "", is_public: true });
  const [photo, setPhoto] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const update = (key: keyof typeof form, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!photo) {
      setError("A manager profile photo is required.");
      return;
    }
    setBusy(true);
    setError("");
    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => data.append(key, String(value)));
    data.append("photo", photo);
    try {
      const response = await fetch(url("/api/v1/platform/admin-control/sales-managers"), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: data,
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.error?.message || "Could not create manager");
      await onCreated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create manager");
    } finally {
      setBusy(false);
    }
  }

  return <Modal title="Add verified sales manager" close={close}><form className="sa-form" onSubmit={submit}><div className="sa-create-note"><BadgeCheck/><div><strong>Real account provisioning</strong><p>The manager receives a generated username and temporary password by email immediately after creation. The public About card is created from this same verified record.</p></div></div><div className="sa-grid"><label>First name<input required value={form.first_name} onChange={(e) => update("first_name", e.target.value)}/></label><label>Last name<input required value={form.last_name} onChange={(e) => update("last_name", e.target.value)}/></label><label>Email<input type="email" required value={form.email} onChange={(e) => update("email", e.target.value)}/></label><label>Title<input required value={form.title} onChange={(e) => update("title", e.target.value)}/></label><label>Phone<input value={form.phone} onChange={(e) => update("phone", e.target.value)}/></label><label>Preferred username <small>optional</small><input value={form.username} onChange={(e) => update("username", e.target.value)}/></label><label className="wide">Profile photo<input type="file" accept="image/jpeg,image/png,image/webp" required onChange={(e) => setPhoto(e.target.files?.[0] || null)}/></label><label className="sa-check wide"><input type="checkbox" checked={form.is_public} onChange={(e) => update("is_public", e.target.checked)}/> Publish verified card on the About page</label></div><button className="pa3-primary sa-wide" disabled={busy}>{busy ? "Creating & sending credentials…" : "Create manager & email credentials"}</button></form></Modal>;
}

function EditManagerModal({ manager, busy, close, save }: { manager: Manager; busy: string; close: () => void; save: (body: Record<string, unknown>) => Promise<void> }) {
  const [form, setForm] = useState({ first_name: manager.first_name, last_name: manager.last_name, title: manager.title, email: manager.email, phone: manager.phone || "", is_active: manager.is_active, is_public: manager.is_public });
  const update = (key: keyof typeof form, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));
  return <Modal title={`Edit ${manager.name}`} close={close}><div className="sa-form"><div className="sa-grid"><label>First name<input value={form.first_name} onChange={(e) => update("first_name", e.target.value)}/></label><label>Last name<input value={form.last_name} onChange={(e) => update("last_name", e.target.value)}/></label><label>Email<input type="email" value={form.email} onChange={(e) => update("email", e.target.value)}/></label><label>Title<input value={form.title} onChange={(e) => update("title", e.target.value)}/></label><label>Phone<input value={form.phone} onChange={(e) => update("phone", e.target.value)}/></label><label className="sa-check"><input type="checkbox" checked={form.is_active} onChange={(e) => update("is_active", e.target.checked)}/> Active account</label><label className="sa-check wide"><input type="checkbox" checked={form.is_public} onChange={(e) => update("is_public", e.target.checked)}/> Visible as a verified manager on About</label></div><button className="pa3-primary sa-wide" disabled={!!busy} onClick={() => void save(form)}>Save manager</button></div></Modal>;
}

function ReplacePhotoModal({ token, manager, close, saved, setError }: { token: string; manager: Manager; close: () => void; saved: () => Promise<void>; setError: (message: string) => void }) {
  const [photo, setPhoto] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  async function upload() {
    if (!photo) return;
    setBusy(true);
    const data = new FormData();
    data.append("photo", photo);
    try {
      const response = await fetch(url(`/api/v1/platform/admin-control/sales-managers/${manager.id}/photo`), { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: data });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.error?.message || "Photo update failed");
      await saved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Photo update failed");
    } finally {
      setBusy(false);
    }
  }
  return <Modal title="Replace manager photo" close={close}><div className="sa-form">{manager.photo_url && <img className="sa-photo-preview" src={`${API_BASE_URL}${manager.photo_url}`} alt={manager.name}/>}<label>New verified profile photo<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(e) => setPhoto(e.target.files?.[0] || null)}/></label><button className="pa3-primary sa-wide" disabled={busy || !photo} onClick={() => void upload()}><Camera/> Replace photo</button></div></Modal>;
}

function ManagerDrawer({ manager, detail, busy, close, edit, photo, growth, reset, remove }: { manager: Manager; detail: ActivityDetail | null; busy: string; close: () => void; edit: () => void; photo: () => void; growth: () => Promise<void>; reset: () => Promise<void>; remove: () => Promise<void> }) {
  const [section, setSection] = useState<"overview" | "reports" | "sessions" | "activity">("overview");
  return <div className="pa3-drawer-layer" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}><aside className="pa3-drawer sa-drawer"><header><div><small>SALES MANAGER CONTROL</small><h2>{manager.name}</h2><p>@{manager.username} · {manager.email}</p></div><button onClick={close}><X/></button></header><div className="sa-profile-head">{manager.photo_url ? <img src={`${API_BASE_URL}${manager.photo_url}`} alt={manager.name}/> : <span><UserRound/></span>}<div><strong>{manager.title}</strong><p>{manager.phone || "No phone"} · {manager.is_public ? "Public verified card" : "Hidden from About"}</p></div></div><div className="sa-subnav">{(["overview","reports","sessions","activity"] as const).map((id) => <button className={section === id ? "active" : ""} key={id} onClick={() => setSection(id)}>{id}</button>)}</div>
    {section === "overview" && <><section><h3>1,000-point progress</h3><AdminScoreBars score={manager.score}/></section><section><h3>Performance</h3><div className="pa3-detail-grid"><Info title="Reports" value={String(manager.stats.submitted_reports)}/><Info title="Clinics reported" value={String(manager.stats.reported_clinics)}/><Info title="Logins" value={String(manager.stats.login_count)}/><Info title="Commission events" value={String(manager.stats.commission_events)}/><Info title="Last login" value={when(manager.last_login_at)}/><Info title="Last logout" value={when(manager.last_logout_at)}/></div></section><section><h3>Financial ledger</h3><div className="sa-balance-list">{manager.balances.map((row) => <div key={row.currency}><strong>{money(row.available,row.currency)}</strong><span>available</span><small>{money(row.earned,row.currency)} earned · {money(row.paid_out,row.currency)} paid · {money(row.pending_withdrawal,row.currency)} pending</small></div>)}{!manager.balances.length && <p className="pa3-muted">No commission ledger yet.</p>}</div></section></>}
    {section === "reports" && <section><h3>Permanent daily report history</h3>{detail ? <div className="sa-report-list">{detail.reports.map((report) => <article key={report.id}><div><strong>{report.report_date}</strong><span>{report.status}</span><small>{report.clinics.length} clinic(s)</small></div>{report.summary && <p>{report.summary}</p>}{report.clinics.map((clinic) => <div className="sa-report-clinic" key={clinic.id}><strong>{clinic.clinic_name}</strong><small>{clinic.city}, {clinic.country} · {clinic.outcome_status}</small><p>{clinic.negotiation_result}</p><span>{clinic.email || "No email"} · {clinic.phone || "No phone"}</span></div>)}</article>)}</div> : <Loading/>}</section>}
    {section === "sessions" && <section><h3>Login / logout sessions</h3>{detail ? <div className="sa-session-list">{detail.sessions.map((session) => <article key={session.id}><ShieldCheck/><div><strong>{when(session.started_at)}</strong><span>{session.ended_at ? `Logout ${when(session.ended_at)}` : "Session active / expired without logout"}</span><small>Last seen {when(session.last_seen_at)} · IP hash {session.ip_hash || "—"}</small><code>{session.user_agent || "Unknown user agent"}</code></div></article>)}</div> : <Loading/>}</section>}
    {section === "activity" && <section><h3>Full manager activity trail</h3>{detail ? <div className="sa-activity-list">{detail.activities.map((row) => <article key={row.id}><Activity/><div><strong>{row.action.replaceAll("_"," ")}</strong><span>{row.entity_type || "Manager"} {row.entity_id ? `· ${row.entity_id}` : ""}</span><small>{when(row.created_at)}</small><code>{JSON.stringify(row.details)}</code></div></article>)}</div> : <Loading/>}</section>}
    <footer><button className="pa3-secondary" disabled={!!busy} onClick={edit}>Edit manager</button><button className="pa3-secondary" disabled={!!busy} onClick={photo}><Camera/> Photo</button><button className="pa3-secondary" disabled={!!busy} onClick={() => void growth()}><Trophy/> +10 growth points</button><button className="pa3-secondary" disabled={!!busy} onClick={() => void reset()}><KeyRound/> Reset password</button>{manager.is_active && <button className="pa3-danger" disabled={!!busy} onClick={() => void remove()}><Trash2/> Remove access</button>}</footer>
  </aside></div>;
}

function AttributionReview({ rows, managers, busy, confirm }: { rows: Attribution[]; managers: Manager[]; busy: string; confirm: (row: Attribution, managerId: string) => Promise<void> }) {
  const [choices, setChoices] = useState<Record<string,string>>({});
  return <section className="pa3-panel"><div className="sa-toolbar"><div><small>ATTRIBUTION SAFETY QUEUE</small><h2>Clinic ownership review</h2><p>Automatic attribution only credits a unique high-confidence report match. Ambiguous or unmatched clinics stay here until an administrator confirms the manager.</p></div></div><div className="pa3-table-wrap"><table className="pa3-table"><thead><tr><th>Clinic</th><th>Match state</th><th>Evidence</th><th>Assign manager</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td><strong>{row.clinic_name || "Unknown clinic"}</strong><small>{row.access_request_id}</small></td><td><span className={`pa3-status pa3-status-${statusClass(row.status)}`}>{row.status}</span><small>Score {row.match_score}</small></td><td><code>{JSON.stringify(row.match_details)}</code></td><td><div className="sa-assign"><select value={choices[row.id] || ""} onChange={(e) => setChoices((current) => ({...current,[row.id]:e.target.value}))}><option value="">Select manager…</option>{managers.filter((manager) => manager.is_active).map((manager) => <option key={manager.id} value={manager.id}>{manager.name}</option>)}</select><button className="pa3-primary" disabled={!!busy || !choices[row.id]} onClick={() => void confirm(row,choices[row.id])}>Confirm</button></div></td></tr>)}</tbody></table></div></section>;
}

function AdminScoreBars({ score }: { score: ScoreSummary }) {
  return <div className="sa-score-bars">{Object.values(score.categories).map(item=><div key={item.key} className={item.completed?"complete":""}><span><strong>{item.label}</strong><b>{item.points}/{item.target}</b></span><i><em style={{width:`${Math.min(100,item.percent)}%`}}/></i></div>)}<footer><strong>Total {score.total}/1000</strong><span>{score.award?.is_winner ? `3% award: ${score.award.status}` : score.all_complete ? "All targets complete" : "In progress"}</span></footer></div>;
}

function GrowthIdeasAdmin({ rows, busy, error, approve, reject, refresh }: { rows: GrowthIdeaAdmin[]; busy: string; error: string; approve: (row: GrowthIdeaAdmin) => Promise<void>; reject: (row: GrowthIdeaAdmin) => Promise<void>; refresh: () => Promise<void> }) {
  const pending=rows.filter(row=>row.status==="PENDING");
  return <div className="sa-stack">{error&&<div className="pa3-error">{error}</div>}<section className="pa3-metric-grid pa3-metric-grid-small"><article><span><Lightbulb/></span><small>Pending ideas</small><strong>{pending.length}</strong></article><article><span><Check/></span><small>Approved</small><strong>{rows.filter(r=>r.status==="APPROVED").length}</strong></article><article><span><X/></span><small>Rejected</small><strong>{rows.filter(r=>r.status==="REJECTED").length}</strong></article></section><section className="pa3-panel"><div className="sa-toolbar"><div><small>SALES MANAGER IDEAS</small><h2>Product & growth proposals</h2><p>Approve only concrete contributions. Approval automatically adds 10 points to the manager's 130-point growth target.</p></div><button className="pa3-secondary" onClick={()=>void refresh()}><RefreshCw/> Refresh</button></div><div className="sa-idea-admin-list">{rows.map(row=><article key={row.id}><header><div><strong>{row.title}</strong><span>{row.manager_name} · {row.manager_email}</span></div><span className={`pa3-status pa3-status-${statusClass(row.status)}`}>{row.status}</span></header><p>{row.description}</p>{row.expected_impact&&<div><small>Expected impact</small><p>{row.expected_impact}</p></div>}<footer><span>{when(row.submitted_at)}</span>{row.admin_note&&<b>{row.admin_note}</b>}{row.status==="PENDING"&&<div className="sa-actions"><button className="pa3-primary" disabled={!!busy} onClick={()=>void approve(row)}><Check/> Approve +10</button><button className="pa3-danger" disabled={!!busy} onClick={()=>void reject(row)}><X/> Reject</button></div>}</footer></article>)}{!rows.length&&<div className="pa3-empty">No growth ideas submitted yet.</div>}</div></section></div>;
}

function EquityAwardView({ award, busy, error, confirm, refresh }: { award: EquityAwardAdmin | null; busy: string; error: string; confirm: (row: EquityAwardAdmin) => Promise<void>; refresh: () => Promise<void> }) {
  return <div className="sa-stack">{error&&<div className="pa3-error">{error}</div>}<section className="pa3-panel sa-equity-panel"><div className="sa-toolbar"><div><small>FIRST TO 1,000</small><h2>3% equity award review</h2><p>The platform records only the first manager to complete all three category targets. Legal ownership transfer remains subject to administrator confirmation and legal documentation.</p></div><button className="pa3-secondary" onClick={()=>void refresh()}><RefreshCw/> Refresh</button></div>{award?<div className="sa-equity-winner"><Trophy/><div><small>RECORDED WINNER</small><h3>{award.manager_name}</h3><p>{award.manager_email} · reached 1,000 points {when(award.reached_at)}</p><AdminScoreBars score={award.score}/><div className="sa-equity-status"><span>Equity award</span><strong>{award.equity_percent}%</strong><span>Status</span><strong>{award.status.replaceAll("_"," ")}</strong></div>{award.status!=="CONFIRMED"&&<button className="pa3-primary" disabled={!!busy} onClick={()=>void confirm(award)}><Check/> Confirm administrator review</button>}{award.admin_note&&<div className="pa3-note">{award.admin_note}</div>}</div></div>:<div className="pa3-empty"><Trophy/><span>No manager has completed all three targets yet.</span></div>}</section></div>;
}

function WithdrawalsView({ rows, busy, error, confirm, reject, refresh }: { rows: Withdrawal[]; busy: string; error: string; confirm: (row: Withdrawal) => Promise<void>; reject: (row: Withdrawal) => Promise<void>; refresh: () => Promise<void> }) {
  const pending = rows.filter((row) => row.status === "PENDING");
  return <div className="sa-stack">{error && <div className="pa3-error">{error}</div>}<section className="pa3-metric-grid pa3-metric-grid-small"><article><span><CreditCard/></span><small>Pending requests</small><strong>{pending.length}</strong></article><article><span><Check/></span><small>Paid requests</small><strong>{rows.filter((row) => row.status === "PAID").length}</strong></article><article><span><Clock3/></span><small>Total request history</small><strong>{rows.length}</strong></article></section><section className="pa3-panel"><div className="sa-toolbar"><div><small>MANUAL PAYOUT CONTROL</small><h2>Sales manager withdrawal requests</h2><p>Pay the displayed card manually, then enter the real payment reference before confirming.</p></div><button className="pa3-secondary" onClick={() => void refresh()}><RefreshCw/> Refresh</button></div><div className="pa3-table-wrap"><table className="pa3-table"><thead><tr><th>Manager</th><th>Amount</th><th>Payout card</th><th>Requested</th><th>Status</th><th>Admin action</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td><strong>{row.manager_name}</strong><small>{row.manager_email}</small></td><td><strong>{money(row.amount,row.currency)}</strong></td><td><strong>{row.card_number}</strong><small>{row.bank_account_holder || "Holder not recorded"}</small></td><td>{when(row.requested_at)}</td><td><span className={`pa3-status pa3-status-${statusClass(row.status)}`}>{row.status}</span>{row.paid_reference && <small>Ref {row.paid_reference}</small>}</td><td>{row.status === "PENDING" ? <div className="sa-actions"><button className="pa3-primary" disabled={!!busy} onClick={() => void confirm(row)}><Check/> Mark paid</button><button className="pa3-danger" disabled={!!busy} onClick={() => void reject(row)}><X/> Reject</button></div> : <small>{row.admin_note || "Finalized"}</small>}</td></tr>)}</tbody></table>{!rows.length && <div className="pa3-empty">No withdrawal requests yet.</div>}</div></section></div>;
}

function Modal({ title, close, children }: { title: string; close: () => void; children: React.ReactNode }) {
  return <div className="pa3-modal-layer" onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}><section className="pa3-modal sa-modal"><header><h2>{title}</h2><button onClick={close}><X/></button></header>{children}</section></div>;
}

function Info({ title, value }: { title: string; value: string }) {
  return <div className="pa3-info"><small>{title}</small><strong>{value}</strong></div>;
}

function Loading() {
  return <div className="pa3-loading"><RefreshCw className="spin"/> Loading manager activity…</div>;
}
