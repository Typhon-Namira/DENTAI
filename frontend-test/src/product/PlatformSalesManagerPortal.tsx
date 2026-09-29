import {
  Banknote,
  Building2,
  CheckCircle2,
  CircleDollarSign,
  ClipboardList,
  History,
  LogOut,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Trash2,
  UserRound,
  WalletCards,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { API_BASE_URL } from "../api/client";
import "./platform-sales-manager.css";

const SESSION_KEY = "teta2-sales-manager-session";

type Manager = {
  id: string;
  username: string;
  email: string;
  full_name: string;
  title: string;
  phone?: string | null;
  territory?: string | null;
  bank_card_last4?: string | null;
  bank_card_holder?: string | null;
  commission_rate_bps: number;
};

type Commission = {
  id: string;
  clinic_id: string;
  clinic_name: string;
  gross_amount: number;
  commission_amount: number;
  currency: string;
  rate_percent: number;
  status: string;
  created_at: string;
};

type Withdrawal = {
  id: string;
  currency: string;
  amount: number;
  status: string;
  bank_card_last4: string;
  requested_at: string;
  processed_at?: string | null;
  payment_reference?: string | null;
  admin_note?: string | null;
};

type Dashboard = {
  manager: Manager;
  metrics: {
    reports: number;
    clinic_contacts: number;
    attributed_clinics: number;
  };
  available_balance: Record<string, number>;
  commissions: Commission[];
  withdrawals: Withdrawal[];
};

type Contact = {
  id?: string;
  clinic_name: string;
  country?: string | null;
  city?: string | null;
  address?: string | null;
  website?: string | null;
  contact_name?: string | null;
  contact_role?: string | null;
  email?: string | null;
  phone?: string | null;
  negotiation_result: string;
  outcome: string;
  next_step?: string | null;
  follow_up_date?: string | null;
};

type Report = {
  id: string;
  report_date: string;
  summary?: string | null;
  submitted_at: string;
  updated_at: string;
  contacts: Contact[];
};

type Tab = "overview" | "report" | "history" | "earnings" | "payouts" | "payment";

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

async function json<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
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

function dateTime(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : parsed.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

const emptyContact = (): Contact => ({
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
  outcome: "FOLLOW_UP",
  next_step: "",
  follow_up_date: "",
});

export function PlatformSalesManagerPortal() {
  const active = window.location.pathname === "/platform-managers";
  const [token, setToken] = useState(() => sessionStorage.getItem(SESSION_KEY) || "");
  const [authenticated, setAuthenticated] = useState(false);
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [reports, setReports] = useState<Report[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [reportDate, setReportDate] = useState(today());
  const [reportSummary, setReportSummary] = useState("");
  const [contacts, setContacts] = useState<Contact[]>([emptyContact()]);
  const [cardNumber, setCardNumber] = useState("");
  const [cardHolder, setCardHolder] = useState("");
  const [withdrawCurrency, setWithdrawCurrency] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");

  const load = useCallback(async (authToken: string) => {
    const [nextDashboard, nextReports] = await Promise.all([
      json<Dashboard>("/api/v1/platform/sales/dashboard", authToken),
      json<Report[]>("/api/v1/platform/sales/reports", authToken),
    ]);
    setDashboard(nextDashboard);
    setReports(nextReports);
    setAuthenticated(true);
    setError("");
  }, []);

  useEffect(() => {
    if (!active) return;
    const previousLang = document.documentElement.lang;
    document.documentElement.lang = "en";
    document.body.classList.add("sales-manager-active");
    return () => {
      document.body.classList.remove("sales-manager-active");
      document.documentElement.lang = previousLang;
    };
  }, [active]);

  useEffect(() => {
    if (!active || !token || authenticated) return;
    void load(token).catch(() => {
      sessionStorage.removeItem(SESSION_KEY);
      setToken("");
      setAuthenticated(false);
    });
  }, [active, authenticated, load, token]);

  const balances = useMemo(() => Object.entries(dashboard?.available_balance ?? {}), [dashboard]);

  if (!active) return null;

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setBusy("login");
    setError("");
    try {
      const result = await json<{ access_token: string }>("/api/v1/platform/sales/login", undefined, {
        method: "POST",
        body: JSON.stringify({ login: login.trim(), password }),
      });
      sessionStorage.setItem(SESSION_KEY, result.access_token);
      setToken(result.access_token);
      setPassword("");
      await load(result.access_token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign in failed");
    } finally {
      setBusy("");
    }
  }

  async function logout() {
    try {
      if (token) await json("/api/v1/platform/sales/logout", token, { method: "POST", body: "{}" });
    } catch {
      // Local sign-out still completes if the session already expired.
    }
    sessionStorage.removeItem(SESSION_KEY);
    setToken("");
    setAuthenticated(false);
    setDashboard(null);
    setReports([]);
  }

  async function saveReport() {
    const validContacts = contacts.filter((item) => item.clinic_name.trim() && item.negotiation_result.trim());
    if (!validContacts.length) {
      setError("Add at least one clinic with a negotiation result.");
      return;
    }
    setBusy("report");
    setError("");
    try {
      await json("/api/v1/platform/sales/reports/daily", token, {
        method: "PUT",
        body: JSON.stringify({
          report_date: reportDate,
          summary: reportSummary || null,
          contacts: validContacts.map((item) => ({
            ...item,
            follow_up_date: item.follow_up_date || null,
            email: item.email || null,
          })),
        }),
      });
      await load(token);
      setReportSummary("");
      setContacts([emptyContact()]);
      setTab("history");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save daily report");
    } finally {
      setBusy("");
    }
  }

  async function saveCard() {
    setBusy("card");
    setError("");
    try {
      await json("/api/v1/platform/sales/bank-card", token, {
        method: "PUT",
        body: JSON.stringify({ card_number: cardNumber, holder_name: cardHolder || null }),
      });
      setCardNumber("");
      await load(token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save bank card");
    } finally {
      setBusy("");
    }
  }

  async function requestPayout() {
    const amount = Number(withdrawAmount);
    if (!withdrawCurrency || !Number.isFinite(amount) || amount <= 0) {
      setError("Choose a currency and enter a valid amount.");
      return;
    }
    setBusy("withdraw");
    setError("");
    try {
      await json("/api/v1/platform/sales/withdrawals", token, {
        method: "POST",
        body: JSON.stringify({ currency: withdrawCurrency, amount: Math.trunc(amount) }),
      });
      setWithdrawAmount("");
      await load(token);
      setTab("payouts");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not request payout");
    } finally {
      setBusy("");
    }
  }

  if (!authenticated || !dashboard) {
    return <main className="sm-root sm-login-root">
      <section className="sm-login-card">
        <span className="sm-security"><ShieldCheck /> TETA2 SALES · SECURE ACCESS</span>
        <div className="sm-brand">Teta2 <small>SALES</small></div>
        <h1>Sales Manager Workspace</h1>
        <p>Sign in with the credentials issued by Teta2 administration.</p>
        <form onSubmit={submitLogin}>
          <label>Username or email<input value={login} onChange={(event) => setLogin(event.target.value)} autoComplete="username" required autoFocus /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required /></label>
          {error && <div className="sm-error">{error}</div>}
          <button className="sm-primary" disabled={busy === "login"}>{busy === "login" ? "Signing in…" : "Sign in"}</button>
        </form>
      </section>
    </main>;
  }

  const manager = dashboard.manager;
  const nav: Array<[Tab, string, typeof Building2]> = [
    ["overview", "Overview", Building2],
    ["report", "Daily report", ClipboardList],
    ["history", "Activity history", History],
    ["earnings", "Earnings", CircleDollarSign],
    ["payouts", "Payouts", Banknote],
    ["payment", "Payment details", WalletCards],
  ];

  return <main className="sm-root">
    <aside className="sm-sidebar">
      <div className="sm-brand">Teta2 <small>SALES</small></div>
      <div className="sm-manager"><span><UserRound /></span><div><strong>{manager.full_name}</strong><small>{manager.title}</small></div></div>
      <nav>{nav.map(([id, title, Icon]) => <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}><Icon /><span>{title}</span></button>)}</nav>
      <button className="sm-signout" onClick={() => void logout()}><LogOut /> Sign out</button>
    </aside>
    <section className="sm-main">
      <header className="sm-topbar"><div><small>SALES OPERATIONS</small><h1>{nav.find(([id]) => id === tab)?.[1]}</h1></div><button title="Refresh" onClick={() => void load(token)}><RefreshCw /></button></header>
      {error && <div className="sm-error sm-page-error">{error}</div>}

      {tab === "overview" && <div className="sm-stack">
        <section className="sm-metrics">
          <Metric label="Daily reports" value={dashboard.metrics.reports} icon={ClipboardList} />
          <Metric label="Clinics contacted" value={dashboard.metrics.clinic_contacts} icon={Building2} />
          <Metric label="Attributed clinics" value={dashboard.metrics.attributed_clinics} icon={CheckCircle2} />
          <Metric label="Commission rate" value={`${manager.commission_rate_bps / 100}%`} icon={CircleDollarSign} />
        </section>
        <section className="sm-panel"><Heading title="Available earnings" /><div className="sm-balances">{balances.length ? balances.map(([currency, amount]) => <article key={currency}><span>{currency}</span><strong>{money(amount, currency)}</strong><button onClick={() => { setWithdrawCurrency(currency); setWithdrawAmount(String(amount)); setTab("payouts"); }}>Request payout</button></article>) : <p>No commission is available yet. Verified subscription commissions will appear here automatically.</p>}</div></section>
        <section className="sm-panel"><Heading title="Recent commissions" /><CommissionTable rows={dashboard.commissions.slice(0, 8)} /></section>
      </div>}

      {tab === "report" && <section className="sm-panel">
        <Heading title="Submit today's clinic activity" subtitle="Fast daily reporting. Every clinic entry is retained and may be used to attribute future subscriptions." />
        <div className="sm-report-head"><label>Report date<input type="date" value={reportDate} onChange={(event) => setReportDate(event.target.value)} /></label><label>Daily summary<textarea rows={2} value={reportSummary} onChange={(event) => setReportSummary(event.target.value)} placeholder="Optional overall summary" /></label></div>
        <div className="sm-contact-list">{contacts.map((contact, index) => <ClinicContactEditor key={index} value={contact} index={index} onChange={(next) => setContacts((current) => current.map((item, itemIndex) => itemIndex === index ? next : item))} onRemove={() => setContacts((current) => current.length === 1 ? current : current.filter((_, itemIndex) => itemIndex !== index))} />)}</div>
        <div className="sm-report-actions"><button className="sm-secondary" onClick={() => setContacts((current) => [...current, emptyContact()])}><Plus /> Add clinic</button><button className="sm-primary" disabled={busy === "report"} onClick={() => void saveReport()}><Save /> {busy === "report" ? "Saving…" : "Submit daily report"}</button></div>
      </section>}

      {tab === "history" && <section className="sm-panel"><Heading title="Permanent report history" subtitle="Submitted clinic conversations remain visible in chronological order." /><div className="sm-history">{reports.map((report) => <article key={report.id}><header><div><strong>{report.report_date}</strong><small>{report.contacts.length} clinic(s) · submitted {dateTime(report.submitted_at)}</small></div></header>{report.summary && <p>{report.summary}</p>}<div className="sm-history-contacts">{report.contacts.map((contact) => <div key={contact.id || contact.clinic_name}><strong>{contact.clinic_name}</strong><span>{[contact.city, contact.country].filter(Boolean).join(", ") || "Location not recorded"}</span><b>{contact.outcome}</b><p>{contact.negotiation_result}</p>{contact.next_step && <small>Next: {contact.next_step}</small>}</div>)}</div></article>)}{!reports.length && <p className="sm-empty">No daily reports have been submitted yet.</p>}</div></section>}

      {tab === "earnings" && <div className="sm-stack"><section className="sm-panel"><Heading title="Commission ledger" subtitle="Commissions are created only after a clinic payment is verified and sales attribution is confirmed." /><CommissionTable rows={dashboard.commissions} /></section></div>}

      {tab === "payouts" && <div className="sm-stack"><section className="sm-panel"><Heading title="Request withdrawal" subtitle={manager.bank_card_last4 ? `Destination card ending •••• ${manager.bank_card_last4}` : "Add a bank card before requesting a payout."} /><div className="sm-payout-form"><label>Currency<select value={withdrawCurrency} onChange={(event) => setWithdrawCurrency(event.target.value)}><option value="">Select</option>{balances.map(([currency]) => <option key={currency}>{currency}</option>)}</select></label><label>Amount<input type="number" min="1" value={withdrawAmount} onChange={(event) => setWithdrawAmount(event.target.value)} /></label><button className="sm-primary" disabled={busy === "withdraw" || !manager.bank_card_last4} onClick={() => void requestPayout()}><Banknote /> Request payout</button></div></section><section className="sm-panel"><Heading title="Withdrawal history" /><div className="sm-table-wrap"><table><thead><tr><th>Requested</th><th>Amount</th><th>Status</th><th>Destination</th><th>Reference</th></tr></thead><tbody>{dashboard.withdrawals.map((row) => <tr key={row.id}><td>{dateTime(row.requested_at)}</td><td>{money(row.amount, row.currency)}</td><td><Status value={row.status} /></td><td>•••• {row.bank_card_last4}</td><td>{row.payment_reference || "—"}</td></tr>)}</tbody></table></div></section></div>}

      {tab === "payment" && <section className="sm-panel sm-payment-panel"><Heading title="Payout bank card" subtitle="The full card number is encrypted at rest. The workspace displays only the last four digits after saving." />{manager.bank_card_last4 && <div className="sm-current-card"><WalletCards /><div><small>Current destination</small><strong>•••• •••• •••• {manager.bank_card_last4}</strong><span>{manager.bank_card_holder || "Card holder not specified"}</span></div></div>}<div className="sm-card-form"><label>Card or payout account number<input value={cardNumber} onChange={(event) => setCardNumber(event.target.value)} inputMode="numeric" autoComplete="off" placeholder="Enter full number" /></label><label>Card holder name<input value={cardHolder} onChange={(event) => setCardHolder(event.target.value)} placeholder="Optional" /></label><button className="sm-primary" disabled={busy === "card" || !cardNumber.trim()} onClick={() => void saveCard()}><Save /> Save payment details</button></div></section>}
    </section>
  </main>;
}

function Metric({ label, value, icon: Icon }: { label: string; value: number | string; icon: typeof Building2 }) {
  return <article><span><Icon /></span><small>{label}</small><strong>{typeof value === "number" ? value.toLocaleString("en-US") : value}</strong></article>;
}

function Heading({ title, subtitle }: { title: string; subtitle?: string }) {
  return <div className="sm-heading"><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>;
}

function Status({ value }: { value: string }) {
  return <span className={`sm-status sm-status-${value.toLowerCase()}`}>{value.replaceAll("_", " ")}</span>;
}

function CommissionTable({ rows }: { rows: Commission[] }) {
  return <div className="sm-table-wrap"><table><thead><tr><th>Date</th><th>Clinic</th><th>Subscription</th><th>Rate</th><th>Your commission</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{dateTime(row.created_at)}</td><td><strong>{row.clinic_name}</strong><small>{row.clinic_id.slice(0, 8)}</small></td><td>{money(row.gross_amount, row.currency)}</td><td>{row.rate_percent}%</td><td><strong>{money(row.commission_amount, row.currency)}</strong></td></tr>)}</tbody></table>{!rows.length && <p className="sm-empty">No verified commissions yet.</p>}</div>;
}

function ClinicContactEditor({ value, index, onChange, onRemove }: { value: Contact; index: number; onChange: (value: Contact) => void; onRemove: () => void }) {
  const set = (key: keyof Contact, next: string) => onChange({ ...value, [key]: next });
  return <article className="sm-contact-card">
    <header><div><small>CLINIC {String(index + 1).padStart(2, "0")}</small><strong>{value.clinic_name || "New clinic contact"}</strong></div><button title="Remove clinic" onClick={onRemove}><Trash2 /></button></header>
    <div className="sm-form-grid">
      <label>Clinic name *<input value={value.clinic_name} onChange={(event) => set("clinic_name", event.target.value)} placeholder="Official clinic name" /></label>
      <label>Outcome *<select value={value.outcome} onChange={(event) => set("outcome", event.target.value)}><option>FOLLOW_UP</option><option>INTERESTED</option><option>PAYMENT_EXPECTED</option><option>NOT_INTERESTED</option><option>CALL_BACK</option><option>MEETING_BOOKED</option></select></label>
      <label>Contact person<input value={value.contact_name || ""} onChange={(event) => set("contact_name", event.target.value)} /></label>
      <label>Role<input value={value.contact_role || ""} onChange={(event) => set("contact_role", event.target.value)} /></label>
      <label>Email<input type="email" value={value.email || ""} onChange={(event) => set("email", event.target.value)} /></label>
      <label>Phone<input value={value.phone || ""} onChange={(event) => set("phone", event.target.value)} /></label>
      <label>Country<input value={value.country || ""} onChange={(event) => set("country", event.target.value)} /></label>
      <label>City<input value={value.city || ""} onChange={(event) => set("city", event.target.value)} /></label>
      <label className="wide">Address<input value={value.address || ""} onChange={(event) => set("address", event.target.value)} /></label>
      <label className="wide">Website<input value={value.website || ""} onChange={(event) => set("website", event.target.value)} placeholder="clinic.example" /></label>
      <label className="wide">Negotiation result *<textarea rows={3} value={value.negotiation_result} onChange={(event) => set("negotiation_result", event.target.value)} placeholder="What was discussed and what was the result?" /></label>
      <label className="wide">Next step<textarea rows={2} value={value.next_step || ""} onChange={(event) => set("next_step", event.target.value)} placeholder="Optional follow-up action" /></label>
      <label>Follow-up date<input type="date" value={value.follow_up_date || ""} onChange={(event) => set("follow_up_date", event.target.value)} /></label>
    </div>
  </article>;
}
