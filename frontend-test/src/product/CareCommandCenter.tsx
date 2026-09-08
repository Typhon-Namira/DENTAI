import { CalendarClock, Check, ChevronLeft, ChevronRight, Clock3, MessageCircle, Plus, RefreshCw, Settings2, Sparkles, UserPlus, X } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, errorMessage, hasSession } from "../api/client";
import { productApi, type BranchSummary, type CareAppointment, type CareConversation, type CareMessage, type CarePlan, type CareSettings } from "../api/product";
import type { CurrentUser, Patient } from "../api/types";

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
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");
  const [lang, setLang] = useState<Lang>(() => langNow());
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
  const [weekOffset, setWeekOffset] = useState(0);
  const [view, setView] = useState<"day" | "week">("week");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = window.setInterval(() => {
      const signedIn = hasSession();
      setActive(signedIn);
      setLang(langNow());
      if (!signedIn) { setOpen(false); setUser(null); }
    }, 800);
    return () => window.clearInterval(timer);
  }, []);

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

  async function refresh() {
    if (!hasSession()) return;
    setBusy("refresh"); setError("");
    try {
      const me = await api.me();
      const [patientPage, branchRows, planRows, conversationRows, appointmentRows] = await Promise.all([
        api.listPatients(), productApi.branches(), productApi.carePlans(), productApi.careConversations(), productApi.careAppointments(range.start.toISOString(), range.end.toISOString())
      ]);
      setUser(me); setPatients(patientPage.items); setBranches(branchRows); setPlans(planRows); setConversations(conversationRows); setAppointments(appointmentRows);
      const branchId = selectedBranch || branchRows[0]?.id || "";
      setSelectedBranch(branchId);
      if (branchId) setSettings(await productApi.careSettings(branchId));
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(""); }
  }

  useEffect(() => { if (open && active) void refresh(); }, [open, active, range.start.getTime(), range.end.getTime()]);
  useEffect(() => {
    if (!selectedConversation) { setMessages([]); return; }
    void productApi.careConversationMessages(selectedConversation).then(setMessages).catch((reason) => setError(errorMessage(reason)));
  }, [selectedConversation]);
  useEffect(() => {
    if (!selectedBranch || !open) return;
    void productApi.careSettings(selectedBranch).then(setSettings).catch((reason) => setError(errorMessage(reason)));
  }, [selectedBranch]);

  if (!active) return null;
  const hy = lang === "hy";
  const confirmed = appointments.filter((x) => x.status === "CONFIRMED").length;
  const contacted = plans.flatMap((p) => p.items).filter((x) => ["CONTACTED", "BOOKED"].includes(x.status)).length;
  const needsReview = plans.filter((p) => p.status === "READY_FOR_REVIEW").length;

  return <>
    <button className="care-ai-launcher" onClick={() => setOpen(true)}><Sparkles/><span><b>Teta2 Care AI</b><small>{hy ? "Ավտոմատ հետագա վերահսկում" : "Autonomous follow-up"}</small></span>{needsReview > 0 && <i>{needsReview}</i>}</button>
    {open && <div className="care-cc-backdrop"><section className="care-cc-shell" role="dialog" aria-modal="true">
      <header className="care-cc-head"><div><span className="care-cc-mark"><Sparkles/></span><div><small>TETA2 CARE · AI ORCHESTRATION</small><h1>{hy ? "Հետագա վերահսկման կառավարման կենտրոն" : "Patient follow-up command center"}</h1><p>{hy ? "AI-ն պատրաստում է պլանը, հաղորդակցվում է և ամրագրում է ժամերը։ Բժիշկը վերահսկում է։" : "AI prepares the care plan, handles the conversation and books the check-up. The clinician stays in control."}</p></div></div><div><button className="care-icon" disabled={busy === "refresh"} onClick={() => void refresh()}><RefreshCw/></button><button className="care-icon" onClick={() => setOpen(false)}><X/></button></div></header>
      <nav className="care-cc-tabs">
        <button className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}><Sparkles/>{hy ? "AI հոսք" : "AI flow"}</button>
        <button className={tab === "appointments" ? "active" : ""} onClick={() => setTab("appointments")}><CalendarClock/>{hy ? "Ամրագրումներ" : "Appointments"}</button>
        <button className={tab === "messages" ? "active" : ""} onClick={() => setTab("messages")}><MessageCircle/>{hy ? "Զրույցներ" : "Messages"}</button>
        <button className={tab === "automation" ? "active" : ""} onClick={() => setTab("automation")}><Settings2/>{hy ? "AI կարգավորումներ" : "AI settings"}</button>
        <button className={tab === "patient" ? "active" : ""} onClick={() => setTab("patient")}><UserPlus/>{hy ? "Նոր պացիենտ" : "New patient"}</button>
      </nav>
      {error && <div className="care-error">{error}<button onClick={() => setError("")}><X/></button></div>}
      <main className="care-cc-body">
        {tab === "overview" && <Overview lang={lang} plans={plans} conversations={conversations} appointments={appointments} contacted={contacted} confirmed={confirmed} needsReview={needsReview}/>} 
        {tab === "appointments" && <Appointments lang={lang} appointments={appointments} view={view} setView={setView} range={range} offset={weekOffset} setOffset={setWeekOffset} onRefresh={refresh}/>} 
        {tab === "messages" && <Messages lang={lang} conversations={conversations} selected={selectedConversation} setSelected={setSelectedConversation} messages={messages}/>} 
        {tab === "automation" && <Automation lang={lang} branches={branches} branchId={selectedBranch} setBranchId={setSelectedBranch} settings={settings} setSettings={setSettings} onSaved={refresh}/>} 
        {tab === "patient" && <NewPatient lang={lang} branches={branches} onCreated={async () => { await refresh(); setTab("overview"); }}/>} 
      </main>
    </section></div>}
  </>;
}

