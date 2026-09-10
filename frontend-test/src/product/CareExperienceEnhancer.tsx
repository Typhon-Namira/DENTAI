import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  Activity, CalendarCheck, Check, ChevronRight, Clock3, HeartPulse, MessageCircle,
  Save, Search, ShieldCheck, Sparkles, WandSparkles, X
} from "lucide-react";
import { api, errorMessage } from "../api/client";
import {
  productApi, type CareAppointment, type CareConversation, type CareMessage,
  type CarePlan, type CarePlanItem
} from "../api/product";
import type { AIAnalysis, PatientProfile, WhatsAppConnection } from "../api/types";
import { WHATSAPP_QR_POLL_MS } from "../utils/whatsapp";

type View = "none" | "analysis" | "plans" | "messages" | "appointments";
type PlanDraft = Pick<CarePlanItem, "target_followup_at" | "recommended_window" | "rationale" | "message_preview">;

const NON_PATHOLOGY = new Set(["FILLING", "CROWN", "ROOT_CANAL_TREATMENT", "IMPLANT", "BRIDGE"]);

function fmt(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}
function title(value: string): string { return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (x) => x.toUpperCase()); }
function patientName(patient: {first_name:string;last_name:string}): string { return `${patient.first_name} ${patient.last_name}`.trim(); }
function currentView(): View {
  if (document.querySelector(".ai-page")) return "analysis";
  if (document.querySelector(".plan-list")) return "plans";
  if (document.querySelector(".chat-workspace")) return "messages";
  if (document.querySelector(".appointment-board")) return "appointments";
  return "none";
}
function selectedPatientFromShell(): string {
  return (document.querySelector(".care-quick-patient select") as HTMLSelectElement | null)?.value ?? "";
}
function ensureHost(view: View): HTMLElement | null {
  const id = `care-enhancer-${view}`;
  const existing = document.getElementById(id);
  if (existing) return existing;
  const selector = view === "analysis" ? ".ai-results-shell" : view === "plans" ? ".plan-list" : view === "messages" ? ".chat-workspace" : view === "appointments" ? ".appointment-board" : "";
  if (!selector) return null;
  const anchor = document.querySelector(selector);
  if (!anchor?.parentElement) return null;
  const host = document.createElement("div");
  host.id = id;
  host.className = `care-enhancer-host ${view}`;
  if (view === "analysis") anchor.parentElement.insertBefore(host, anchor.nextSibling);
  else anchor.parentElement.insertBefore(host, anchor);
  return host;
}

export function CareExperienceEnhancer() {
  const [view, setView] = useState<View>("none");
  const [patientId, setPatientId] = useState("");
  const [host, setHost] = useState<HTMLElement | null>(null);
  useEffect(() => {
    const sync = () => { const next = currentView(); setView(next); setPatientId(selectedPatientFromShell()); setHost(ensureHost(next)); };
    sync();
    const observer = new MutationObserver(sync); observer.observe(document.body, { childList:true, subtree:true, attributes:true, attributeFilter:["class"] });
    const timer = window.setInterval(sync, 1000);
    return () => { observer.disconnect(); window.clearInterval(timer); };
  }, []);
  if (!host || view === "none") return null;
  if (view === "analysis") return createPortal(<GeneratePlanPanel patientId={patientId} />, host);
  if (view === "plans") return createPortal(<ClinicFollowupWorkspace />, host);
  if (view === "messages") return createPortal(<LiveConversationPanel patientId={patientId} />, host);
  return createPortal(<AppointmentContextPanel patientId={patientId} />, host);
}

