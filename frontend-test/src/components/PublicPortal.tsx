import { useEffect, useState, type FormEvent } from "react";
import {
  BrainCircuit,
  Building2,
  CalendarDays,
  Check,
  ChevronRight,
  HeartPulse,
  Languages,
  LockKeyhole,
  Mail,
  Radar,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Workflow
} from "lucide-react";
import { api, clearSession, errorMessage } from "../api/client";
import { platformApi, type PublicPlan } from "../api/platform";
import type { CurrentUser } from "../api/types";
import type { Lang } from "../i18n";
import { tr } from "../i18n";
import { Teta2Logo } from "./Teta2Logo";

type PublicView = "landing" | "login" | "request";

interface PublicPortalProps {
  lang: Lang;
  setLang: (lang: Lang) => void;
  onAuthenticated: (user: CurrentUser) => void;
}

const emptyRequest = {
  clinic_name: "",
  requested_slug: "",
  country: "Armenia",
  city: "Yerevan",
  address: "",
  website: "",
  director_name: "",
  work_email: "",
  phone: "",
  branch_count: 1,
  dentist_count: 1,
  notes: ""
};

export function PublicPortal({ lang, setLang, onAuthenticated }: PublicPortalProps) {
  const c = tr(lang);
  const [view, setView] = useState<PublicView>("landing");
  const [clinicSlug, setClinicSlug] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<"checking" | "online" | "offline">("checking");
  const [plan, setPlan] = useState<PublicPlan | null>(null);
  const [request, setRequest] = useState(emptyRequest);
  const [requestResult, setRequestResult] = useState<{ id: string; message: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api.health(controller.signal), api.ready(controller.signal)])
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
    void platformApi.plan().then(setPlan).catch(() => undefined);
    return () => controller.abort();
  }, []);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.login({
        clinic_slug: clinicSlug.trim().toLowerCase(),
        identifier: identifier.trim(),
        password
      });
      const user = await api.me();
      setPassword("");
      onAuthenticated(user);
    } catch (reason) {
      clearSession();
      setPassword("");
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await platformApi.requestAccess({
        ...request,
        clinic_name: request.clinic_name.trim(),
        requested_slug: request.requested_slug.trim().toLowerCase(),
        country: request.country.trim(),
        city: request.city.trim(),
        address: request.address.trim() || undefined,
        website: request.website.trim() || undefined,
        director_name: request.director_name.trim(),
        work_email: request.work_email.trim(),
        phone: request.phone.trim(),
        notes: request.notes.trim() || undefined
      });
      setRequestResult({ id: result.id, message: result.message });
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function languageToggle() {
    return <div className="public-language-toggle" aria-label="Language"><Languages size={16}/><button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button><button className={lang === "hy" ? "active" : ""} onClick={() => setLang("hy")}>HY</button></div>;
  }

  if (view === "login") return <main className="auth-page premium-auth">
    <section className="auth-visual-panel">
      <div className="auth-topline"><button className="back-button" onClick={() => setView("landing")}>← {c.auth.back}</button>{languageToggle()}</div>
      <div className="auth-visual-copy"><Teta2Logo/><span className="eyebrow-glow">TETA2 CARE</span><h1>{lang === "en" ? "Your clinic, with an intelligent clinical layer." : "Ձեր կլինիկան՝ խելացի կլինիկական շերտով։"}</h1><p>{lang === "en" ? "Review OPG findings, preserve tooth-level history, coordinate follow-up and work from one secure clinical platform." : "Վերանայեք OPG արդյունքները, պահպանեք ատամների պատմությունը և կառավարեք follow-up-ը մեկ անվտանգ հարթակից։"}</p><div className="auth-trust-list"><span><ShieldCheck/>Tenant-isolated clinical data</span><span><BrainCircuit/>OPG intelligence</span><span><HeartPulse/>AI follow-up workflow</span></div></div>
    </section>
    <section className="auth-form-panel"><div className="auth-form-card"><span className={`backend-chip ${health}`}>{health === "online" ? c.auth.backendOnline : health === "checking" ? c.auth.backendChecking : c.auth.backendOffline}</span><h2>{c.auth.loginTitle}</h2><p>Use the clinic ID and credentials issued after your Teta2 Care subscription is activated.</p><form onSubmit={submitLogin}><label>{c.auth.clinicSlug}<input required value={clinicSlug} onChange={(e)=>setClinicSlug(e.target.value.toLowerCase())} placeholder="clinic-name" pattern="[a-z0-9-]+"/></label><label>{c.auth.identifier}<input required value={identifier} onChange={(e)=>setIdentifier(e.target.value)} placeholder="director@clinic.com" autoComplete="username"/></label><label>{c.auth.password}<input required type="password" minLength={8} value={password} onChange={(e)=>setPassword(e.target.value)} autoComplete="current-password"/></label>{error && <div className="auth-error">{error}</div>}<button className="t2-btn primary wide" disabled={busy}>{busy ? c.auth.signingIn : c.auth.signIn}<ChevronRight size={18}/></button></form><p className="auth-switch">Need clinic access? <button onClick={()=>{setView("request");setError("");}}>Request access</button></p></div></section>
  </main>;

  if (view === "request") return <main className="auth-page premium-auth registration-page">
    <section className="auth-visual-panel register-visual">
      <div className="auth-topline"><button className="back-button" onClick={() => setView("landing")}>← {c.auth.back}</button>{languageToggle()}</div>
      <div className="auth-visual-copy"><Teta2Logo/><span className="eyebrow-glow">REQUEST TETA2 CARE ACCESS</span><h1>One plan. One professional clinic workflow.</h1><p>Submit your clinic profile for review. Approved clinics receive payment instructions by email; access begins only after payment verification.</p><div className="register-steps"><span className="done">1</span><div><strong>Request access</strong><small>Clinic and director information</small></div><span>2</span><div><strong>Review & payment</strong><small>Admin approval and payment verification</small></div><span>3</span><div><strong>30-day activation</strong><small>Credentials are issued by email</small></div></div><div className="auth-trust-list"><span><CalendarDays/>Fixed 30-day subscription periods</span><span><LockKeyhole/>Previous data is preserved on renewal</span><span><Mail/>Email-based payment and activation notices</span></div></div>
    </section>
    <section className="auth-form-panel"><div className="auth-form-card registration-card">{requestResult ? <div className="registration-success"><span><Check/></span><h2>Access request submitted</h2><p>{requestResult.message}</p><div className="request-reference"><small>Request ID</small><strong>{requestResult.id}</strong></div><p>Keep this ID. If the request passes review, payment instructions for the single Teta2 Care plan will be sent to your work email.</p><button className="t2-btn primary wide" onClick={()=>setView("login")}>Go to sign in</button></div> : <><div className="request-plan-card"><div><span>TETA2 CARE</span><h2>{plan ? `${plan.price} ${plan.currency}` : "Teta2 Care"}</h2><p>{plan ? `One ${plan.subscription_days}-day access period` : "One fixed 30-day access period"}. Renewal preserves all existing clinic data.</p></div><ShieldCheck/></div><h2>Clinic access request</h2><p>No password is created at this stage. Login credentials are generated only after payment is verified and access is activated.</p><form onSubmit={submitRequest}><div className="form-grid"><label>Clinic name<input required value={request.clinic_name} onChange={(e)=>setRequest({...request,clinic_name:e.target.value})} placeholder="Marstom Clinic"/></label><label>Requested clinic ID<input required pattern="[a-z0-9-]+" value={request.requested_slug} onChange={(e)=>setRequest({...request,requested_slug:e.target.value.toLowerCase().replace(/[^a-z0-9-]/g,"")})} placeholder="marstom"/></label><label>Country<input required value={request.country} onChange={(e)=>setRequest({...request,country:e.target.value})}/></label><label>City<input required value={request.city} onChange={(e)=>setRequest({...request,city:e.target.value})}/></label><label>Clinic address<input value={request.address} onChange={(e)=>setRequest({...request,address:e.target.value})} placeholder="Street, building"/></label><label>Website<input type="url" value={request.website} onChange={(e)=>setRequest({...request,website:e.target.value})} placeholder="https://clinic.com"/></label><label>Director / owner name<input required value={request.director_name} onChange={(e)=>setRequest({...request,director_name:e.target.value})} placeholder="Full name"/></label><label>Work email<input required type="email" value={request.work_email} onChange={(e)=>setRequest({...request,work_email:e.target.value})} placeholder="director@clinic.com"/></label><label>Phone<input required value={request.phone} onChange={(e)=>setRequest({...request,phone:e.target.value})} placeholder="+374 ..."/></label><label>Number of branches<input required type="number" min={1} max={100} value={request.branch_count} onChange={(e)=>setRequest({...request,branch_count:Number(e.target.value)})}/></label><label>Number of dentists<input required type="number" min={1} max={1000} value={request.dentist_count} onChange={(e)=>setRequest({...request,dentist_count:Number(e.target.value)})}/></label><label className="full">Notes<textarea value={request.notes} onChange={(e)=>setRequest({...request,notes:e.target.value})} placeholder="Anything the Teta2 team should know about your clinic or rollout."/></label></div>{error && <div className="auth-error">{error}</div>}<button className="t2-btn primary wide" disabled={busy}>{busy ? "Submitting…" : "Submit access request"}<ChevronRight size={18}/></button></form></>}</div></section>
  </main>;

  return <main className="public-site-v2">
    <header className="public-nav-v2"><button className="brand-button" onClick={()=>window.scrollTo({top:0,behavior:"smooth"})}><Teta2Logo/></button><nav><a href="#product">Product</a><a href="#workflow">Workflow</a><a href="#access">Access</a><a href="#security">Security</a></nav><div className="public-actions-v2">{languageToggle()}<button className="t2-btn ghost" onClick={()=>setView("login")}>Clinic login</button><button className="t2-btn primary" onClick={()=>setView("request")}>Request access</button></div></header>
    <section className="hero-v2"><div className="hero-copy-v2"><span className="hero-badge-v2"><Sparkles size={15}/>TETA2 CARE</span><h1>Clinical intelligence that stays connected to <em>patient follow-up.</em></h1><p>OPG review, longitudinal dental records, AI-assisted WhatsApp follow-up, appointment coordination and patient opportunity intelligence in one clinic workspace.</p><div className="hero-actions-v2"><button className="t2-btn primary large" onClick={()=>setView("request")}>Request Teta2 Care access<ChevronRight size={19}/></button><button className="t2-btn glass large" onClick={()=>setView("login")}>Clinic login</button></div><div className="proof-row-v2"><span><BrainCircuit/>OPG intelligence</span><span><LockKeyhole/>Tenant-isolated data</span><span><HeartPulse/>Clinical follow-up</span></div></div><div className="hero-product-v2"><div className="hero-halo"/><div className="clinical-screen"><div className="clinical-screen-top"><div><span className="mini-logo"><Teta2Logo compact/></span><strong>TETA2 CARE</strong></div><span className="ready-pill">● Ready</span></div><div className="opg-simulation"><div className="jaw-arc top"/><div className="jaw-arc bottom"/><span className="tooth-box t18">18</span><span className="tooth-box t46">46</span><span className="scan-beam"/></div><div className="finding-mini-list"><article><i className="severity amber"/><div><strong>Clinical finding</strong><small>Tooth 46 · clinician review</small></div><b>82%</b></article><article><i className="severity purple"/><div><strong>Follow-up sequence</strong><small>Patient outreach coordinated</small></div><b>AI</b></article></div></div><div className="floating-intel-card radar"><Radar/><div><small>Radar AI</small><strong>Opportunity intelligence</strong></div></div><div className="floating-intel-card recall"><HeartPulse/><div><small>Care AI</small><strong>Follow-up active</strong></div></div></div></section>
    <section className="product-section-v2" id="product"><div className="section-heading-v2"><span>ONE CARE PLATFORM</span><h2>Teta2 Care is the only clinic subscription.</h2><p>There are no Starter, Growth, Scale or Scan plans. Every subscribed clinic receives the same Teta2 Care product surface.</p></div><div className="feature-grid-v2"><article><div className="feature-icon-v2"><BrainCircuit/></div><small>OPG AI</small><h3>Clinical review</h3><p>Structure OPG findings by tooth and keep the clinician in control.</p></article><article><div className="feature-icon-v2"><HeartPulse/></div><small>CARE AI</small><h3>Follow-up orchestration</h3><p>Move pathological findings into organized patient outreach and appointment workflows.</p></article><article><div className="feature-icon-v2"><Radar/></div><small>RADAR AI</small><h3>Patient opportunity intelligence</h3><p>Keep growth intelligence connected to the same operational clinic platform.</p></article></div></section>
    <section className="workflow-section-v2" id="workflow"><div className="workflow-copy"><span>CLINICAL WORKFLOW</span><h2>From OPG evidence to patient attendance.</h2><div className="workflow-list"><article><b>01</b><div><strong>Analyze</strong><p>Upload and review the patient's OPG.</p></div></article><article><b>02</b><div><strong>Approve follow-up</strong><p>The doctor controls which findings enter outreach.</p></div></article><article><b>03</b><div><strong>Coordinate</strong><p>Care AI handles staged WhatsApp communication and scheduling.</p></div></article><article><b>04</b><div><strong>Preserve history</strong><p>Clinical and operational data stays with the clinic across renewals.</p></div></article></div></div><div className="workflow-visual"><div className="workflow-core"><Workflow/></div><span className="wf-node a"><Stethoscope/>Doctor</span><span className="wf-node b"><BrainCircuit/>AI review</span><span className="wf-node c"><HeartPulse/>Follow-up</span><span className="wf-node d"><Radar/>Radar AI</span></div></section>
    <section className="radar-section-v2" id="access"><div><span className="hero-badge-v2"><Building2 size={15}/>CLINIC ACCESS</span><h2>Professional onboarding with controlled activation.</h2><p>Submit a request, complete payment after approval, and receive a 30-day clinic dashboard only after the payment is verified. Future renewals extend access without deleting previous data.</p><button className="t2-btn light" onClick={()=>setView("request")}>Request access<ChevronRight size={18}/></button></div><div className="radar-console-preview"><div className="radar-rings"><i/><i/><i/><span><ShieldCheck/></span></div><div className="radar-lead-card one"><span className="platform-dot instagram"/><div><strong>Request reviewed</strong><small>Admin approval → payment instructions</small></div><b>1</b></div><div className="radar-lead-card two"><span className="platform-dot telegram"/><div><strong>Dashboard activated</strong><small>Verified payment → 30 days</small></div><b>2</b></div></div></section>
    <section className="security-section-v2" id="security"><div className="security-visual"><ShieldCheck/><div><span/><span/><span/></div></div><div><span>SECURITY & CONTINUITY</span><h2>Subscription expiry limits access, not ownership of clinic history.</h2><p>Teta2 Care keeps each clinic tenant isolated. When a 30-day access period expires, login is blocked until renewal; existing patient and clinical records remain in the clinic tenant database.</p><div className="security-points"><span><Check/>Tenant-separated clinical databases</span><span><Check/>Admin-controlled activation and renewal</span><span><Check/>No data reset on renewal</span></div></div></section>
  </main>;
}
