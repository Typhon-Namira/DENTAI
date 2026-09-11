import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Activity,
  Building2,
  Check,
  ChevronRight,
  Database,
  FileCheck2,
  HeartPulse,
  LayoutDashboard,
  LogOut,
  Mail,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Users,
  WalletCards,
  X,
  XCircle
} from "lucide-react";
import { errorMessage } from "../api/client";
import {
  clearPlatformAdminSession,
  hasPlatformAdminSession,
  platformApi,
  type BillingSettings,
  type PlatformAccessRequest,
  type PlatformClinic,
  type PlatformEvent,
  type PlatformHealth,
  type PlatformOverview
} from "../api/platform";
import type { Lang } from "../i18n";
import { Teta2Logo } from "./Teta2Logo";

type Section = "overview" | "requests" | "clinics" | "health" | "billing" | "activity";

function fmt(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function statusLabel(value: string): string {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function splitName(value: string): [string, string] {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length <= 1) return [parts[0] || "Clinic", "Director"];
  return [parts[0], parts.slice(1).join(" ")];
}

export function AdminPanel({ lang, setLang, onExit }: { lang: Lang; setLang: (lang: Lang) => void; onExit: () => void }) {
  const [authenticated, setAuthenticated] = useState(hasPlatformAdminSession());
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [section, setSection] = useState<Section>("overview");
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [requests, setRequests] = useState<PlatformAccessRequest[]>([]);
  const [clinics, setClinics] = useState<PlatformClinic[]>([]);
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [events, setEvents] = useState<PlatformEvent[]>([]);
  const [billing, setBilling] = useState<BillingSettings | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<PlatformAccessRequest | null>(null);
  const [selectedClinic, setSelectedClinic] = useState<PlatformClinic | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [emailPreview, setEmailPreview] = useState<{ subject?: string; body?: string } | null>(null);

  const load = useCallback(async () => {
    if (!hasPlatformAdminSession()) return;
    const results = await Promise.all([
      platformApi.overview(),
      platformApi.requests(),
      platformApi.clinics(),
      platformApi.health(),
      platformApi.events(),
      platformApi.billingSettings()
    ]);
    setOverview(results[0]);
    setRequests(results[1]);
    setClinics(results[2]);
    setHealth(results[3]);
    setEvents(results[4]);
    setBilling(results[5]);
  }, []);

  useEffect(() => {
    if (!authenticated) return;
    void load().catch((reason) => {
      setError(errorMessage(reason));
      if (!hasPlatformAdminSession()) setAuthenticated(false);
    });
  }, [authenticated, load]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await platformApi.adminLogin(email, password);
      setPassword("");
      setAuthenticated(true);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearPlatformAdminSession();
    setAuthenticated(false);
    setOverview(null);
    setRequests([]);
    setClinics([]);
  }

  async function action(run: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError("");
    setNotice("");
    setEmailPreview(null);
    try {
      const result = await run();
      const candidate = result as {
        email_sent?: boolean;
        email_delivery?: string;
        email_preview?: { subject?: string; body?: string } | null;
        credentials_preview?: Record<string, string> | null;
      };
      if (candidate.email_sent === false && candidate.email_preview) setEmailPreview(candidate.email_preview);
      if (candidate.email_sent === false && candidate.credentials_preview) {
        setEmailPreview({
          subject: "Credentials generated — SMTP not configured",
          body: JSON.stringify(candidate.credentials_preview, null, 2)
        });
      }
      setNotice(candidate.email_sent === false ? `${success} Email was not sent: ${candidate.email_delivery ?? "SMTP not configured"}.` : success);
      await load();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  const filteredRequests = useMemo(
    () => requests.filter((item) => `${item.clinic_name} ${item.director_name} ${item.work_email} ${item.requested_slug} ${item.status}`.toLowerCase().includes(query.toLowerCase())),
    [requests, query]
  );
  const filteredClinics = useMemo(
    () => clinics.filter((item) => `${item.name} ${item.slug} ${item.subscription_status}`.toLowerCase().includes(query.toLowerCase())),
    [clinics, query]
  );

  if (!authenticated) return <main className="admin-login-screen">
    <form className="admin-login-card" onSubmit={login}>
      <Teta2Logo/>
      <span className="admin-security-chip"><ShieldCheck size={15}/> SECURE PLATFORM ADMIN</span>
      <h1>Teta2 Control Center</h1>
      <p>Manage clinic access, 30-day Teta2 Care subscriptions, platform health and operational activity.</p>
      <label>Admin email<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username"/></label>
      <label>Password<input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password"/></label>
      {error && <div className="auth-error">{error}</div>}
      <button className="t2-btn primary wide" disabled={busy}>{busy ? "Signing in…" : "Open control center"}</button>
      <button className="text-button" type="button" onClick={onExit}>← Back to Teta2</button>
    </form>
  </main>;

  const pending = (overview?.access_requests.SUBMITTED ?? 0) + (overview?.access_requests.PAYMENT_PENDING ?? 0) + (overview?.access_requests.PAYMENT_VERIFIED ?? 0);
  const nav: Array<[Section, React.ReactNode, string, number?]> = [
    ["overview", <LayoutDashboard key="o" size={18}/>, "Overview"],
    ["requests", <FileCheck2 key="r" size={18}/>, "Access requests", pending],
    ["clinics", <Building2 key="c" size={18}/>, "Clinics", clinics.length],
    ["health", <HeartPulse key="h" size={18}/>, "System health"],
    ["billing", <WalletCards key="b" size={18}/>, "Billing settings"],
    ["activity", <Activity key="a" size={18}/>, "Activity"]
  ];

  return <div className="admin-shell">
    <aside className="admin-sidebar">
      <Teta2Logo/>
      <div className="admin-side-label">PLATFORM CONTROL</div>
      <nav>{nav.map(([id, icon, label, count]) => <button key={id} className={section === id ? "active" : ""} onClick={() => { setSection(id); setQuery(""); }}>{icon}<span>{label}</span>{typeof count === "number" && <i>{count}</i>}</button>)}</nav>
      <div className="admin-preview-note"><ShieldCheck size={17}/><div><strong>One commercial plan</strong><small>Teta2 Care · fixed 30-day access periods</small></div></div>
      <button className="admin-exit" onClick={logout}><LogOut size={17}/>Sign out</button>
    </aside>

    <main className="admin-main">
      <header className="admin-topbar"><div><h1>Teta2 Platform Administration</h1><p>Access, subscriptions, health and operational usage in one control plane.</p></div><div className="admin-top-actions"><button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button><button className={lang === "hy" ? "active" : ""} onClick={() => setLang("hy")}>HY</button><button title="Refresh" onClick={() => void action(load, "Platform data refreshed.")}><RefreshCw size={17}/></button><span className="admin-avatar">TA</span></div></header>
      {error && <div className="care-error">{error}<button onClick={() => setError("")}><X size={16}/></button></div>}
      {notice && <div className="case-notice"><Check size={17}/>{notice}</div>}

      {section === "overview" && <>
        <section className="admin-metrics">
          <Metric icon={<Building2/>} label="Registered clinics" value={overview?.clinics.total ?? 0} note={`${overview?.clinics.active ?? 0} active`}/>
          <Metric icon={<FileCheck2/>} label="Requests requiring action" value={pending} note={`${overview?.access_requests.PAYMENT_VERIFIED ?? 0} paid & ready`}/>
          <Metric icon={<Users/>} label="Patients across platform" value={overview?.platform_usage.patients ?? 0} note={`${overview?.platform_usage.visits ?? 0} recorded visits`}/>
          <Metric icon={<HeartPulse/>} label="Tenant DB health" value={overview?.tenant_health.healthy ?? 0} note={`${overview?.tenant_health.unhealthy ?? 0} unhealthy`}/>
        </section>
        <section className="admin-overview-grid">
          <div className="admin-card"><div className="admin-card-heading"><div><h2>Teta2 Care usage</h2><p>Cross-clinic operational totals from tenant databases.</p></div></div><div className="platform-stat-grid"><Stat label="Visits" value={overview?.platform_usage.visits ?? 0}/><Stat label="OPG / X-rays" value={overview?.platform_usage.xrays ?? 0}/><Stat label="AI analyses" value={overview?.platform_usage.analyses ?? 0}/><Stat label="Appointments" value={overview?.platform_usage.appointments ?? 0}/></div></div>
          <div className="admin-card payment-queue"><div className="admin-card-heading"><div><h2>Access workflow queue</h2><p>Requests move through review → payment → activation.</p></div></div>{requests.filter((item) => item.status !== "ACTIVE" && item.status !== "REJECTED").slice(0, 6).map((item) => <button className="queue-row" key={item.id} onClick={() => setSelectedRequest(item)}><span className="clinic-monogram">{item.clinic_name.slice(0,2).toUpperCase()}</span><div><strong>{item.clinic_name}</strong><small>{statusLabel(item.status)} · {item.work_email}</small></div><ChevronRight size={17}/></button>)}{pending === 0 && <div className="admin-empty">No pending access actions.</div>}</div>
        </section>
      </>}

      {section === "requests" && <section className="admin-card admin-table-card">
        <Toolbar query={query} setQuery={setQuery} placeholder="Search request, clinic, email or status"/>
        <div className="admin-table-wrap"><table><thead><tr><th>Clinic</th><th>Director</th><th>Plan</th><th>Status</th><th>Submitted</th><th></th></tr></thead><tbody>{filteredRequests.map((item) => <tr key={item.id}><td><div className="clinic-cell"><span>{item.clinic_name.slice(0,2).toUpperCase()}</span><div><strong>{item.clinic_name}</strong><small>{item.requested_slug} · {item.city}, {item.country}</small></div></div></td><td><strong>{item.director_name}</strong><small>{item.work_email}</small></td><td><span className="plan-pill growth">Teta2 Care</span><small>30 days</small></td><td><span className={`state-pill ${item.status.toLowerCase()}`}>{statusLabel(item.status)}</span></td><td>{fmt(item.created_at)}</td><td><button className="row-open" onClick={() => setSelectedRequest(item)}><ChevronRight size={18}/></button></td></tr>)}</tbody></table></div>
      </section>}

      {section === "clinics" && <section className="admin-card admin-table-card">
        <Toolbar query={query} setQuery={setQuery} placeholder="Search clinic or subscription state"/>
        <div className="admin-table-wrap"><table><thead><tr><th>Clinic</th><th>Subscription</th><th>Expires</th><th>Patients</th><th>Visits</th><th>DB</th><th></th></tr></thead><tbody>{filteredClinics.map((clinic) => <tr key={clinic.id}><td><div className="clinic-cell"><span>{clinic.name.slice(0,2).toUpperCase()}</span><div><strong>{clinic.name}</strong><small>{clinic.slug} · Teta2 Care</small></div></div></td><td><span className={`state-pill ${clinic.subscription_expired ? "suspended" : "active"}`}>{clinic.subscription_expired ? "Expired / suspended" : "Active"}</span></td><td>{fmt(clinic.subscription_ends_at)}</td><td>{clinic.usage?.patients ?? 0}</td><td>{clinic.usage?.visits ?? 0}</td><td><span className={`state-pill ${clinic.usage?.database === "healthy" ? "active" : "suspended"}`}>{clinic.usage?.database ?? "unknown"}</span></td><td><button className="row-open" onClick={() => setSelectedClinic(clinic)}><ChevronRight size={18}/></button></td></tr>)}</tbody></table></div>
      </section>}

      {section === "health" && <section className="admin-card"><div className="admin-card-heading"><div><h2>System health</h2><p>Real control-plane and tenant database checks. No synthetic green status.</p></div></div><div className="health-summary-grid"><HealthState label="Control database" state={health?.control_database ?? "checking"}/><HealthState label="Outbound email / SMTP" state={health?.smtp ?? "checking"}/><HealthState label="Healthy tenant DBs" state={`${overview?.tenant_health.healthy ?? 0}/${overview?.clinics.total ?? 0}`}/></div><div className="admin-table-wrap"><table><thead><tr><th>Clinic</th><th>Database</th><th>Patients</th><th>Visits</th><th>X-rays</th><th>AI analyses</th><th>Appointments</th></tr></thead><tbody>{health?.tenant_databases.map((item) => <tr key={String(item.clinic_id)}><td><strong>{String(item.name)}</strong><small>{String(item.slug)}</small></td><td>{String(item.database)}</td><td>{Number(item.patients ?? 0)}</td><td>{Number(item.visits ?? 0)}</td><td>{Number(item.xrays ?? 0)}</td><td>{Number(item.analyses ?? 0)}</td><td>{Number(item.appointments ?? 0)}</td></tr>)}</tbody></table></div></section>}

      {section === "billing" && billing && <BillingEditor billing={billing} busy={busy} onSave={(next) => void action(() => platformApi.updateBillingSettings(next), "Billing settings saved.")}/>} 

      {section === "activity" && <section className="admin-card activity-card"><div className="admin-card-heading"><div><h2>Platform activity</h2><p>Server-side access, payment, subscription and administration events.</p></div></div>{events.map((event) => <div className="activity-row" key={event.id}><span><Activity size={16}/></span><div><strong>{statusLabel(event.action)}</strong><small>{event.entity_type}{event.entity_id ? ` · ${event.entity_id}` : ""} · {fmt(event.created_at)}</small></div></div>)}{events.length === 0 && <div className="admin-empty">No platform activity recorded yet.</div>}</section>}
    </main>

    {selectedRequest && <RequestDrawer request={selectedRequest} busy={busy} onClose={() => setSelectedRequest(null)} onApprove={() => void action(() => platformApi.approveRequest(selectedRequest.id), "Payment instructions prepared and approval recorded.")} onReject={(reason) => void action(() => platformApi.rejectRequest(selectedRequest.id, reason), "Access request rejected.")} onVerify={(reference, note) => void action(() => platformApi.verifyPayment(selectedRequest.id, reference, note), "Payment verified. Request is ready for activation.")} onActivate={(payload) => void action(() => platformApi.activate(selectedRequest.id, payload), "Teta2 Care access activated for 30 days.")}/>} 
    {selectedClinic && <ClinicDrawer clinic={selectedClinic} busy={busy} onClose={() => setSelectedClinic(null)} onRenew={() => void action(() => platformApi.renewClinic(selectedClinic.id), "Subscription extended by 30 days without changing clinic data.")} onSuspend={() => void action(() => platformApi.suspendClinic(selectedClinic.id, "Suspended by platform administrator"), "Clinic subscription suspended.")}/>} 
    {emailPreview && <div className="admin-drawer-backdrop"><aside className="admin-drawer"><header><div><small>EMAIL DELIVERY FALLBACK</small><h2>{emailPreview.subject}</h2><p>SMTP is unavailable, so this generated email was not sent.</p></div><button onClick={() => setEmailPreview(null)}><X/></button></header><div className="drawer-section"><pre style={{whiteSpace:"pre-wrap"}}>{emailPreview.body}</pre></div></aside></div>}
  </div>;
}

function Metric({ icon, label, value, note }: { icon: React.ReactNode; label: string; value: number; note: string }) {
  return <article><span className="metric-icon purple">{icon}</span><div><small>{label}</small><strong>{value.toLocaleString()}</strong><em>{note}</em></div></article>;
}

function Stat({label,value}:{label:string;value:number}) {
  return <div className="admin-stat"><small>{label}</small><strong>{value.toLocaleString()}</strong></div>;
}

function HealthState({label,state}:{label:string;state:string}) {
  const good=state === "healthy" || state === "configured" || /^\d+\/\d+$/.test(state);
  return <div className="health-state"><span className={good?"healthy":"warning"}>{good?<Check/>:<Activity/>}</span><div><small>{label}</small><strong>{statusLabel(state)}</strong></div></div>;
}

function Toolbar({query,setQuery,placeholder}:{query:string;setQuery:(value:string)=>void;placeholder:string}) {
  return <div className="admin-table-toolbar"><div className="search-box"><Search size={17}/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder={placeholder}/></div></div>;
}

function BillingEditor({billing,busy,onSave}:{billing:BillingSettings;busy:boolean;onSave:(body:Omit<BillingSettings,"id"|"plan_code"|"plan_name"|"subscription_days"|"updated_at">)=>void}) {
  const [form,setForm]=useState({price:billing.price,currency:billing.currency,bank_name:billing.bank_name,cardholder_name:billing.cardholder_name,card_number:billing.card_number,payment_note:billing.payment_note,support_email:billing.support_email,login_url:billing.login_url});
  useEffect(()=>setForm({price:billing.price,currency:billing.currency,bank_name:billing.bank_name,cardholder_name:billing.cardholder_name,card_number:billing.card_number,payment_note:billing.payment_note,support_email:billing.support_email,login_url:billing.login_url}),[billing]);
  return <section className="admin-card"><div className="admin-card-heading"><div><h2>Teta2 Care billing</h2><p>Price and payment destination are editable. The product is always Teta2 Care and each paid access period is always 30 days.</p></div><span className="admin-security-chip"><ShieldCheck size={14}/> 30 DAYS FIXED</span></div><div className="form-grid"><label>Plan<input value="Teta2 Care" disabled/></label><label>Access period<input value="30 days" disabled/></label><label>Price<input value={form.price} onChange={(e)=>setForm({...form,price:e.target.value})}/></label><label>Currency<input value={form.currency} onChange={(e)=>setForm({...form,currency:e.target.value.toUpperCase()})}/></label><label>Bank name<input value={form.bank_name} onChange={(e)=>setForm({...form,bank_name:e.target.value})}/></label><label>Cardholder name<input value={form.cardholder_name} onChange={(e)=>setForm({...form,cardholder_name:e.target.value})}/></label><label>Card / payment number<input value={form.card_number} onChange={(e)=>setForm({...form,card_number:e.target.value})}/></label><label>Support email<input type="email" value={form.support_email} onChange={(e)=>setForm({...form,support_email:e.target.value})}/></label><label className="full">Login URL<input value={form.login_url} onChange={(e)=>setForm({...form,login_url:e.target.value})}/></label><label className="full">Payment note<textarea value={form.payment_note} onChange={(e)=>setForm({...form,payment_note:e.target.value})}/></label></div><button className="t2-btn primary" disabled={busy} onClick={()=>onSave(form)}><Settings2 size={16}/>Save billing settings</button></section>;
}

function RequestDrawer({request,busy,onClose,onApprove,onReject,onVerify,onActivate}:{request:PlatformAccessRequest;busy:boolean;onClose:()=>void;onApprove:()=>void;onReject:(reason:string)=>void;onVerify:(reference:string,note:string)=>void;onActivate:(payload:{tenant_database_url:string;username?:string;first_name:string;last_name:string;branch_name:string;branch_code:string})=>void}) {
  const [adminNote,setAdminNote]=useState(request.admin_note ?? "");
  const [paymentRef,setPaymentRef]=useState(request.payment_reference ?? "");
  const [paymentNote,setPaymentNote]=useState(request.payment_proof_note ?? "");
  const [databaseUrl,setDatabaseUrl]=useState("");
  const [username,setUsername]=useState("");
  const [first,last]=splitName(request.director_name);
  const [firstName,setFirstName]=useState(first);
  const [lastName,setLastName]=useState(last);
  const [branchName,setBranchName]=useState(`${request.clinic_name} Main`);
  const [branchCode,setBranchCode]=useState("MAIN");
  return <div className="admin-drawer-backdrop" onMouseDown={onClose}><aside className="admin-drawer" onMouseDown={(e)=>e.stopPropagation()}><header><div><small>ACCESS REQUEST · {request.id}</small><h2>{request.clinic_name}</h2><p>{statusLabel(request.status)} · {request.city}, {request.country}</p></div><button onClick={onClose}><X/></button></header><div className="drawer-section"><h3>Clinic request</h3><dl><div><dt>Director</dt><dd>{request.director_name}</dd></div><div><dt>Email</dt><dd>{request.work_email}</dd></div><div><dt>Phone</dt><dd>{request.phone}</dd></div><div><dt>Requested clinic ID</dt><dd>{request.requested_slug}</dd></div><div><dt>Branches</dt><dd>{request.branch_count}</dd></div><div><dt>Dentists</dt><dd>{request.dentist_count}</dd></div><div><dt>Plan</dt><dd>Teta2 Care · 30 days</dd></div><div><dt>Submitted</dt><dd>{fmt(request.created_at)}</dd></div></dl>{request.address && <p><b>Address:</b> {request.address}</p>}{request.website && <p><b>Website:</b> {request.website}</p>}{request.notes && <p><b>Clinic note:</b> {request.notes}</p>}</div>
    {request.status === "SUBMITTED" && <div className="drawer-section"><h3>Stage 1 · Review</h3><label>Admin review note<textarea value={adminNote} onChange={(e)=>setAdminNote(e.target.value)} placeholder="Optional internal note; required if rejecting."/></label><div className="drawer-actions"><button className="t2-btn primary" disabled={busy} onClick={onApprove}><Mail size={16}/>Approve & send payment email</button><button className="t2-btn ghost" disabled={busy || adminNote.trim().length < 2} onClick={()=>onReject(adminNote)}><XCircle size={16}/>Reject</button></div></div>}
    {request.status === "PAYMENT_PENDING" && <div className="drawer-section"><h3>Stage 2 · Verify payment</h3><p>Payment instructions were sent {fmt(request.payment_instructions_sent_at)}. Verify the receipt before activation.</p><label>Payment / receipt reference<input value={paymentRef} onChange={(e)=>setPaymentRef(e.target.value)} placeholder="Bank transaction or receipt reference"/></label><label>Verification note<textarea value={paymentNote} onChange={(e)=>setPaymentNote(e.target.value)} placeholder="Optional payment verification details"/></label><button className="t2-btn primary" disabled={busy || !paymentRef.trim()} onClick={()=>onVerify(paymentRef,paymentNote)}><Check size={16}/>Verify payment</button></div>}
    {request.status === "PAYMENT_VERIFIED" && <div className="drawer-section"><h3>Stage 3 · Provision & activate</h3><p>Activation creates the clinic Director account and starts exactly 30 days of Teta2 Care access. Existing data is preserved on future renewals.</p><label>Tenant database URL<input type="password" value={databaseUrl} onChange={(e)=>setDatabaseUrl(e.target.value)} placeholder="postgresql+asyncpg://…" autoComplete="off"/></label><div className="form-grid"><label>Director first name<input value={firstName} onChange={(e)=>setFirstName(e.target.value)}/></label><label>Director last name<input value={lastName} onChange={(e)=>setLastName(e.target.value)}/></label><label>Username (optional)<input value={username} onChange={(e)=>setUsername(e.target.value)} placeholder={`director.${request.requested_slug}`}/></label><label>Branch name<input value={branchName} onChange={(e)=>setBranchName(e.target.value)}/></label><label>Branch code<input value={branchCode} onChange={(e)=>setBranchCode(e.target.value.toUpperCase())}/></label></div><button className="t2-btn primary wide" disabled={busy || databaseUrl.length < 10 || !firstName || !lastName || !branchName || !branchCode} onClick={()=>onActivate({tenant_database_url:databaseUrl,username:username||undefined,first_name:firstName,last_name:lastName,branch_name:branchName,branch_code:branchCode})}><ShieldCheck size={16}/>Activate 30-day dashboard & send login</button></div>}
    {request.status === "ACTIVE" && <div className="drawer-section"><span className="admin-security-chip"><Check size={14}/> ACTIVE CLINIC</span><p>Dashboard access was activated {fmt(request.activated_at)}. Future access periods are renewed from the Clinics section.</p></div>}
    {request.status === "REJECTED" && <div className="drawer-section"><span className="admin-security-chip"><XCircle size={14}/> REJECTED</span><p>{request.admin_note || "No rejection reason recorded."}</p></div>}
  </aside></div>;
}

function ClinicDrawer({clinic,busy,onClose,onRenew,onSuspend}:{clinic:PlatformClinic;busy:boolean;onClose:()=>void;onRenew:()=>void;onSuspend:()=>void}) {
  return <div className="admin-drawer-backdrop" onMouseDown={onClose}><aside className="admin-drawer" onMouseDown={(e)=>e.stopPropagation()}><header><div><small>CLINIC · {clinic.slug}</small><h2>{clinic.name}</h2><p>Teta2 Care · {clinic.subscription_expired ? "Access inactive" : "Access active"}</p></div><button onClick={onClose}><X/></button></header><div className="drawer-section"><h3>30-day subscription</h3><dl><div><dt>Status</dt><dd>{statusLabel(clinic.subscription_status)}</dd></div><div><dt>Started</dt><dd>{fmt(clinic.subscription_started_at)}</dd></div><div><dt>Expires</dt><dd>{fmt(clinic.subscription_ends_at)}</dd></div><div><dt>Renewals</dt><dd>{clinic.renewal_count}</dd></div></dl><div className="drawer-actions"><button className="t2-btn primary" disabled={busy} onClick={onRenew}><RefreshCw size={16}/>Add 30 days</button><button className="t2-btn ghost" disabled={busy || clinic.subscription_status === "SUSPENDED"} onClick={onSuspend}><XCircle size={16}/>Suspend access</button></div></div><div className="drawer-section"><h3>Platform data</h3><dl><div><dt>Patients</dt><dd>{clinic.usage?.patients ?? 0}</dd></div><div><dt>Visits</dt><dd>{clinic.usage?.visits ?? 0}</dd></div><div><dt>X-rays</dt><dd>{clinic.usage?.xrays ?? 0}</dd></div><div><dt>AI analyses</dt><dd>{clinic.usage?.analyses ?? 0}</dd></div><div><dt>Appointments</dt><dd>{clinic.usage?.appointments ?? 0}</dd></div><div><dt>Database</dt><dd>{clinic.usage?.database ?? "unknown"}</dd></div></dl></div><div className="drawer-section"><p><Database size={16}/> Renewing changes only the access expiry. Tenant data is never recreated or cleared.</p></div></aside></div>;
}
