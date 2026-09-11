import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Activity,
  Building2,
  Check,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  Database,
  HeartPulse,
  Mail,
  RefreshCw,
  Save,
  Send,
  ServerCog,
  ShieldCheck,
  Stethoscope,
  UsersRound,
  X,
} from "lucide-react";

import { API_BASE_URL } from "../api/client";

const ADMIN_KEY = "teta2-platform-admin-token";
const PLAN_NAME = "Teta2 Care";

function navigate(path: string) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new Event("teta2-route"));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function jsonRequest<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(API_BASE_URL + path, { ...init, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload?.error?.message ?? payload?.detail ?? response.statusText;
    throw new Error(message);
  }
  return payload as T;
}

type Commercial = {
  plan_name: string;
  subscription_days: number;
  price_amount: number;
  currency: string;
  bank_name?: string | null;
  card_holder?: string | null;
  card_number?: string | null;
  payment_instructions?: string | null;
  support_email?: string | null;
  sender_name?: string;
};

type AccessRequest = {
  id: string;
  status: string;
  clinic_name: string;
  legal_name?: string | null;
  country: string;
  city: string;
  address?: string | null;
  website?: string | null;
  contact_name: string;
  contact_role?: string | null;
  contact_email: string;
  contact_phone: string;
  dentist_count?: number | null;
  monthly_patient_volume?: number | null;
  preferred_language: string;
  notes?: string | null;
  quoted_price_amount?: number | null;
  quoted_currency?: string | null;
  payment_reference?: string | null;
  payment_notes?: string | null;
  receipt_reference?: string | null;
  review_note?: string | null;
  payment_email_sent_at?: string | null;
  payment_confirmed_at?: string | null;
  activated_at?: string | null;
  clinic_registry_id?: string | null;
  created_at: string;
};

type Clinic = {
  id: string;
  slug: string;
  name: string;
  access_status: string;
  subscription_enforced: boolean;
  access_expires_at?: string | null;
  subscription_terms?: number;
};

type Overview = {
  platform: { plan_name: string; subscription_days: number; api: string; control_database: string; generated_at: string };
  clinics: { total: number; active_paid: number; expired_paid: number; legacy: number };
  requests: Record<string, number>;
  email_delivery: Record<string, number>;
  totals: { patients: number; users: number; visits: number; analyses: number };
  health: Array<Record<string, string | number>>;
  recent_visits: Array<{ clinic_name: string; visit_id: string; patient_id: string; doctor_id: string; visit_date: string; summary: string }>;
};

function Logo() {
  return <button className="platform-logo" onClick={() => navigate("/")}><span><HeartPulse /></span><div><strong>Teta2</strong><small>CARE PLATFORM</small></div></button>;
}