function GeneratePlanPanel({ patientId }: { patientId: string }) {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [done, setDone] = useState("");
  const load = useCallback(async () => {
    if (!patientId) { setProfile(null); setPlans([]); return; }
    const [p, rows] = await Promise.all([api.patientProfile(patientId), productApi.carePlans(patientId)]); setProfile(p); setPlans(rows);
  }, [patientId]);
  useEffect(() => { void load().catch((reason)=>setError(errorMessage(reason))); }, [load]);
  const analysis = useMemo<AIAnalysis | null>(() => profile ? [...profile.ai_analyses].filter((x)=>x.status==="COMPLETED").sort((a,b)=>b.requested_at.localeCompare(a.requested_at))[0] ?? null : null, [profile]);
  const problems = useMemo(() => analysis ? (profile?.findings ?? []).filter((f) => f.analysis_id === analysis.id && f.tooth_code && !NON_PATHOLOGY.has(f.finding_type.toUpperCase()) && (f.confidence ?? 0) >= .60 && f.review_status !== "REJECTED") : [], [analysis, profile]);
  const reviewed = problems.filter((f)=>f.review_status === "CONFIRMED").length;
  const plan = analysis ? plans.find((p)=>p.analysis_id===analysis.id) : undefined;
  const generated = !!plan && ["PENDING_APPROVAL","ACTIVE","PAUSED","COMPLETED"].includes(plan.status);
  const ready = analysis?.status === "COMPLETED" && problems.length > 0;
  async function generate() {
    if (!analysis) return; setBusy(true); setError(""); setDone("");
    try { const next = await productApi.generateCarePlan(analysis.id); setPlans((rows)=>[next,...rows.filter((p)=>p.id!==next.id)]); setDone(`Generated a sequential plan for ${next.items.length} pathological tooth finding${next.items.length===1?"":"s"}.`); }
    catch(reason){setError(errorMessage(reason));} finally{setBusy(false);}
  }
  function openPlans(){ const buttons=Array.from(document.querySelectorAll(".care-sidebar nav button")) as HTMLButtonElement[]; buttons.find((b)=>["Follow-up plans","Հետագա պլաններ"].includes(b.getAttribute("aria-label")??""))?.click(); }
  if (!patientId || !analysis) return null;
  return <section className="care-flow-banner care-card bottom-placement">
    <div className="flow-orb"><WandSparkles/></div>
    <div className="flow-copy"><span>AI FOLLOW-UP ORCHESTRATION</span><h2>{generated?"Follow-up plan ready":"Generate follow-up plan"}</h2>
      <p>{problems.length ? `${problems.length} pathological/red tooth finding${problems.length===1?"":"s"} can enter the plan. Review is recommended, not required. ${reviewed}/${problems.length} currently clinician-confirmed.` : "No eligible pathological/red tooth findings are available in this completed OPG analysis."}</p>
      <div className="flow-teeth">{problems.slice(0,12).map((f)=><span key={f.id}>Tooth {f.tooth_code} · {title(f.finding_type)}{f.review_status==="CONFIRMED"?" · reviewed":""}</span>)}</div>
      {problems.some((f)=>f.review_status==="PENDING")&&<div className="review-advice"><ShieldCheck/>Recommended: review AI findings before approving outreach, but generation is available now.</div>}
      {done&&<div className="flow-success"><Check/>{done}</div>}{error&&<div className="care-inline-error">{error}</div>}
    </div>
    <div className="flow-actions">{generated?<button className="care-primary" onClick={openPlans}>Open follow-up plans <ChevronRight/></button>:<button className="care-primary" disabled={!ready||busy} onClick={()=>void generate()}><Sparkles/>{busy?"Generating…":"Generate with AI"}</button>}<small><ShieldCheck/>Doctor remains in control</small></div>
  </section>;
}

