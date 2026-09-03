import { useEffect, useMemo, useState, type FormEvent } from "react";
import { BrainCircuit, ChevronRight, HeartPulse, Languages, LockKeyhole, Radar, ShieldCheck, Sparkles, Stethoscope, Workflow } from "lucide-react";
import { api, clearSession, errorMessage } from "../api/client";
import type { CurrentUser } from "../api/types";
import type { Lang } from "../i18n";
import { tr } from "../i18n";
import { Teta2Logo } from "./Teta2Logo";

type PublicView = "landing" | "login" | "register";

interface PublicPortalProps {
  lang: Lang;
  setLang: (lang: Lang) => void;
  onAuthenticated: (user: CurrentUser) => void;
}

const APPLICATIONS_KEY = "teta2-clinic-applications-v1";

export function PublicPortal({ lang, setLang, onAuthenticated }: PublicPortalProps) {
  const c = tr(lang);
  const [view, setView] = useState<PublicView>("landing");
  const [clinicSlug, setClinicSlug] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState<"checking" | "online" | "offline">("checking");
  const [registrationSent, setRegistrationSent] = useState(false);
  const [registration, setRegistration] = useState({ clinicName: "", city: "Yerevan", country: "Armenia", directorName: "", email: "", phone: "", slug: "", branches: "1", plan: "Starter", password: "" });

  const features = useMemo(() => [
    { icon: BrainCircuit, title: c.public.feature1Title, copy: c.public.feature1Copy, kicker: "OPG AI" },
    { icon: HeartPulse, title: c.public.feature2Title, copy: c.public.feature2Copy, kicker: "SMART RECALL" },
    { icon: Radar, title: c.public.feature3Title, copy: c.public.feature3Copy, kicker: "RADAR AI" }
  ], [c]);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api.health(controller.signal), api.ready(controller.signal)])
      .then(() => setHealth("online"))
      .catch(() => setHealth("offline"));
    return () => controller.abort();
  }, []);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await api.login({ clinic_slug: clinicSlug.trim().toLowerCase(), identifier: identifier.trim(), password });
      const user = await api.me();
      setPassword(""); onAuthenticated(user);
    } catch (reason) {
      clearSession(); setPassword(""); setError(errorMessage(reason));
    } finally { setBusy(false); }
  }

  function submitRegistration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const item = { ...registration, branches: Number(registration.branches), createdAt: new Date().toISOString() };
    try {
      const current = JSON.parse(localStorage.getItem(APPLICATIONS_KEY) || "[]") as unknown[];
      localStorage.setItem(APPLICATIONS_KEY, JSON.stringify([...current, item]));
    } catch { localStorage.setItem(APPLICATIONS_KEY, JSON.stringify([item])); }
    setRegistrationSent(true);
  }

  function languageToggle() {
    return <div className="public-language-toggle" aria-label="Language"><Languages size={16}/><button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button><button className={lang === "hy" ? "active" : ""} onClick={() => setLang("hy")}>HY</button></div>;
  }

  if (view === "login") return <main className="auth-page premium-auth">
    <section className="auth-visual-panel">
      <div className="auth-topline"><button className="back-button" onClick={() => setView("landing")}>← {c.auth.back}</button>{languageToggle()}</div>
      <div className="auth-visual-copy"><Teta2Logo/><span className="eyebrow-glow">{c.brand.tagline}</span><h1>{lang === "en" ? "Your clinic, with an intelligent clinical layer." : "Ձեր կլինիկան՝ խելացի կլինիկական շերտով։"}</h1><p>{lang === "en" ? "Review OPG findings, preserve tooth-level history, coordinate recall, and work from one secure dental intelligence platform." : "Վերանայեք OPG արդյունքները, պահպանեք յուրաքանչյուր ատամի պատմությունը, կառավարեք recall-ը և աշխատեք մեկ անվտանգ ատամնաբուժական AI հարթակից։"}</p><div className="auth-trust-list"><span><ShieldCheck/>Tenant-isolated clinical data</span><span><BrainCircuit/>9-model OPG intelligence</span><span><HeartPulse/>Longitudinal smart recall</span></div></div>
      <div className="auth-orbit-card"><div className="orbit-core"><Sparkles/></div><span className="orbit-node one"><BrainCircuit/></span><span className="orbit-node two"><HeartPulse/></span><span className="orbit-node three"><Radar/></span></div>
    </section>
    <section className="auth-form-panel"><div className="auth-form-card"><span className={`backend-chip ${health}`}>{health === "online" ? c.auth.backendOnline : health === "checking" ? c.auth.backendChecking : c.auth.backendOffline}</span><h2>{c.auth.loginTitle}</h2><p>{c.auth.loginCopy}</p><form onSubmit={submitLogin}><label>{c.auth.clinicSlug}<input required value={clinicSlug} onChange={(e)=>setClinicSlug(e.target.value.toLowerCase())} placeholder="marstom" pattern="[a-z0-9-]+"/></label><label>{c.auth.identifier}<input required value={identifier} onChange={(e)=>setIdentifier(e.target.value)} placeholder="doctor@clinic.com" autoComplete="username"/></label><label>{c.auth.password}<input required type="password" minLength={8} value={password} onChange={(e)=>setPassword(e.target.value)} autoComplete="current-password"/></label>{error && <div className="auth-error">{error}</div>}<button className="t2-btn primary wide" disabled={busy}>{busy ? c.auth.signingIn : c.auth.signIn}<ChevronRight size={18}/></button></form><p className="auth-switch">{c.auth.noAccount} <button onClick={()=>setView("register")}>{c.auth.registerLink}</button></p></div></section>
  </main>;

  if (view === "register") return <main className="auth-page premium-auth registration-page">
    <section className="auth-visual-panel register-visual"><div className="auth-topline"><button className="back-button" onClick={() => setView("landing")}>← {c.auth.back}</button>{languageToggle()}</div><div className="auth-visual-copy"><Teta2Logo/><span className="eyebrow-glow">CLINIC ONBOARDING</span><h1>{c.auth.registerTitle}</h1><p>{c.auth.registerCopy}</p><div className="register-steps"><span className="done">1</span><div><strong>Clinic profile</strong><small>Identity, director, branch footprint</small></div><span>2</span><div><strong>Secure provisioning</strong><small>Tenant DB, Director account, billing state</small></div><span>3</span><div><strong>Launch</strong><small>Invite team and analyze first OPG</small></div></div></div></section>
    <section className="auth-form-panel"><div className="auth-form-card registration-card">{registrationSent ? <div className="registration-success"><span><Checkmark/></span><h2>{c.auth.applicationSaved}</h2><p>{c.auth.applicationSavedCopy}</p><button className="t2-btn primary wide" onClick={()=>setView("login")}>{c.auth.goLogin}</button></div> : <><h2>{c.auth.registerTitle}</h2><p>{c.auth.registerCopy}</p><form onSubmit={submitRegistration}><div className="form-grid"><label>{c.auth.clinicName}<input required value={registration.clinicName} onChange={(e)=>setRegistration({...registration,clinicName:e.target.value})} placeholder="Marstom Clinic"/></label><label>{c.auth.city}<input required value={registration.city} onChange={(e)=>setRegistration({...registration,city:e.target.value})}/></label><label>{c.auth.country}<input required value={registration.country} onChange={(e)=>setRegistration({...registration,country:e.target.value})}/></label><label>{c.auth.directorName}<input required value={registration.directorName} onChange={(e)=>setRegistration({...registration,directorName:e.target.value})} placeholder="David Gevorgyan"/></label><label>{c.auth.workEmail}<input required type="email" value={registration.email} onChange={(e)=>setRegistration({...registration,email:e.target.value})} placeholder="director@clinic.com"/></label><label>{c.auth.phone}<input required value={registration.phone} onChange={(e)=>setRegistration({...registration,phone:e.target.value})} placeholder="+374 ..."/></label><label>{c.auth.slug}<input required pattern="[a-z0-9-]+" value={registration.slug} onChange={(e)=>setRegistration({...registration,slug:e.target.value.toLowerCase()})} placeholder="marstom"/></label><label>{c.auth.branches}<select value={registration.branches} onChange={(e)=>setRegistration({...registration,branches:e.target.value})}><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4+</option></select></label><label>{c.auth.plan}<select value={registration.plan} onChange={(e)=>setRegistration({...registration,plan:e.target.value})}><option>Starter</option><option>Growth</option><option>Scale</option></select></label><label>{c.auth.passwordNew}<input required type="password" minLength={12} value={registration.password} onChange={(e)=>setRegistration({...registration,password:e.target.value})}/></label></div><button className="t2-btn primary wide">{c.auth.submitRegistration}<ChevronRight size={18}/></button></form></>}</div></section>
  </main>;

  return <main className="public-site-v2">
    <header className="public-nav-v2"><button className="brand-button" onClick={()=>window.scrollTo({top:0,behavior:"smooth"})}><Teta2Logo/></button><nav><a href="#product">{c.public.nav.product}</a><a href="#workflow">{c.public.nav.workflow}</a><a href="#radar">{c.public.nav.radar}</a><a href="#security">{c.public.nav.security}</a></nav><div className="public-actions-v2">{languageToggle()}<button className="t2-btn ghost" onClick={()=>setView("login")}>{c.public.nav.login}</button><button className="t2-btn primary" onClick={()=>setView("register")}>{c.public.nav.register}</button></div></header>
    <section className="hero-v2"><div className="hero-copy-v2"><span className="hero-badge-v2"><Sparkles size={15}/>{c.public.badge}</span><h1>{c.public.heroTitleA}<em>{c.public.heroTitleB}</em></h1><p>{c.public.heroCopy}</p><div className="hero-actions-v2"><button className="t2-btn primary large" onClick={()=>setView("register")}>{c.public.heroPrimary}<ChevronRight size={19}/></button><button className="t2-btn glass large" onClick={()=>setView("login")}>{c.public.heroSecondary}</button></div><div className="proof-row-v2"><span><BrainCircuit/>{c.public.proof1}</span><span><LockKeyhole/>{c.public.proof2}</span><span><ShieldCheck/>{c.public.proof3}</span></div></div><div className="hero-product-v2"><div className="hero-halo"/><div className="clinical-screen"><div className="clinical-screen-top"><div><span className="mini-logo"><Teta2Logo compact/></span><strong>OPG AI REVIEW</strong></div><span className="ready-pill">● Ready</span></div><div className="opg-simulation"><div className="jaw-arc top"/><div className="jaw-arc bottom"/><span className="tooth-box t18">18</span><span className="tooth-box t46">46</span><span className="scan-beam"/></div><div className="finding-mini-list"><article><i className="severity amber"/><div><strong>Deep caries candidate</strong><small>Tooth 46 · review required</small></div><b>82%</b></article><article><i className="severity purple"/><div><strong>Restoration detected</strong><small>Tooth 18 · historical context</small></div><b>94%</b></article></div></div><div className="floating-intel-card radar"><Radar/><div><small>Radar AI</small><strong>12 opportunities</strong></div></div><div className="floating-intel-card recall"><HeartPulse/><div><small>Smart Recall</small><strong>7 patients due</strong></div></div></div></section>
    <section className="product-section-v2" id="product"><div className="section-heading-v2"><span>{c.public.sectionKicker}</span><h2>{c.public.sectionTitle}</h2></div><div className="feature-grid-v2">{features.map(({icon:Icon,...feature})=><article key={feature.title}><div className="feature-icon-v2"><Icon/></div><small>{feature.kicker}</small><h3>{feature.title}</h3><p>{feature.copy}</p><span className="feature-line"/></article>)}</div></section>
    <section className="workflow-section-v2" id="workflow"><div className="workflow-copy"><span>{c.public.workflowKicker}</span><h2>{c.public.workflowTitle}</h2><div className="workflow-list"><article><b>01</b><div><strong>Upload</strong><p>Attach the OPG to the patient record.</p></div></article><article><b>02</b><div><strong>Analyze</strong><p>Teta2 V5 produces structured tooth-level evidence.</p></div></article><article><b>03</b><div><strong>Review</strong><p>The clinician validates findings and preserves context.</p></div></article><article><b>04</b><div><strong>Recall</strong><p>Future care and communication stay connected to the record.</p></div></article></div></div><div className="workflow-visual"><div className="workflow-core"><Workflow/></div><span className="wf-node a"><Stethoscope/>Patient</span><span className="wf-node b"><BrainCircuit/>AI review</span><span className="wf-node c"><HeartPulse/>Recall</span><span className="wf-node d"><Radar/>Radar AI</span></div></section>
    <section className="radar-section-v2" id="radar"><div><span className="hero-badge-v2"><Radar size={15}/>RADAR AI</span><h2>{c.public.feature3Title}</h2><p>{c.public.feature3Copy}</p><button className="t2-btn light" onClick={()=>setView("register")}>{c.public.heroPrimary}<ChevronRight size={18}/></button></div><div className="radar-console-preview"><div className="radar-rings"><i/><i/><i/><span><Radar/></span></div><div className="radar-lead-card one"><span className="platform-dot instagram"/><div><strong>Implant consultation</strong><small>Yerevan · Instagram · 91 score</small></div><b>HOT</b></div><div className="radar-lead-card two"><span className="platform-dot telegram"/><div><strong>Emergency endodontics</strong><small>Yerevan · Telegram · 84 score</small></div><b>HOT</b></div></div></section>
    <section className="security-section-v2" id="security"><div className="security-visual"><ShieldCheck/><div><span>PRIVATE S3</span><span>TENANT DB</span><span>CLINICIAN REVIEW</span></div></div><div><span>{c.public.securityKicker}</span><h2>{c.public.securityTitle}</h2><p>{c.public.footer}</p></div></section>
    <section className="cta-section-v2"><div><Teta2Logo/><h2>{c.public.ctaTitle}</h2><p>{c.public.ctaCopy}</p></div><button className="t2-btn light large" onClick={()=>setView("register")}>{c.public.heroPrimary}<ChevronRight/></button></section>
    <footer className="public-footer-v2"><Teta2Logo/><p>{c.public.footer}</p><div>{languageToggle()}</div></footer>
  </main>;
}

function Checkmark(){ return <svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><path d="m5 12 4 4L19 6" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>; }
