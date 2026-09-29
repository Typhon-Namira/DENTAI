import {
  Banknote,
  Check,
  CircleDollarSign,
  Eye,
  Mail,
  Pencil,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Trash2,
  Upload,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { API_BASE_URL } from "../api/client";
import "./sales-admin-operations.css";

type Manager = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  title: string;
  phone?: string | null;
  territory?: string | null;
  bio?: string | null;
  is_active: boolean;
  public_verified: boolean;
  commission_rate_bps: number;
  bank_card_last4?: string | null;
  bank_card_holder?: string | null;
  last_login_at?: string | null;
  created_at: string;
  activity_count: number;
  report_count: number;
  available_balance: Record<string, number>;
  photo_available: boolean;
};

type Withdrawal = {
  id: string;
  manager_id: string;
  manager_name: string;
  currency: string;
  amount: number;
  status: string;
  bank_card_last4: string;
  bank_card_holder?: string | null;
  requested_at: string;
  processed_at?: string | null;
  payment_reference?: string | null;
  admin_note?: string | null;
};

type Attribution = {
  id: string;
  manager_id: string;
  manager_name: string;
  clinic_id: string;
  access_request_id?: string | null;
  clinic_contact_id?: string | null;
  reported_clinic_name?: string | null;
  match_score: number;
  matched_signals: Record<string, boolean>;
  status: string;
  attributed_at: string;
};

type ManagerDetail = {
  manager: Manager;
  dashboard: {
    metrics: Record<string, number>;
    available_balance: Record<string, number>;
    commissions: Array<Record<string, unknown>>;
    withdrawals: Withdrawal[];
  };
  reports: Array<{
    id: string;
    report_date: string;
    summary?: string | null;
    contacts: Array<{
      id: string;
      clinic_name: string;
      city?: string | null;
      country?: string | null;
      contact_name?: string | null;
      email?: string | null;
      phone?: string | null;
      outcome: string;
      negotiation_result: string;
      next_step?: string | null;
    }>;
  }>;
  activities: Array<{
    id: string;
    action: string;
    details: Record<string, unknown>;
    ip_address?: string | null;
    created_at: string;
  }>;
  sessions: Array<{
    id: string;
    ip_address?: string | null;
    user_agent?: string | null;
    login_at: string;
    last_seen_at: string;
    expires_at: string;
    logout_at?: string | null;
    logout_reason?: string | null;
  }>;
};

type View = "managers" | "withdrawals" | "attributions";

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

async function json<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
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