function ClinicFollowupWorkspace() {
  const [plans,setPlans]=useState<CarePlan[]>([]); const [query,setQuery]=useState(""); const [busy,setBusy]=useState(""); const [error,setError]=useState(""); const [notice,setNotice]=useState("");
  const [drafts,setDrafts]=useState<Record<string,PlanDraft>>({});
  const load=useCallback(async()=>{const rows=await productApi.sequentialCarePlans();setPlans(rows);const next:Record<string,PlanDraft>={};rows.forEach((p)=>p.items.forEach((i)=>{next[i.id]={target_followup_at:i.target_followup_at,recommended_window:i.recommended_window,rationale:i.rationale,message_preview:i.message_preview};}));setDrafts(next);},[]);
  useEffect(()=>{void load().catch((r)=>setError(errorMessage(r)));},[load]);
  const visible=plans.filter((p)=>{const patient=p.patient;const hay=`${patient?patientName(patient):""} ${patient?.patient_number??""} ${patient?.whatsapp_phone??""} ${p.summary??""}`.toLowerCase();return hay.includes(query.toLowerCase());});
  function patch(id:string,key:keyof PlanDraft,value:string|null){setDrafts((d)=>({...d,[id]:{...d[id],[key]:value}}));}
  async function save(planId:string,item:CarePlanItem){const draft=drafts[item.id];if(!draft)return;setBusy(item.id);setError("");try{await productApi.updateCarePlanItem(planId,item.id,draft);setNotice(`Saved tooth ${item.tooth_fdi}.`);await load();}catch(r){setError(errorMessage(r));}finally{setBusy("");}}
  async function approve(planId:string){setBusy(planId);setError("");try{await productApi.approveSequentialCarePlan(planId);setNotice("Sequential outreach activated. Only the first priority tooth is scheduled; later teeth remain blocked until the previous outcome is recorded.");await load();}catch(r){setError(errorMessage(r));}finally{setBusy("");}}
  return <div className="care-followup-enhanced clinic-scale"><ClinicWhatsAppBridge/>
    <section className="care-card followup-command-card"><header className="followup-command-head"><div><span><Sparkles/>CLINIC FOLLOW-UP QUEUE</span><h2>Patient follow-up plans</h2><p>One clinic WhatsApp connection serves all patients. Each patient keeps their own stored WhatsApp number and sequential tooth plan.</p></div><div className="followup-command-stats"><b>{visible.length}</b><small>patient plans</small></div></header>
      <div className="followup-toolbar"><label><Search/><input value={query} onChange={(e)=>setQuery(e.target.value)} placeholder="Search patient, ID or WhatsApp"/></label><span>Showing up to 200 recent plans</span></div>
      {notice&&<div className="flow-success"><Check/>{notice}</div>}{error&&<div className="care-inline-error">{error}</div>}
      <div className="followup-editor-list">{visible.length?visible.map((plan)=><PatientPlan key={plan.id} plan={plan} drafts={drafts} busy={busy} onPatch={patch} onSave={save} onApprove={approve}/>):<div className="care-empty"><HeartPulse/><p>No matching follow-up plans.</p></div>}</div>
    </section>
  </div>;
}

function PatientPlan({plan,drafts,busy,onPatch,onSave,onApprove}:{plan:CarePlan;drafts:Record<string,PlanDraft>;busy:string;onPatch:(id:string,key:keyof PlanDraft,value:string|null)=>void;onSave:(planId:string,item:CarePlanItem)=>Promise<void>;onApprove:(planId:string)=>Promise<void>}){
  const p=plan.patient; return <article className="followup-plan-editor patient-plan"><div className="patient-plan-head"><div className="patient-identity"><span>{p?`${p.first_name[0]??""}${p.last_name[0]??""}`:"PT"}</span><div><h3>{p?patientName(p):plan.patient_id}</h3><small>{p?.patient_number??"Patient"} · WhatsApp: <b>{p?.whatsapp_phone??"Not registered"}</b></small><p>{plan.summary}</p></div></div><div className="plan-actions-enhanced"><span className={`clinical-pill ${plan.status.toLowerCase()}`}>{title(plan.status)}</span>{plan.status==="PENDING_APPROVAL"&&<button className="care-primary" disabled={!!busy} onClick={()=>void onApprove(plan.id)}><Check/>{busy===plan.id?"Activating…":"Approve sequential outreach"}</button>}</div></div>
    <div className="sequence-line">{[...plan.items].sort((a,b)=>(a.sequence_order??999)-(b.sequence_order??999)).map((item,index)=>{const d=drafts[item.id]??{target_followup_at:item.target_followup_at,recommended_window:item.recommended_window,rationale:item.rationale,message_preview:item.message_preview};const editable=plan.status==="PENDING_APPROVAL";return <section className={`followup-tooth-card sequence-card ${index===0?"first":""}`} key={item.id}><header><span className="sequence-index">#{item.sequence_order??index+1}</span><span className="tooth-number">{item.tooth_fdi}</span><div><strong>{title(item.finding_type)}</strong><small>{item.priority_level??"Priority"} · {item.confidence==null?"AI finding":`${Math.round(item.confidence*100)}% confidence`}</small></div><i className={`clinical-pill ${item.status.toLowerCase()}`}>{title(item.status)}</i></header>
      <div className="sequence-status"><span><Clock3/>Conversation start: <b>{item.conversation_start_at?fmt(item.conversation_start_at):"After previous tooth outcome"}</b></span>{item.outcome&&<span><Check/>Outcome: <b>{title(item.outcome)}</b></span>}</div>
      <div className="followup-fields"><label>Clinical follow-up target<input type="datetime-local" disabled={!editable} value={new Date(d.target_followup_at).toISOString().slice(0,16)} onChange={(e)=>onPatch(item.id,"target_followup_at",new Date(e.target.value).toISOString())}/></label><label>Recommended window<input disabled={!editable} value={d.recommended_window} onChange={(e)=>onPatch(item.id,"recommended_window",e.target.value)}/></label><label className="wide">Rationale<textarea disabled={!editable} rows={2} value={d.rationale} onChange={(e)=>onPatch(item.id,"rationale",e.target.value)}/></label><label className="wide">WhatsApp opening message<textarea disabled={!editable} rows={3} value={d.message_preview??""} onChange={(e)=>onPatch(item.id,"message_preview",e.target.value||null)}/></label></div>{editable&&<button className="care-secondary followup-save" disabled={busy===item.id} onClick={()=>void onSave(plan.id,item)}><Save/>{busy===item.id?"Saving…":"Save tooth plan"}</button>}
    </section>;})}</div></article>;
}

