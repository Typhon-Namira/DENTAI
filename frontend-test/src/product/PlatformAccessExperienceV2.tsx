import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Activity,
  Building2,
  Check,
  CircleAlert,
  CreditCard,
  Mail,
  RefreshCw,
  Save,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";

import { API_BASE_URL } from "../api/client";
import { productCopy } from "./content";
import { PublicFooter, PublicNavbar } from "./PublicChrome";
import "./platform-access-v2.css";

const ADMIN_SESSION_KEY = "teta2-platform-admin-session";
type AccessLang = "en" | "hy" | "ru";
type MarketCode = "AM" | "RU";

type MarketConfig = {
  name: string;
  currency: string;
  standard_price: number;
  funding_price: number;
  payment_subject: string;
};

type MarketPlans = {
  name: string;
  period_days: number;
  funding_limit: number;
  markets: Record<MarketCode, MarketConfig>;
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
  created_at: string;
};

type Clinic = {
  id: string;
  slug: string;
  name: string;
  is_active: boolean;
  subscription_plan: string;
  subscription_expires_at?: string | null;
  days_remaining?: number | null;
  created_at: string;
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

type Overview = {
  health: Record<string, boolean | string>;
  metrics: Record<string, number>;
  request_statuses: Record<string, number>;
  top_routes: [string, number][];
  recent_emails: Array<{ id: string; kind: string; recipient: string; status: string; created_at: string; error?: string | null }>;
};

const FALLBACK_PLANS: MarketPlans = {
  name: "Teta2",
  period_days: 30,
  funding_limit: 50,
  markets: {
    AM: { name: "Armenia", currency: "AMD", standard_price: 49000, funding_price: 39000, payment_subject: "Teta2 clinic access — Armenia payment instructions" },
    RU: { name: "Russia", currency: "RUB", standard_price: 14000, funding_price: 11400, payment_subject: "Teta2 — инструкция по оплате для клиники в России" },
  },
};

const ACCESS_COPY = {
  en: {
    eyebrow: "REQUEST ACCESS",
    title: "Bring your clinic into Teta2.",
    lead: "Submit one secure application. Country determines the correct market pricing automatically when your request is reviewed.",
    funding: "Funding Plan",
    first: "first 50 clinics",
    standard: "Standard",
    monthly: "per clinic / month",
    retained: "Your clinical workspace is continuous",
    retainedText: "When access expires, the workspace is locked rather than deleted. Renewal reactivates the same clinic data and history.",
    application: "CLINIC APPLICATION",
    request: "Access request",
    submit: "Submit access request",
  },
  hy: {
    eyebrow: "ՄՈՒՏՔԻ ՀԱՐՑՈՒՄ",
    title: "Միացրեք ձեր կլինիկան Teta2-ին։",
    lead: "Ուղարկեք մեկ անվտանգ հայտ։ Հայտում նշված երկիրը review-ի պահին ավտոմատ ընտրում է ճիշտ market pricing-ը։",
    funding: "Funding Plan",
    first: "առաջին 50 clinics",
    standard: "Standard",
    monthly: "մեկ clinic / ամիս",
    retained: "Clinical workspace-ը շարունակական է",
    retainedText: "Access-ի ավարտից հետո workspace-ը կողպվում է, ոչ թե ջնջվում։ Renewal-ը վերադարձնում է նույն clinic data-ն և history-ն։",
    application: "ԿԼԻՆԻԿԱՅԻ ՀԱՅՏ",
    request: "Մուտքի հարցում",
    submit: "Ուղարկել հարցումը",
  },
  ru: {
    eyebrow: "ЗАПРОС ДОСТУПА",
    title: "Подключите клинику к Teta2.",
    lead: "Отправьте одну защищенную заявку. Страна в заявке автоматически определяет правильную цену и письмо при review.",
    funding: "Funding Plan",
    first: "первые 50 клиник",
    standard: "Standard",
    monthly: "за клинику / месяц",
    retained: "Рабочее пространство клиники сохраняется",
    retainedText: "После окончания доступа workspace блокируется, а не удаляется. Продление возвращает те же данные и историю.",
    application: "ЗАЯВКА КЛИНИКИ",
    request: "Запрос доступа",
    submit: "Отправить заявку",
  },
} as const;

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

async function publicJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.error?.message || body?.detail || "Request failed");
  return body as T;
}

