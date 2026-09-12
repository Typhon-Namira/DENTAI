import {
  Activity,
  ArrowRight,
  Bell,
  CalendarClock,
  Check,
  ChevronRight,
  CircleUserRound,
  ClipboardCheck,
  FileImage,
  FolderHeart,
  HeartPulse,
  History,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  MessageCircle,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  UserRound,
  UsersRound,
  WandSparkles,
  X
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { api, clearSession, errorMessage, hasSession } from "../api/client";
import { productApi, type BranchSummary, type DashboardSummary, type FollowUp, type FollowUpPriority, type FollowUpStatus } from "../api/product";
import type { AIAnalysis, CurrentUser, DentalFinding, Patient, PatientProfile, WhatsAppOutreach, XRay } from "../api/types";
import { AnalysisResults } from "../components/AnalysisResults";
import { WhatsAppOutreachCard } from "../components/WhatsAppOutreachCard";
import { productCopy, type ProductLang } from "./content";
import ClinicalCareApp from "./ClinicalCareApp";
import { FirstVisitLanguageModal, LanguageDropdown, PublicFooter as SharedFooter, PublicNavbar, type PublicLanguage } from "./PublicChrome";

const LANG_KEY = "teta2-product-language";
const OPG_HERO_URL = "https://images.squarespace-cdn.com/content/v1/57e01f4c2e69cf3a18c52ac1/09f04224-c53b-4362-aff2-52ae4d2cc114/OPG.jpg";

const PUBLIC_ROUTES = [
  "/",
  "/product",
  "/how-it-works",
  "/pricing",
  "/clinical-safety",
  "/about",
  "/login",
  "/register"
] as const;

type PublicRoute = typeof PUBLIC_ROUTES[number];
type ClinicSection = "dashboard" | "patients" | "opg" | "followups" | "messages" | "settings";
type PatientTab = "overview" | "opg" | "findings" | "followups" | "messages";
type Market = "AM" | "RU";

function browserRoute(): PublicRoute {
  const legacy: Record<string, PublicRoute> = {
    "/platform": "/product",
    "/ai-workspace": "/how-it-works",
    "/smart-recall": "/product",
    "/security": "/clinical-safety",
    "/radar-ai": "/product"
  };
  const path = legacy[window.location.pathname] ?? window.location.pathname;
  return PUBLIC_ROUTES.includes(path as PublicRoute) ? path as PublicRoute : "/";
}

function storedLanguage(): ProductLang | null {
  const value = localStorage.getItem(LANG_KEY) ?? localStorage.getItem("teta2-v4-language");
  return value === "en" || value === "hy" || value === "ru" ? value : null;
}

const LANGUAGE_LOCALE: Record<ProductLang, string> = { en: "en-US", hy: "hy-AM", ru: "ru-RU" };

function initialLanguage(): ProductLang {
  const stored = storedLanguage();
  if (stored) return stored;
  const browser = navigator.language.toLowerCase();
  return browser.startsWith("hy") ? "hy" : browser.startsWith("ru") ? "ru" : "en";
}

function patientName(patient: Patient): string {
  return `${patient.first_name} ${patient.last_name}`.trim();
}

function patientInitials(patient: Patient): string {
  return `${patient.first_name[0] ?? ""}${patient.last_name[0] ?? ""}`.toUpperCase();
}

function dateTime(value: string | null | undefined, lang: ProductLang): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return new Intl.DateTimeFormat(LANGUAGE_LOCALE[lang], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(parsed);
}

function dateOnly(value: string | null | undefined, lang: ProductLang): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return new Intl.DateTimeFormat(LANGUAGE_LOCALE[lang], {
    year: "numeric",
    month: "short",
    day: "numeric"
  }).format(parsed);
}

function statusText(status: string, lang: ProductLang): string {
  const normalized = status.toUpperCase();
  if (lang === "en") return normalized.replaceAll("_", " ");
  const map: Record<string, string> = {
    QUEUED: "Հերթագրված",
    PROCESSING: "Մշակվում է",
    COMPLETED: "Ավարտված",
    FAILED: "Ձախողված",
    PENDING: "Սպասող",
    CONFIRMED: "Հաստատված",
    REJECTED: "Մերժված",
    UNREVIEWED: "Չվերանայված",
    REVIEWED: "Վերանայված",
    SCHEDULED: "Պլանավորված",
    DUE: "Ժամկետը հասել է",
    CANCELLED: "Չեղարկված",
    SENT: "Ուղարկված",
    SENDING: "Ուղարկվում է",
    FAILED_OUTREACH: "Ձախողված"
  };
  return map[normalized] ?? normalized.replaceAll("_", " ");
}

function findingLabel(value: string, lang: ProductLang): string {
  const normalized = value.toUpperCase();
  if (lang === "en") return normalized.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
  const map: Record<string, string> = {
    CARIES: "Կարիես",
    DEEP_CARIES: "Խորը կարիես",
    FILLING: "Լցոնում",
    CROWN: "Պսակ",
    IMPACTED: "Իմպակցված ատամ",
    ROOT_CANAL_TREATMENT: "Արմատախողովակային բուժում",
    APICAL_PERIODONTITIS: "Ապիկալ պերիօդոնտիտ",
    BONE_RESORPTION: "Ոսկրային ռեզորբցիա",
    ROOT_FRAGMENT: "Արմատի բեկոր"
  };
  return map[normalized] ?? normalized.replaceAll("_", " ");
}

