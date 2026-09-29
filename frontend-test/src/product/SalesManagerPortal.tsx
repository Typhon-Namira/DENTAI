import {
  Activity,
  Banknote,
  Building2,
  Check,
  ClipboardList,
  CreditCard,
  History,
  LogOut,
  Plus,
  RefreshCw,
  Save,
  Send,
  ShieldCheck,
  Trash2,
  UserRound,
  WalletCards,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { API_BASE_URL } from "../api/client";
import "./sales-manager-portal.css";

const SESSION_KEY = "teta2-sales-manager-session";

type ManagerProfile = {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  name: string;
  title: string;
  phone?: string | null;
  must_change_password: boolean;
  bank_card_last4?: string | null;
  bank_account_holder?: string | null;
  last_login_at?: string | null;
  photo_url?: string | null;
};

type Balance = {
  currency: string;
  earned: number;
  pending_withdrawal: number;
  paid_out: number;
  available: number;
};

type Commission = {
  id: string;
  clinic_id: string;
  gross_amount: number;
  commission_rate_percent: number;
  commission_amount: number;
  currency: string;
  status: string;
  created_at: string;
};

type Withdrawal = {
  id: string;
  amount: number;
  currency: string;
  status: string;
  bank_card_last4: string;
  requested_at: string;
  reviewed_at?: string | null;
  paid_at?: string | null;
  paid_reference?: string | null;
  admin_note?: string | null;
};

type Dashboard = {
  manager: ManagerProfile;
  summary: {
    submitted_reports: number;
    reported_clinics: number;
    commission_events: number;
    today_report_status: string;
  };
  balances: Balance[];
  recent_commissions: Commission[];
  withdrawals: Withdrawal[];
};

type ReportClinic = {
  id?: string;
  clinic_name: string;
  country: string;
  city: string;
  address: string;
  website: string;
  contact_name: string;
  contact_role: string;
  email: string;
  phone: string;
  negotiation_result: string;
  outcome_status: string;
  next_step: string;
  notes: string;
  contacted_at?: string;
};

type DailyReport = {
  id: string;
  report_date: string;
  status: string;
  summary?: string | null;
  submitted_at?: string | null;
  clinics: ReportClinic[];
};

type Tab = "overview" | "report" | "history" | "earnings" | "payout";

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
  if (!response.ok) throw new Error(body?.error?.message || body?.detail || "Request failed");
  return body as T;
}

function money(value: number, currency: string) {
  return `${Number(value || 0).toLocaleString("en-US")} ${currency}`;
}

function stamp(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString("en-US");
}

function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function emptyClinic(): ReportClinic {
  return {
    clinic_name: "",
    country: "",
    city: "",
    address: "",
    website: "",
    contact_name: "",
    contact_role: "",
    email: "",
    phone: "",
    negotiation_result: "",
    outcome_status: "CONTACTED",
    next_step: "",
    notes: "",
  };
}

