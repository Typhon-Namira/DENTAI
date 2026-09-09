import {
  Activity, BrainCircuit, CalendarClock, Check, ChevronLeft, ChevronRight, Clock3, FileImage,
  HeartPulse, MessageCircle, Plus, RefreshCw, Settings2, ShieldCheck, Sparkles, UploadCloud,
  UserPlus, WandSparkles, X
} from "lucide-react";
import { createPortal } from "react-dom";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { api, errorMessage, hasSession } from "../api/client";
import {
  productApi, type BranchSummary, type CareAppointment, type CareConversation, type CareMessage,
  type CarePlan, type CareSettings, type PatientCreateInput
} from "../api/product";
import type { AIAnalysis, CurrentUser, Patient, PatientProfile } from "../api/types";

type Tab = "overview" | "appointments" | "messages" | "automation" | "patient";
type Lang = "en" | "hy";

function langNow(): Lang {
  const value = localStorage.getItem("teta2-product-language") ?? localStorage.getItem("teta2-v4-language");
  return value === "hy" ? "hy" : "en";
}
function nameOf(p?: Patient | null) { return p ? `${p.first_name} ${p.last_name}`.trim() : "—"; }
function fmt(value: string, lang: Lang) { return new Intl.DateTimeFormat(lang === "hy" ? "hy-AM" : "en-US", { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value)); }
function localInputValue(value: Date) { const d = new Date(value.getTime() - value.getTimezoneOffset() * 60000); return d.toISOString().slice(0, 16); }