async function adminJson<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  return publicJson<T>(path, {
    ...init,
    headers: { Authorization: `Bearer ${token}`, ...(init?.headers || {}) },
  });
}

function go(path: string) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function requestMarket(row: Pick<AccessRequest, "country" | "city" | "address">): MarketCode | null {
  const country = row.country.trim().toLowerCase();
  if (["armenia", "am", "հայաստան", "армения"].includes(country)) return "AM";
  if (["russia", "ru", "russian federation", "россия", "российская федерация"].includes(country)) return "RU";
  const location = `${row.city || ""} ${row.address || ""}`.toLowerCase();
  if (/yerevan|երևան|ереван|armenia|հայաստան|армения/.test(location)) return "AM";
  if (/russia|россия|moscow|москва|saint petersburg|санкт/.test(location)) return "RU";
  return null;
}

function money(value: number, currency: string) {
  return `${value.toLocaleString("en-US")} ${currency}`;
}

function Brand() {
  return <div className="pav2-brand"><strong>Teta2</strong><span>Platform</span></div>;
}

export function PlatformAccessExperienceV2() {
  const [route, setRoute] = useState(window.location.pathname);
  useEffect(() => {
    const onRoute = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", onRoute);
    return () => window.removeEventListener("popstate", onRoute);
  }, []);

  if (route === "/register" || route === "/request-access") return <AccessRequestPage />;
  if (route === "/platform-admin") return <PlatformAdmin />;
  return null;
}