function ClinicWhatsAppBridge(){
  const [connection,setConnection]=useState<WhatsAppConnection>({connected:false,connection:"unknown",sender:null});const [qrOpen,setQrOpen]=useState(false);const [qr,setQr]=useState<string|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  const refresh=useCallback(async()=>{const next=await api.whatsappStatus();setConnection(next);if(next.connected){setQrOpen(false);setQr(null);}return next;},[]);
  useEffect(()=>{void refresh().catch((r)=>setError(errorMessage(r)));},[refresh]);
  useEffect(()=>{if(!qrOpen||connection.connected)return;let stopped=false;let timer=0;const poll=async()=>{try{const next=await api.whatsappQr();if(stopped)return;setConnection(next);setQr(next.qr??null);if(next.connected){setQrOpen(false);setQr(null);return;}}catch(r){if(!stopped)setError(errorMessage(r));}if(!stopped)timer=window.setTimeout(()=>void poll(),WHATSAPP_QR_POLL_MS);};void poll();return()=>{stopped=true;window.clearTimeout(timer);};},[qrOpen,connection.connected]);
  async function disconnect(){setBusy(true);setError("");try{await api.whatsappLogout();setConnection({connected:false,connection:"logged_out",sender:null});}catch(r){setError(errorMessage(r));}finally{setBusy(false);}}
  return <section className="care-card whatsapp-bridge clinic-only"><div className="whatsapp-mark"><MessageCircle/></div><div className="whatsapp-bridge-copy"><span>CLINIC WHATSAPP</span><strong>{connection.connected?"Clinic WhatsApp connected":"Connect clinic WhatsApp"}</strong><small>{connection.connected?`Sender: ${connection.sender??"linked device"}. This single clinic account is used for authorized patient follow-up.`:"One clinic-level connection. Patient phone numbers remain inside each patient record and plan."}</small>{error&&<em>{error}</em>}</div><div className="whatsapp-bridge-actions"><span className={connection.connected?"connected":""}><i/>{connection.connected?"Connected":"Disconnected"}</span>{connection.connected?<button className="care-secondary" disabled={busy} onClick={()=>void disconnect()}>Disconnect</button>:<button className="care-primary whatsapp-connect" onClick={()=>setQrOpen(true)}>Connect with QR</button>}</div>{qrOpen&&<div className="care-qr-backdrop" role="dialog" aria-modal="true"><div className="care-qr-modal"><button className="care-qr-close" aria-label="Close" onClick={()=>setQrOpen(false)}><X/></button><div className="whatsapp-mark large"><MessageCircle/></div><span>WHATSAPP LINKED DEVICE</span><h2>Scan with the clinic phone</h2>{qr?<img src={qr} alt="WhatsApp QR code"/>:<div className="care-qr-loading"><Activity/>Generating secure QR…</div>}<p>WhatsApp → Linked devices → Link a device → scan this code.</p></div></div>}</section>;
}