export function CareCommandCenter() {
  const [active, setActive] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");
  const [lang, setLang] = useState<Lang>(() => langNow());
  const [navTarget, setNavTarget] = useState<HTMLElement | null>(null);
  const [mainTarget, setMainTarget] = useState<HTMLElement | null>(null);
  const [shellTarget, setShellTarget] = useState<HTMLElement | null>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [branches, setBranches] = useState<BranchSummary[]>([]);
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [appointments, setAppointments] = useState<CareAppointment[]>([]);
  const [conversations, setConversations] = useState<CareConversation[]>([]);
  const [messages, setMessages] = useState<CareMessage[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [settings, setSettings] = useState<CareSettings | null>(null);
  const [selectedBranch, setSelectedBranch] = useState("");
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [weekOffset, setWeekOffset] = useState(0);
  const [view, setView] = useState<"day" | "week">("week");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const syncTargets = () => {
      setNavTarget(document.querySelector(".clinic-sidebar nav") as HTMLElement | null);
      setMainTarget(document.querySelector(".clinic-main") as HTMLElement | null);
      setShellTarget(document.querySelector(".clinic-shell") as HTMLElement | null);
      setLang(langNow());
    };
    syncTargets();
    const observer = new MutationObserver(syncTargets);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!shellTarget) return;
    shellTarget.classList.toggle("care-integrated-active", active);
    return () => shellTarget.classList.remove("care-integrated-active");
  }, [active, shellTarget]);

  useEffect(() => {
    if (!navTarget) return;
    const buttons = Array.from(navTarget.querySelectorAll("button:not(.care-nav-button)"));
    const leaveCare = () => setActive(false);
    buttons.forEach((button) => button.addEventListener("click", leaveCare));
    return () => buttons.forEach((button) => button.removeEventListener("click", leaveCare));
  }, [navTarget]);

  const range = useMemo(() => {
    const now = new Date();
    const base = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (view === "day") {
      base.setDate(base.getDate() + weekOffset);
      const end = new Date(base); end.setDate(end.getDate() + 1);
      return { start: base, end };
    }
    const mondayDelta = (base.getDay() + 6) % 7;
    base.setDate(base.getDate() - mondayDelta + weekOffset * 7);
    const end = new Date(base); end.setDate(end.getDate() + 7);
    return { start: base, end };
  }, [weekOffset, view]);

  const refresh = useCallback(async () => {
    if (!hasSession()) return;
    setBusy("refresh"); setError("");
    try {
      const me = await api.me();
      const [patientPage, branchRows, planRows, conversationRows, appointmentRows] = await Promise.all([
        api.listPatients(), productApi.branches(), productApi.carePlans(), productApi.careConversations(),
        productApi.careAppointments(range.start.toISOString(), range.end.toISOString())
      ]);
      setUser(me); setPatients(patientPage.items); setBranches(branchRows); setPlans(planRows);
      setConversations(conversationRows); setAppointments(appointmentRows);
      setSelectedPatientId((current) => current || patientPage.items[0]?.id || "");
      const branchId = selectedBranch || branchRows[0]?.id || "";
      setSelectedBranch(branchId);
      if (branchId) setSettings(await productApi.careSettings(branchId));
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(""); }
  }, [range.start.getTime(), range.end.getTime(), selectedBranch]);

  useEffect(() => { if (active) void refresh(); }, [active, range.start.getTime(), range.end.getTime()]);
  useEffect(() => {
    if (!selectedConversation) { setMessages([]); return; }
    void productApi.careConversationMessages(selectedConversation).then(setMessages).catch((reason) => setError(errorMessage(reason)));
  }, [selectedConversation]);
  useEffect(() => {
    if (!selectedBranch || !active) return;
    void productApi.careSettings(selectedBranch).then(setSettings).catch((reason) => setError(errorMessage(reason)));
  }, [selectedBranch, active]);

  function enter(next: Tab) { setTab(next); setActive(true); }
  function openProductOpg(patientId?: string) {
    if (patientId) setSelectedPatientId(patientId);
    setActive(false);
    requestAnimationFrame(() => {
      const productButtons = Array.from(document.querySelectorAll(".clinic-sidebar nav > button:not(.care-nav-button)")) as HTMLButtonElement[];
      productButtons[2]?.click();
      if (patientId) {
        const select = document.querySelector(".clinic-patient-select select") as HTMLSelectElement | null;
        if (select) { select.value = patientId; select.dispatchEvent(new Event("change", { bubbles: true })); }
      }
    });
  }

  if (!navTarget || !mainTarget || !shellTarget || !hasSession()) return null;
  const hy = lang === "hy";
  const confirmed = appointments.filter((x) => x.status === "CONFIRMED").length;
  const contacted = plans.flatMap((p) => p.items).filter((x) => ["CONTACTED", "BOOKED"].includes(x.status)).length;
  const needsReview = plans.filter((p) => p.status === "READY_FOR_REVIEW").length;

  const nav = createPortal(
    <div className="care-nav-cluster" aria-label="Teta2 Care AI">
      <div className="care-nav-label"><span className="care-nav-orb"><Sparkles /></span><b>Teta2 Care AI</b><i>{hy ? "ԻՆՔՆԱՎԱՐ" : "AUTONOMOUS"}</i></div>
      <button className={`care-nav-button ${active && tab === "overview" ? "active" : ""}`} onClick={() => enter("overview")}><BrainCircuit /><span>{hy ? "AI հոսք" : "AI Care"}</span>{needsReview > 0 && <i>{needsReview}</i>}</button>
      <button className={`care-nav-button ${active && tab === "appointments" ? "active" : ""}`} onClick={() => enter("appointments")}><CalendarClock /><span>{hy ? "Ամրագրումներ" : "Appointments"}</span></button>
      <button className={`care-nav-button ${active && tab === "messages" ? "active" : ""}`} onClick={() => enter("messages")}><MessageCircle /><span>{hy ? "AI զրույցներ" : "AI Messages"}</span></button>
      <button className={`care-nav-button ${active && tab === "automation" ? "active" : ""}`} onClick={() => enter("automation")}><Settings2 /><span>{hy ? "AI կանոններ" : "AI Settings"}</span></button>
    </div>, navTarget
  );

  const workspace = active ? createPortal(
    <section className="care-integrated-workspace">
      <header className="care-integrated-head">
        <div className="care-ai-identity"><AIOrb /><div><small>TETA2 CARE · CLINICAL ORCHESTRATION</small><h1>{tab === "overview" ? (hy ? "AI խնամքի հոսք" : "AI care workflow") : tab === "appointments" ? (hy ? "Չեքափի ամրագրումներ" : "Check-up appointments") : tab === "messages" ? (hy ? "Պացիենտների AI զրույցներ" : "Patient AI conversations") : (hy ? "AI կանոններ և հիշողություն" : "AI schedule & memory")}</h1><p>{hy ? "Բժիշկը վերահսկում է կլինիկական որոշումները։ Teta2 Care-ը կազմակերպում է մնացած հոսքը։" : "You control clinical decisions. Teta2 Care coordinates the workflow, outreach, conversation and booking."}</p></div></div>
        <div className="care-head-actions"><span className="care-live"><i />AI LIVE</span><button className="care-icon" disabled={busy === "refresh"} onClick={() => void refresh()}><RefreshCw /></button></div>
      </header>
      <nav className="care-top-tabs">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}><Sparkles />{hy ? "AI հոսք" : "AI flow"}</button>
        <button className={tab === "appointments" ? "active" : ""} onClick={() => setTab("appointments")}><CalendarClock />{hy ? "Ամրագրումներ" : "Appointments"}</button>
        <button className={tab === "messages" ? "active" : ""} onClick={() => setTab("messages")}><MessageCircle />{hy ? "Զրույցներ" : "Messages"}</button>
        <button className={tab === "automation" ? "active" : ""} onClick={() => setTab("automation")}><Settings2 />{hy ? "Կարգավորումներ" : "AI settings"}</button>
        <button className={tab === "patient" ? "active" : ""} onClick={() => setTab("patient")}><UserPlus />{hy ? "Նոր պացիենտ" : "New patient"}</button>
      </nav>
      {error && <div className="care-error">{error}<button onClick={() => setError("")}><X /></button></div>}
      <main className="care-integrated-body">
        {tab === "overview" && <Overview lang={lang} user={user} patients={patients} selectedPatientId={selectedPatientId} setSelectedPatientId={setSelectedPatientId} plans={plans} conversations={conversations} appointments={appointments} contacted={contacted} confirmed={confirmed} needsReview={needsReview} onRefresh={refresh} onNewPatient={() => setTab("patient")} onOpenOpg={openProductOpg} />}
        {tab === "appointments" && <Appointments lang={lang} appointments={appointments} view={view} setView={setView} range={range} offset={weekOffset} setOffset={setWeekOffset} onRefresh={refresh} />}
        {tab === "messages" && <Messages lang={lang} conversations={conversations} selected={selectedConversation} setSelected={setSelectedConversation} messages={messages} />}
        {tab === "automation" && <Automation lang={lang} branches={branches} branchId={selectedBranch} setBranchId={setSelectedBranch} settings={settings} setSettings={setSettings} onSaved={refresh} />}
        {tab === "patient" && <NewPatient lang={lang} branches={branches} onCreated={async (patient) => { setSelectedPatientId(patient.id); await refresh(); setTab("overview"); }} />}
      </main>
    </section>, mainTarget
  ) : null;

  return <>{nav}{workspace}</>;
}