function AccessRequestPage() {
  const initial = localStorage.getItem("teta2-product-language");
  const [lang, setLang] = useState<AccessLang>(initial === "hy" || initial === "ru" ? initial : "en");
  const copy = ACCESS_COPY[lang];
  const [plans, setPlans] = useState<MarketPlans>(FALLBACK_PLANS);
  const [country, setCountry] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    const syncLanguage = (event: Event) => setLang((event as CustomEvent<AccessLang>).detail);
    window.addEventListener("teta2-language-change", syncLanguage);
    return () => window.removeEventListener("teta2-language-change", syncLanguage);
  }, []);

  useEffect(() => {
    void publicJson<MarketPlans>("/api/v1/platform/market/plans").then(setPlans).catch(() => setPlans(FALLBACK_PLANS));
  }, []);

  const selectedMarket = country === "Armenia" ? plans.markets.AM : country === "Russia" ? plans.markets.RU : null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const value = (key: string) => String(form.get(key) || "").trim();
    try {
      await publicJson("/api/v1/platform/access-requests", {
        method: "POST",
        body: JSON.stringify({
          clinic_name: value("clinic_name"),
          country: value("country"),
          city: value("city"),
          address: value("address") || null,
          website: value("website") || null,
          contact_name: value("contact_name"),
          contact_role: value("contact_role"),
          email: value("email"),
          phone: value("phone"),
          dentists_count: Number(value("dentists_count") || 1),
          branches_count: Number(value("branches_count") || 1),
          notes: value("notes") || null,
        }),
      });
      setDone(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not submit request");
    } finally {
      setBusy(false);
    }
  }

  return <div className="pav2-overlay pav2-access-page">
    <PublicNavbar
      language={lang}
      onLanguage={(next) => {
        localStorage.setItem("teta2-product-language", next);
        localStorage.setItem("teta2-v4-language", next);
        document.documentElement.lang = next;
        setLang(next);
      }}
      copy={productCopy(lang).nav}
      route="/register"
      go={go}
    />
    <main className="pav2-access-main">
      <section className="pav2-access-story">
        <span className="pav2-eyebrow">{copy.eyebrow}</span>
        <h1>{copy.title}</h1>
        <p>{copy.lead}</p>
        <div className="pav2-market-preview">
          {(["AM", "RU"] as const).map((code) => {
            const market = plans.markets[code];
            return <article key={code} className={country === market.name ? "selected" : ""}>
              <header><b>{code}</b><span>{market.name}</span></header>
              <div><small>{copy.funding} · {copy.first}</small><strong>{money(market.funding_price, market.currency)}</strong><span>{copy.monthly}</span></div>
              <footer><small>{copy.standard}</small><b>{money(market.standard_price, market.currency)}</b></footer>
            </article>;
          })}
        </div>
        <div className="pav2-continuity"><ShieldCheck/><div><b>{copy.retained}</b><p>{copy.retainedText}</p></div></div>
      </section>

      <section className="pav2-request-card">
        {done ? <div className="pav2-success"><span><Check/></span><h2>Request submitted</h2><p>Your application is waiting for review. If approved, Teta2 will automatically select the Armenia or Russia pricing email from the country in your request.</p><button onClick={() => go("/")} className="pav2-primary">Back to Teta2</button></div> : <>
          <div className="pav2-card-head"><div><small>{copy.application}</small><h2>{copy.request}</h2></div><span>01 / 03</span></div>
          <form onSubmit={submit} className="pav2-form">
            <label className="wide"><span>Clinic name *</span><input name="clinic_name" required minLength={2}/></label>
            <label><span>Country *</span><select name="country" required value={country} onChange={(e)=>setCountry(e.target.value)}><option value="">Select market</option><option value="Armenia">Armenia</option><option value="Russia">Russia</option></select></label>
            <label><span>City *</span><input name="city" required/></label>
            {selectedMarket && <div className="pav2-live-price wide"><span><Activity/>Pricing selected from country</span><strong>{money(selectedMarket.funding_price, selectedMarket.currency)}</strong><small>{copy.funding} · eligibility confirmed during review · standard {money(selectedMarket.standard_price, selectedMarket.currency)}</small></div>}
            <label className="wide"><span>Clinic address</span><input name="address"/></label>
            <label className="wide"><span>Website</span><input name="website" type="url" placeholder="https://"/></label>
            <label><span>Contact person *</span><input name="contact_name" required/></label>
            <label><span>Role / title *</span><input name="contact_role" required placeholder="Director, owner, dentist…"/></label>
            <label><span>Email *</span><input name="email" type="email" required/></label>
            <label><span>Phone *</span><input name="phone" required/></label>
            <label><span>Number of dentists *</span><input name="dentists_count" type="number" min="1" defaultValue="1" required/></label>
            <label><span>Number of branches *</span><input name="branches_count" type="number" min="1" defaultValue="1" required/></label>
            <label className="wide"><span>Anything we should know?</span><textarea name="notes" rows={4}/></label>
            {error && <div className="pav2-error wide">{error}</div>}
            <div className="pav2-form-footer wide"><p>Funding Plan availability is confirmed during review. Submission does not reserve a slot or activate access.</p><button className="pav2-primary" disabled={busy}>{busy ? <Activity className="spin"/> : <Send/>}{busy ? "…" : copy.submit}</button></div>
          </form>
        </>}
      </section>
    </main>
    <PublicFooter copy={productCopy(lang).nav} description={lang === "hy" ? "AI-ով OPG ինտելեկտ և պացիենտի follow-up։" : lang === "ru" ? "ИИ-анализ OPG и follow-up пациентов." : "AI-powered OPG intelligence and patient follow-up."} language={lang} go={go}/>
  </div>;
}