export default function ProductApp() {
  const [lang, setLangState] = useState<ProductLang>(() => initialLanguage());
  const [showLanguageModal, setShowLanguageModal] = useState(() => storedLanguage() === null);
  const [route, setRoute] = useState<PublicRoute>(() => browserRoute());
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [restoring, setRestoring] = useState(hasSession());

  const setLang = useCallback((next: ProductLang) => {
    localStorage.setItem(LANG_KEY, next);
    localStorage.setItem("teta2-v4-language", next);
    document.documentElement.lang = next;
    setLangState(next);
    setShowLanguageModal(false);
    window.dispatchEvent(new CustomEvent("teta2-language-change", { detail: next }));
  }, []);

  const go = useCallback((path: PublicRoute) => {
    window.history.pushState({}, "", path);
    setRoute(path);
    // PlatformAccessExperience owns the live access-request form and listens
    // for route changes independently. pushState does not emit popstate, so
    // notify every mounted route consumer immediately instead of requiring a
    // full page refresh before the form appears.
    window.dispatchEvent(new PopStateEvent("popstate"));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  useEffect(() => {
    const listener = () => setRoute(browserRoute());
    window.addEventListener("popstate", listener);
    return () => window.removeEventListener("popstate", listener);
  }, []);

  useEffect(() => {
    if (lang) document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    if (!hasSession()) {
      setRestoring(false);
      return;
    }
    api.me()
      .then(setUser)
      .catch(() => clearSession())
      .finally(() => setRestoring(false));
  }, []);

  const experience = restoring ? <div className="product-restore"><strong>Teta2</strong><span className="product-spinner" /></div>
    : user ? <ClinicalCareApp onSignedOut={() => setUser(null)} />
    : route === "/login" ? <LoginPage lang={lang} setLang={setLang} onAuthenticated={setUser} go={go} />
    : route === "/register" ? null
    : <PublicProduct lang={lang} setLang={setLang} route={route} go={go} />;
  return <>{experience}{showLanguageModal && <FirstVisitLanguageModal onSelect={(next: PublicLanguage) => setLang(next)} />}</>;
}

function PublicProduct({ lang, setLang, route, go }: { lang: ProductLang; setLang: (lang: ProductLang) => void; route: PublicRoute; go: (route: PublicRoute) => void }) {
  return (
    <div className="product-public">
      <PublicNavbar language={lang} onLanguage={setLang} copy={productCopy(lang).nav} route={route} go={go} />
      {route === "/" && <HomePage lang={lang} go={go} />}
      {route === "/product" && <ProductPage lang={lang} go={go} />}
      {route === "/how-it-works" && <HowPage lang={lang} go={go} />}
      {route === "/pricing" && <PricingPage lang={lang} go={go} />}
      {route === "/clinical-safety" && <SafetyPage lang={lang} go={go} />}
      {route === "/about" && <AboutPage lang={lang} go={go} />}
      <SharedFooter copy={productCopy(lang).nav} description={lang === "hy" ? "AI-ով OPG ինտելեկտ և պացիենտի հետագա վերահսկում։" : lang === "ru" ? "ИИ-анализ OPG и клиническое наблюдение пациентов." : "AI-powered OPG intelligence and patient follow-up."} go={go} />
    </div>
  );
}

function HomePage({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  const c = productCopy(lang);
  return (
    <>
      <section className="product-hero">
        <div className="product-hero-copy">
          <span className="product-pill"><Sparkles size={15} />{c.hero.eyebrow}</span>
          <h1>{c.hero.title}</h1>
          <p>{c.hero.lead}</p>
          <div className="product-hero-actions">
            <button className="product-primary" onClick={() => go("/login")}>{c.hero.primary}<ArrowRight size={18} /></button>
            <button className="product-secondary" onClick={() => go("/how-it-works")}>{c.hero.secondary}</button>
          </div>
          <div className="product-proof-row">{c.hero.proof.map((item) => <span key={item}><Check size={14} />{item}</span>)}</div>
        </div>
        <HeroOpgVisual lang={lang} />
      </section>
      <SafetyStrip lang={lang} go={go} />
      <section className="product-final-cta"><div><span>{c.workflow.kicker}</span><h2>{c.plans.care.tagline}</h2><p>{c.plans.care.outcome}</p></div><button className="product-primary" onClick={() => go("/register")}>{c.nav.access}<ArrowRight size={18} /></button></section>
    </>
  );
}

function HeroOpgVisual({ lang }: { lang: ProductLang }) {
  return (
    <div className="product-hero-visual" aria-label={lang === "hy" ? "OPG վերլուծության նախադիտում" : "OPG analysis preview"}>
      <div className="product-hero-visual-top"><span><i />AI-assisted review</span><b>{lang === "hy" ? "Բժիշկը վերահսկում է" : "Clinician in control"}</b></div>
      <div className="product-hero-opg"><img src={OPG_HERO_URL} alt="Panoramic dental X-ray" /><span className="product-demo-region r1">16</span><span className="product-demo-region r2">24</span><span className="product-demo-region pathology r3">36</span></div>
      <div className="product-hero-loop"><span>OPG</span><ArrowRight /><span>AI</span><ArrowRight /><span>{lang === "hy" ? "Քարտ" : "Record"}</span><ArrowRight /><span>{lang === "hy" ? "Հետևել" : "Follow"}</span><ArrowRight /><strong>{lang === "hy" ? "Վերադարձ" : "Return"}</strong></div>
    </div>
  );
}

function ProblemSection({ lang }: { lang: ProductLang }) {
  const c = productCopy(lang).problem;
  const icons = [<WandSparkles key="a" />, <FolderHeart key="b" />, <HeartPulse key="c" />];
  return (
    <section className="product-section product-problem">
      <SectionHeading kicker={c.kicker} title={c.title} body={c.body} />
      <div className="product-three-grid">{c.cards.map(([title, body], index) => <article key={title}><span>{icons[index]}</span><h3>{title}</h3><p>{body}</p></article>)}</div>
    </section>
  );
}

function WorkflowSection({ lang }: { lang: ProductLang }) {
  const c = productCopy(lang).workflow;
  return (
    <section className="product-section product-workflow-section" id="workflow">
      <SectionHeading kicker={c.kicker} title={c.title} />
      <div className="product-workflow-grid">{c.steps.map(([number, title, body]) => <article key={number}><b>{number}</b><div><h3>{title}</h3><p>{body}</p></div></article>)}</div>
    </section>
  );
}

function PlanSection({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  const c = productCopy(lang);
  return (
    <section className="product-section product-plans-section">
      <SectionHeading kicker={c.plans.kicker} title={c.plans.title} />
      <div className="product-plan-grid">
        <PlanCard plan="scan" lang={lang} onAction={() => go("/pricing")} />
        <PlanCard plan="care" lang={lang} onAction={() => go("/pricing")} featured />
      </div>
    </section>
  );
}

function PlanCard({ plan, lang, onAction, featured = false }: { plan: "scan" | "care"; lang: ProductLang; onAction: () => void; featured?: boolean }) {
  const c = productCopy(lang);
  const details = c.plans[plan];
  return (
    <article className={`product-plan-card ${featured ? "featured" : ""}`}>
      <div className="product-plan-card-head"><span>{plan === "scan" ? <FileImage /> : <HeartPulse />}</span><div><small>{details.outcome}</small><h3>{details.name}</h3><p>{details.tagline}</p></div></div>
      <ul>{details.features.map((feature) => <li key={feature}><Check size={15} />{feature}</li>)}</ul>
      <button className={featured ? "product-primary" : "product-secondary"} onClick={onAction}>{c.nav.pricing}<ArrowRight size={16} /></button>
    </article>
  );
}

function SafetyStrip({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  const c = productCopy(lang).safety;
  return (
    <section className="product-safety-strip"><ShieldCheck /><div><span>{c.kicker}</span><h2>{c.title}</h2><p>{c.body}</p></div><button onClick={() => go("/clinical-safety")}>{productCopy(lang).nav.safety}<ArrowRight size={16} /></button></section>
  );
}

function ProductPage({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  return <main className="product-marketing-page"><ProblemSection lang={lang} /><PlanSection lang={lang} go={go} /></main>;
}

function HowPage({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  const c = productCopy(lang);
  return <main className="product-marketing-page"><WorkflowSection lang={lang} /><section className="product-final-cta"><div><span>{c.plans.kicker}</span><h2>{c.plans.scan.tagline}</h2><p>{c.safety.body}</p></div><button className="product-primary" onClick={() => go("/login")}>{c.hero.primary}<ArrowRight size={18} /></button></section></main>;
}

function PricingPage({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  const c = productCopy(lang);
  const [market, setMarket] = useState<Market>("AM");
  const pricing = market === "AM" ? { scan: "49,000 AMD", care: "99,000 AMD" } : { scan: "4,990 RUB", care: "9,990 RUB" };
  return (
    <main className="product-marketing-page product-pricing-page">
      <SectionHeading kicker={c.nav.pricing} title={c.pricing.title} body={c.pricing.lead} />
      <div className="product-market-switch"><span>{c.pricing.market}</span><button className={market === "AM" ? "active" : ""} onClick={() => setMarket("AM")}>Armenia</button><button className={market === "RU" ? "active" : ""} onClick={() => setMarket("RU")}>Russia</button></div>
      <div className="product-pricing-grid">
        {(["scan", "care"] as const).map((plan) => {
          const details = c.plans[plan];
          return <article key={plan} className={plan === "care" ? "featured" : ""}><small>{details.outcome}</small><h2>{details.name}</h2><p>{details.tagline}</p><div className="product-price"><strong>{pricing[plan]}</strong><span>/ {c.pricing.monthly}</span></div><div className="product-unlimited"><Check size={16} />{c.pricing.unlimited}</div><ul>{details.features.map((feature) => <li key={feature}><Check size={14} />{feature}</li>)}</ul><button className={plan === "care" ? "product-primary" : "product-secondary"} onClick={() => go("/register")}>{c.pricing.choose}</button></article>;
        })}
      </div>
      <p className="product-annual-note">{c.pricing.annual}</p>
    </main>
  );
}

function SafetyPage({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  const c = productCopy(lang).safety;
  const icons = [<ClipboardCheck key="a" />, <LockKeyhole key="b" />, <ShieldCheck key="c" />];
  return (
    <main className="product-marketing-page">
      <SectionHeading kicker={c.kicker} title={c.title} body={c.body} />
      <div className="product-three-grid product-safety-grid">{c.items.map(([title, body], index) => <article key={title}><span>{icons[index]}</span><h3>{title}</h3><p>{body}</p></article>)}</div>
      <section className="product-clinical-language"><strong>{lang === "hy" ? "Teta2-ի կլինիկական լեզուն" : "Teta2 clinical language"}</strong><p>{lang === "hy" ? "«Հնարավոր հայտնաբերում», «AI-ով աջակցվող վերլուծություն» և «պահանջում է ատամնաբույժի զննում»։" : "“Possible finding”, “AI-assisted analysis”, and “requires dentist examination”."}</p></section>
      <section className="product-final-cta"><div><span>{c.kicker}</span><h2>{lang === "hy" ? "Սկսեք վերահսկվող կլինիկական workflow-ից։" : "Start with a clinician-controlled workflow."}</h2></div><button className="product-primary" onClick={() => go("/register")}>{productCopy(lang).nav.access}</button></section>
    </main>
  );
}

function AboutPage({ lang, go }: { lang: ProductLang; go: (route: PublicRoute) => void }) {
  const c = productCopy(lang).about;
  return (
    <main className="product-marketing-page">
      <SectionHeading kicker="Teta2" title={c.title} body={c.lead} />
      <blockquote className="product-principle">{c.principle}</blockquote>
      <div className="product-roadmap">{c.roadmap.map((item, index) => <article key={item}><b>0{index + 1}</b><p>{item}</p></article>)}</div>
      <section className="product-final-cta"><div><span>Teta2</span><h2>{productCopy(lang).plans.care.tagline}</h2></div><button className="product-primary" onClick={() => go("/register")}>{productCopy(lang).nav.access}</button></section>
    </main>
  );
}

function SectionHeading({ kicker, title, body }: { kicker: string; title: string; body?: string }) {
  return <header className="product-section-heading"><span>{kicker}</span><h2>{title}</h2>{body && <p>{body}</p>}</header>;
}

function LoginPage({ lang, setLang, onAuthenticated, go }: { lang: ProductLang; setLang: (lang: ProductLang) => void; onAuthenticated: (user: CurrentUser) => void; go: (route: PublicRoute) => void }) {
  const [clinic, setClinic] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.login({ clinic_slug: clinic.trim(), identifier: identifier.trim(), password });
      onAuthenticated(await api.me());
    } catch (reason) {
      clearSession();
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="product-auth-shell">
      <PublicNavbar language={lang} onLanguage={setLang} copy={productCopy(lang).nav} route="/login" go={go} />
      <main className="product-login-page">
      <section className="product-login-story"><span className="product-kicker">OPG → AI → RECORD → FOLLOW → RETURN</span><h1>{lang === "hy" ? "Մուտք գործեք ձեր կլինիկական workspace։" : lang === "ru" ? "Войдите в клиническое рабочее пространство." : "Sign in to your clinical workspace."}</h1><p>{lang === "hy" ? "Մեկ կենտրոնացված workflow՝ OPG վերլուծության, պացիենտի քարտի և հետագա վերահսկման համար։" : lang === "ru" ? "Единый процесс для OPG-анализа, карты пациента и последующего наблюдения." : "One focused workflow for OPG analysis, the smart patient file and follow-up."}</p><HeroOpgVisual lang={lang} /></section>
      <section className="product-login-card"><h2>{lang === "hy" ? "Կլինիկայի մուտք" : lang === "ru" ? "Вход для клиники" : "Clinic sign in"}</h2><p>{lang === "hy" ? "Օգտագործեք ձեր provision արված clinic slug-ը և հաշիվը։" : lang === "ru" ? "Используйте идентификатор клиники и учетную запись, полученные при активации." : "Use the clinic slug and account provisioned for your clinic."}</p><form onSubmit={submit}><label>{lang === "ru" ? "Идентификатор клиники" : "Clinic slug"}<input required autoComplete="organization" value={clinic} onChange={(event) => setClinic(event.target.value)} placeholder="your-clinic" /></label><label>{lang === "hy" ? "Էլ․ փոստ կամ օգտանուն" : lang === "ru" ? "Email или имя пользователя" : "Email or username"}<input required autoComplete="username" value={identifier} onChange={(event) => setIdentifier(event.target.value)} /></label><label>{lang === "hy" ? "Գաղտնաբառ" : lang === "ru" ? "Пароль" : "Password"}<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>{error && <div className="product-error" role="alert">{error}</div>}<button className="product-primary" disabled={busy}>{busy ? (lang === "hy" ? "Մուտք…" : lang === "ru" ? "Вход…" : "Signing in…") : (lang === "hy" ? "Անվտանգ մուտք" : lang === "ru" ? "Безопасный вход" : "Sign in securely")}</button></form><button className="product-link-button" onClick={() => go("/register")}>{productCopy(lang).nav.access}</button></section>
      </main>
      <SharedFooter copy={productCopy(lang).nav} description={lang === "hy" ? "AI-ով OPG ինտելեկտ և պացիենտի հետագա վերահսկում։" : lang === "ru" ? "ИИ-анализ OPG и клиническое наблюдение пациентов." : "AI-powered OPG intelligence and patient follow-up."} go={go} />
    </div>
  );
}

function ClinicProduct({ lang, setLang, user, onLogout }: { lang: ProductLang; setLang: (lang: ProductLang) => void; user: CurrentUser; onLogout: () => void }) {
  const c = productCopy(lang).clinic;
  const [section, setSection] = useState<ClinicSection>("dashboard");
  const [patients, setPatients] = useState<Patient[]>([]);
  const [branches, setBranches] = useState<BranchSummary[]>([]);
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createPatientOpen, setCreatePatientOpen] = useState(false);

  const selectedPatient = patients.find((patient) => patient.id === selectedPatientId) ?? null;

  const refreshCore = useCallback(async () => {
    const [patientPage, branchRows, dashboardSummary, followUpPage] = await Promise.all([
      api.listPatients(),
      productApi.branches(),
      productApi.dashboard(user.role),
      productApi.listFollowUps()
    ]);
    setPatients(patientPage.items);
    setBranches(branchRows);
    setDashboard(dashboardSummary);
    setFollowUps(followUpPage.items);
    setSelectedPatientId((current) => current ?? patientPage.items[0]?.id ?? null);
  }, [user.role]);

  const loadProfile = useCallback(async (patientId: string) => {
    setProfile(await api.patientProfile(patientId));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    void refreshCore().catch((reason) => setError(errorMessage(reason))).finally(() => setLoading(false));
  }, [refreshCore]);

  useEffect(() => {
    if (!selectedPatientId) {
      setProfile(null);
      return;
    }
    setError("");
    void loadProfile(selectedPatientId).catch((reason) => setError(errorMessage(reason)));
  }, [selectedPatientId, loadProfile]);

  async function logout() {
    try { await api.logout(); } finally { clearSession(); onLogout(); }
  }

  function openPatient(patientId: string, target: ClinicSection = "patients") {
    setSelectedPatientId(patientId);
    setSection(target);
  }

  const nav: Array<[ClinicSection, string, React.ReactNode]> = [
    ["dashboard", c.dashboard, <LayoutDashboard key="dashboard" />],
    ["patients", c.patients, <UsersRound key="patients" />],
    ["opg", c.opg, <FileImage key="opg" />],
    ["followups", c.followups, <CalendarClock key="followups" />],
    ["messages", c.messages, <MessageCircle key="messages" />],
    ["settings", c.settings, <Settings key="settings" />]
  ];

  return (
    <div className="clinic-shell">
      <aside className="clinic-sidebar">
        <strong className="product-wordmark">Teta2</strong>
        <nav>{nav.map(([key, label, icon]) => <button key={key} className={section === key ? "active" : ""} onClick={() => setSection(key)}>{icon}<span>{label}</span>{key === "followups" && Number(dashboard?.followups_due ?? 0) > 0 && <i>{dashboard?.followups_due}</i>}</button>)}</nav>
        <div className="clinic-user"><span>{user.username.slice(0, 2).toUpperCase()}</span><div><strong>{user.username}</strong><small>{user.role}</small></div><button aria-label="Sign out" onClick={() => void logout()}><LogOut /></button></div>
      </aside>
      <header className="clinic-header">
        <div><strong>{section === "dashboard" ? c.dashboardTitle : nav.find(([key]) => key === section)?.[1]}</strong><span>{section === "dashboard" ? c.dashboardLead : selectedPatient ? `${patientName(selectedPatient)} · ${selectedPatient.patient_number}` : c.selectPatient}</span></div>
        <div className="clinic-header-actions">
          <PatientQuickSelect lang={lang} patients={patients} selectedPatientId={selectedPatientId} onSelect={setSelectedPatientId} />
          <LanguageDropdown language={lang} onChange={setLang} />
          <button className="clinic-icon-button" aria-label="Notifications"><Bell /></button>
        </div>
      </header>
      <main className="clinic-main">
        {error && <div className="product-error clinic-error" role="alert">{error}<button onClick={() => setError("")}><X /></button></div>}
        {loading ? <ClinicLoading /> : (
          <>
            {section === "dashboard" && <ClinicDashboard lang={lang} dashboard={dashboard} patients={patients} followUps={followUps} onOpenPatient={openPatient} onGo={setSection} />}
            {section === "patients" && <PatientsPage lang={lang} user={user} patients={patients} branches={branches} selectedPatientId={selectedPatientId} profile={profile} onSelect={setSelectedPatientId} onOpenCreate={() => setCreatePatientOpen(true)} onGoOpg={() => setSection("opg")} onProfileRefresh={() => selectedPatientId ? loadProfile(selectedPatientId) : undefined} />}
            {section === "opg" && <OpgPage lang={lang} user={user} patients={patients} selectedPatientId={selectedPatientId} profile={profile} onSelectPatient={setSelectedPatientId} onProfile={setProfile} />}
            {section === "followups" && <FollowUpsPage lang={lang} patients={patients} followUps={followUps} selectedPatientId={selectedPatientId} onSelectPatient={setSelectedPatientId} onRefresh={async () => { const page = await productApi.listFollowUps(); setFollowUps(page.items); setDashboard(await productApi.dashboard(user.role)); if (selectedPatientId) await loadProfile(selectedPatientId); }} />}
            {section === "messages" && <MessagesPage lang={lang} patients={patients} selectedPatientId={selectedPatientId} onSelectPatient={setSelectedPatientId} onPatientUpdated={(updated) => { setPatients((current) => current.map((item) => item.id === updated.id ? updated : item)); if (profile?.patient.id === updated.id) setProfile({ ...profile, patient: updated }); }} />}
            {section === "settings" && <SettingsPage lang={lang} user={user} branches={branches} />}
          </>
        )}
      </main>
      {createPatientOpen && <CreatePatientModal lang={lang} branches={branches} onClose={() => setCreatePatientOpen(false)} onCreated={async (patient) => { setCreatePatientOpen(false); await refreshCore(); setSelectedPatientId(patient.id); setSection("patients"); }} />}
    </div>
  );
}

function PatientQuickSelect({ lang, patients, selectedPatientId, onSelect }: { lang: ProductLang; patients: Patient[]; selectedPatientId: string | null; onSelect: (id: string) => void }) {
  return <label className="clinic-patient-select"><Search /><select value={selectedPatientId ?? ""} onChange={(event) => onSelect(event.target.value)}><option value="" disabled>{productCopy(lang).clinic.selectPatient}</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patientName(patient)} · {patient.patient_number}</option>)}</select></label>;
}

function ClinicLoading() {
  return <div className="clinic-loading"><span className="product-spinner" /><p>Loading clinical workspace…</p></div>;
}

function ClinicDashboard({ lang, dashboard, patients, followUps, onOpenPatient, onGo }: { lang: ProductLang; dashboard: DashboardSummary | null; patients: Patient[]; followUps: FollowUp[]; onOpenPatient: (id: string, target?: ClinicSection) => void; onGo: (section: ClinicSection) => void }) {
  const c = productCopy(lang).clinic;
  const patientCount = Number(dashboard?.patient_count ?? dashboard?.authorized_patient_count ?? dashboard?.assigned_patient_count ?? patients.length);
  const analysisCount = dashboard?.ai_analysis_count;
  const due = followUps.filter((item) => item.status === "DUE").length || Number(dashboard?.followups_due ?? 0);
  const activeFollowUps = followUps.filter((item) => item.status === "DUE" || item.status === "SCHEDULED").length;
  return (
    <div className="clinic-dashboard-page">
      <section className="clinic-action-hero"><div><span className="product-kicker">OPG → AI → RECORD → FOLLOW → RETURN</span><h1>{c.dashboardTitle}</h1><p>{c.dashboardLead}</p></div><button className="product-primary" onClick={() => onGo("opg")}><UploadCloud />{c.upload}</button></section>
      <div className="clinic-metric-grid">
        <MetricCard icon={<UsersRound />} value={patientCount} label={c.patients} />
        <MetricCard icon={<WandSparkles />} value={typeof analysisCount === "number" ? analysisCount : "—"} label={lang === "hy" ? "AI վերլուծություններ" : "AI analyses"} />
        <MetricCard icon={<CalendarClock />} value={due} label={lang === "hy" ? "Ժամկետը հասած" : "Follow-ups due"} urgent={due > 0} />
        <MetricCard icon={<HeartPulse />} value={activeFollowUps} label={lang === "hy" ? "Ակտիվ հետագա վերահսկում" : "Active follow-up"} />
      </div>
      <div className="clinic-dashboard-grid">
        <section className="clinic-card"><CardHeading title={lang === "hy" ? "Վերջին պացիենտները" : "Recent patients"} action={c.patients} onAction={() => onGo("patients")} /><div className="clinic-patient-list">{patients.slice(0, 6).map((patient) => <button key={patient.id} onClick={() => onOpenPatient(patient.id)}><span>{patientInitials(patient)}</span><div><strong>{patientName(patient)}</strong><small>{patient.patient_number}</small></div><ChevronRight /></button>)}</div></section>
        <section className="clinic-card"><CardHeading title={lang === "hy" ? "Հետագա գործողություններ" : "Follow-up actions"} action={c.followups} onAction={() => onGo("followups")} />{followUps.length ? <div className="clinic-followup-compact">{followUps.slice(0, 6).map((item) => { const patient = patients.find((row) => row.id === item.patient_id); return <article key={item.id}><span className={`clinic-status ${item.status.toLowerCase()}`}>{statusText(item.status, lang)}</span><div><strong>{patient ? patientName(patient) : item.patient_id}</strong><p>{item.reason}</p></div><time>{dateOnly(item.due_at, lang)}</time></article>; })}</div> : <EmptyState icon={<CalendarClock />} text={productCopy(lang).clinic.noFollowups} />}</section>
      </div>
    </div>
  );
}

function MetricCard({ icon, value, label, urgent = false }: { icon: React.ReactNode; value: string | number; label: string; urgent?: boolean }) {
  return <article className={`clinic-metric-card ${urgent ? "urgent" : ""}`}><span>{icon}</span><div><strong>{value}</strong><small>{label}</small></div></article>;
}

function CardHeading({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return <header className="clinic-card-heading"><h2>{title}</h2>{action && onAction && <button onClick={onAction}>{action}<ArrowRight size={15} /></button>}</header>;
}

function PatientsPage({ lang, user, patients, branches, selectedPatientId, profile, onSelect, onOpenCreate, onGoOpg }: { lang: ProductLang; user: CurrentUser; patients: Patient[]; branches: BranchSummary[]; selectedPatientId: string | null; profile: PatientProfile | null; onSelect: (id: string) => void; onOpenCreate: () => void; onGoOpg: () => void; onProfileRefresh: () => Promise<void> | void }) {
  const [query, setQuery] = useState("");
  const visible = patients.filter((patient) => `${patientName(patient)} ${patient.patient_number}`.toLowerCase().includes(query.toLowerCase()));
  return (
    <div className="clinic-patients-page">
      <div className="clinic-page-toolbar"><label><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={lang === "hy" ? "Փնտրել պացիենտ" : "Search patients"} /></label>{user.role !== "DOCTOR" && <button className="product-primary" onClick={onOpenCreate}><Plus />{productCopy(lang).clinic.newPatient}</button>}</div>
      <div className="clinic-patient-layout">
        <section className="clinic-card clinic-directory"><div className="clinic-directory-list">{visible.map((patient) => <button key={patient.id} className={selectedPatientId === patient.id ? "active" : ""} onClick={() => onSelect(patient.id)}><span>{patientInitials(patient)}</span><div><strong>{patientName(patient)}</strong><small>{patient.patient_number}</small></div><i>{patient.status}</i></button>)}</div></section>
        <SmartPatientFile lang={lang} profile={profile} branches={branches} onGoOpg={onGoOpg} />
      </div>
    </div>
  );
}

function SmartPatientFile({ lang, profile, branches, onGoOpg }: { lang: ProductLang; profile: PatientProfile | null; branches: BranchSummary[]; onGoOpg: () => void }) {
  const c = productCopy(lang).clinic;
  const [tab, setTab] = useState<PatientTab>("overview");
  useEffect(() => setTab("overview"), [profile?.patient.id]);
  if (!profile) return <section className="clinic-card clinic-smart-file"><EmptyState icon={<CircleUserRound />} text={c.noPatient} /></section>;
  const patient = profile.patient;
  const latestAnalysis = [...profile.ai_analyses].sort((a, b) => b.requested_at.localeCompare(a.requested_at))[0];
  const findings = latestAnalysis ? profile.findings.filter((finding) => finding.analysis_id === latestAnalysis.id) : profile.findings;
  const branch = branches.find((item) => item.id === patient.branch_id);
  const tabs: Array<[PatientTab, string]> = [["overview", c.overview], ["opg", c.opgHistory], ["findings", c.findings], ["followups", c.timeline], ["messages", c.messageHistory]];
  return (
    <section className="clinic-card clinic-smart-file">
      <header className="smart-file-head"><div><span className="patient-large-avatar">{patientInitials(patient)}</span><div><small>{c.careRecord}</small><h2>{patientName(patient)}</h2><p>{patient.patient_number} · {branch?.name ?? patient.branch_id}</p></div></div><button className="product-secondary" onClick={onGoOpg}><FileImage />{c.opg}</button></header>
      <nav className="smart-file-tabs">{tabs.map(([key, label]) => <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{label}</button>)}</nav>
      {tab === "overview" && <div className="smart-overview"><dl><div><dt>{lang === "hy" ? "Հեռախոս" : "Phone"}</dt><dd>{patient.phone ?? "—"}</dd></div><div><dt>WhatsApp</dt><dd>{patient.whatsapp_phone ?? "—"}</dd></div><div><dt>{lang === "hy" ? "Էլ․ փոստ" : "Email"}</dt><dd>{patient.email ?? "—"}</dd></div><div><dt>{lang === "hy" ? "OPG-ներ" : "OPGs"}</dt><dd>{profile.xrays.length}</dd></div><div><dt>{lang === "hy" ? "AI վերլուծություններ" : "AI analyses"}</dt><dd>{profile.ai_analyses.length}</dd></div><div><dt>{lang === "hy" ? "Հետագա վերահսկումներ" : "Follow-ups"}</dt><dd>{profile.followups.length}</dd></div></dl>{latestAnalysis && <div className="smart-latest-analysis"><span>{statusText(latestAnalysis.status, lang)}</span><div><strong>{lang === "hy" ? "Վերջին AI վերլուծություն" : "Latest AI-assisted analysis"}</strong><p>{dateTime(latestAnalysis.completed_at ?? latestAnalysis.requested_at, lang)} · {findings.length} {c.possibleFinding}</p></div></div>}</div>}
      {tab === "opg" && <OpgHistory lang={lang} xrays={profile.xrays} analyses={profile.ai_analyses} />}
      {tab === "findings" && <FindingsTable lang={lang} findings={profile.findings} />}
      {tab === "followups" && <PatientFollowUpTimeline lang={lang} followUps={profile.followups as FollowUp[]} />}
      {tab === "messages" && <PatientMessageHistory lang={lang} patient={patient} />}
    </section>
  );
}

function OpgHistory({ lang, xrays, analyses }: { lang: ProductLang; xrays: XRay[]; analyses: AIAnalysis[] }) {
  const sorted = [...xrays].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at));
  return <div className="smart-table">{sorted.length ? sorted.map((xray) => { const analysis = [...analyses].filter((item) => item.xray_id === xray.id).sort((a, b) => b.requested_at.localeCompare(a.requested_at))[0]; return <article key={xray.id}><FileImage /><div><strong>{xray.original_filename}</strong><small>{dateTime(xray.captured_at ?? xray.uploaded_at, lang)}</small></div><span>{analysis ? statusText(analysis.status, lang) : (lang === "hy" ? "Չվերլուծված" : "Not analyzed")}</span></article>; }) : <EmptyState icon={<History />} text={lang === "hy" ? "OPG պատմություն դեռ չկա։" : "No OPG history yet."} />}</div>;
}

function FindingsTable({ lang, findings }: { lang: ProductLang; findings: DentalFinding[] }) {
  const visible = [...findings].sort((a, b) => b.created_at.localeCompare(a.created_at));
  return <div className="smart-findings">{visible.length ? visible.map((finding) => <article key={finding.id}><b>{finding.tooth_code ?? "—"}</b><div><strong>{findingLabel(finding.finding_type, lang)}</strong><small>{productCopy(lang).clinic.requiresExam}</small></div><span className={`clinic-status ${finding.review_status.toLowerCase()}`}>{statusText(finding.review_status, lang)}</span></article>) : <EmptyState icon={<ClipboardCheck />} text={lang === "hy" ? "Հայտնաբերումներ չկան։" : "No possible findings available."} />}</div>;
}

function PatientFollowUpTimeline({ lang, followUps }: { lang: ProductLang; followUps: FollowUp[] }) {
  const sorted = [...followUps].sort((a, b) => a.due_at.localeCompare(b.due_at));
  return <div className="smart-timeline">{sorted.length ? sorted.map((item) => <article key={item.id}><span /><div><strong>{item.reason}</strong><p>{dateTime(item.due_at, lang)} · {item.priority}</p></div><i className={`clinic-status ${item.status.toLowerCase()}`}>{statusText(item.status, lang)}</i></article>) : <EmptyState icon={<CalendarClock />} text={productCopy(lang).clinic.noFollowups} />}</div>;
}

function PatientMessageHistory({ lang, patient }: { lang: ProductLang; patient: Patient }) {
  const [items, setItems] = useState<WhatsAppOutreach[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { setLoading(true); void api.patientWhatsAppOutreach(patient.id).then((page) => setItems(page.items)).catch(() => setItems([])).finally(() => setLoading(false)); }, [patient.id]);
  if (loading) return <div className="smart-inline-loading">Loading…</div>;
  return <div className="smart-table">{items.length ? items.map((item) => <article key={item.id}><MessageCircle /><div><strong>{item.tooth_fdi} · {findingLabel(item.finding_type, lang)}</strong><small>{dateTime(item.created_at, lang)}</small></div><span>{statusText(item.status, lang)}</span></article>) : <EmptyState icon={<MessageCircle />} text={lang === "hy" ? "Հաղորդագրության պատմություն դեռ չկա։" : "No patient follow-up messages yet."} />}</div>;
}

function CreatePatientModal({ lang, branches, onClose, onCreated }: { lang: ProductLang; branches: BranchSummary[]; onClose: () => void; onCreated: (patient: Patient) => Promise<void> | void }) {
  const [number, setNumber] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [branchId, setBranchId] = useState(branches[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try { await onCreated(await productApi.createPatient({ patient_number: number.trim(), first_name: firstName.trim(), last_name: lastName.trim(), branch_id: branchId })); }
    catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(false); }
  }
  return <div className="clinic-modal-backdrop" role="dialog" aria-modal="true"><form className="clinic-modal" onSubmit={submit}><button type="button" className="clinic-modal-close" onClick={onClose}><X /></button><span className="product-kicker">{productCopy(lang).clinic.careRecord}</span><h2>{productCopy(lang).clinic.newPatient}</h2><label>{lang === "hy" ? "Պացիենտի համար" : "Patient number"}<input required value={number} onChange={(event) => setNumber(event.target.value)} /></label><div className="clinic-form-row"><label>{lang === "hy" ? "Անուն" : "First name"}<input required value={firstName} onChange={(event) => setFirstName(event.target.value)} /></label><label>{lang === "hy" ? "Ազգանուն" : "Last name"}<input required value={lastName} onChange={(event) => setLastName(event.target.value)} /></label></div><label>{lang === "hy" ? "Մասնաճյուղ" : "Branch"}<select required value={branchId} onChange={(event) => setBranchId(event.target.value)}>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label>{error && <div className="product-error">{error}</div>}<button className="product-primary" disabled={busy || !branchId}>{busy ? "…" : productCopy(lang).clinic.newPatient}</button></form></div>;
}

function OpgPage({ lang, user, patients, selectedPatientId, profile, onSelectPatient, onProfile }: { lang: ProductLang; user: CurrentUser; patients: Patient[]; selectedPatientId: string | null; profile: PatientProfile | null; onSelectPatient: (id: string) => void; onProfile: (profile: PatientProfile) => void }) {
  const c = productCopy(lang).clinic;
  const [selectedXrayId, setSelectedXrayId] = useState<string | null>(null);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const latestXray = profile?.xrays.length ? [...profile.xrays].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at))[0] : null;
    setSelectedXrayId(latestXray?.id ?? null);
  }, [profile?.patient.id, profile?.xrays.length]);

  const analysesForXray = useMemo(() => profile?.ai_analyses.filter((item) => item.xray_id === selectedXrayId).sort((a, b) => b.requested_at.localeCompare(a.requested_at)) ?? [], [profile?.ai_analyses, selectedXrayId]);
  useEffect(() => setSelectedAnalysisId(analysesForXray[0]?.id ?? null), [selectedXrayId, analysesForXray[0]?.id]);
  const selectedAnalysis = profile?.ai_analyses.find((item) => item.id === selectedAnalysisId) ?? analysesForXray[0] ?? null;
  const selectedXray = profile?.xrays.find((item) => item.id === selectedXrayId) ?? null;
  const findings = selectedAnalysis ? profile?.findings.filter((finding) => finding.analysis_id === selectedAnalysis.id) ?? [] : [];

  const refresh = useCallback(async () => {
    if (!selectedPatientId) return;
    onProfile(await api.patientProfile(selectedPatientId));
  }, [selectedPatientId, onProfile]);

  useEffect(() => {
    if (!selectedAnalysis || !["QUEUED", "PROCESSING"].includes(selectedAnalysis.status)) return;
    const timer = window.setInterval(() => void refresh().catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, [selectedAnalysis?.id, selectedAnalysis?.status, refresh]);

  async function upload(file: File) {
    if (!selectedPatientId) return;
    setUploading(true); setError("");
    try { const xray = await api.uploadXray(selectedPatientId, file); await refresh(); setSelectedXrayId(xray.id); }
    catch (reason) { setError(errorMessage(reason)); }
    finally { setUploading(false); if (inputRef.current) inputRef.current.value = ""; }
  }

  async function analyze() {
    if (!selectedXrayId) return;
    setAnalyzing(true); setError("");
    try { const analysis = await api.createAnalysis(selectedXrayId); await refresh(); setSelectedAnalysisId(analysis.id); }
    catch (reason) { setError(errorMessage(reason)); }
    finally { setAnalyzing(false); }
  }

  return (
    <div className="clinic-opg-page">
      <section className="clinic-card opg-control-bar">
        <label><span>{c.selectPatient}</span><select value={selectedPatientId ?? ""} onChange={(event) => onSelectPatient(event.target.value)}><option value="" disabled>{c.selectPatient}</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patientName(patient)} · {patient.patient_number}</option>)}</select></label>
        <label><span>{lang === "hy" ? "OPG հետազոտություն" : "OPG study"}</span><select value={selectedXrayId ?? ""} disabled={!profile?.xrays.length} onChange={(event) => setSelectedXrayId(event.target.value)}><option value="">{lang === "hy" ? "Ընտրեք OPG" : "Select OPG"}</option>{profile?.xrays.map((xray) => <option key={xray.id} value={xray.id}>{xray.original_filename} · {dateOnly(xray.uploaded_at, lang)}</option>)}</select></label>
        <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp,application/dicom,.dcm" hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); }} />
        <button className="product-secondary" disabled={!selectedPatientId || uploading} onClick={() => inputRef.current?.click()}><UploadCloud />{uploading ? "…" : c.upload}</button>
        <button className="product-primary" disabled={!selectedXrayId || analyzing || user.role !== "DOCTOR"} title={user.role !== "DOCTOR" ? (lang === "hy" ? "AI վերլուծությունը գործարկում է բժիշկը։" : "Only a Doctor can request AI analysis.") : undefined} onClick={() => void analyze()}><WandSparkles />{analyzing ? "…" : c.analyze}</button>
      </section>
      {error && <div className="product-error">{error}</div>}
      {!selectedPatientId ? <section className="clinic-card"><EmptyState icon={<UserRound />} text={c.noPatient} /></section> : !selectedXray ? <section className="clinic-card"><EmptyState icon={<FileImage />} text={lang === "hy" ? "Վերբեռնեք պացիենտի OPG-ն՝ AI-ով վերլուծությունը սկսելու համար։" : "Upload the patient’s OPG to start AI-assisted analysis."} /></section> : selectedAnalysis ? <AnalysisResults analysis={selectedAnalysis} xray={selectedXray} findings={findings} role={user.role} onReviewed={refresh} /> : <section className="clinic-card"><EmptyState icon={<Sparkles />} text={lang === "hy" ? "OPG-ն պատրաստ է։ Գործարկեք AI-ով աջակցվող վերլուծությունը։" : "The OPG is ready. Run AI-assisted analysis to generate possible findings."} /></section>}
    </div>
  );
}