function AIOrb() {
  return <div className="care-ai-orb" aria-hidden="true"><span className="r1" /><span className="r2" /><span className="r3" /><i className="n1" /><i className="n2" /><i className="n3" /><BrainCircuit /></div>;
}

function Overview({ lang, user, patients, selectedPatientId, setSelectedPatientId, plans, conversations, appointments, contacted, confirmed, needsReview, onRefresh, onNewPatient, onOpenOpg }: {
  lang: Lang; user: CurrentUser | null; patients: Patient[]; selectedPatientId: string; setSelectedPatientId:(id:string)=>void;
  plans: CarePlan[]; conversations: CareConversation[]; appointments: CareAppointment[]; contacted:number; confirmed:number; needsReview:number;
  onRefresh:()=>Promise<void>; onNewPatient:()=>void; onOpenOpg:(patientId?:string)=>void;
}) {
  const hy = lang === "hy";
  const patient = patients.find((x) => x.id === selectedPatientId) ?? null;
  const patientPlans = patient ? plans.filter((p) => p.patient_id === patient.id) : [];
  return <div className="care-overview">
    <section className="care-start-card">
      <div className="care-start-copy"><span className="care-kicker"><Activity /> LIVE CLINICAL LOOP</span><h2>{hy ? "Պարզապես ստեղծեք պացիենտը և վերբեռնեք OPG-ն։" : "Create the patient. Upload the OPG. Teta2 Care takes it from there."}</h2><p>{hy ? "Վերլուծությունից հետո AI-ն պատրաստում է ատամ առ ատամ care plan-ը։ Բժիշկը հաստատում է հայտնաբերումները, այնուհետև WhatsApp follow-up-ը, ժամերի բանակցությունն ու ամրագրումը շարունակվում են ավտոմատ։" : "After analysis, AI builds a tooth-level care plan. You confirm the clinical findings; then follow-up, WhatsApp conversation, slot negotiation and booking continue automatically."}</p><div className="care-safety-line"><ShieldCheck />{hy ? "Պացիենտին կլինիկական հաղորդագրություն չի ուղարկվում մինչև բժշկի հաստատումը։" : "Clinical outreach stays behind the clinician-review gate."}</div></div>
      <div className="care-start-actions"><label>{hy ? "Ակտիվ պացիենտ" : "Active patient"}<select value={selectedPatientId} onChange={(e) => setSelectedPatientId(e.target.value)}><option value="">{hy ? "Ընտրեք" : "Select patient"}</option>{patients.map((p) => <option key={p.id} value={p.id}>{nameOf(p)} · {p.patient_number}</option>)}</select></label><button className="care-primary" onClick={() => onOpenOpg(selectedPatientId || undefined)} disabled={!selectedPatientId}><UploadCloud />{hy ? "Վերբեռնել OPG և վերլուծել" : "Upload OPG & analyze"}</button><button className="care-secondary" onClick={onNewPatient}><Plus />{hy ? "Նոր պացիենտ" : "Create patient"}</button></div>
    </section>
    <div className="care-metrics"><article><span><BrainCircuit /></span><strong>{plans.length}</strong><small>{hy ? "AI care պլան" : "AI care plans"}</small></article><article><span><Check /></span><strong>{contacted}</strong><small>{hy ? "Կապ հաստատված" : "Findings contacted"}</small></article><article><span><MessageCircle /></span><strong>{conversations.length}</strong><small>{hy ? "AI զրույց" : "AI conversations"}</small></article><article><span><CalendarClock /></span><strong>{confirmed}</strong><small>{hy ? "Հաստատված ժամ" : "Confirmed bookings"}</small></article></div>
    <section className="care-flow-card"><header><div><small>AUTONOMOUS CARE LOOP</small><h2>{hy ? "OPG-ից մինչև հաստատված չեքափ" : "From OPG to confirmed check-up"}</h2></div>{needsReview > 0 && <span className="care-review-badge">{needsReview} {hy ? "վերանայման" : "need review"}</span>}</header><div className="care-flow-line"><b>1</b><span>OPG</span><ChevronRight/><b>2</b><span>{hy ? "AI վերլուծություն" : "AI analysis"}</span><ChevronRight/><b>3</b><span>{hy ? "Բժշկի հաստատում" : "Clinician review"}</span><ChevronRight/><b>4</b><span>WhatsApp AI</span><ChevronRight/><b>5</b><span>{hy ? "Ժամի բանակցում" : "Slot negotiation"}</span><ChevronRight/><b>6</b><span>{hy ? "Ամրագրում" : "Booking"}</span></div></section>
    {patient && <section className="care-patient-status"><header><div><span>{patient.first_name[0]}{patient.last_name[0]}</span><div><small>{hy ? "ԱԿՏԻՎ ԲԺՇԿԱԿԱՆ ՔԱՐՏ" : "ACTIVE CLINICAL RECORD"}</small><h2>{nameOf(patient)}</h2><p>{patient.patient_number} · {patient.whatsapp_phone || patient.phone || (hy ? "WhatsApp չկա" : "No WhatsApp number")}</p></div></div><button className="care-secondary" onClick={() => onOpenOpg(patient.id)}><FileImage />{hy ? "Բացել OPG workspace" : "Open OPG workspace"}</button></header><div className="care-patient-plan-strip"><div><small>{hy ? "AI CARE ՊԼԱՆՆԵՐ" : "AI CARE PLANS"}</small><strong>{patientPlans.length}</strong></div><div><small>{hy ? "ՎԵՐՋԻՆ ԿԱՐԳԱՎԻՃԱԿ" : "LATEST STATE"}</small><strong>{patientPlans[0]?.status?.replaceAll("_", " ") ?? (hy ? "Սպասում է OPG-ի" : "Awaiting OPG")}</strong></div><div><small>{hy ? "ՀԱՋՈՐԴ ՔԱՅԼ" : "NEXT ACTION"}</small><strong>{patientPlans[0]?.status === "READY_FOR_REVIEW" ? (hy ? "Բժշկի հաստատում" : "Clinician review") : patientPlans[0] ? (hy ? "AI վերահսկում" : "AI monitoring") : (hy ? "Վերբեռնել OPG" : "Upload OPG")}</strong></div></div></section>}
    <section className="care-plan-list"><header><h2>{hy ? "Վերջին AI Care պլանները" : "Latest AI care plans"}</h2><button className="care-icon light" onClick={() => void onRefresh()}><RefreshCw /></button></header>{plans.slice(0,8).map((plan) => <article key={plan.id}><div><span className={`care-state ${plan.status.toLowerCase()}`}>{plan.status.replaceAll("_"," ")}</span><strong>{plan.items.length} {hy ? "ատամ / հայտնաբերում" : "tooth finding(s)"}</strong><small>{plan.summary ?? "Teta2 Care"}</small></div><div className="care-teeth">{plan.items.slice(0,8).map((item) => <span key={item.id}><b>{item.tooth_fdi}</b>{item.finding_type.replaceAll("_"," ")}</span>)}</div>{plan.status === "READY_FOR_REVIEW" && user?.role === "DOCTOR" && <button className="care-review-action" onClick={() => onOpenOpg(plan.patient_id)}><WandSparkles />{hy ? "Վերանայել" : "Review findings"}</button>}</article>)}</section>
  </div>;
}

