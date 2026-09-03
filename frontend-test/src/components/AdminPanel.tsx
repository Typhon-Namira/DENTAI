import { useMemo, useState } from "react";
import {
  Activity, BadgeDollarSign, Building2, Check, ChevronRight, CircleDollarSign,
  CreditCard, Filter, LayoutDashboard, LogOut, MoreHorizontal, Search, ShieldCheck,
  Users, WalletCards, X
} from "lucide-react";
import type { Lang } from "../i18n";
import { tr } from "../i18n";
import { Teta2Logo } from "./Teta2Logo";

type Plan = "Starter" | "Growth" | "Scale";
type SubscriptionState = "TRIAL" | "ACTIVE" | "SUSPENDED";
type PaymentState = "PENDING" | "PAID" | "OVERDUE" | "REJECTED";

export interface AdminClinic {
  id: string;
  name: string;
  owner: string;
  email: string;
  phone: string;
  city: string;
  country: string;
  plan: Plan;
  monthlyPrice: number;
  subscription: SubscriptionState;
  payment: PaymentState;
  branches: number;
  seats: number;
  registeredAt: string;
  nextBilling: string;
  slug: string;
}

const STORAGE_KEY = "teta2-admin-clinics-v1";
const APPLICATIONS_KEY = "teta2-clinic-applications-v1";

const seed: AdminClinic[] = [
  { id: "CL-1001", name: "Marstom Clinic", owner: "David Gevorgyan", email: "director@marstom.am", phone: "+374 91 440 221", city: "Yerevan", country: "Armenia", plan: "Growth", monthlyPrice: 249, subscription: "ACTIVE", payment: "PAID", branches: 2, seats: 14, registeredAt: "2026-07-12", nextBilling: "2026-09-12", slug: "marstom" },
  { id: "CL-1002", name: "Ardent Dental Center", owner: "Mariam Sargsyan", email: "mariam@ardent.am", phone: "+374 55 920 110", city: "Yerevan", country: "Armenia", plan: "Starter", monthlyPrice: 129, subscription: "TRIAL", payment: "PENDING", branches: 1, seats: 5, registeredAt: "2026-08-27", nextBilling: "2026-09-10", slug: "ardent" },
  { id: "CL-1003", name: "SmileCraft", owner: "Arman Petrosyan", email: "arman@smilecraft.am", phone: "+374 77 718 900", city: "Gyumri", country: "Armenia", plan: "Scale", monthlyPrice: 449, subscription: "ACTIVE", payment: "PAID", branches: 4, seats: 31, registeredAt: "2026-06-04", nextBilling: "2026-09-04", slug: "smilecraft" },
  { id: "CL-1004", name: "NovaDent", owner: "Lilit Hakobyan", email: "lilit@novadent.am", phone: "+374 43 120 980", city: "Yerevan", country: "Armenia", plan: "Growth", monthlyPrice: 249, subscription: "SUSPENDED", payment: "OVERDUE", branches: 2, seats: 11, registeredAt: "2026-05-20", nextBilling: "2026-08-20", slug: "novadent" }
];

function readClinics(): AdminClinic[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const base = stored ? JSON.parse(stored) as AdminClinic[] : seed;
    const rawApplications = localStorage.getItem(APPLICATIONS_KEY);
    const applications = rawApplications ? JSON.parse(rawApplications) as Array<Record<string, unknown>> : [];
    const applicationClinics = applications.map((app, index): AdminClinic => ({
      id: `APP-${String(index + 1).padStart(3, "0")}`,
      name: String(app.clinicName ?? "New clinic"),
      owner: String(app.directorName ?? "—"),
      email: String(app.email ?? "—"),
      phone: String(app.phone ?? "—"),
      city: String(app.city ?? "Yerevan"),
      country: String(app.country ?? "Armenia"),
      plan: (String(app.plan ?? "Starter") as Plan),
      monthlyPrice: String(app.plan ?? "Starter") === "Scale" ? 449 : String(app.plan ?? "Starter") === "Growth" ? 249 : 129,
      subscription: "TRIAL",
      payment: "PENDING",
      branches: Number(app.branches ?? 1),
      seats: 1,
      registeredAt: String(app.createdAt ?? new Date().toISOString()).slice(0, 10),
      nextBilling: new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10),
      slug: String(app.slug ?? "new-clinic")
    }));
    const ids = new Set(base.map((item) => item.slug));
    return [...base, ...applicationClinics.filter((item) => !ids.has(item.slug))];
  } catch { return seed; }
}