function LiveConversationPanel({patientId}:{patientId:string}){
  const [conversations,setConversations]=useState<CareConversation[]>([]);const [selected,setSelected]=useState("");const [messages,setMessages]=useState<CareMessage[]>([]);const [error,setError]=useState("");
  const load=useCallback(async()=>{const all=await productApi.careConversations();const rows=all.filter((r)=>!patientId||r.patient_id===patientId);setConversations(rows);const id=selected&&rows.some((r)=>r.id===selected)?selected:rows[0]?.id??"";if(id!==selected)setSelected(id);setMessages(id?await productApi.careConversationMessages(id):[]);},[patientId,selected]);
  useEffect(()=>{void load().catch((r)=>setError(errorMessage(r)));const t=window.setInterval(()=>void load().catch(()=>undefined),5000);return()=>window.clearInterval(t);},[load]);const conversation=conversations.find((x)=>x.id===selected);const appointment=conversation?.latest_appointment;
  return <section className="care-card enhanced-conversation"><header><div><span><MessageCircle/>LIVE AI CONVERSATION</span><h2>{conversation?.patient?patientName(conversation.patient):"Patient conversation"}</h2><p>{conversation?.summary??"Every WhatsApp message is mirrored here."}</p></div><div className="conversation-live"><i/>Live sync · 5s</div></header>{error&&<div className="care-inline-error">{error}</div>}{appointment&&<div className={`conversation-appointment ${appointment.status==="PROPOSED"?"pending":""}`}><CalendarCheck/><div><span>{appointment.status==="PROPOSED"?"APPOINTMENT AWAITING DOCTOR APPROVAL":"CONVERSATION APPOINTMENT"}</span><strong>{fmt(appointment.starts_at)}</strong><small>{appointment.reason}{appointment.tooth_fdi?` · Tooth ${appointment.tooth_fdi}`:""}{appointment.visit_outcome?` · ${title(appointment.visit_outcome)}`:""}</small></div><b>{title(appointment.status)}</b></div>}<div className="enhanced-thread">{messages.length?messages.map((m)=><article key={m.id} className={m.direction==="OUT"?"ai":"patient"}><div><span>{m.direction==="OUT"?<><Sparkles/>Teta2 Care AI</>:"Patient"}</span><time>{fmt(m.created_at)}</time></div><p>{m.body}</p><small>{title(m.status)}</small></article>):<div className="care-empty"><MessageCircle/><p>No messages for this patient yet.</p></div>}</div></section>;
}

function AppointmentContextPanel({patientId}:{patientId:string}){
  const [rows,setRows]=useState<CareAppointment[]>([]);const [busy,setBusy]=useState("");const [error,setError]=useState("");
  const load=useCallback(async()=>{const start=new Date();start.setDate(start.getDate()-60);const end=new Date();end.setDate(end.getDate()+180);const data=await productApi.careAppointments(start.toISOString(),end.toISOString());setRows(data.filter((r)=>!patientId||r.patient_id===patientId));},[patientId]);useEffect(()=>{void load().catch((r)=>setError(errorMessage(r)));},[load]);
  async function outcome(id:string,value:"TREATED"|"ATTENDED_NOT_TREATED"|"NO_SHOW"){const note=window.prompt("Optional clinical note")??undefined;setBusy(id);setError("");try{await productApi.recordAppointmentOutcome(id,value,note);await load();}catch(r){setError(errorMessage(r));}finally{setBusy("");}}
  return <section className="care-card appointment-context"><header><div><span><CalendarCheck/>VISIT OUTCOME → AI FOLLOW-UP</span><h2>Appointment outcomes</h2><p>Record what actually happened. Teta2 Care uses the outcome to continue the current tooth or unlock the next priority tooth.</p></div><Clock3/></header>{error&&<div className="care-inline-error">{error}</div>}<div className="appointment-context-grid">{rows.slice(0,12).map((a)=><article key={a.id}><div className="appointment-date"><b>{new Date(a.starts_at).getDate()}</b><span>{new Intl.DateTimeFormat("en-US",{month:"short"}).format(new Date(a.starts_at))}</span></div><div><span>{a.visit_outcome?title(a.visit_outcome):title(a.status)}</span><strong>{a.patient?patientName(a.patient):a.reason}</strong><p>{fmt(a.starts_at)}</p><small>{a.reason}{a.tooth_fdi?` · Tooth ${a.tooth_fdi}`:""}</small>{a.visit_outcome?<div className="outcome-recorded"><Check/>Outcome recorded {fmt(a.outcome_recorded_at)}</div>:["APPROVED","PROPOSED","RESCHEDULE_REQUESTED"].includes(a.status)&&<div className="outcome-actions"><button disabled={busy===a.id} onClick={()=>void outcome(a.id,"TREATED")}>Came · treated</button><button disabled={busy===a.id} onClick={()=>void outcome(a.id,"ATTENDED_NOT_TREATED")}>Came · not treated</button><button disabled={busy===a.id} onClick={()=>void outcome(a.id,"NO_SHOW")}>No-show</button></div>}</div></article>)}</div></section>;
}