function FollowUpsPage({ lang, patients, followUps, selectedPatientId, onSelectPatient, onRefresh }: { lang: ProductLang; patients: Patient[]; followUps: FollowUp[]; selectedPatientId: string | null; onSelectPatient: (id: string) => void; onRefresh: () => Promise<void> }) {
  const [filter, setFilter] = useState<"ALL" | FollowUpStatus>("ALL");
  const [formOpen, setFormOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [priority, setPriority] = useState<FollowUpPriority>("NORMAL");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const visible = followUps.filter((item) => filter === "ALL" || item.status === filter).sort((a, b) => a.due_at.localeCompare(b.due_at));

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!selectedPatientId) return;
    setBusy("create"); setError("");
    try { await productApi.createFollowUp(selectedPatientId, { reason: reason.trim(), due_at: new Date(dueAt).toISOString(), priority }); setFormOpen(false); setReason(""); setDueAt(""); await onRefresh(); }
    catch (reasonValue) { setError(errorMessage(reasonValue)); }
    finally { setBusy(""); }
  }

  async function update(id: string, status: FollowUpStatus) {
    setBusy(id); setError("");
    try { await productApi.updateFollowUp(id, status); await onRefresh(); }
    catch (reasonValue) { setError(errorMessage(reasonValue)); }
    finally { setBusy(""); }
  }

  return (
    <div className="clinic-followups-page">
      <section className="clinic-card followup-toolbar"><div className="followup-filters">{(["ALL", "DUE", "SCHEDULED", "COMPLETED", "CANCELLED"] as const).map((item) => <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item === "ALL" ? (lang === "hy" ? "Բոլորը" : "All") : statusText(item, lang)}</button>)}</div><button className="product-primary" disabled={!selectedPatientId} onClick={() => setFormOpen((value) => !value)}><Plus />{lang === "hy" ? "Ստեղծել հետագա վերահսկում" : "Create follow-up"}</button></section>
      {formOpen && <form className="clinic-card followup-create-form" onSubmit={create}><label>{productCopy(lang).clinic.selectPatient}<select value={selectedPatientId ?? ""} onChange={(event) => onSelectPatient(event.target.value)}>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patientName(patient)}</option>)}</select></label><label>{lang === "hy" ? "Պատճառ" : "Reason"}<input required value={reason} onChange={(event) => setReason(event.target.value)} placeholder={lang === "hy" ? "Օր. ատամ 36-ի վերահսկում" : "e.g. Review tooth 36 finding"} /></label><label>{lang === "hy" ? "Ժամկետ" : "Due at"}<input required type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} /></label><label>{lang === "hy" ? "Առաջնահերթություն" : "Priority"}<select value={priority} onChange={(event) => setPriority(event.target.value as FollowUpPriority)}><option value="LOW">LOW</option><option value="NORMAL">NORMAL</option><option value="HIGH">HIGH</option><option value="URGENT">URGENT</option></select></label><button className="product-primary" disabled={busy === "create"}>{busy === "create" ? "…" : (lang === "hy" ? "Պահպանել" : "Save follow-up")}</button></form>}
      {error && <div className="product-error">{error}</div>}
      <section className="clinic-card followup-table">{visible.length ? visible.map((item) => { const patient = patients.find((row) => row.id === item.patient_id); return <article key={item.id}><div className="followup-date"><b>{new Date(item.due_at).getDate()}</b><span>{new Intl.DateTimeFormat(lang === "hy" ? "hy-AM" : "en-US", { month: "short" }).format(new Date(item.due_at))}</span></div><div className="followup-main"><div><strong>{patient ? patientName(patient) : item.patient_id}</strong><small>{patient?.patient_number ?? ""}</small></div><h3>{item.reason}</h3><p>{dateTime(item.due_at, lang)} · {item.priority}</p></div><span className={`clinic-status ${item.status.toLowerCase()}`}>{statusText(item.status, lang)}</span><div className="followup-row-actions">{item.status !== "COMPLETED" && <button disabled={busy === item.id} onClick={() => void update(item.id, "COMPLETED")}><Check />{lang === "hy" ? "Ավարտել" : "Complete"}</button>}{item.status !== "CANCELLED" && item.status !== "COMPLETED" && <button disabled={busy === item.id} onClick={() => void update(item.id, "CANCELLED")}><X />{lang === "hy" ? "Չեղարկել" : "Cancel"}</button>}</div></article>; }) : <EmptyState icon={<CalendarClock />} text={productCopy(lang).clinic.noFollowups} />}</section>
    </div>
  );
}