function dateTime(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

function money(value: number, currency: string) {
  return `${Number(value || 0).toLocaleString("en-US")} ${currency}`;
}

function Status({ value }: { value: string }) {
  return <span className={`sao-status sao-status-${value.toLowerCase()}`}>{value.replaceAll("_", " ")}</span>;
}

export function SalesAdminOperations({ token }: { token: string }) {
  const [view, setView] = useState<View>("managers");
  const [managers, setManagers] = useState<Manager[]>([]);
  const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
  const [attributions, setAttributions] = useState<Attribution[]>([]);
  const [selected, setSelected] = useState<ManagerDetail | null>(null);
  const [editing, setEditing] = useState<Manager | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    const [nextManagers, nextWithdrawals, nextAttributions] = await Promise.all([
      json<Manager[]>("/api/v1/platform/sales/admin/managers", token),
      json<Withdrawal[]>("/api/v1/platform/sales/admin/withdrawals", token),
      json<Attribution[]>("/api/v1/platform/sales/admin/attributions", token),
    ]);
    setManagers(nextManagers);
    setWithdrawals(nextWithdrawals);
    setAttributions(nextAttributions);
    setError("");
  }, [token]);

  useEffect(() => {
    void load().catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load sales operations"));
  }, [load]);

  const pendingWithdrawals = useMemo(() => withdrawals.filter((row) => row.status === "REQUESTED"), [withdrawals]);
  const pendingAttributions = useMemo(() => attributions.filter((row) => row.status === "REVIEW_REQUIRED"), [attributions]);

  async function openManager(manager: Manager) {
    setBusy(`detail-${manager.id}`);
    try {
      setSelected(await json<ManagerDetail>(`/api/v1/platform/sales/admin/managers/${manager.id}/detail`, token));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load manager detail");
    } finally {
      setBusy("");
    }
  }

  async function mutate(path: string, init: RequestInit) {
    setBusy(path);
    setError("");
    try {
      const result = await json(path, token, init);
      await load();
      return result;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Administrative action failed");
      throw reason;
    } finally {
      setBusy("");
    }
  }

  return <div className="sao-root">
    <header className="sao-toolbar">
      <div><small>SALES OPERATIONS</small><h2>Sales management</h2></div>
      <div className="sao-toolbar-actions">
        <button className={view === "managers" ? "active" : ""} onClick={() => setView("managers")}><UsersRound /> Managers <b>{managers.length}</b></button>
        <button className={view === "withdrawals" ? "active" : ""} onClick={() => setView("withdrawals")}><Banknote /> Payout requests <b>{pendingWithdrawals.length}</b></button>
        <button className={view === "attributions" ? "active" : ""} onClick={() => setView("attributions")}><ShieldCheck /> Attribution review <b>{pendingAttributions.length}</b></button>
        <button title="Refresh" onClick={() => void load()}><RefreshCw /></button>
      </div>
    </header>
    {error && <div className="sao-error">{error}<button onClick={() => setError("")}><X /></button></div>}

    {view === "managers" && <section className="sao-panel">
      <div className="sao-panel-head"><div><small>VERIFIED SALES TEAM</small><h3>Manager accounts</h3></div><button className="sao-primary" onClick={() => setCreating(true)}><Plus /> Add sales manager</button></div>
      <div className="sao-table-wrap"><table><thead><tr><th>Manager</th><th>Territory</th><th>Reports</th><th>Activity</th><th>Available earnings</th><th>Last login</th><th>Public</th><th /></tr></thead><tbody>{managers.map((manager) => <tr key={manager.id}><td><strong>{manager.full_name}</strong><small>@{manager.username} · {manager.email}</small></td><td>{manager.territory || "—"}</td><td>{manager.report_count}</td><td>{manager.activity_count}</td><td>{Object.entries(manager.available_balance).length ? Object.entries(manager.available_balance).map(([currency, amount]) => <span key={currency} className="sao-money">{money(amount, currency)}</span>) : "—"}</td><td>{dateTime(manager.last_login_at)}</td><td><Status value={manager.public_verified && manager.is_active ? "VERIFIED" : "HIDDEN"} /></td><td><button className="sao-icon" title="Open manager" disabled={!!busy} onClick={() => void openManager(manager)}><Eye /></button><button className="sao-icon" title="Edit manager" onClick={() => setEditing(manager)}><Pencil /></button></td></tr>)}</tbody></table></div>
    </section>}

    {view === "withdrawals" && <section className="sao-panel">
      <div className="sao-panel-head"><div><small>MANUAL PAYOUT QUEUE</small><h3>Withdrawal requests</h3></div></div>
      <div className="sao-table-wrap"><table><thead><tr><th>Manager</th><th>Requested</th><th>Amount</th><th>Destination</th><th>Status</th><th>Reference</th><th>Actions</th></tr></thead><tbody>{withdrawals.map((row) => <tr key={row.id}><td><strong>{row.manager_name}</strong></td><td>{dateTime(row.requested_at)}</td><td><strong>{money(row.amount, row.currency)}</strong></td><td>•••• {row.bank_card_last4}<small>{row.bank_card_holder || ""}</small></td><td><Status value={row.status} /></td><td>{row.payment_reference || "—"}</td><td>{row.status === "REQUESTED" ? <div className="sao-actions"><button className="sao-primary" onClick={async () => { try { const destination = await json<{card_number:string;holder_name?:string|null}>(`/api/v1/platform/sales/admin/withdrawals/${row.id}/destination`, token); const reference = window.prompt(`Pay ${money(row.amount,row.currency)} to ${destination.card_number}${destination.holder_name ? ` · ${destination.holder_name}` : ""}. Enter transfer reference after payment:`); if (!reference?.trim()) return; await mutate(`/api/v1/platform/sales/admin/withdrawals/${row.id}/pay`, { method:"POST", body:JSON.stringify({ payment_reference:reference.trim(), admin_note:"Paid manually from Teta2 admin control center" }) }); } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not process payout"); } }}><Check /> Pay & confirm</button><button className="sao-danger" onClick={() => { const note = window.prompt("Reason for rejection") ?? ""; if (window.confirm(`Reject payout for ${row.manager_name}?`)) void mutate(`/api/v1/platform/sales/admin/withdrawals/${row.id}/reject`, {method:"POST",body:JSON.stringify({admin_note:note})}); }}><X /> Reject</button></div> : "—"}</td></tr>)}</tbody></table></div>
    </section>}

    {view === "attributions" && <section className="sao-panel">
      <div className="sao-panel-head"><div><small>REPORT-BASED MATCHING</small><h3>Clinic attribution decisions</h3></div></div>
      <div className="sao-table-wrap"><table><thead><tr><th>Reported clinic</th><th>Suggested manager</th><th>Score</th><th>Signals</th><th>Status</th><th>Action</th></tr></thead><tbody>{attributions.map((row) => <tr key={row.id}><td><strong>{row.reported_clinic_name || row.clinic_id}</strong><small>{row.clinic_id}</small></td><td>{row.manager_name}</td><td>{row.match_score}</td><td>{Object.entries(row.matched_signals).filter(([,matched]) => matched).map(([name]) => name).join(", ") || "—"}</td><td><Status value={row.status} /></td><td>{row.status === "REVIEW_REQUIRED" ? <button className="sao-primary" onClick={() => { if (window.confirm(`Confirm attribution to ${row.manager_name}?`)) void mutate(`/api/v1/platform/sales/admin/attributions/${row.id}/confirm`, {method:"POST",body:JSON.stringify({manager_id:row.manager_id,clinic_contact_id:row.clinic_contact_id})}); }}><Check /> Confirm match</button> : "—"}</td></tr>)}</tbody></table></div>
    </section>}

    {selected && <ManagerDrawer detail={selected} token={token} close={() => setSelected(null)} onEdit={() => setEditing(selected.manager)} onRefresh={async () => { const next = await json<ManagerDetail>(`/api/v1/platform/sales/admin/managers/${selected.manager.id}/detail`, token); setSelected(next); }} mutate={mutate} />}
    {creating && <ManagerForm token={token} close={() => setCreating(false)} onSaved={async () => { setCreating(false); await load(); }} />}
    {editing && <ManagerForm token={token} manager={editing} close={() => setEditing(null)} onSaved={async () => { setEditing(null); setSelected(null); await load(); }} />}
  </div>;
}

function ManagerForm({ token, manager, close, onSaved }: { token: string; manager?: Manager; close: () => void; onSaved: () => Promise<void> }) {
  const [form, setForm] = useState({
    full_name: manager?.full_name || "",
    email: manager?.email || "",
    title: manager?.title || "Sales Manager",
    phone: manager?.phone || "",
    territory: manager?.territory || "",
    bio: manager?.bio || "",
    is_active: manager?.is_active ?? true,
    public_verified: manager?.public_verified ?? true,
  });
  const [photo, setPhoto] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const update = (key: keyof typeof form, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  async function save() {
    setBusy(true); setError("");
    try {
      const response = await fetch(apiUrl(manager ? `/api/v1/platform/sales/admin/managers/${manager.id}` : "/api/v1/platform/sales/admin/managers"), {
        method: manager ? "PATCH" : "POST",
        headers: { "content-type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          full_name: form.full_name,
          email: form.email,
          title: form.title,
          phone: form.phone || null,
          territory: form.territory || null,
          bio: form.bio || null,
          ...(manager ? { is_active: form.is_active } : {}),
          public_verified: form.public_verified,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.error?.message || body?.detail || "Could not save manager");
      const saved = body as Manager;
      if (photo) {
        const data = new FormData();
        data.append("file", photo);
        const photoResponse = await fetch(apiUrl(`/api/v1/platform/sales/admin/managers/${saved.id}/photo`), {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: data,
        });
        const photoBody = await photoResponse.json().catch(() => ({}));
        if (!photoResponse.ok) throw new Error(photoBody?.error?.message || photoBody?.detail || "Manager saved, but photo upload failed");
      }
      await onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save manager");
    } finally { setBusy(false); }
  }

  return <div className="sao-modal-layer" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><section className="sao-modal"><header><div><small>{manager ? "EDIT SALES MANAGER" : "NEW SALES MANAGER"}</small><h3>{manager ? manager.full_name : "Create verified manager"}</h3></div><button onClick={close}><X /></button></header><div className="sao-form-grid"><label>Full name<input value={form.full_name} onChange={(event) => update("full_name",event.target.value)} /></label><label>Email<input type="email" value={form.email} onChange={(event) => update("email",event.target.value)} /></label><label>Title<input value={form.title} onChange={(event) => update("title",event.target.value)} /></label><label>Phone<input value={form.phone} onChange={(event) => update("phone",event.target.value)} /></label><label>Territory<input value={form.territory} onChange={(event) => update("territory",event.target.value)} /></label><label>Manager photo<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setPhoto(event.target.files?.[0] || null)} /></label><label className="wide">Public bio<textarea rows={4} value={form.bio} onChange={(event) => update("bio",event.target.value)} /></label>{manager && <label className="check"><input type="checkbox" checked={form.is_active} onChange={(event) => update("is_active",event.target.checked)} /> Account active</label>}<label className="check"><input type="checkbox" checked={form.public_verified} onChange={(event) => update("public_verified",event.target.checked)} /> Show as verified manager on About page</label></div>{error && <div className="sao-error">{error}</div>}<button className="sao-primary sao-wide" disabled={busy || !form.full_name.trim() || !form.email.trim()} onClick={() => void save()}>{busy ? "Saving…" : manager ? "Save manager" : <><Mail /> Create account & email credentials</>}</button></section></div>;
}

function ManagerDrawer({ detail, token, close, onEdit, onRefresh, mutate }: { detail: ManagerDetail; token: string; close: () => void; onEdit: () => void; onRefresh: () => Promise<void>; mutate: (path:string,init:RequestInit)=>Promise<unknown> }) {
  const manager = detail.manager;
  return <div className="sao-drawer-layer" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><aside className="sao-drawer"><header><div><small>SALES MANAGER CONTROL</small><h2>{manager.full_name}</h2><p>@{manager.username} · {manager.email}</p></div><button onClick={close}><X /></button></header><div className="sao-drawer-actions"><button onClick={onEdit}><Pencil /> Edit</button><button onClick={async () => { if (window.confirm(`Reset password for ${manager.full_name} and email new credentials?`)) { await mutate(`/api/v1/platform/sales/admin/managers/${manager.id}/reset-password`,{method:"POST",body:"{}"}); await onRefresh(); } }}><RotateCcw /> Reset password</button><button className="danger" onClick={async () => { if (window.confirm(`Disable and remove ${manager.full_name} from verified managers? History will be preserved.`)) { await mutate(`/api/v1/platform/sales/admin/managers/${manager.id}`,{method:"DELETE"}); close(); } }}><Trash2 /> Remove manager</button></div><section><h3>Account & performance</h3><div className="sao-info-grid"><Info label="Status" value={manager.is_active ? "ACTIVE" : "DISABLED"} /><Info label="Public profile" value={manager.public_verified ? "VERIFIED" : "HIDDEN"} /><Info label="Reports" value={String(detail.dashboard.metrics.reports || 0)} /><Info label="Clinics contacted" value={String(detail.dashboard.metrics.clinic_contacts || 0)} /><Info label="Attributed clinics" value={String(detail.dashboard.metrics.attributed_clinics || 0)} /><Info label="Last login" value={dateTime(manager.last_login_at)} /></div></section><section><h3>Login / logout history</h3><div className="sao-event-list">{detail.sessions.map((row) => <article key={row.id}><div><strong>{dateTime(row.login_at)}</strong><small>{row.ip_address || "IP unavailable"}</small></div><span>{row.logout_at ? `Signed out ${dateTime(row.logout_at)}` : "Session active"}{row.logout_reason ? ` · ${row.logout_reason}` : ""}</span></article>)}</div></section><section><h3>Complete tracked activity</h3><div className="sao-event-list">{detail.activities.map((row) => <article key={row.id}><div><strong>{row.action.replaceAll("_"," ")}</strong><small>{dateTime(row.created_at)} · {row.ip_address || "IP unavailable"}</small></div><code>{JSON.stringify(row.details)}</code></article>)}</div></section><section><h3>Daily reports</h3><div className="sao-report-list">{detail.reports.map((report) => <article key={report.id}><strong>{report.report_date}</strong><small>{report.contacts.length} clinic(s)</small>{report.contacts.map((contact) => <div key={contact.id}><b>{contact.clinic_name}</b><span>{contact.outcome}</span><p>{contact.negotiation_result}</p></div>)}</article>)}</div></section></aside></div>;
}

function Info({ label, value }: { label:string; value:string }) {
  return <div><small>{label}</small><strong>{value}</strong></div>;
}