export function SalesManagerPortal() {
  const [route, setRoute] = useState(window.location.pathname);
  const active = route === "/platform-managers";
  const [token, setToken] = useState(() => sessionStorage.getItem(SESSION_KEY) || "");
  const [profile, setProfile] = useState<ManagerProfile | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [reports, setReports] = useState<DailyReport[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const listener = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", listener);
    return () => window.removeEventListener("popstate", listener);
  }, []);

  useEffect(() => {
    if (!active) return;
    const oldLang = document.documentElement.lang;
    document.documentElement.lang = "en";
    document.body.classList.add("sm-active");
    return () => {
      document.documentElement.lang = oldLang;
      document.body.classList.remove("sm-active");
    };
  }, [active]);

  const load = useCallback(async (sessionToken: string) => {
    const [me, nextDashboard, nextReports] = await Promise.all([
      requestJson<ManagerProfile>("/api/v1/platform/sales-managers/me", sessionToken),
      requestJson<Dashboard>("/api/v1/platform/sales-managers/dashboard", sessionToken),
      requestJson<DailyReport[]>("/api/v1/platform/sales-managers/reports", sessionToken),
    ]);
    setProfile(me);
    setDashboard(nextDashboard);
    setReports(nextReports);
    setError("");
  }, []);

  useEffect(() => {
    if (!active || !token || profile) return;
    void load(token).catch(() => {
      sessionStorage.removeItem(SESSION_KEY);
      setToken("");
      setProfile(null);
    });
  }, [active, token, profile, load]);

  if (!active) return null;

  if (!token || !profile) {
    return <ManagerLogin onAuthenticated={(sessionToken, manager) => {
      sessionStorage.setItem(SESSION_KEY, sessionToken);
      setToken(sessionToken);
      setProfile(manager);
      void load(sessionToken);
    }} />;
  }

  async function logout() {
    try {
      await requestJson("/api/v1/platform/sales-managers/logout", token, { method: "POST" });
    } catch {
      // The local session must still be removed if the server session already expired.
    }
    sessionStorage.removeItem(SESSION_KEY);
    setToken("");
    setProfile(null);
    setDashboard(null);
    setReports([]);
  }

  async function reload() {
    setBusy(true);
    try {
      await load(token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not refresh manager data");
    } finally {
      setBusy(false);
    }
  }

  if (profile.must_change_password) {
    return <ForcedPasswordChange token={token} profile={profile} onDone={() => {
      sessionStorage.removeItem(SESSION_KEY);
      setToken("");
      setProfile(null);
    }} />;
  }

  const nav: Array<[Tab, string, typeof Activity]> = [
    ["overview", "Overview", Activity],
    ["report", "Daily report", ClipboardList],
    ["history", "Activity history", History],
    ["earnings", "Commissions", Banknote],
    ["payout", "Payouts", WalletCards],
  ];

  return <main className="sm-root">
    <aside className="sm-sidebar">
      <div className="sm-brand"><strong>Teta2</strong><span>SALES</span></div>
      <div className="sm-person">{profile.photo_url ? <img src={`${API_BASE_URL}${profile.photo_url}`} alt={profile.name}/> : <span>{profile.first_name[0]}{profile.last_name[0]}</span>}<div><strong>{profile.name}</strong><small>{profile.title}</small></div></div>
      <nav>{nav.map(([id, title, Icon]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon/><span>{title}</span></button>)}</nav>
      <div className="sm-side-bottom"><button onClick={() => void logout()}><LogOut/> Sign out</button></div>
    </aside>
    <section className="sm-main">
      <header className="sm-topbar"><div><small>SALES MANAGER WORKSPACE</small><h1>{nav.find(([id]) => id === tab)?.[1]}</h1></div><button title="Refresh" onClick={() => void reload()} disabled={busy}><RefreshCw className={busy ? "spin" : ""}/></button></header>
      {error && <div className="sm-error">{error}<button onClick={() => setError("")}><X/></button></div>}
      {tab === "overview" && <Overview dashboard={dashboard} setTab={setTab}/>}
      {tab === "report" && <ReportEditor token={token} reports={reports} onSaved={reload}/>}
      {tab === "history" && <ReportHistory reports={reports}/>}
      {tab === "earnings" && <Earnings dashboard={dashboard}/>}
      {tab === "payout" && <Payouts token={token} dashboard={dashboard} profile={profile} onSaved={reload}/>}
    </section>
  </main>;
}

function ManagerLogin({ onAuthenticated }: { onAuthenticated: (token: string, manager: ManagerProfile) => void }) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await requestJson<{ access_token: string; manager: ManagerProfile }>("/api/v1/platform/sales-managers/login", undefined, {
        method: "POST",
        body: JSON.stringify({ identifier: identifier.trim(), password }),
      });
      onAuthenticated(result.access_token, result.manager);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return <main className="sm-login-root"><section className="sm-login-card">
    <div className="sm-login-mark"><ShieldCheck/><span>VERIFIED SALES OPERATIONS</span></div>
    <div className="sm-login-wordmark">Teta2 <small>SALES</small></div>
    <h1>Sales Manager Portal</h1>
    <p>Use the credentials issued by Teta2 platform administration.</p>
    <form onSubmit={submit}>
      <label>Email or username<input required autoComplete="username" value={identifier} onChange={(event) => setIdentifier(event.target.value)} autoFocus/></label>
      <label>Password<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)}/></label>
      {error && <div className="sm-error">{error}</div>}
      <button className="sm-primary" disabled={busy}>{busy ? "Signing in…" : "Sign in securely"}</button>
    </form>
  </section></main>;
}