function Appointments({ lang, appointments, view, setView, range, offset, setOffset, onRefresh }: { lang: Lang; appointments: CareAppointment[]; view: "day"|"week"; setView:(v:"day"|"week")=>void; range:{start:Date;end:Date}; offset:number; setOffset:(n:number)=>void; onRefresh:()=>Promise<void> }) {
  const hy = lang === "hy"; const [editing,setEditing]=useState<CareAppointment|null>(null); const [when,setWhen]=useState(""); const [note,setNote]=useState(""); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  async function reschedule(e:FormEvent){e.preventDefault();if(!editing)return;setBusy(true);setError("");try{await productApi.requestCareReschedule(editing.id,when?new Date(when).toISOString():null,note);setEditing(null);await onRefresh()}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  return <div className="care-appts"><div className="care-calendar-bar"><div><button onClick={()=>setOffset(offset-1)}><ChevronLeft/></button><strong>{new Intl.DateTimeFormat(lang==="hy"?"hy-AM":"en-US",{month:"long",day:"numeric",year:"numeric"}).format(range.start)} — {new Intl.DateTimeFormat(lang==="hy"?"hy-AM":"en-US",{month:"short",day:"numeric"}).format(new Date(range.end.getTime()-1))}</strong><button onClick={()=>setOffset(offset+1)}><ChevronRight/></button></div><div className="care-view-toggle"><button className={view==="day"?"active":""} onClick={()=>{setView("day");setOffset(0)}}>{hy?"Օր":"Day"}</button><button className={view==="week"?"active":""} onClick={()=>{setView("week");setOffset(0)}}>{hy?"Շաբաթ":"Week"}</button></div></div>
    <section className="care-appt-list">{appointments.length?appointments.map((a)=><article key={a.id}><time><b>{new Date(a.starts_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</b><span>{new Intl.DateTimeFormat(lang==="hy"?"hy-AM":"en-US",{weekday:"short",month:"short",day:"numeric"}).format(new Date(a.starts_at))}</span></time><div><span className={`care-state ${a.status.toLowerCase()}`}>{a.status.replaceAll("_"," ")}</span><h3>{nameOf(a.patient)}</h3><p>{a.reason}</p><small>{a.tooth_fdi?`${hy?"Ատամ":"Tooth"} ${a.tooth_fdi} · `:""}{a.source} · {a.timezone}</small></div><button className="care-reschedule" onClick={()=>{setEditing(a);setWhen(localInputValue(new Date(a.starts_at)));setNote("")}}><Clock3/>{hy?"Փոխել ժամը":"Change time"}</button></article>):<div className="care-empty">{hy?"Այս ժամանակահատվածում ամրագրումներ չկան։":"No appointments in this period."}</div>}</section>
    {editing&&<div className="care-modal-bg"><form className="care-modal" onSubmit={reschedule}><button type="button" className="care-close" onClick={()=>setEditing(null)}><X/></button><small>TETA2 CARE · RESCHEDULE</small><h2>{hy?"AI-ին հանձնարարել ժամի փոփոխություն":"Ask AI to renegotiate the appointment"}</h2><p>{nameOf(editing.patient)} · {editing.reason}</p><label>{hy?"Բժշկի նախընտրած նոր ժամը":"Doctor-preferred new time"}<input type="datetime-local" value={when} onChange={e=>setWhen(e.target.value)}/></label><label>{hy?"Նշում AI-ի համար":"Instruction for AI"}<textarea value={note} onChange={e=>setNote(e.target.value)} placeholder={hy?"Եթե այս ժամը հարմար չէ, առաջարկիր հաջորդ երեքշաբթի կեսօրից հետո":"If unavailable, offer next Tuesday afternoon"}/></label>{error&&<div className="care-error">{error}</div>}<button className="care-primary" disabled={busy}>{busy?"…":hy?"Սկսել WhatsApp զրույց":"Start rescheduling conversation"}</button></form></div>}
  </div>;
}

function Messages({ lang, conversations, selected, setSelected, messages }: { lang: Lang; conversations: CareConversation[]; selected:string|null; setSelected:(id:string)=>void; messages:CareMessage[] }) {
  const hy=lang==="hy"; const active=conversations.find(x=>x.id===selected)??conversations[0];
  useEffect(()=>{if(!selected&&conversations[0])setSelected(conversations[0].id)},[conversations.length,selected]);
  return <div className="care-message-layout"><aside><header><h2>{hy?"Պացիենտների զրույցներ":"Patient conversations"}</h2><span>{conversations.length}</span></header>{conversations.map(c=><button key={c.id} className={active?.id===c.id?"active":""} onClick={()=>setSelected(c.id)}><span>{nameOf(c.patient).split(" ").map(x=>x[0]).join("").slice(0,2)}</span><div><strong>{nameOf(c.patient)}</strong><small>{c.summary??c.whatsapp_phone}</small></div><i className={`care-state ${c.latest_appointment?.status?.toLowerCase()??"active"}`}>{c.latest_appointment?.status??c.status}</i></button>)}</aside><section className="care-transcript">{active?<><header><div><strong>{nameOf(active.patient)}</strong><small>{active.whatsapp_phone} · {active.language.toUpperCase()}</small></div>{active.latest_appointment&&<span><CalendarClock/>{fmt(active.latest_appointment.starts_at,lang)} · {active.latest_appointment.status}</span>}</header><div className="care-bubbles">{messages.map(m=><article key={m.id} className={m.direction==="OUT"?"out":"in"}><p>{m.body}</p><small>{fmt(m.created_at,lang)} · {m.status}</small></article>)}</div></>:<div className="care-empty">{hy?"Զրույց դեռ չկա։":"No Care conversation yet."}</div>}</section></div>;
}

function Automation({ lang, branches, branchId, setBranchId, settings, setSettings, onSaved }: { lang:Lang; branches:BranchSummary[]; branchId:string; setBranchId:(id:string)=>void; settings:CareSettings|null; setSettings:(s:CareSettings)=>void; onSaved:()=>Promise<void> }) {
  const hy=lang==="hy"; const [busy,setBusy]=useState(false); const [error,setError]=useState(""); if(!settings)return <div className="care-empty">{hy?"Ընտրեք մասնաճյուղ։":"Select a branch."}</div>;
  const patch=(key:keyof CareSettings,value:unknown)=>setSettings({...settings,[key]:value});
  async function save(){setBusy(true);setError("");try{const {id:_id,branch_id:_branch,...body}=settings;setSettings(await productApi.updateCareSettings(branchId,body));await onSaved()}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  return <div className="care-settings"><section className="care-settings-hero"><div><small>CLINIC MEMORY · BOOKING POLICY</small><h2>{hy?"AI-ի ժամային և հաղորդակցության կանոնները":"Clinic schedule & AI booking memory"}</h2><p>{hy?"Այս տվյալները պահպանվում և օգտագործվում են ամեն WhatsApp զրույցում։":"These rules are persistent context for every Care conversation and appointment offer."}</p></div><label>{hy?"Մասնաճյուղ":"Branch"}<select value={branchId} onChange={e=>setBranchId(e.target.value)}>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label></section><div className="care-settings-grid"><label>{hy?"Ժամային գոտի":"Timezone"}<input value={settings.timezone} onChange={e=>patch("timezone",e.target.value)}/></label><label>{hy?"Աշխատանքի սկիզբ":"Clinic opens"}<input type="time" value={settings.day_start} onChange={e=>patch("day_start",e.target.value)}/></label><label>{hy?"Աշխատանքի ավարտ":"Clinic closes"}<input type="time" value={settings.day_end} onChange={e=>patch("day_end",e.target.value)}/></label><label>{hy?"Չեքափի տևողություն":"Check-up duration"}<input type="number" min="10" max="240" value={settings.appointment_minutes} onChange={e=>patch("appointment_minutes",Number(e.target.value))}/><small>min</small></label><label>{hy?"Սլոտերի միջակայք":"Slot interval"}<input type="number" min="5" max="240" value={settings.slot_interval_minutes} onChange={e=>patch("slot_interval_minutes",Number(e.target.value))}/><small>min</small></label><label>{hy?"Բուֆեր":"Appointment buffer"}<input type="number" min="0" max="120" value={settings.buffer_minutes} onChange={e=>patch("buffer_minutes",Number(e.target.value))}/><small>min</small></label><label>{hy?"Նվազագույն նախազգուշացում":"Minimum notice"}<input type="number" min="0" value={settings.min_booking_notice_minutes} onChange={e=>patch("min_booking_notice_minutes",Number(e.target.value))}/><small>min</small></label><label>{hy?"Ամրագրման հորիզոն":"Booking horizon"}<input type="number" min="1" max="365" value={settings.booking_horizon_days} onChange={e=>patch("booking_horizon_days",Number(e.target.value))}/><small>days</small></label></div><div className="care-weekdays"><span>{hy?"Աշխատանքային օրեր":"Working days"}</span>{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((d,i)=><button key={d} className={settings.working_days.includes(i)?"active":""} onClick={()=>patch("working_days",settings.working_days.includes(i)?settings.working_days.filter(x=>x!==i):[...settings.working_days,i].sort())}>{d}</button>)}</div><label className="care-instructions">{hy?"AI-ի ամրագրման հատուկ կանոններ":"Booking instructions for the AI"}<textarea value={settings.booking_instructions??""} onChange={e=>patch("booking_instructions",e.target.value)} placeholder={hy?"Օր. չորեքշաբթի առավոտները նախընտրելի են":"e.g. Prefer Wednesday mornings; urgent check-ups may use the final slot"}/></label><div className="care-toggle-grid"><label><input type="checkbox" checked={settings.auto_followup_enabled} onChange={e=>patch("auto_followup_enabled",e.target.checked)}/><span><b>{hy?"Ավտոմատ Care պլան":"Automatic Care plan"}</b><small>{hy?"Վերլուծությունից հետո ստեղծել պլան":"Prepare after OPG analysis"}</small></span></label><label><input type="checkbox" checked={settings.auto_outreach_after_review} onChange={e=>patch("auto_outreach_after_review",e.target.checked)}/><span><b>{hy?"Ավտոմատ WhatsApp":"Automatic WhatsApp after review"}</b><small>{hy?"Միայն բժշկի հաստատած հայտնաբերումների համար":"Only clinician-confirmed findings"}</small></span></label><label><input type="checkbox" checked={settings.attach_tooth_image} onChange={e=>patch("attach_tooth_image",e.target.checked)}/><span><b>{hy?"Կցել ատամի պատկերը":"Attach tooth crop"}</b><small>{hy?"Խնդրահարույց ատամի պատկերը":"Send the relevant tooth image"}</small></span></label></div>{error&&<div className="care-error">{error}</div>}<button className="care-primary save" onClick={()=>void save()} disabled={busy}>{busy?"…":hy?"Պահպանել AI կանոնները":"Save AI automation rules"}</button></div>;
}

function NewPatient({ lang, branches, onCreated }: { lang:Lang; branches:BranchSummary[]; onCreated:(patient:Patient)=>Promise<void> }) {
  const hy=lang==="hy"; const [form,setForm]=useState<PatientCreateInput>({patient_number:"",first_name:"",last_name:"",branch_id:branches[0]?.id??"",date_of_birth:null,sex:null,phone:null,whatsapp_phone:null,email:null}); const[busy,setBusy]=useState(false);const[error,setError]=useState("");
  useEffect(()=>{if(!form.branch_id&&branches[0])setForm(v=>({...v,branch_id:branches[0].id}))},[branches.length]);
  const patch=(key:keyof PatientCreateInput,value:string|null)=>setForm(v=>({...v,[key]:value}));
  async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError("");try{const body={...form,patient_number:form.patient_number.trim(),first_name:form.first_name.trim(),last_name:form.last_name.trim(),phone:form.phone?.trim()||null,whatsapp_phone:form.whatsapp_phone?.trim()||null,email:form.email?.trim()||null};const patient=await productApi.createPatient(body);await onCreated(patient)}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  return <form className="care-new-patient medical-intake" onSubmit={submit}><div className="care-new-patient-copy"><span><HeartPulse/></span><small>NEW CLINICAL RECORD · START CARE LOOP</small><h2>{hy?"Ստեղծեք իրական բժշկական քարտը":"Create the patient’s clinical record"}</h2><p>{hy?"WhatsApp համարը մուտքագրեք միջազգային ձևաչափով։ Այն նաև օգնում է Teta2 Care-ին ընտրել հիվանդի հաղորդակցության լեզուն։":"Use international format for the WhatsApp number. Teta2 Care also uses it to choose the patient’s communication language."}</p><div className="care-record-note"><ShieldCheck/><span>{hy?"Տվյալները պահվում են տվյալ կլինիկայի patient record-ում։":"This becomes the patient’s clinic-scoped medical record and Care context."}</span></div></div><div className="care-new-fields"><div><label>{hy?"Պացիենտի համար":"Patient number"}<input required value={form.patient_number} onChange={e=>patch("patient_number",e.target.value)} placeholder="P-0001"/></label><label>{hy?"Ծննդյան ամսաթիվ":"Date of birth"}<input type="date" value={form.date_of_birth??""} onChange={e=>patch("date_of_birth",e.target.value||null)}/></label></div><div><label>{hy?"Անուն":"First name"}<input required value={form.first_name} onChange={e=>patch("first_name",e.target.value)}/></label><label>{hy?"Ազգանուն":"Last name"}<input required value={form.last_name} onChange={e=>patch("last_name",e.target.value)}/></label></div><div><label>{hy?"Սեռ":"Sex"}<select value={form.sex??""} onChange={e=>patch("sex",e.target.value||null)}><option value="">—</option><option value="FEMALE">Female</option><option value="MALE">Male</option><option value="OTHER">Other / unspecified</option></select></label><label>{hy?"Մասնաճյուղ":"Branch"}<select required value={form.branch_id} onChange={e=>patch("branch_id",e.target.value)}>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label></div><label>WhatsApp <small>International E.164 · +374… / +7… / +98…</small><input value={form.whatsapp_phone??""} onChange={e=>patch("whatsapp_phone",e.target.value||null)} placeholder="+374XXXXXXXX"/></label><div><label>{hy?"Հեռախոս":"Phone"}<input value={form.phone??""} onChange={e=>patch("phone",e.target.value||null)} placeholder="+374XXXXXXXX"/></label><label>Email<input type="email" value={form.email??""} onChange={e=>patch("email",e.target.value||null)}/></label></div>{error&&<div className="care-error">{error}</div>}<button className="care-primary" disabled={busy||!form.branch_id}><Plus/>{busy?"…":hy?"Ստեղծել բժշկական քարտ":"Create clinical record"}</button></div></form>;
}