function MessagesPage({ lang, patients, selectedPatientId, onSelectPatient, onPatientUpdated }: { lang: ProductLang; patients: Patient[]; selectedPatientId: string | null; onSelectPatient: (id: string) => void; onPatientUpdated: (patient: Patient) => void }) {
  const patient = patients.find((item) => item.id === selectedPatientId) ?? null;
  return <div className="clinic-messages-page"><section className="clinic-card message-context"><div><span className="product-kicker">TETA2</span><h1>{productCopy(lang).clinic.messages}</h1><p>{productCopy(lang).clinic.messagesLead}</p></div><label><span>{productCopy(lang).clinic.selectPatient}</span><select value={selectedPatientId ?? ""} onChange={(event) => onSelectPatient(event.target.value)}><option value="" disabled>{productCopy(lang).clinic.selectPatient}</option>{patients.map((item) => <option key={item.id} value={item.id}>{patientName(item)} · {item.patient_number}</option>)}</select></label></section>{patient ? <div className="v4-outreach-tool product-whatsapp-wrapper"><WhatsAppOutreachCard patient={patient} onPatientUpdated={onPatientUpdated} /></div> : <section className="clinic-card"><EmptyState icon={<MessageCircle />} text={productCopy(lang).clinic.noPatient} /></section>}</div>;
}