function ForcedPasswordChange({ token, profile, onDone }: { token: string; profile: ManagerProfile; onDone: () => void }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (next !== confirm) {
      setError("New passwords do not match.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await requestJson("/api/v1/platform/sales-managers/password", token, {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      onDone();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Password change failed");
    } finally {
      setBusy(false);
    }
  }

  return <main className="sm-login-root"><section className="sm-login-card"><div className="sm-login-mark"><ShieldCheck/><span>FIRST SIGN-IN SECURITY</span></div><h1>Set your private password</h1><p>Hello {profile.first_name}. Replace the temporary password before opening the sales workspace.</p><form onSubmit={submit}><label>Temporary password<input type="password" required value={current} onChange={(e) => setCurrent(e.target.value)}/></label><label>New password<input type="password" minLength={10} required value={next} onChange={(e) => setNext(e.target.value)}/></label><label>Confirm new password<input type="password" minLength={10} required value={confirm} onChange={(e) => setConfirm(e.target.value)}/></label>{error && <div className="sm-error">{error}</div>}<button className="sm-primary" disabled={busy}>{busy ? "Updating…" : "Set password & sign in again"}</button></form></section></main>;
}

function Overview({ dashboard, setTab }: { dashboard: Dashboard | null; setTab: (tab: Tab) => void }) {
  if (!dashboard) return <Loading/>;
  const cards = [
    ["Reports submitted", dashboard.summary.submitted_reports, ClipboardList],
    ["Clinics reported", dashboard.summary.reported_clinics, Building2],
    ["Commission events", dashboard.summary.commission_events, Banknote],
    ["Today's report", dashboard.summary.today_report_status.replaceAll("_", " "), Check],
  ] as const;
  return <div className="sm-stack">
    <section className="sm-metrics">{cards.map(([title, value, Icon]) => <article key={title}><Icon/><small>{title}</small><strong>{value}</strong></article>)}</section>
    <section className="sm-panel"><div className="sm-panel-head"><div><small>AVAILABLE TO WITHDRAW</small><h2>Commission balance</h2></div><button className="sm-secondary" onClick={() => setTab("payout")}>Open payouts</button></div><div className="sm-balance-grid">{dashboard.balances.length ? dashboard.balances.map((balance) => <article key={balance.currency}><span>{balance.currency}</span><strong>{money(balance.available, balance.currency)}</strong><small>Earned {money(balance.earned, balance.currency)} · Paid {money(balance.paid_out, balance.currency)}</small></article>) : <p className="sm-muted">No verified commission has been credited yet.</p>}</div></section>
    <section className="sm-panel"><div className="sm-panel-head"><div><small>DAILY DISCIPLINE</small><h2>Today's clinic report</h2></div><button className="sm-primary" onClick={() => setTab("report")}><ClipboardList/> {dashboard.summary.today_report_status === "SUBMITTED" ? "View report" : "Complete report"}</button></div><p className="sm-muted">Record every clinic conversation, the negotiation result and the next step. Submitted reports are preserved as the attribution record.</p></section>
  </div>;
}

