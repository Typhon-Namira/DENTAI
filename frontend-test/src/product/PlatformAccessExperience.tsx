import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Activity,
  Building2,
  Check,
  CreditCard,
  HeartPulse,
  Mail,
  RefreshCw,
  Save,
  Send,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

import { API_BASE_URL } from "../api/client";

const ADMIN_TOKEN_KEY = "teta2-platform-admin-token";

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
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.headers || {}),
    },
  });
}

function routeIs(path: string) {
  return window.location.pathname === path;
}

function go(path: string) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function PlatformAccessExperience() {
  const [route, setRoute] = useState(window.location.pathname);
  useEffect(() => {
    const onRoute = () => setRoute(window.location.pathname);
    window.addEventListener("popstate", onRoute);
    return () => window.removeEventListener("popstate", onRoute);
  }, []);

  useEffect(() => {
    const hideLegacyPlans = () => {
      document.querySelectorAll(".product-plan-grid > article:not(.featured), .product-pricing-grid > article:not(.featured)").forEach((node) => {
        (node as HTMLElement).style.display = "none";
      });
      document.querySelectorAll(".product-plan-grid, .product-pricing-grid").forEach((node) => node.classList.add("care-only-grid"));
    };
    hideLegacyPlans();
    const observer = new MutationObserver(hideLegacyPlans);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  if (route === "/register" || route === "/request-access") return <AccessRequestPage />;
  if (route === "/platform-admin") return <PlatformAdmin />;
  return null;
}

function Brand() {
  return <div className="pa-brand"><span><HeartPulse /></span><div><strong>Teta2 Care</strong><small>Clinic access</small></div></div>;
}

function AccessRequestPage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [plan, setPlan] = useState<{ name: string; period_days: number; price_amount: number; price_currency: string } | null>(null);

  useEffect(() => {
    void publicJson<typeof plan>("/api/v1/platform/public-plan").then(setPlan).catch(() => undefined);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    const value = (key: string) => String(form.get(key) || "").trim();
    try {
      await publicJson("/api/v1/platform/access-requests", {
        method: "POST",
        body: JSON.stringify({
          clinic_name: value("clinic_name"), country: value("country"), city: value("city"), address: value("address") || null,
          website: value("website") || null, contact_name: value("contact_name"), contact_role: value("contact_role"),
          email: value("email"), phone: value("phone"), dentists_count: Number(value("dentists_count") || 1),
          branches_count: Number(value("branches_count") || 1), notes: value("notes") || null,
        }),
      });
      setDone(true);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not submit request"); }
    finally { setBusy(false); }
  }

  return <main className="pa-overlay pa-access-page">
    <header className="pa-public-head"><button onClick={() => go("/")} className="pa-plain"><Brand /></button><button onClick={() => go("/login")} className="pa-link">Clinic login</button></header>
    <section className="pa-access-layout">
      <aside className="pa-access-story">
        <span className="pa-eyebrow">REQUEST ACCESS</span>
        <h1>Bring your clinic into Teta2 Care.</h1>
        <p>Submit one secure application. Our team reviews the clinic, sends payment instructions, verifies payment, and activates the same clinic workspace for a fixed 30-day subscription period.</p>
        <div className="pa-single-plan"><HeartPulse/><div><small>THE ONLY TETA2 PLAN</small><strong>Teta2 Care</strong><span>{plan ? `${plan.price_amount.toLocaleString()} ${plan.price_currency} · ${plan.period_days} days` : "30-day clinic subscription"}</span></div></div>
        <div className="pa-flow-note"><ShieldCheck/><div><b>Data is retained between renewals</b><p>When access expires, the clinic dashboard is locked—not deleted. Renewal restores the same patients, analyses, follow-ups, conversations and history.</p></div></div>
      </aside>
      <section className="pa-request-card">
        {done ? <div className="pa-success"><span><Check/></span><h2>Request submitted</h2><p>Your application is now waiting for review. If approved, payment instructions will be sent to the email you provided.</p><button onClick={() => go("/")} className="pa-primary">Back to Teta2</button></div> : <>
          <div className="pa-card-head"><div><small>CLINIC APPLICATION</small><h2>Access request</h2></div><span>Step 1 of 3</span></div>
          <form onSubmit={submit} className="pa-form">
            <label className="wide"><span>Clinic name *</span><input name="clinic_name" required minLength={2}/></label>
            <label><span>Country *</span><input name="country" required/></label><label><span>City *</span><input name="city" required/></label>
            <label className="wide"><span>Clinic address</span><input name="address"/></label>
            <label className="wide"><span>Website</span><input name="website" type="url" placeholder="https://"/></label>
            <label><span>Contact person *</span><input name="contact_name" required/></label><label><span>Role / title *</span><input name="contact_role" required placeholder="Director, owner, dentist…"/></label>
            <label><span>Email *</span><input name="email" type="email" required/></label><label><span>Phone *</span><input name="phone" required/></label>
            <label><span>Number of dentists *</span><input name="dentists_count" type="number" min="1" defaultValue="1" required/></label><label><span>Number of branches *</span><input name="branches_count" type="number" min="1" defaultValue="1" required/></label>
            <label className="wide"><span>Anything we should know?</span><textarea name="notes" rows={4}/></label>
            {error && <div className="pa-error wide">{error}</div>}
            <div className="pa-form-footer wide"><p>By submitting, you confirm that the information belongs to a legitimate clinic and may be reviewed for platform access.</p><button className="pa-primary" disabled={busy}>{busy ? <Activity className="spin"/> : <Send/>}{busy ? "Submitting…" : "Submit access request"}</button></div>
          </form>
        </>}
      </section>
    </section>
  </main>;
}

function PlatformAdmin() {
  const [token, setToken] = useState(() => sessionStorage.getItem(ADMIN_TOKEN_KEY) || "");
  const [authenticated, setAuthenticated] = useState(false);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [tab, setTab] = useState<"overview"|"requests"|"clinics"|"settings">("overview");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(async (authToken = token) => {
    const [o, r, c, s] = await Promise.all([
      adminJson<Overview>("/api/v1/platform/admin/overview", authToken),
      adminJson<AccessRequest[]>("/api/v1/platform/admin/access-requests", authToken),
      adminJson<Clinic[]>("/api/v1/platform/admin/clinics", authToken),
      adminJson<PlatformSettings>("/api/v1/platform/admin/settings", authToken),
    ]);
    setOverview(o); setRequests(r); setClinics(c); setSettings(s); setAuthenticated(true); setError("");
  }, [token]);

  async function login(event: FormEvent) {
    event.preventDefault();
    try { await load(token); sessionStorage.setItem(ADMIN_TOKEN_KEY, token); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Admin authentication failed"); }
  }

  async function action(id: string, name: string, body: unknown = {}) {
    setBusy(`${name}-${id}`); setError("");
    try {
      await adminJson(`/api/v1/platform/admin/${name}`, token, { method: "POST", body: JSON.stringify(body) });
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Action failed"); }
    finally { setBusy(""); }
  }

  if (!authenticated) return <main className="pa-overlay pa-admin-login"><section><Brand/><span className="pa-eyebrow">PLATFORM ADMINISTRATION</span><h1>Admin control center</h1><p>Enter the private platform administrator token.</p><form onSubmit={login}><input type="password" value={token} onChange={(e)=>setToken(e.target.value)} autoFocus placeholder="Platform admin token"/><button className="pa-primary">Open admin panel</button></form>{error&&<div className="pa-error">{error}</div>}<button className="pa-link" onClick={()=>go("/")}>Back to website</button></section></main>;

  return <main className="pa-overlay pa-admin-shell">
    <aside className="pa-admin-side"><Brand/><nav>{(["overview","requests","clinics","settings"] as const).map((item)=><button key={item} className={tab===item?"active":""} onClick={()=>setTab(item)}>{item==="overview"?<Activity/>:item==="requests"?<Mail/>:item==="clinics"?<Building2/>:<CreditCard/>}<span>{item[0].toUpperCase()+item.slice(1)}</span>{item==="requests"&&overview?.metrics.requests_pending?<i>{overview.metrics.requests_pending}</i>:null}</button>)}</nav><button className="pa-admin-exit" onClick={()=>go("/")}><X/>Exit admin</button></aside>
    <section className="pa-admin-main">
      <header><div><small>TETA2 PLATFORM</small><h1>{tab[0].toUpperCase()+tab.slice(1)}</h1></div><button onClick={()=>void load()} className="pa-icon" title="Refresh"><RefreshCw/></button></header>
      {error&&<div className="pa-error">{error}</div>}
      {tab==="overview"&&<OverviewPanel overview={overview}/>} 
      {tab==="requests"&&<RequestsPanel rows={requests} busy={busy} action={action}/>} 
      {tab==="clinics"&&<ClinicsPanel rows={clinics} busy={busy} action={action}/>} 
      {tab==="settings"&&settings&&<SettingsPanel value={settings} token={token} onSaved={load} setError={setError}/>} 
    </section>
  </main>;
}

function OverviewPanel({overview}:{overview:Overview|null}) {
  if(!overview) return <div className="pa-loading"><Activity className="spin"/>Loading platform…</div>;
  const cards=[
    ["Active clinics",overview.metrics.clinics_active],["Pending requests",overview.metrics.requests_pending],["Visits · 24h",overview.metrics.visits_24h],["Unique visitors · 30d",overview.metrics.unique_visitors_30d],
  ];
  return <><div className="pa-metrics">{cards.map(([label,value])=><article key={String(label)}><small>{label}</small><strong>{value}</strong></article>)}</div><div className="pa-admin-two"><section className="pa-panel"><div className="pa-panel-title"><ShieldCheck/><div><small>SYSTEM HEALTH</small><h3>Platform services</h3></div></div>{Object.entries(overview.health).map(([key,value])=><div className="pa-health-row" key={key}><span>{key.replaceAll("_"," ")}</span><b className={value===true||value==="HEALTHY"?"good":"warn"}>{String(value)}</b></div>)}</section><section className="pa-panel"><div className="pa-panel-title"><Activity/><div><small>TRAFFIC</small><h3>Most visited routes</h3></div></div>{overview.top_routes.length?overview.top_routes.map(([path,count])=><div className="pa-health-row" key={path}><span>{path}</span><b>{count}</b></div>):<p className="pa-muted">Traffic data will appear as visits are recorded.</p>}</section></div><section className="pa-panel"><div className="pa-panel-title"><Mail/><div><small>EMAIL OPERATIONS</small><h3>Recent platform email</h3></div></div><div className="pa-table"><div className="pa-table-head"><span>Type</span><span>Recipient</span><span>Status</span><span>Time</span></div>{overview.recent_emails.map(e=><div className="pa-table-row" key={e.id}><span>{e.kind.replaceAll("_"," ")}</span><span>{e.recipient}</span><span className={`pa-status ${e.status.toLowerCase()}`}>{e.status}</span><span>{new Date(e.created_at).toLocaleString()}</span></div>)}</div></section></>;
}

function RequestsPanel({rows,busy,action}:{rows:AccessRequest[];busy:string;action:(id:string,name:string,body?:unknown)=>Promise<void>}) {
  const [selected,setSelected]=useState<string>(rows[0]?.id||"");
  useEffect(()=>{if(!selected&&rows[0])setSelected(rows[0].id)},[rows,selected]);
  const row=rows.find(r=>r.id===selected)||rows[0];
  return <div className="pa-request-workspace"><aside>{rows.map(r=><button key={r.id} className={r.id===row?.id?"active":""} onClick={()=>setSelected(r.id)}><b>{r.clinic_name}</b><span>{r.contact_name} · {r.country}</span><em>{r.status.replaceAll("_"," ")}</em></button>)}{!rows.length&&<p className="pa-muted">No access requests yet.</p>}</aside>{row&&<section className="pa-panel pa-request-detail"><header><div><small>ACCESS REQUEST</small><h2>{row.clinic_name}</h2><p>{row.city}, {row.country}</p></div><span className={`pa-status ${row.status.toLowerCase()}`}>{row.status.replaceAll("_"," ")}</span></header><div className="pa-detail-grid"><div><small>Contact</small><b>{row.contact_name}</b><span>{row.contact_role}</span></div><div><small>Email</small><b>{row.email}</b><span>{row.phone}</span></div><div><small>Clinic size</small><b>{row.dentists_count} dentists</b><span>{row.branches_count} branches</span></div><div><small>Submitted</small><b>{new Date(row.created_at).toLocaleDateString()}</b><span>{row.website||"No website"}</span></div></div>{row.notes&&<div className="pa-note"><small>Applicant note</small><p>{row.notes}</p></div>}<div className="pa-request-actions">{row.status==="SUBMITTED"&&<><button className="pa-danger" disabled={!!busy} onClick={()=>void action(row.id,`access-requests/${row.id}/reject`,{note:"Rejected from admin panel"})}>Reject</button><button className="pa-primary" disabled={!!busy} onClick={()=>void action(row.id,`access-requests/${row.id}/send-payment`,{})}><Send/>Approve & send payment email</button></>}{["PAYMENT_REQUESTED","PAYMENT_REVIEW"].includes(row.status)&&<><button className="pa-secondary" disabled={!!busy} onClick={()=>void action(row.id,`access-requests/${row.id}/payment-received`,{proof_note:"Payment receipt received by email; awaiting final verification."})}>Mark receipt received</button><button className="pa-primary" disabled={!!busy} onClick={()=>{const reference=window.prompt("Payment reference / bank transaction ID (optional)",row.payment_reference||"")||"";void action(row.id,`access-requests/${row.id}/activate`,{reference,proof_note:"Payment verified by platform administrator."})}}><Check/>Verify payment & activate 30 days</button></>}{row.status==="ACTIVE"&&<div className="pa-complete"><Check/>Clinic activated and credentials email sent.</div>}{row.status==="REJECTED"&&<div className="pa-muted">This request was rejected.</div>}</div></section>}</div>;
}

function ClinicsPanel({rows,busy,action}:{rows:Clinic[];busy:string;action:(id:string,name:string,body?:unknown)=>Promise<void>}) {
  return <section className="pa-panel"><div className="pa-panel-title"><Building2/><div><small>CLINIC DIRECTORY</small><h3>{rows.length} registered clinics</h3></div></div><div className="pa-clinic-list">{rows.map(c=><article key={c.id}><div className="pa-clinic-icon"><Building2/></div><div><b>{c.name}</b><span>{c.slug}</span></div><div><small>Plan</small><b>{c.subscription_plan==="TETA2_CARE"?"Teta2 Care":c.subscription_plan}</b></div><div><small>Access</small><b>{c.subscription_expires_at?new Date(c.subscription_expires_at).toLocaleDateString():"Legacy / no expiry"}</b><span>{c.days_remaining!=null?`${c.days_remaining} days remaining`:""}</span></div><span className={`pa-status ${c.is_active?"sent":"failed"}`}>{c.is_active?"ACTIVE":"EXPIRED"}</span><button className="pa-secondary" disabled={!!busy} onClick={()=>void action(c.id,`clinics/${c.id}/renew`,{days:30})}><RefreshCw/>Renew +30 days</button></article>)}</div></section>;
}

function SettingsPanel({value,token,onSaved,setError}:{value:PlatformSettings;token:string;onSaved:()=>Promise<void>;setError:(v:string)=>void}) {
  const [form,setForm]=useState(value); const [busy,setBusy]=useState(false);
  useEffect(()=>setForm(value),[value]);
  const update=(key:keyof PlatformSettings,val:string|number)=>setForm(prev=>({...prev,[key]:val}));
  async function save(){setBusy(true);setError("");try{await adminJson("/api/v1/platform/admin/settings",token,{method:"PUT",body:JSON.stringify({price_amount:form.price_amount,price_currency:form.price_currency,payment_recipient:form.payment_recipient,payment_card:form.payment_card,payment_bank_details:form.payment_bank_details,payment_email_subject:form.payment_email_subject,payment_email_intro:form.payment_email_intro,activation_email_subject:form.activation_email_subject,activation_email_intro:form.activation_email_intro})});await onSaved()}catch(e){setError(e instanceof Error?e.message:"Could not save settings")}finally{setBusy(false)}}
  return <section className="pa-panel pa-settings"><div className="pa-settings-fixed"><ShieldCheck/><div><small>FIXED PRODUCT RULE</small><b>Teta2 Care · 30-day access periods</b><p>The product name and 30-day subscription lifecycle are fixed. Price, payment destination and email copy are editable.</p></div></div><div className="pa-settings-grid"><label><span>Subscription price</span><input type="number" value={form.price_amount} onChange={e=>update("price_amount",Number(e.target.value))}/></label><label><span>Currency</span><input value={form.price_currency} onChange={e=>update("price_currency",e.target.value)}/></label><label className="wide"><span>Payment recipient</span><input value={form.payment_recipient} onChange={e=>update("payment_recipient",e.target.value)}/></label><label className="wide"><span>Card / payment number</span><input value={form.payment_card} onChange={e=>update("payment_card",e.target.value)} placeholder="Editable payment card or account number"/></label><label className="wide"><span>Bank / transfer details</span><textarea rows={4} value={form.payment_bank_details} onChange={e=>update("payment_bank_details",e.target.value)}/></label><label className="wide"><span>Payment email subject</span><input value={form.payment_email_subject} onChange={e=>update("payment_email_subject",e.target.value)}/></label><label className="wide"><span>Payment email introduction</span><textarea rows={5} value={form.payment_email_intro} onChange={e=>update("payment_email_intro",e.target.value)}/></label><label className="wide"><span>Activation email subject</span><input value={form.activation_email_subject} onChange={e=>update("activation_email_subject",e.target.value)}/></label><label className="wide"><span>Activation email introduction</span><textarea rows={5} value={form.activation_email_intro} onChange={e=>update("activation_email_intro",e.target.value)}/></label></div><button className="pa-primary pa-save" disabled={busy} onClick={()=>void save()}><Save/>{busy?"Saving…":"Save platform settings"}</button></section>;
}