function SettingsPage({ lang, user, branches }: { lang: ProductLang; user: CurrentUser; branches: BranchSummary[] }) {
  return <div className="clinic-settings-grid"><section className="clinic-card"><CardHeading title={lang === "hy" ? "Հաշիվ" : "Account"} /><dl className="settings-dl"><div><dt>{lang === "hy" ? "Օգտանուն" : "Username"}</dt><dd>{user.username}</dd></div><div><dt>{lang === "hy" ? "Էլ․ փոստ" : "Email"}</dt><dd>{user.email}</dd></div><div><dt>{lang === "hy" ? "Դեր" : "Role"}</dt><dd>{user.role}</dd></div><div><dt>Clinic ID</dt><dd>{user.clinic_id}</dd></div></dl></section><section className="clinic-card"><CardHeading title={lang === "hy" ? "Մասնաճյուղերի հասանելիություն" : "Branch access"} /><div className="settings-branches">{branches.map((branch) => <article key={branch.id}><span><ShieldCheck /></span><div><strong>{branch.name}</strong><small>{branch.code ?? branch.id}</small></div></article>)}</div></section><section className="clinic-card settings-safety"><ShieldCheck /><div><h2>{lang === "hy" ? "Կլինիկական անվտանգության հիշեցում" : "Clinical safety reminder"}</h2><p>{productCopy(lang).safety.body}</p></div></section></div>;
}

function EmptyState({ icon, text }: { icon: React.ReactNode; text: string }) {
  return <div className="clinic-empty"><span>{icon}</span><p>{text}</p></div>;
}