function Overview({ lang, plans, conversations, appointments, contacted, confirmed, needsReview }: { lang: Lang; plans: CarePlan[]; conversations: CareConversation[]; appointments: CareAppointment[]; contacted: number; confirmed: number; needsReview: number }) {
  const hy = lang === "hy";
  return <div className="care-overview"><div className="care-metrics"><article><span><Sparkles/></span><strong>{plans.length}</strong><small>{hy ? "AI Care պլան" : "AI care plans"}</small></article><article><span><Check/></span><strong>{contacted}</strong><small>{hy ? "Կապ հաստատված" : "Patients contacted"}</small></article><article><span><MessageCircle/></span><strong>{conversations.length}</strong><small>{hy ? "Ակտիվ զրույց" : "Care conversations"}</small></article><article><span><CalendarClock/></span><strong>{confirmed}</strong><small>{hy ? "Հաստատված ժամ" : "Confirmed bookings"}</small></article></div>
    <section className="care-flow-card"><header><div><small>AUTONOMOUS CARE LOOP</small><h2>{hy ? "OPG-ից մինչև հաստատված չեքափ" : "From OPG to confirmed check-up"}</h2></div>{needsReview > 0 && <span className="care-review-badge">{needsReview} {hy ? "վերանայման" : "need review"}</span>}</header><div className="care-flow-line"><b>1</b><span>{hy ? "OPG վերլուծություն" : "OPG analyzed"}</span><ChevronRight/><b>2</b><span>{hy ? "Խնդրահարույց ատամներ" : "Possible findings"}</span><ChevronRight/><b>3</b><span>{hy ? "Բժշկի հաստատում" : "Clinician review"}</span><ChevronRight/><b>4</b><span>WhatsApp AI</span><ChevronRight/><b>5</b><span>{hy ? "Ժամի ընտրություն" : "Slot negotiation"}</span><ChevronRight/><b>6</b><span>{hy ? "Ամրագրում" : "Booked"}</span></div></section>
    <section className="care-plan-list"><header><h2>{hy ? "Վերջին AI Care պլանները" : "Latest AI care plans"}</h2></header>{plans.slice(0,8).map((plan) => <article key={plan.id}><div><span className={`care-state ${plan.status.toLowerCase()}`}>{plan.status.replaceAll("_"," ")}</span><strong>{plan.items.length} {hy ? "ատամ / հայտնաբերում" : "tooth finding(s)"}</strong><small>{plan.summary ?? "Teta2 Care"}</small></div><div className="care-teeth">{plan.items.slice(0,8).map((item) => <span key={item.id}><b>{item.tooth_fdi}</b>{item.finding_type.replaceAll("_"," ")}</span>)}</div></article>)}</section>
  </div>;
}