function persist(clinics: AdminClinic[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(clinics.filter((item) => !item.id.startsWith("APP-"))));
}

export function AdminPanel({ lang, setLang, onExit }: { lang: Lang; setLang: (lang: Lang) => void; onExit: () => void }) {
  const c = tr(lang);
  const [previewUnlocked, setPreviewUnlocked] = useState(false);
  const [clinics, setClinics] = useState<AdminClinic[]>(() => readClinics());
  const [query, setQuery] = useState("");
  const [subscriptionFilter, setSubscriptionFilter] = useState("ALL");
  const [selected, setSelected] = useState<AdminClinic | null>(null);
  const [section, setSection] = useState<"overview" | "clinics" | "payments" | "activity">("overview");

  const filtered = useMemo(() => clinics.filter((clinic) => {
    const matchQuery = `${clinic.name} ${clinic.owner} ${clinic.email} ${clinic.slug}`.toLowerCase().includes(query.toLowerCase());
    const matchState = subscriptionFilter === "ALL" || clinic.subscription === subscriptionFilter;
    return matchQuery && matchState;
  }), [clinics, query, subscriptionFilter]);

  const metrics = useMemo(() => ({
    total: clinics.length,
    active: clinics.filter((item) => item.subscription === "ACTIVE").length,
    pending: clinics.filter((item) => item.payment === "PENDING").length,
    mrr: clinics.filter((item) => item.subscription === "ACTIVE" && item.payment === "PAID").reduce((sum, item) => sum + item.monthlyPrice, 0)
  }), [clinics]);

  function patchClinic(id: string, patch: Partial<AdminClinic>) {
    setClinics((current) => {
      const next = current.map((clinic) => clinic.id === id ? { ...clinic, ...patch } : clinic);
      persist(next);
      const updated = next.find((clinic) => clinic.id === id) ?? null;
      setSelected(updated);
      return next;
    });
  }

  if (!previewUnlocked) {
    return <div className="admin-login-screen">
      <div className="admin-login-card">
        <Teta2Logo />
        <span className="admin-security-chip"><ShieldCheck size={15} /> {c.admin.frontendMode}</span>
        <h1>{c.admin.loginTitle}</h1>
        <p>{c.admin.loginCopy}</p>
        <label>Admin email<input type="email" defaultValue="admin@teta2.ai" /></label>
        <label>{c.auth.password}<input type="password" defaultValue="preview-only" /></label>
        <button className="t2-btn primary wide" type="button" onClick={() => setPreviewUnlocked(true)}>{c.admin.enterPreview}</button>
        <button className="text-button" type="button" onClick={onExit}>{c.auth.back}</button>
      </div>
    </div>;
  }

  return <div className="admin-shell">
    <aside className="admin-sidebar">
      <Teta2Logo />
      <div className="admin-side-label">PLATFORM CONTROL</div>
      <nav>
        <button className={section === "overview" ? "active" : ""} onClick={() => setSection("overview")}><LayoutDashboard size={18}/>{c.admin.overview}</button>
        <button className={section === "clinics" ? "active" : ""} onClick={() => setSection("clinics")}><Building2 size={18}/>{c.admin.clinics}<span>{clinics.length}</span></button>
        <button className={section === "payments" ? "active" : ""} onClick={() => setSection("payments")}><WalletCards size={18}/>{c.admin.payments}<span>{metrics.pending}</span></button>
        <button className={section === "activity" ? "active" : ""} onClick={() => setSection("activity")}><Activity size={18}/>{c.admin.activity}</button>
      </nav>
      <div className="admin-preview-note"><ShieldCheck size={17}/><div><strong>{c.admin.frontendMode}</strong><small>{c.admin.frontendModeCopy}</small></div></div>
      <button className="admin-exit" onClick={onExit}><LogOut size={17}/>{c.common.logout}</button>
    </aside>

    <main className="admin-main">
      <header className="admin-topbar"><div><h1>{c.admin.title}</h1><p>{c.admin.subtitle}</p></div><div className="admin-top-actions"><button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button><button className={lang === "hy" ? "active" : ""} onClick={() => setLang("hy")}>HY</button><span className="admin-avatar">TA</span></div></header>

      {section === "overview" && <>
        <section className="admin-metrics">
          <article><span className="metric-icon purple"><Building2 size={20}/></span><div><small>{c.admin.totalClinics}</small><strong>{metrics.total}</strong><em>+2 this month</em></div></article>
          <article><span className="metric-icon green"><BadgeDollarSign size={20}/></span><div><small>{c.admin.activeSubscriptions}</small><strong>{metrics.active}</strong><em>{Math.round(metrics.active / Math.max(metrics.total, 1) * 100)}% active</em></div></article>
          <article><span className="metric-icon amber"><CreditCard size={20}/></span><div><small>{c.admin.pendingPayments}</small><strong>{metrics.pending}</strong><em>requires review</em></div></article>
          <article><span className="metric-icon blue"><CircleDollarSign size={20}/></span><div><small>{c.admin.mrr}</small><strong>${metrics.mrr.toLocaleString()}</strong><em>current approved MRR</em></div></article>
        </section>
        <section className="admin-overview-grid">
          <div className="admin-card revenue-card"><div className="admin-card-heading"><div><h2>Subscription revenue</h2><p>Approved monthly recurring revenue by plan.</p></div><MoreHorizontal size={20}/></div><div className="revenue-chart"><div style={{height:"42%"}}><span>Starter</span></div><div style={{height:"68%"}}><span>Growth</span></div><div style={{height:"88%"}}><span>Scale</span></div></div><div className="chart-axis"><span>$0</span><span>$250</span><span>$500</span><span>$750</span></div></div>
          <div className="admin-card payment-queue"><div className="admin-card-heading"><div><h2>{c.admin.paymentQueue}</h2><p>{c.admin.paymentQueueCopy}</p></div></div>{clinics.filter((item) => item.payment === "PENDING").slice(0,4).map((clinic) => <div className="queue-row" key={clinic.id}><span className="clinic-monogram">{clinic.name.slice(0,2).toUpperCase()}</span><div><strong>{clinic.name}</strong><small>{clinic.plan} · ${clinic.monthlyPrice}/mo</small></div><button onClick={() => patchClinic(clinic.id,{payment:"PAID",subscription:"ACTIVE"})}><Check size={16}/>{c.admin.approve}</button></div>)}{metrics.pending === 0 && <div className="admin-empty">{c.common.noData}</div>}</div>
        </section>
      </>}

      {(section === "clinics" || section === "payments") && <section className="admin-card admin-table-card">
        <div className="admin-table-toolbar"><div className="search-box"><Search size={17}/><input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder={c.admin.searchClinics}/></div><div className="filter-box"><Filter size={16}/><select value={subscriptionFilter} onChange={(e)=>setSubscriptionFilter(e.target.value)}><option value="ALL">{c.common.all}</option><option value="ACTIVE">{c.common.active}</option><option value="TRIAL">{c.admin.trial}</option><option value="SUSPENDED">{c.admin.suspended}</option></select></div></div>
        <div className="admin-table-wrap"><table><thead><tr><th>{c.admin.clinic}</th><th>{c.admin.owner}</th><th>{c.admin.plan}</th><th>{c.admin.subscription}</th><th>{c.admin.payment}</th><th>{c.admin.renewal}</th><th></th></tr></thead><tbody>{filtered.filter((clinic)=>section !== "payments" || clinic.payment !== "PAID").map((clinic)=><tr key={clinic.id}><td><div className="clinic-cell"><span>{clinic.name.slice(0,2).toUpperCase()}</span><div><strong>{clinic.name}</strong><small>{clinic.slug} · {clinic.city}</small></div></div></td><td><strong>{clinic.owner}</strong><small>{clinic.email}</small></td><td><span className={`plan-pill ${clinic.plan.toLowerCase()}`}>{clinic.plan}</span><small>${clinic.monthlyPrice}/mo</small></td><td><span className={`state-pill ${clinic.subscription.toLowerCase()}`}>{clinic.subscription}</span></td><td><span className={`state-pill payment-${clinic.payment.toLowerCase()}`}>{clinic.payment}</span></td><td>{clinic.nextBilling}</td><td><button className="row-open" onClick={()=>setSelected(clinic)}><ChevronRight size={18}/></button></td></tr>)}</tbody></table></div>
      </section>}

      {section === "activity" && <section className="admin-card activity-card"><div className="admin-card-heading"><div><h2>{c.admin.activity}</h2><p>Operational actions in the frontend preview.</p></div></div>{["Payment approved for Marstom Clinic","Subscription activated for Ardent Dental Center","Scale plan assigned to SmileCraft","NovaDent suspended after overdue payment"].map((item,index)=><div className="activity-row" key={item}><span><Activity size={16}/></span><div><strong>{item}</strong><small>{index+1}h ago · platform-admin</small></div></div>)}</section>}
    </main>

    {selected && <div className="admin-drawer-backdrop" onMouseDown={() => setSelected(null)}><aside className="admin-drawer" onMouseDown={(e)=>e.stopPropagation()}><header><div><small>{selected.id}</small><h2>{selected.name}</h2><p>{selected.city}, {selected.country}</p></div><button onClick={()=>setSelected(null)}><X size={20}/></button></header><div className="drawer-section"><h3>Clinic account</h3><dl><div><dt>{c.admin.owner}</dt><dd>{selected.owner}</dd></div><div><dt>Email</dt><dd>{selected.email}</dd></div><div><dt>{c.admin.branches}</dt><dd>{selected.branches}</dd></div><div><dt>{c.admin.seats}</dt><dd>{selected.seats}</dd></div><div><dt>{c.admin.created}</dt><dd>{selected.registeredAt}</dd></div></dl></div><div className="drawer-section"><h3>{c.admin.subscription}</h3><label>{c.admin.changePlan}<select value={selected.plan} onChange={(e)=>{ const plan=e.target.value as Plan; patchClinic(selected.id,{plan,monthlyPrice:plan==="Scale"?449:plan==="Growth"?249:129}); }}><option>Starter</option><option>Growth</option><option>Scale</option></select></label><label>{c.admin.monthlyPrice}<input type="number" value={selected.monthlyPrice} onChange={(e)=>patchClinic(selected.id,{monthlyPrice:Number(e.target.value)})}/></label><div className="drawer-action-grid"><button className="t2-btn positive" onClick={()=>patchClinic(selected.id,{payment:"PAID",subscription:"ACTIVE"})}><Check size={16}/>{c.admin.approvePayment}</button><button className="t2-btn soft" onClick={()=>patchClinic(selected.id,{subscription:selected.subscription==="SUSPENDED"?"ACTIVE":"SUSPENDED"})}>{selected.subscription==="SUSPENDED"?c.admin.activate:c.admin.suspend}</button></div></div><div className="drawer-status-strip"><div><small>{c.admin.payment}</small><strong className={`payment-${selected.payment.toLowerCase()}`}>{selected.payment}</strong></div><div><small>{c.admin.subscription}</small><strong>{selected.subscription}</strong></div><div><small>{c.admin.renewal}</small><strong>{selected.nextBilling}</strong></div></div></aside></div>}
  </div>;
}