export function AccessRequestPortal() {
  const [commercial, setCommercial] = useState<Commercial | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);

  useEffect(() => {
    void jsonRequest<Commercial>("/api/v1/platform/commercial").then(setCommercial).catch(() => undefined);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const body = Object.fromEntries(form.entries());
    try {
      const result = await jsonRequest<{ id: string }>("/api/v1/platform/access-requests", {
        method: "POST",
        body: JSON.stringify({
          ...body,
          dentist_count: body.dentist_count ? Number(body.dentist_count) : null,
          monthly_patient_volume: body.monthly_patient_volume ? Number(body.monthly_patient_volume) : null,
        }),
      });
      setSubmitted(result.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to submit request.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="platform-public-shell">
    <header><Logo /><button onClick={() => navigate("/login")}>Already have access? Sign in</button></header>
    <section className="access-request-layout">
      <aside>
        <span className="platform-eyebrow">CLINIC ONBOARDING</span>
        <h1>Request access to <em>{PLAN_NAME}</em></h1>
        <p>Submit your clinic details for review. Teta2 will send payment instructions only after the request is approved for the payment stage.</p>
        <div className="access-plan-card">
          <small>ONE PROFESSIONAL PLAN</small>
          <h2>{PLAN_NAME}</h2>
          <strong>{commercial ? `${commercial.price_amount.toLocaleString()} ${commercial.currency}` : "Configured by Teta2"}</strong>
          <span>/ {commercial?.subscription_days ?? 30} days</span>
          <ul>
            <li><Check />AI-assisted OPG analysis</li>
            <li><Check />Smart patient records</li>
            <li><Check />Automated follow-up and WhatsApp conversations</li>
            <li><Check />Appointment workflow and clinical dashboard</li>
            <li><Check />Renewable without deleting previous clinic data</li>
          </ul>
        </div>
      </aside>
      <section className="access-form-card">
        {submitted ? <div className="access-success"><span><Check /></span><h2>Request received</h2><p>Your request reference is <b>{submitted}</b>. Our team will review it. If approved, payment instructions for the 30-day Teta2 Care subscription will be sent to your email.</p><button onClick={() => navigate("/")}>Return to Teta2</button></div> : <>
          <div className="access-form-head"><div><small>REQUEST ACCESS</small><h2>Clinic information</h2></div><ShieldCheck /></div>
          <form onSubmit={submit}>
            <div className="access-form-grid">
              <label><span>Clinic name *</span><input name="clinic_name" required minLength={2} /></label>
              <label><span>Legal / registered name</span><input name="legal_name" /></label>
              <label><span>Country *</span><input name="country" required /></label>
              <label><span>City *</span><input name="city" required /></label>
              <label className="wide"><span>Clinic address</span><input name="address" /></label>
              <label className="wide"><span>Website</span><input name="website" type="url" placeholder="https://" /></label>
            </div>
            <div className="access-divider"><span>Primary contact</span></div>
            <div className="access-form-grid">
              <label><span>Full name *</span><input name="contact_name" required /></label>
              <label><span>Role / title</span><input name="contact_role" placeholder="Clinic director" /></label>
              <label><span>Email *</span><input name="contact_email" type="email" required /></label>
              <label><span>Phone *</span><input name="contact_phone" required /></label>
              <label><span>Number of dentists</span><input name="dentist_count" type="number" min="1" /></label>
              <label><span>Monthly patient volume</span><input name="monthly_patient_volume" type="number" min="0" /></label>
              <label><span>Preferred language</span><select name="preferred_language" defaultValue="en"><option value="en">English</option><option value="hy">Armenian</option><option value="ru">Russian</option><option value="fa">Persian</option><option value="tr">Turkish</option></select></label>
            </div>
            <label className="access-notes"><span>Anything we should know?</span><textarea name="notes" rows={4} /></label>
            {error && <div className="platform-error">{error}</div>}
            <button className="platform-primary" disabled={busy}>{busy ? <Activity className="spin" /> : <Send />}{busy ? "Submitting…" : "Submit access request"}</button>
            <p className="access-terms">Submitting this form does not create an account or charge the clinic. Access is activated only after manual payment verification by Teta2.</p>
          </form>
        </>}
      </section>
    </section>
  </main>;
}

function useAdminToken() {
  const [token, setTokenState] = useState(() => sessionStorage.getItem(ADMIN_KEY) ?? "");
  const setToken = (value: string) => {
    if (value) sessionStorage.setItem(ADMIN_KEY, value); else sessionStorage.removeItem(ADMIN_KEY);
    setTokenState(value);
  };
  return [token, setToken] as const;
}

export function PlatformAdminPortal() {
  const [token, setToken] = useAdminToken();
  const [section, setSection] = useState<"overview" | "requests" | "clinics" | "commercial" | "audit">("overview");
  const [error, setError] = useState("");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [commercial, setCommercial] = useState<Commercial | null>(null);
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([]);
  const [busy, setBusy] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const [ov, req, cls, cfg, aud] = await Promise.all([
        jsonRequest<Overview>("/api/v1/platform/admin/overview", {}, token),
        jsonRequest<AccessRequest[]>("/api/v1/platform/admin/access-requests", {}, token),
        jsonRequest<Clinic[]>("/api/v1/platform/admin/clinics", {}, token),
        jsonRequest<Commercial>("/api/v1/platform/admin/commercial", {}, token),
        jsonRequest<Array<Record<string, unknown>>>("/api/v1/platform/admin/audit", {}, token),
      ]);
      setOverview(ov); setRequests(req); setClinics(cls); setCommercial(cfg); setAudit(aud); setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load platform data.");
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  if (!token) return <AdminLogin onToken={setToken} />;

  async function action(id: string, name: "send-payment" | "payment-confirmed" | "activate" | "reject") {
    setBusy(`${id}-${name}`); setError("");
    const note = name === "payment-confirmed" ? window.prompt("Optional payment / receipt note") : name === "reject" ? window.prompt("Reason for rejection") : null;
    try {
      await jsonRequest(`/api/v1/platform/admin/access-requests/${encodeURIComponent(id)}/${name}`, {
        method: "POST",
        body: name === "payment-confirmed" || name === "reject" ? JSON.stringify({ note, receipt_reference: null }) : undefined,
      }, token);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Action failed."); }
    finally { setBusy(""); }
  }

  return <div className="platform-admin-shell">
    <aside className="platform-admin-sidebar">
      <Logo />
      <div className="platform-admin-badge"><ShieldCheck /><span><small>CONTROL PLANE</small><b>Platform Admin</b></span></div>
      <nav>
        <button className={section === "overview" ? "active" : ""} onClick={() => setSection("overview")}><ServerCog />Overview</button>
        <button className={section === "requests" ? "active" : ""} onClick={() => setSection("requests")}><Mail />Access requests{requests.filter(x => x.status === "SUBMITTED").length > 0 && <i>{requests.filter(x => x.status === "SUBMITTED").length}</i>}</button>
        <button className={section === "clinics" ? "active" : ""} onClick={() => setSection("clinics")}><Building2 />Clinics</button>
        <button className={section === "commercial" ? "active" : ""} onClick={() => setSection("commercial")}><CircleDollarSign />Commercial</button>
        <button className={section === "audit" ? "active" : ""} onClick={() => setSection("audit")}><Database />Audit log</button>
      </nav>
      <button className="platform-admin-signout" onClick={() => setToken("")}>Sign out</button>
    </aside>
    <main className="platform-admin-main">
      <header><div><small>TETA2 PLATFORM</small><h1>{section === "overview" ? "System overview" : section === "requests" ? "Clinic access requests" : section === "clinics" ? "Clinics & subscriptions" : section === "commercial" ? "Commercial configuration" : "Admin audit trail"}</h1></div><button onClick={() => void load()}><RefreshCw />Refresh</button></header>
      {error && <div className="platform-error"><X />{error}</div>}
      {section === "overview" && <OverviewPanel data={overview} />}
      {section === "requests" && <RequestsPanel requests={requests} busy={busy} action={action} />}
      {section === "clinics" && <ClinicsPanel clinics={clinics} />}
      {section === "commercial" && commercial && <CommercialPanel value={commercial} token={token} onSaved={load} />}
      {section === "audit" && <AuditPanel rows={audit} />}
    </main>
  </div>;
}

function AdminLogin({ onToken }: { onToken: (token: string) => void }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try {
      const result = await jsonRequest<{ access_token: string }>("/api/v1/platform/admin/login", { method: "POST", body: JSON.stringify({ username: data.get("username"), password: data.get("password") }) });
      onToken(result.access_token);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Sign-in failed."); }
    finally { setBusy(false); }
  }
  return <main className="platform-admin-login"><section><Logo /><div className="admin-lock"><ShieldCheck /></div><small>PLATFORM CONTROL PLANE</small><h1>Teta2 Admin</h1><p>Restricted operations console for clinic onboarding, subscriptions and platform health.</p><form onSubmit={login}><label>Username<input name="username" autoComplete="username" required /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label>{error && <div className="platform-error">{error}</div>}<button className="platform-primary" disabled={busy}>{busy ? "Signing in…" : "Open admin panel"}</button></form></section></main>;
}

function OverviewPanel({ data }: { data: Overview | null }) {
  if (!data) return <div className="platform-loading"><Activity className="spin" />Loading platform health…</div>;
  const cards = [
    ["Clinics", data.clinics.total, <Building2 key="c" />],
    ["Active subscriptions", data.clinics.active_paid, <ShieldCheck key="s" />],
    ["Patients", data.totals.patients, <UsersRound key="p" />],
    ["Visits", data.totals.visits, <Stethoscope key="v" />],
    ["AI analyses", data.totals.analyses, <Activity key="a" />],
  ] as const;
  return <>
    <section className="platform-stat-grid">{cards.map(([label, value, icon]) => <article key={label}><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></article>)}</section>
    <section className="platform-panel"><header><div><small>SERVICE HEALTH</small><h2>Clinic infrastructure</h2></div><span className="healthy"><Check />API healthy</span></header><div className="platform-health-grid">{data.health.map((row) => <article key={String(row.clinic_id)}><div><b>{String(row.name)}</b><small>{String(row.slug)}</small></div><span className={row.database === "healthy" ? "healthy" : "danger"}>{String(row.database)}</span><p>{Number(row.patients ?? 0)} patients · {Number(row.visits ?? 0)} visits · {Number(row.analyses ?? 0)} analyses</p></article>)}</div></section>
    <section className="platform-panel"><header><div><small>RECENT ACTIVITY</small><h2>Visits across clinics</h2></div></header><div className="platform-table"><div className="thead"><span>Clinic</span><span>Date</span><span>Summary</span></div>{data.recent_visits.slice(0, 30).map((visit) => <div className="trow" key={visit.visit_id}><span><b>{visit.clinic_name}</b></span><span>{new Date(visit.visit_date).toLocaleString()}</span><span>{visit.summary}</span></div>)}</div></section>
  </>;
}

function RequestsPanel({ requests, busy, action }: { requests: AccessRequest[]; busy: string; action: (id: string, name: "send-payment" | "payment-confirmed" | "activate" | "reject") => Promise<void> }) {
  const ordered = useMemo(() => [...requests].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()), [requests]);
  return <section className="platform-request-list">{ordered.map((row) => <article key={row.id}>
    <header><div><span className={`request-status ${row.status.toLowerCase()}`}>{row.status.replaceAll("_", " ")}</span><h2>{row.clinic_name}</h2><p>{row.city}, {row.country} · {row.contact_name} · {row.contact_email}</p></div><small>{new Date(row.created_at).toLocaleString()}</small></header>
    <div className="request-facts"><span><b>Contact</b>{row.contact_phone}</span><span><b>Dentists</b>{row.dentist_count ?? "—"}</span><span><b>Patients / month</b>{row.monthly_patient_volume ?? "—"}</span><span><b>Plan</b>{PLAN_NAME}</span>{row.payment_reference && <span><b>Payment ref</b>{row.payment_reference}</span>}</div>
    {row.notes && <p className="request-note">{row.notes}</p>}
    <footer>
      {row.status === "SUBMITTED" && <><button className="platform-primary" disabled={Boolean(busy)} onClick={() => void action(row.id, "send-payment")}><Send />Send payment email</button><button className="danger" disabled={Boolean(busy)} onClick={() => void action(row.id, "reject")}><X />Reject</button></>}
      {row.status === "PAYMENT_REQUEST_SENT" && <button className="platform-primary" disabled={Boolean(busy)} onClick={() => void action(row.id, "payment-confirmed")}><Check />Payment verified</button>}
      {row.status === "PAYMENT_CONFIRMED" && <button className="platform-primary" disabled={Boolean(busy)} onClick={() => void action(row.id, "activate")}><ShieldCheck />Activate 30-day dashboard</button>}
      {row.status === "ACTIVATED" && <span className="request-complete"><Check />Workspace activated</span>}
    </footer>
  </article>)}{!ordered.length && <div className="platform-empty">No access requests yet.</div>}</section>;
}

function ClinicsPanel({ clinics }: { clinics: Clinic[] }) {
  return <section className="platform-panel"><header><div><small>TENANTS</small><h2>Clinic subscriptions</h2></div></header><div className="platform-table clinics"><div className="thead"><span>Clinic</span><span>Status</span><span>Access until</span><span>Terms</span></div>{clinics.map((row) => <div className="trow" key={row.id}><span><b>{row.name}</b><small>{row.slug}</small></span><span className={row.access_status === "ACTIVE" ? "healthy" : row.access_status === "LEGACY" ? "neutral" : "danger"}>{row.access_status}</span><span>{row.access_expires_at ? new Date(row.access_expires_at).toLocaleString() : "Legacy / not enforced"}</span><span>{row.subscription_terms ?? 0}</span></div>)}</div></section>;
}

function CommercialPanel({ value, token, onSaved }: { value: Commercial; token: string; onSaved: () => Promise<void> }) {
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState(""); const [error, setError] = useState("");
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(""); setError("");
    const data = new FormData(event.currentTarget);
    try {
      await jsonRequest("/api/v1/platform/admin/commercial", { method: "PUT", body: JSON.stringify({ price_amount: Number(data.get("price_amount")), currency: data.get("currency"), bank_name: data.get("bank_name") || null, card_holder: data.get("card_holder") || null, card_number: data.get("card_number") || null, payment_instructions: data.get("payment_instructions") || null, support_email: data.get("support_email") || null, sender_name: data.get("sender_name") || "Teta2 Care" }) }, token);
      setMessage("Commercial settings saved."); await onSaved();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Save failed."); }
    finally { setBusy(false); }
  }
  return <section className="platform-panel commercial"><header><div><small>EDITABLE BILLING DETAILS</small><h2>{PLAN_NAME} · fixed 30-day access cycle</h2></div><span className="fixed-term"><Clock3 />30 days fixed</span></header><form onSubmit={save}><div className="access-form-grid"><label><span>Subscription price</span><input name="price_amount" type="number" min="1" defaultValue={value.price_amount} required /></label><label><span>Currency</span><input name="currency" defaultValue={value.currency} required /></label><label><span>Bank name</span><input name="bank_name" defaultValue={value.bank_name ?? ""} /></label><label><span>Card holder</span><input name="card_holder" defaultValue={value.card_holder ?? ""} /></label><label className="wide"><span>Card / account number</span><input name="card_number" defaultValue={value.card_number ?? ""} /></label><label><span>Support email</span><input name="support_email" type="email" defaultValue={value.support_email ?? ""} /></label><label><span>Email sender name</span><input name="sender_name" defaultValue={value.sender_name ?? "Teta2 Care"} /></label></div><label className="access-notes"><span>Payment instructions appended to the fixed payment email</span><textarea name="payment_instructions" rows={5} defaultValue={value.payment_instructions ?? ""} /></label>{message && <div className="platform-success"><Check />{message}</div>}{error && <div className="platform-error">{error}</div>}<button className="platform-primary" disabled={busy}><Save />{busy ? "Saving…" : "Save commercial settings"}</button></form></section>;
}

function AuditPanel({ rows }: { rows: Array<Record<string, unknown>> }) {
  return <section className="platform-panel"><header><div><small>IMMUTABLE OPERATION HISTORY</small><h2>Platform admin actions</h2></div></header><div className="platform-table audit"><div className="thead"><span>Action</span><span>Time</span><span>Reference</span></div>{rows.map((row) => <div className="trow" key={String(row.id)}><span><b>{String(row.action)}</b></span><span>{new Date(String(row.created_at)).toLocaleString()}</span><span>{String(row.request_id ?? row.clinic_id ?? "—")}</span></div>)}</div></section>;
}

export function CareOnlyMarketing() {
  useEffect(() => {
    let commercial: Commercial | null = null;
    void jsonRequest<Commercial>("/api/v1/platform/commercial").then((value) => { commercial = value; sanitize(); }).catch(() => undefined);
    const sanitize = () => {
      document.querySelectorAll<HTMLElement>(".product-plan-card, .product-pricing-grid > article").forEach((card) => {
        if (/Teta2 Scan/i.test(card.textContent ?? "")) card.remove();
      });
      document.querySelectorAll<HTMLElement>(".product-plan-grid, .product-pricing-grid").forEach((grid) => grid.classList.add("care-only"));
      document.querySelectorAll<HTMLElement>(".product-market-switch").forEach((switcher) => switcher.remove());
      document.querySelectorAll<HTMLElement>(".product-pricing-grid > article").forEach((card) => {
        if (!/Teta2 Care/i.test(card.textContent ?? "")) return;
        const price = card.querySelector<HTMLElement>(".product-price strong");
        if (price && commercial) price.textContent = `${commercial.price_amount.toLocaleString()} ${commercial.currency}`;
      });
      document.querySelectorAll<HTMLElement>("h1,h2,p,span").forEach((node) => {
        if (node.children.length) return;
        const text = node.textContent ?? "";
        if (text.includes("Two focused plans")) node.textContent = text.replace("Two focused plans", "One complete plan");
        if (text.includes("Choose analysis only—or close the follow-up loop.")) node.textContent = "One plan for OPG intelligence, follow-up, WhatsApp and patient return.";
      });
    };
    sanitize();
    const observer = new MutationObserver(sanitize);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);
  return null;
}