function Appointments({ lang, appointments, view, setView, range, offset, setOffset, onRefresh }: { lang: Lang; appointments: CareAppointment[]; view: "day"|"week"; setView:(v:"day"|"week")=>void; range:{start:Date;end:Date}; offset:number; setOffset:(n:number)=>void; onRefresh:()=>Promise<void> }) {
  const hy = lang === "hy"; const [editing,setEditing]=useState<CareAppointment|null>(null); const [when,setWhen]=useState(""); const [note,setNote]=useState(""); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  async function reschedule(e:FormEvent){e.preventDefault();if(!editing)return;setBusy(true);setError("");try{await productApi.requestCareReschedule(editing.id,when?new Date(when).toISOString():null,note);setEditing(null);await onRefresh()}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  return <div className="care-appts"><div className="care-calendar-bar"><div><button onClick={()=>setOffset(offset-1)}><ChevronLeft/></button><strong>{new Intl.DateTimeFormat(lang==="hy"?"hy-AM":"en-US",{month:"long",day:"numeric",year:"numeric"}).format(range.start)} — {new Intl.DateTimeFormat(lang==="hy"?"hy-AM":"en-US",{month:"short",day:"numeric"}).format(new Date(range.end.getTime()-1))}</strong><button onClick={()=>setOffset(offset+1)}><ChevronRight/></button></div><div className="care-view-toggle"><button className={view==="day"?"active":""} onClick={()=>{setView("day");setOffset(0)}}>{hy?"Օր":"Day"}</button><button className={view==="week"?"active":""} onClick={()=>{setView("week");setOffset(0)}}>{hy?"Շաբաթ":"Week"}</button></div></div>
    <section className="care-appt-list">{appointments.length?appointments.map((a)=><article key={a.id}><time><b>{new Date(a.starts_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</b><span>{new Intl.DateTimeFormat(lang==="hy"?"hy-AM":"en-US",{weekday:"short",month:"short",day:"numeric"}).format(new Date(a.starts_at))}</span></time><div><span className={`care-state ${a.status.toLowerCase()}`}>{a.status.replaceAll("_"," ")}</span><h3>{nameOf(a.patient)}</h3><p>{a.reason}</p><small>{a.tooth_fdi?`${hy?"Ատամ":"Tooth"} ${a.tooth_fdi} · `:""}{a.source} · {a.timezone}</small></div><button className="care-reschedule" onClick={()=>{setEditing(a);setWhen(localInputValue(new Date(a.starts_at)));setNote("")}}><Clock3/>{hy?"Փոխել ժամը":"Change time"}</button></article>):<div className="care-empty">{hy?"Այս ժամանակահատվածում ամրագրումներ չկան։":"No appointments in this period."}</div>}</section>
    {editing&&<div className="care-modal-bg"><form className="care-modal" onSubmit={reschedule}><button type="button" className="care-close" onClick={()=>setEditing(null)}><X/></button><small>TETA2 CARE · RESCHEDULE</small><h2>{hy?"AI-ին հանձնարարել ժամի փոփոխություն":"Ask AI to renegotiate the appointment"}</h2><p>{nameOf(editing.patient)} · {editing.reason}</p><label>{hy?"Բժշկի նախընտրած նոր ժամը":"Doctor-preferred new time"}<input type="datetime-local" value={when} onChange={e=>setWhen(e.target.value)}/></label><label>{hy?"Նշում AI-ի համար":"Instruction for AI"}<textarea value={note} onChange={e=>setNote(e.target.value)} placeholder={hy?"Օր. եթե այս ժամը հարմար չէ, առաջարկիր հաջորդ երեքշաբթի կեսօրից հետո":"e.g. If unavailable, offer next Tuesday afternoon"}/></label>{error&&<div className="care-error">{error}</div>}<button className="care-primary" disabled={busy}>{busy?"…":hy?"Սկսել նոր WhatsApp զրույց":"Start rescheduling conversation"}</button></form></div>}
  </div>;
}

function Messages({ lang, conversations, selected, setSelected, messages }: { lang: Lang; conversations: CareConversation[]; selected:string|null; setSelected:(id:string)=>void; messages:CareMessage[] }) {
  const hy=lang==="hy"; const active=conversations.find(x=>x.id===selected)??conversations[0]; useEffect(()=>{if(!selected&&conversations[0])setSelected(conversations[0].id)},[conversations.length]);
  return <div className="care-message-layout"><aside><header><h2>{hy?"Պացիենտների զրույցներ":"Patient conversations"}</h2><span>{conversations.length}</span></header>{conversations.map(c=><button key={c.id} className={active?.id===c.id?"active":""} onClick={()=>setSelected(c.id)}><span>{nameOf(c.patient).split(" ").map(x=>x[0]).join("").slice(0,2)}</span><div><strong>{nameOf(c.patient)}</strong><small>{c.summary??c.whatsapp_phone}</small></div><i className={`care-state ${c.latest_appointment?.status?.toLowerCase()??"active"}`}>{c.latest_appointment?.status??c.status}</i></button>)}</aside><section className="care-transcript">{active?<><header><div><strong>{nameOf(active.patient)}</strong><small>{active.whatsapp_phone} · {active.language.toUpperCase()}</small></div>{active.latest_appointment&&<span><CalendarClock/>{fmt(active.latest_appointment.starts_at,lang)} · {active.latest_appointment.status}</span>}</header><div className="care-bubbles">{messages.map(m=><article key={m.id} className={m.direction==="OUT"?"out":"in"}><p>{m.body}</p><small>{fmt(m.created_at,lang)} · {m.status}</small></article>)}</div></>:<div className="care-empty">{hy?"Զրույց դեռ չկա։":"No Care conversation yet."}</div>}</section></div>;
}

function Automation({ lang, branches, branchId, setBranchId, settings, setSettings, onSaved }: { lang:Lang; branches:BranchSummary[]; branchId:string; setBranchId:(id:string)=>void; settings:CareSettings|null; setSettings:(s:CareSettings)=>void; onSaved:()=>Promise<void> }) {
  const hy=lang==="hy"; const [busy,setBusy]=useState(false); const [error,setError]=useState(""); if(!settings)return <div className="care-empty">{hy?"Ընտրեք մասնաճյուղ։":"Select a branch."}</div>;
  const patch=(key:keyof CareSettings,value:unknown)=>setSettings({...settings,[key]:value});
  async function save(){setBusy(true);setError("");try{const {id:_id,branch_id:_branch,...body}=settings;setSettings(await productApi.updateCareSettings(branchId,body));await onSaved()}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  return <div className="care-settings"><section className="care-settings-hero"><div><small>CLINIC MEMORY · BOOKING POLICY</small><h2>{hy?"AI-ի ժամային և հաղորդակցության կանոնները":"Clinic schedule & AI booking memory"}</h2><p>{hy?"Այս տվյալները օգտագործվում են ամեն WhatsApp զրույցում՝ ազատ ժամերը ճիշտ առաջարկելու համար։":"These rules become persistent context for every Care conversation and appointment offer."}</p></div><label>{hy?"Մասնաճյուղ":"Branch"}<select value={branchId} onChange={e=>setBranchId(e.target.value)}>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label></section><div className="care-settings-grid"><label>{hy?"Ժամային գոտի":"Timezone"}<input value={settings.timezone} onChange={e=>patch("timezone",e.target.value)}/></label><label>{hy?"Աշխատանքի սկիզբ":"Clinic opens"}<input type="time" value={settings.day_start} onChange={e=>patch("day_start",e.target.value)}/></label><label>{hy?"Աշխատանքի ավարտ":"Clinic closes"}<input type="time" value={settings.day_end} onChange={e=>patch("day_end",e.target.value)}/></label><label>{hy?"Չեքափի տևողություն":"Check-up duration"}<input type="number" min="10" max="240" value={settings.appointment_minutes} onChange={e=>patch("appointment_minutes",Number(e.target.value))}/><small>min</small></label><label>{hy?"Սլոտերի միջակայք":"Slot interval"}<input type="number" min="5" max="240" value={settings.slot_interval_minutes} onChange={e=>patch("slot_interval_minutes",Number(e.target.value))}/><small>min</small></label><label>{hy?"Նվազագույն նախազգուշացում":"Minimum notice"}<input type="number" min="0" value={settings.min_booking_notice_minutes} onChange={e=>patch("min_booking_notice_minutes",Number(e.target.value))}/><small>min</small></label><label>{hy?"Ամրագրման հորիզոն":"Booking horizon"}<input type="number" min="1" max="365" value={settings.booking_horizon_days} onChange={e=>patch("booking_horizon_days",Number(e.target.value))}/><small>days</small></label></div><div className="care-weekdays"><span>{hy?"Աշխատանքային օրեր":"Working days"}</span>{["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((d,i)=><button key={d} className={settings.working_days.includes(i)?"active":""} onClick={()=>patch("working_days",settings.working_days.includes(i)?settings.working_days.filter(x=>x!==i):[...settings.working_days,i].sort())}>{d}</button>)}</div><label className="care-instructions">{hy?"AI-ի ամրագրման հատուկ կանոններ":"Booking instructions for the AI"}<textarea value={settings.booking_instructions??""} onChange={e=>patch("booking_instructions",e.target.value)} placeholder={hy?"Օր. չորեքշաբթի առավոտները նախընտրելի են, շտապ դեպքերը՝ օրվա վերջում":"e.g. Prefer Wednesday mornings; urgent check-ups may use the final slot of the day"}/></label><div className="care-toggle-grid"><label><input type="checkbox" checked={settings.auto_followup_enabled} onChange={e=>patch("auto_followup_enabled",e.target.checked)}/><span><b>{hy?"Ավտոմատ Care պլան":"Automatic Care plan"}</b><small>{hy?"Վերլուծությունից հետո ստեղծել պլան":"Prepare after OPG analysis"}</small></span></label><label><input type="checkbox" checked={settings.auto_outreach_after_review} onChange={e=>patch("auto_outreach_after_review",e.target.checked)}/><span><b>{hy?"Ավտոմատ WhatsApp":"Automatic WhatsApp after review"}</b><small>{hy?"Միայն բժշկի հաստատած հայտնաբերումների համար":"Only for clinician-confirmed findings"}</small></span></label><label><input type="checkbox" checked={settings.attach_tooth_image} onChange={e=>patch("attach_tooth_image",e.target.checked)}/><span><b>{hy?"Կցել ատամի պատկերը":"Attach tooth crop"}</b><small>{hy?"Ոչ ամբողջ OPG-ն":"Never the full OPG by default"}</small></span></label></div>{error&&<div className="care-error">{error}</div>}<button className="care-primary save" onClick={()=>void save()} disabled={busy}>{busy?"…":hy?"Պահպանել AI կանոնները":"Save AI automation rules"}</button></div>;
}

function NewPatient({ lang, branches, onCreated }: { lang:Lang; branches:BranchSummary[]; onCreated:()=>Promise<void> }) {
  const hy=lang==="hy"; const [number,setNumber]=useState("");const[first,setFirst]=useState("");const[last,setLast]=useState("");const[branch,setBranch]=useState(branches[0]?.id??"");const[busy,setBusy]=useState(false);const[error,setError]=useState("");
  useEffect(()=>{if(!branch&&branches[0])setBranch(branches[0].id)},[branches.length]); async function submit(e:FormEvent){e.preventDefault();setBusy(true);setError("");try{await productApi.createPatient({patient_number:number.trim(),first_name:first.trim(),last_name:last.trim(),branch_id:branch});setNumber("");setFirst("");setLast("");await onCreated()}catch(r){setError(errorMessage(r))}finally{setBusy(false)}}
  return <form className="care-new-patient" onSubmit={submit}><div className="care-new-patient-copy"><span><UserPlus/></span><small>START THE CARE LOOP</small><h2>{hy?"Ստեղծեք պացիենտ, հետո պարզապես վերբեռնեք OPG-ն":"Create the patient, then upload the OPG"}</h2><p>{hy?"AI-ն վերլուծությունից հետո ինքնուրույն պատրաստում է Care պլանը։ Բժիշկը հաստատում է կլինիկական հայտնաբերումները, իսկ Care-ը շարունակում է follow-up-ը։":"After analysis, AI prepares the Care plan automatically. The clinician confirms the clinical findings, then Care handles follow-up, WhatsApp negotiation and booking."}</p></div><div className="care-new-fields"><label>{hy?"Պացիենտի համար":"Patient number"}<input required value={number} onChange={e=>setNumber(e.target.value)} placeholder="P-0001"/></label><div><label>{hy?"Անուն":"First name"}<input required value={first} onChange={e=>setFirst(e.target.value)}/></label><label>{hy?"Ազգանուն":"Last name"}<input required value={last} onChange={e=>setLast(e.target.value)}/></label></div><label>{hy?"Մասնաճյուղ":"Branch"}<select required value={branch} onChange={e=>setBranch(e.target.value)}>{branches.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}</select></label>{error&&<div className="care-error">{error}</div>}<button className="care-primary" disabled={busy||!branch}><Plus/>{busy?"…":hy?"Ստեղծել և սկսել":"Create patient"}</button></div></form>;
}