function PlatformAdmin() {
  const [token, setToken] = useState(() => sessionStorage.getItem(ADMIN_SESSION_KEY) || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [plans, setPlans] = useState<MarketPlans>(FALLBACK_PLANS);
  const [tab, setTab] = useState<"overview"|"requests"|"clinics"|"settings">("overview");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [authBusy, setAuthBusy] = useState(false);

  const load = useCallback(async (authToken: string) => {
    const [o, r, c, s, p] = await Promise.all([
      adminJson<Overview>("/api/v1/platform/admin/overview", authToken),
      adminJson<AccessRequest[]>("/api/v1/platform/admin/access-requests", authToken),
      adminJson<Clinic[]>("/api/v1/platform/admin/clinics", authToken),
      adminJson<PlatformSettings>("/api/v1/platform/admin/settings", authToken),
      publicJson<MarketPlans>("/api/v1/platform/market/plans").catch(() => FALLBACK_PLANS),
    ]);
    setOverview(o); setRequests(r); setClinics(c); setSettings(s); setPlans(p); setAuthenticated(true); setError("");
  }, []);

  useEffect(() => {
    if (!token || authenticated) return;
    void load(token).catch(() => { sessionStorage.removeItem(ADMIN_SESSION_KEY); setToken(""); setAuthenticated(false); });
  }, [authenticated, load, token]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setAuthBusy(true); setError("");
    try {
      const session = await publicJson<{access_token: string}>("/api/v1/platform/admin/login", { method: "POST", body: JSON.stringify({ email: email.trim(), password }) });
      sessionStorage.setItem(ADMIN_SESSION_KEY, session.access_token);
      setToken(session.access_token); setPassword(""); await load(session.access_token);
    } catch (reason) {
      sessionStorage.removeItem(ADMIN_SESSION_KEY); setToken(""); setAuthenticated(false); setError(reason instanceof Error ? reason.message : "Admin authentication failed");
    } finally { setAuthBusy(false); }
  }

  function logoutAdmin() {
    sessionStorage.removeItem(ADMIN_SESSION_KEY);
    setToken(""); setAuthenticated(false); setOverview(null); setRequests([]); setClinics([]); setSettings(null); setPassword("");
  }

  async function action(path: string, body: unknown = {}) {
    setBusy(path); setError("");
    try { await adminJson(`/api/v1/platform/${path}`, token, { method: "POST", body: JSON.stringify(body) }); await load(token); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Action failed"); }
    finally { setBusy(""); }
  }

  const marketCounts = useMemo(() => requests.reduce((acc, row) => {
    const market = requestMarket(row);
    if (market) acc[market] += 1;
    return acc;
  }, { AM: 0, RU: 0 }), [requests]);

  if (!authenticated) return <main className="pav2-overlay pav2-admin-login"><section className="pav2-admin-login-card"><Brand/><span className="pav2-eyebrow">PLATFORM ADMINISTRATION</span><h1>Control the clinic pipeline.</h1><p>Secure access for request review, market-aware payment email routing, subscriptions and clinic provisioning.</p><div className="pav2-admin-login-signal"><ShieldCheck/><span>Country-aware pricing</span><b>AM / RU</b></div><form onSubmit={login}><label>Administrator email<input type="email" value={email} onChange={(e)=>setEmail(e.target.value)} autoFocus autoComplete="username" required/></label><label>Password<input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} autoComplete="current-password" required/></label><button className="pav2-primary" disabled={authBusy}>{authBusy?"Signing in…":"Open control center"}</button></form>{error&&<div className="pav2-error">{error}</div>}<button className="pav2-link" onClick={()=>go("/")}>Back to website</button></section></main>;

  return <main className="pav2-overlay pav2-admin-shell">
    <aside className="pav2-admin-side"><Brand/><nav>{(["overview","requests","clinics","settings"] as const).map((item)=><button key={item} className={tab===item?"active":""} onClick={()=>setTab(item)}>{item==="overview"?<Activity/>:item==="requests"?<Mail/>:item==="clinics"?<Building2/>:<CreditCard/>}<span>{item[0].toUpperCase()+item.slice(1)}</span>{item==="requests"&&overview?.metrics.requests_pending?<i>{overview.metrics.requests_pending}</i>:null}</button>)}</nav><button className="pav2-admin-exit" onClick={logoutAdmin}><X/>Sign out</button></aside>
    <section className="pav2-admin-main">
      <header><div><small>TETA2 PLATFORM</small><h1>{tab[0].toUpperCase()+tab.slice(1)}</h1></div><div className="pav2-market-pulse"><span>AM <b>{marketCounts.AM}</b></span><span>RU <b>{marketCounts.RU}</b></span><button onClick={()=>void load(token)} title="Refresh"><RefreshCw/></button></div></header>
      {error&&<div className="pav2-error">{error}</div>}
      {tab==="overview"&&<OverviewPanel overview={overview} plans={plans}/>} 
      {tab==="requests"&&<RequestsPanel rows={requests} plans={plans} busy={busy} action={action}/>} 
      {tab==="clinics"&&<ClinicsPanel rows={clinics} busy={busy} action={action}/>} 
      {tab==="settings"&&settings&&<SettingsPanel value={settings} plans={plans} token={token} onSaved={()=>load(token)} setError={setError}/>} 
    </section>
  </main>;
}

function OverviewPanel({overview, plans}:{overview:Overview|null;plans:MarketPlans}) {
  if(!overview) return <div className="pav2-loading"><Activity className="spin"/>Loading platform…</div>;
  const cards=[["Active clinics",overview.metrics.clinics_active],["Pending requests",overview.metrics.requests_pending],["Visits · 24h",overview.metrics.visits_24h],["Unique visitors · 30d",overview.metrics.unique_visitors_30d]];
  return <><div className="pav2-metrics">{cards.map(([label,value])=><article key={String(label)}><small>{label}</small><strong>{value}</strong></article>)}</div><div className="pav2-market-summary">{(["AM","RU"] as const).map(code=><article key={code}><span>{code}</span><div><small>{plans.markets[code].name}</small><strong>{money(plans.markets[code].funding_price,plans.markets[code].currency)}</strong><p>Funding · first {plans.funding_limit}</p></div><div><small>Standard</small><b>{money(plans.markets[code].standard_price,plans.markets[code].currency)}</b></div></article>)}</div><div className="pav2-admin-two"><section className="pav2-panel"><div className="pav2-panel-title"><ShieldCheck/><div><small>SYSTEM HEALTH</small><h3>Platform services</h3></div></div>{Object.entries(overview.health).map(([key,value])=><div className="pav2-health-row" key={key}><span>{key.replaceAll("_"," ")}</span><b className={value===true||value==="HEALTHY"?"good":"warn"}>{String(value)}</b></div>)}</section><section className="pav2-panel"><div className="pav2-panel-title"><Activity/><div><small>TRAFFIC</small><h3>Most visited routes</h3></div></div>{overview.top_routes.length?overview.top_routes.map(([path,count])=><div className="pav2-health-row" key={path}><span>{path}</span><b>{count}</b></div>):<p className="pav2-muted">Traffic data will appear as visits are recorded.</p>}</section></div><section className="pav2-panel"><div className="pav2-panel-title"><Mail/><div><small>EMAIL OPERATIONS</small><h3>Recent platform email</h3></div></div><div className="pav2-table"><div className="pav2-table-head"><span>Type</span><span>Recipient</span><span>Status</span><span>Time</span></div>{overview.recent_emails.map(e=><div className="pav2-table-row" key={e.id}><span>{e.kind.replaceAll("_"," ")}</span><span>{e.recipient}</span><span className={`pav2-status ${e.status.toLowerCase()}`}>{e.status}</span><span>{new Date(e.created_at).toLocaleString()}</span></div>)}</div></section></>;
}

function RequestsPanel({rows,plans,busy,action}:{rows:AccessRequest[];plans:MarketPlans;busy:string;action:(path:string,body?:unknown)=>Promise<void>}) {
  const [selected,setSelected]=useState<string>(rows[0]?.id||"");
  useEffect(()=>{if(!selected&&rows[0])setSelected(rows[0].id)},[rows,selected]);
  const row=rows.find(r=>r.id===selected)||rows[0];
  const market=row?requestMarket(row):null;
  const marketPlan=market?plans.markets[market]:null;
  return <div className="pav2-request-workspace"><aside>{rows.map(r=>{const code=requestMarket(r);return <button key={r.id} className={r.id===row?.id?"active":""} onClick={()=>setSelected(r.id)}><div><b>{r.clinic_name}</b>{code&&<em className={`market-${code.toLowerCase()}`}>{code}</em>}</div><span>{r.contact_name} · {r.country}</span><small>{r.status.replaceAll("_"," ")}</small></button>})}{!rows.length&&<p className="pav2-muted">No access requests yet.</p>}</aside>{row&&<section className="pav2-panel pav2-request-detail"><header><div><small>ACCESS REQUEST</small><h2>{row.clinic_name}</h2><p>{row.city}, {row.country}</p></div><div className="pav2-request-badges">{market?<span className={`pav2-market-badge market-${market.toLowerCase()}`}>{market} · {marketPlan?.name}</span>:<span className="pav2-market-badge unsupported">UNMAPPED MARKET</span>}<span className={`pav2-status ${row.status.toLowerCase()}`}>{row.status.replaceAll("_"," ")}</span></div></header>{marketPlan&&<div className="pav2-auto-email"><Mail/><div><small>AUTOMATIC PAYMENT EMAIL</small><b>{marketPlan.name} pricing will be selected from the registered country.</b><p>Funding: {money(marketPlan.funding_price,marketPlan.currency)} · first {plans.funding_limit} clinics. Standard: {money(marketPlan.standard_price,marketPlan.currency)}.</p></div></div>}{!market&&<div className="pav2-warning"><CircleAlert/><span>Country/address cannot be mapped to Armenia or Russia. Correct the application before sending payment instructions.</span></div>}<div className="pav2-detail-grid"><div><small>Contact</small><b>{row.contact_name}</b><span>{row.contact_role}</span></div><div><small>Email</small><b>{row.email}</b><span>{row.phone}</span></div><div><small>Clinic size</small><b>{row.dentists_count} dentists</b><span>{row.branches_count} branches</span></div><div><small>Submitted</small><b>{new Date(row.created_at).toLocaleDateString()}</b><span>{row.website||"No website"}</span></div></div>{row.notes&&<div className="pav2-note"><small>Applicant note</small><p>{row.notes}</p></div>}<div className="pav2-request-actions">{row.status==="SUBMITTED"&&<><button className="pav2-danger" disabled={!!busy} onClick={()=>void action(`admin/access-requests/${row.id}/reject`,{note:"Rejected from admin panel"})}>Reject</button><button className="pav2-primary" disabled={!!busy||!market} onClick={()=>void action(`market/admin/access-requests/${row.id}/send-payment`,{})}><Send/>Approve & send {market??"market"} pricing email</button></>}{["PAYMENT_REQUESTED","PAYMENT_REVIEW"].includes(row.status)&&<><button className="pav2-secondary" disabled={!!busy} onClick={()=>void action(`admin/access-requests/${row.id}/payment-received`,{proof_note:"Payment receipt received by email; awaiting final verification."})}>Mark receipt received</button><button className="pav2-primary" disabled={!!busy} onClick={()=>{const reference=window.prompt("Payment reference / bank transaction ID (optional)",row.payment_reference||"")||"";void action(`admin/access-requests/${row.id}/activate`,{reference,proof_note:"Payment verified by platform administrator."})}}><Check/>Verify payment & activate 30 days</button></>}{row.status==="ACTIVE"&&<div className="pav2-complete"><Check/>Clinic activated and credentials email sent.</div>}{row.status==="REJECTED"&&<div className="pav2-muted">This request was rejected.</div>}</div></section>}</div>;
}

function ClinicsPanel({rows,busy,action}:{rows:Clinic[];busy:string;action:(path:string,body?:unknown)=>Promise<void>}) {
  return <section className="pav2-panel"><div className="pav2-panel-title"><Building2/><div><small>CLINIC DIRECTORY</small><h3>{rows.length} registered clinics</h3></div></div><div className="pav2-clinic-list">{rows.map(c=><article key={c.id}><div className="pav2-clinic-icon"><Building2/></div><div><b>{c.name}</b><span>{c.slug}</span></div><div><small>Plan</small><b>{c.subscription_plan==="TETA2_CARE"?"Teta2":c.subscription_plan}</b></div><div><small>Access</small><b>{c.subscription_expires_at?new Date(c.subscription_expires_at).toLocaleDateString():"Legacy / no expiry"}</b><span>{c.days_remaining!=null?`${c.days_remaining} days remaining`:""}</span></div><span className={`pav2-status ${c.is_active?"sent":"failed"}`}>{c.is_active?"ACTIVE":"EXPIRED"}</span><button className="pav2-secondary" disabled={!!busy} onClick={()=>void action(`admin/clinics/${c.id}/renew`,{days:30})}><RefreshCw/>Renew +30 days</button></article>)}</div></section>;
}

function SettingsPanel({value,plans,token,onSaved,setError}:{value:PlatformSettings;plans:MarketPlans;token:string;onSaved:()=>Promise<void>;setError:(v:string)=>void}) {
  const [form,setForm]=useState(value); const [busy,setBusy]=useState(false);
  useEffect(()=>setForm(value),[value]);
  const update=(key:keyof PlatformSettings,val:string|number)=>setForm(prev=>({...prev,[key]:val}));
  async function save(){setBusy(true);setError("");try{await adminJson("/api/v1/platform/admin/settings",token,{method:"PUT",body:JSON.stringify({price_amount:49000,price_currency:"AMD",payment_recipient:form.payment_recipient,payment_card:form.payment_card,payment_bank_details:form.payment_bank_details,payment_email_subject:form.payment_email_subject,payment_email_intro:form.payment_email_intro,activation_email_subject:form.activation_email_subject,activation_email_intro:form.activation_email_intro})});await onSaved()}catch(e){setError(e instanceof Error?e.message:"Could not save settings")}finally{setBusy(false)}}
  return <section className="pav2-settings"><div className="pav2-settings-market-grid">{(["AM","RU"] as const).map(code=><article key={code}><span>{code}</span><div><small>{plans.markets[code].name} · market-routed email</small><h3>{money(plans.markets[code].funding_price,plans.markets[code].currency)}</h3><p>Funding Plan · first {plans.funding_limit} clinics</p><b>Standard {money(plans.markets[code].standard_price,plans.markets[code].currency)}</b></div></article>)}</div><div className="pav2-routing-note"><Mail/><div><small>PAYMENT EMAIL ROUTING</small><b>Armenia and Russia use separate pricing email copy automatically.</b><p>The request country chooses the market email. Common payment recipient/card/bank details below are shared until separate payment accounts are configured.</p></div></div><section className="pav2-panel pav2-settings-panel"><div className="pav2-panel-title"><CreditCard/><div><small>COMMON PAYMENT DESTINATION</small><h3>Payment & activation settings</h3></div></div><div className="pav2-settings-grid"><label className="wide"><span>Payment recipient</span><input value={form.payment_recipient} onChange={e=>update("payment_recipient",e.target.value)}/></label><label className="wide"><span>Card / payment number</span><input value={form.payment_card} onChange={e=>update("payment_card",e.target.value)} placeholder="Payment card or account number"/></label><label className="wide"><span>Bank / transfer details</span><textarea rows={4} value={form.payment_bank_details} onChange={e=>update("payment_bank_details",e.target.value)}/></label><label className="wide"><span>Activation email subject</span><input value={form.activation_email_subject} onChange={e=>update("activation_email_subject",e.target.value)}/></label><label className="wide"><span>Activation email introduction</span><textarea rows={5} value={form.activation_email_intro} onChange={e=>update("activation_email_intro",e.target.value)}/></label></div><button className="pav2-primary pav2-save" disabled={busy} onClick={()=>void save()}><Save/>{busy?"Saving…":"Save shared payment settings"}</button></section></section>;
}