function ReportEditor({ token, reports, onSaved }: { token: string; reports: DailyReport[]; onSaved: () => Promise<void> }) {
  const date = todayIso();
  const existing = reports.find((report) => report.report_date === date);
  const [summary, setSummary] = useState(existing?.summary || "");
  const [clinics, setClinics] = useState<ReportClinic[]>(existing?.clinics?.length ? existing.clinics.map((row) => ({ ...emptyClinic(), ...row })) : [emptyClinic()]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const locked = existing?.status === "SUBMITTED";

  useEffect(() => {
    const row = reports.find((report) => report.report_date === date);
    setSummary(row?.summary || "");
    setClinics(row?.clinics?.length ? row.clinics.map((item) => ({ ...emptyClinic(), ...item })) : [emptyClinic()]);
  }, [reports, date]);

  function update(index: number, key: keyof ReportClinic, value: string) {
    setClinics((current) => current.map((row, position) => position === index ? { ...row, [key]: value } : row));
  }

  async function save(submit: boolean) {
    setBusy(true);
    setMessage("");
    try {
      await requestJson(`/api/v1/platform/sales-managers/reports/${date}`, token, {
        method: "PUT",
        body: JSON.stringify({
          summary,
          submit,
          clinics: clinics.map((row) => ({
            clinic_name: row.clinic_name,
            country: row.country,
            city: row.city,
            address: row.address || null,
            website: row.website || null,
            contact_name: row.contact_name || null,
            contact_role: row.contact_role || null,
            email: row.email || null,
            phone: row.phone || null,
            negotiation_result: row.negotiation_result,
            outcome_status: row.outcome_status,
            next_step: row.next_step || null,
            notes: row.notes || null,
          })),
        }),
      });
      setMessage(submit ? "Daily report submitted and locked." : "Draft saved.");
      await onSaved();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Could not save report");
    } finally {
      setBusy(false);
    }
  }

  if (locked) return <section className="sm-panel"><div className="sm-success"><Check/> Today's report has been submitted and is now part of your permanent activity history.</div><ReportDetail report={existing!}/></section>;

  return <div className="sm-stack"><section className="sm-panel"><div className="sm-panel-head"><div><small>{date}</small><h2>Daily sales report</h2></div><span className="sm-pill">DRAFT</span></div><label className="sm-field">Day summary<textarea rows={3} value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Short overall summary, priorities and follow-ups."/></label></section>
    {clinics.map((clinic, index) => <section className="sm-panel sm-clinic-entry" key={index}><div className="sm-panel-head"><div><small>CLINIC {String(index + 1).padStart(2, "0")}</small><h2>{clinic.clinic_name || "New clinic conversation"}</h2></div>{clinics.length > 1 && <button className="sm-icon-danger" onClick={() => setClinics((rows) => rows.filter((_, i) => i !== index))}><Trash2/></button>}</div><div className="sm-form-grid">
      <label className="sm-field">Clinic name<input required value={clinic.clinic_name} onChange={(e) => update(index, "clinic_name", e.target.value)}/></label>
      <label className="sm-field">Country<input required value={clinic.country} onChange={(e) => update(index, "country", e.target.value)}/></label>
      <label className="sm-field">City<input required value={clinic.city} onChange={(e) => update(index, "city", e.target.value)}/></label>
      <label className="sm-field">Address<input value={clinic.address} onChange={(e) => update(index, "address", e.target.value)}/></label>
      <label className="sm-field">Clinic website<input value={clinic.website} onChange={(e) => update(index, "website", e.target.value)} placeholder="https://…"/></label>
      <label className="sm-field">Contact name<input value={clinic.contact_name} onChange={(e) => update(index, "contact_name", e.target.value)}/></label>
      <label className="sm-field">Contact role<input value={clinic.contact_role} onChange={(e) => update(index, "contact_role", e.target.value)} placeholder="Director, owner, dentist…"/></label>
      <label className="sm-field">Email<input type="email" value={clinic.email} onChange={(e) => update(index, "email", e.target.value)}/></label>
      <label className="sm-field">Phone<input value={clinic.phone} onChange={(e) => update(index, "phone", e.target.value)}/></label>
      <label className="sm-field">Outcome<select value={clinic.outcome_status} onChange={(e) => update(index, "outcome_status", e.target.value)}><option>CONTACTED</option><option>INTERESTED</option><option>FOLLOW_UP</option><option>PAYMENT_EXPECTED</option><option>NOT_INTERESTED</option><option>NO_RESPONSE</option></select></label>
      <label className="sm-field wide">Negotiation result<textarea rows={3} required value={clinic.negotiation_result} onChange={(e) => update(index, "negotiation_result", e.target.value)} placeholder="What was discussed, what did the clinic decide, objections, price discussion, decision maker response…"/></label>
      <label className="sm-field wide">Next step<textarea rows={2} value={clinic.next_step} onChange={(e) => update(index, "next_step", e.target.value)} placeholder="Call again, send materials, payment expected, meeting date…"/></label>
      <label className="sm-field wide">Internal notes<textarea rows={2} value={clinic.notes} onChange={(e) => update(index, "notes", e.target.value)}/></label>
    </div></section>)}
    <div className="sm-report-actions"><button className="sm-secondary" onClick={() => setClinics((rows) => [...rows, emptyClinic()])}><Plus/> Add clinic</button><span>{message}</span><button className="sm-secondary" disabled={busy} onClick={() => void save(false)}><Save/> Save draft</button><button className="sm-primary" disabled={busy} onClick={() => void save(true)}><Send/> Submit daily report</button></div>
  </div>;
}

function ReportHistory({ reports }: { reports: DailyReport[] }) {
  const [selected, setSelected] = useState<DailyReport | null>(reports[0] || null);
  useEffect(() => setSelected((current) => current || reports[0] || null), [reports]);
  return <div className="sm-history-layout"><section className="sm-panel sm-history-list"><div className="sm-panel-head"><div><small>PERMANENT RECORD</small><h2>Daily reports</h2></div><b>{reports.length}</b></div>{reports.map((report) => <button className={selected?.id === report.id ? "active" : ""} key={report.id} onClick={() => setSelected(report)}><strong>{report.report_date}</strong><span>{report.clinics.length} clinic(s)</span><small>{report.status}</small></button>)}{!reports.length && <p className="sm-muted">No reports yet.</p>}</section><section className="sm-panel">{selected ? <ReportDetail report={selected}/> : <p className="sm-muted">Select a report.</p>}</section></div>;
}

function ReportDetail({ report }: { report: DailyReport }) {
  return <div className="sm-report-detail"><div className="sm-panel-head"><div><small>{report.report_date}</small><h2>{report.status}</h2></div><span>{report.submitted_at ? stamp(report.submitted_at) : "Draft"}</span></div>{report.summary && <div className="sm-note"><strong>Summary</strong><p>{report.summary}</p></div>}<div className="sm-report-clinics">{report.clinics.map((clinic) => <article key={clinic.id || `${clinic.clinic_name}-${clinic.contact_name}`}><div><strong>{clinic.clinic_name}</strong><span>{clinic.city}, {clinic.country}</span><small>{clinic.outcome_status.replaceAll("_", " ")}</small></div><p>{clinic.negotiation_result}</p><dl><div><dt>Contact</dt><dd>{clinic.contact_name || "—"} {clinic.contact_role ? `· ${clinic.contact_role}` : ""}</dd></div><div><dt>Email / phone</dt><dd>{clinic.email || "—"} · {clinic.phone || "—"}</dd></div><div><dt>Website</dt><dd>{clinic.website || "—"}</dd></div><div><dt>Next step</dt><dd>{clinic.next_step || "—"}</dd></div></dl></article>)}</div></div>;
}

function Earnings({ dashboard }: { dashboard: Dashboard | null }) {
  if (!dashboard) return <Loading/>;
  return <div className="sm-stack"><section className="sm-balance-grid">{dashboard.balances.map((balance) => <article key={balance.currency}><span>{balance.currency}</span><strong>{money(balance.available, balance.currency)}</strong><small>Available now</small><dl><div><dt>Total earned</dt><dd>{money(balance.earned, balance.currency)}</dd></div><div><dt>Pending payout</dt><dd>{money(balance.pending_withdrawal, balance.currency)}</dd></div><div><dt>Paid out</dt><dd>{money(balance.paid_out, balance.currency)}</dd></div></dl></article>)}</section><section className="sm-panel"><div className="sm-panel-head"><div><small>30% VERIFIED SUBSCRIPTION COMMISSION</small><h2>Commission ledger</h2></div></div><div className="sm-table-wrap"><table><thead><tr><th>Date</th><th>Subscription</th><th>Rate</th><th>Your commission</th><th>Status</th></tr></thead><tbody>{dashboard.recent_commissions.map((row) => <tr key={row.id}><td>{stamp(row.created_at)}</td><td>{money(row.gross_amount, row.currency)}</td><td>{row.commission_rate_percent}%</td><td><strong>{money(row.commission_amount, row.currency)}</strong></td><td>{row.status}</td></tr>)}</tbody></table>{!dashboard.recent_commissions.length && <p className="sm-muted">No verified subscription commission yet.</p>}</div></section></div>;
}

function Payouts({ token, dashboard, profile, onSaved }: { token: string; dashboard: Dashboard | null; profile: ManagerProfile; onSaved: () => Promise<void> }) {
  const [card, setCard] = useState("");
  const [holder, setHolder] = useState(profile.bank_account_holder || "");
  const [amounts, setAmounts] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  if (!dashboard) return <Loading/>;

  async function saveCard(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setMessage("");
    try {
      await requestJson("/api/v1/platform/sales-managers/bank-card", token, { method: "PUT", body: JSON.stringify({ card_number: card, account_holder: holder }) });
      setCard("");
      setMessage("Payout card saved securely.");
      await onSaved();
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Could not save card"); }
    finally { setBusy(false); }
  }

  async function withdraw(balance: Balance) {
    const amount = Number(amounts[balance.currency] || balance.available);
    if (!Number.isFinite(amount) || amount <= 0) return;
    setBusy(true); setMessage("");
    try {
      await requestJson("/api/v1/platform/sales-managers/withdrawals", token, { method: "POST", body: JSON.stringify({ amount, currency: balance.currency }) });
      setMessage("Withdrawal request sent to platform administration.");
      setAmounts((current) => ({ ...current, [balance.currency]: "" }));
      await onSaved();
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Could not request withdrawal"); }
    finally { setBusy(false); }
  }

  return <div className="sm-stack"><section className="sm-panel"><div className="sm-panel-head"><div><small>PAYOUT DESTINATION</small><h2>Bank card</h2></div>{profile.bank_card_last4 && <span className="sm-pill">•••• {profile.bank_card_last4}</span>}</div><p className="sm-muted">Your full card number is encrypted at rest. Only platform administrators can reveal the payout destination when processing a withdrawal.</p><form className="sm-card-form" onSubmit={saveCard}><label className="sm-field">Card number<input value={card} onChange={(e) => setCard(e.target.value)} required placeholder={profile.bank_card_last4 ? `Replace card ending ${profile.bank_card_last4}` : "Card number"}/></label><label className="sm-field">Cardholder / account holder<input value={holder} onChange={(e) => setHolder(e.target.value)} required/></label><button className="sm-secondary" disabled={busy}><CreditCard/> Save payout card</button></form></section>
    <section className="sm-panel"><div className="sm-panel-head"><div><small>AVAILABLE BALANCE</small><h2>Request withdrawal</h2></div></div><div className="sm-withdraw-grid">{dashboard.balances.map((balance) => <article key={balance.currency}><strong>{money(balance.available, balance.currency)}</strong><span>available · {money(balance.pending_withdrawal, balance.currency)} pending</span><div><input type="number" min="1" max={balance.available} value={amounts[balance.currency] || ""} onChange={(e) => setAmounts((current) => ({ ...current, [balance.currency]: e.target.value }))} placeholder={String(balance.available)}/><button className="sm-primary" disabled={busy || balance.available <= 0 || !profile.bank_card_last4} onClick={() => void withdraw(balance)}>Withdraw</button></div></article>)}</div>{message && <div className="sm-note">{message}</div>}</section>
    <section className="sm-panel"><div className="sm-panel-head"><div><small>PAYOUT HISTORY</small><h2>Withdrawal requests</h2></div></div><div className="sm-table-wrap"><table><thead><tr><th>Requested</th><th>Amount</th><th>Card</th><th>Status</th><th>Paid reference</th></tr></thead><tbody>{dashboard.withdrawals.map((row) => <tr key={row.id}><td>{stamp(row.requested_at)}</td><td>{money(row.amount, row.currency)}</td><td>•••• {row.bank_card_last4}</td><td>{row.status}</td><td>{row.paid_reference || "—"}</td></tr>)}</tbody></table></div></section>
  </div>;
}

function Loading() {
  return <div className="sm-loading"><RefreshCw className="spin"/> Loading sales workspace…</div>;
}
