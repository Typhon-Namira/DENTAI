import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { CalendarCheck, Check, Clock3, MessageCircle, Sparkles } from "lucide-react";

import { errorMessage } from "../api/client";
import { productApi, type CareAppointment, type CareConversation, type CareMessage } from "../api/product";
import { dashboardLocale, dashboardStatus, type DashboardLang } from "./dashboardI18n";
import { useDashboardLanguage } from "./useDashboardLanguage";

type View = "none" | "messages" | "appointments";

const COPY = {
  en: {
    liveConversation:"LIVE AI CONVERSATION", patientConversation:"Patient conversation", mirrored:"Every WhatsApp message is mirrored here.", liveSync:"Live sync · 5s", waitingApproval:"APPOINTMENT AWAITING DOCTOR APPROVAL", conversationAppointment:"CONVERSATION APPOINTMENT", patient:"Patient", noMessages:"No messages for this patient yet.", tooth:"Tooth",
    outcomeKicker:"VISIT OUTCOME → AI FOLLOW-UP", outcomes:"Appointment outcomes", outcomesLead:"Record what actually happened. Teta2 uses the outcome to continue the current tooth or unlock the next priority tooth.", optionalNote:"Optional clinical note", outcomeRecorded:"Outcome recorded", treated:"Came · treated", notTreated:"Came · not treated", noShow:"No-show"
  },
  hy: {
    liveConversation:"ԱԲ-ԱՋԱԿՑՎՈՂ ԱԿՏԻՎ ԶՐՈՒՅՑ", patientConversation:"Զրույց պացիենտի հետ", mirrored:"WhatsApp-ի յուրաքանչյուր հաղորդագրություն ցուցադրվում է այստեղ։", liveSync:"Ուղիղ համաժամացում · 5 վրկ", waitingApproval:"ԱՅՑԸ ՍՊԱՍՈՒՄ Է ԲԺՇԿԻ ՀԱՍՏԱՏՄԱՆԸ", conversationAppointment:"ԶՐՈՒՅՑԻՆ ԿԱՊՎԱԾ ԱՅՑ", patient:"Պացիենտ", noMessages:"Այս պացիենտի համար դեռ հաղորդագրություններ չկան։", tooth:"Ատամ",
    outcomeKicker:"ԱՅՑԻ ԱՐԴՅՈՒՆՔ → ԱԲ ՀԵՏԱԳԱ ՀՍԿՈՂՈՒԹՅՈՒՆ", outcomes:"Այցերի արդյունքներ", outcomesLead:"Գրանցեք այցի իրական արդյունքը։ Teta2-ն այն օգտագործում է ընթացիկ ատամի փուլը շարունակելու կամ հաջորդ առաջնահերթ ատամը բացելու համար։", optionalNote:"Կլինիկական նշում (ըստ ցանկության)", outcomeRecorded:"Արդյունքը գրանցված է", treated:"Այցելել է · բուժվել է", notTreated:"Այցելել է · բուժում չի կատարվել", noShow:"Չի ներկայացել"
  },
  ru: {
    liveConversation:"АКТИВНЫЙ ДИАЛОГ С ИИ", patientConversation:"Диалог с пациентом", mirrored:"Здесь отображается каждое сообщение WhatsApp.", liveSync:"Синхронизация · 5 с", waitingApproval:"ПРИЕМ ОЖИДАЕТ ПОДТВЕРЖДЕНИЯ ВРАЧА", conversationAppointment:"ПРИЕМ, СВЯЗАННЫЙ С ДИАЛОГОМ", patient:"Пациент", noMessages:"Для этого пациента сообщений пока нет.", tooth:"Зуб",
    outcomeKicker:"РЕЗУЛЬТАТ ПРИЕМА → ПОСЛЕДУЮЩЕЕ НАБЛЮДЕНИЕ С ИИ", outcomes:"Итоги приемов", outcomesLead:"Зафиксируйте фактический результат приема. Teta2 использует его, чтобы продолжить этап по текущему зубу или открыть следующий приоритетный зуб.", optionalNote:"Клиническая заметка (необязательно)", outcomeRecorded:"Результат зафиксирован", treated:"Пришел · лечение проведено", notTreated:"Пришел · без лечения", noShow:"Не явился"
  }
} as const;

function patientName(patient:{first_name:string;last_name:string}):string{return `${patient.first_name} ${patient.last_name}`.trim()}
function fmt(value:string|null|undefined,lang:DashboardLang):string{if(!value)return"—";const date=new Date(value);if(Number.isNaN(date.getTime()))return"—";return new Intl.DateTimeFormat(dashboardLocale(lang),{month:"short",day:"numeric",year:"numeric",hour:"2-digit",minute:"2-digit"}).format(date)}
function selectedPatientFromShell():string{return(document.querySelector(".care-quick-patient select") as HTMLSelectElement|null)?.value??""}
function currentView():View{if(document.querySelector(".chat-workspace"))return"messages";if(document.querySelector(".appointment-board"))return"appointments";return"none"}
function ensureHost(view:View):HTMLElement|null{const id=`care-enhancer-${view}`;const existing=document.getElementById(id);if(existing)return existing;const selector=view==="messages"?".chat-workspace":view==="appointments"?".appointment-board":"";if(!selector)return null;const anchor=document.querySelector(selector);if(!anchor?.parentElement)return null;const host=document.createElement("div");host.id=id;host.className=`care-enhancer-host ${view}`;anchor.parentElement.insertBefore(host,anchor);return host}

/** Analysis and plan enhancements are owned by CareGenerationContractPanel and FollowupCaseWorkspace. */
export function CareExperienceEnhancer(){
  const[view,setView]=useState<View>("none");const[patientId,setPatientId]=useState("");const[host,setHost]=useState<HTMLElement|null>(null);
  useEffect(()=>{const sync=()=>{const next=currentView();setView(next);setPatientId(selectedPatientFromShell());setHost(ensureHost(next))};sync();const observer=new MutationObserver(sync);observer.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:["class"]});const timer=window.setInterval(sync,1000);return()=>{observer.disconnect();window.clearInterval(timer)}},[]);
  if(!host||view==="none")return null;if(view==="messages")return createPortal(<LiveConversationPanel patientId={patientId}/>,host);return createPortal(<AppointmentContextPanel patientId={patientId}/>,host);
}

function LiveConversationPanel({patientId}:{patientId:string}){
  const lang=useDashboardLanguage();const c=COPY[lang];const[conversations,setConversations]=useState<CareConversation[]>([]);const[selected,setSelected]=useState("");const[messages,setMessages]=useState<CareMessage[]>([]);const[error,setError]=useState("");
  const load=useCallback(async()=>{const all=await productApi.careConversations();const rows=all.filter((row)=>!patientId||row.patient_id===patientId);setConversations(rows);const id=selected&&rows.some((row)=>row.id===selected)?selected:rows[0]?.id??"";if(id!==selected)setSelected(id);setMessages(id?await productApi.careConversationMessages(id):[])},[patientId,selected]);
  useEffect(()=>{void load().catch((reason)=>setError(errorMessage(reason)));const timer=window.setInterval(()=>void load().catch(()=>undefined),5000);return()=>window.clearInterval(timer)},[load]);
  const conversation=conversations.find((row)=>row.id===selected);const appointment=conversation?.latest_appointment;
  return <section className="care-card enhanced-conversation"><header><div><span><MessageCircle/>{c.liveConversation}</span><h2>{conversation?.patient?patientName(conversation.patient):c.patientConversation}</h2><p>{conversation?.summary??c.mirrored}</p></div><div className="conversation-live"><i/>{c.liveSync}</div></header>{error&&<div className="care-inline-error">{error}</div>}{appointment&&<div className={`conversation-appointment ${appointment.status==="PROPOSED"?"pending":""}`}><CalendarCheck/><div><span>{appointment.status==="PROPOSED"?c.waitingApproval:c.conversationAppointment}</span><strong>{fmt(appointment.starts_at,lang)}</strong><small>{appointment.reason}{appointment.tooth_fdi?` · ${c.tooth} ${appointment.tooth_fdi}`:""}{appointment.visit_outcome?` · ${dashboardStatus(appointment.visit_outcome,lang)}`:""}</small></div><b>{dashboardStatus(appointment.status,lang)}</b></div>}<div className="enhanced-thread">{messages.length?messages.map((message)=><article key={message.id} className={message.direction==="OUT"?"ai":"patient"}><div><span>{message.direction==="OUT"?<><Sparkles/>Teta2 AI</>:c.patient}</span><time>{fmt(message.created_at,lang)}</time></div><p>{message.body}</p><small>{dashboardStatus(message.status,lang)}</small></article>):<div className="care-empty"><MessageCircle/><p>{c.noMessages}</p></div>}</div></section>;
}

function AppointmentContextPanel({patientId}:{patientId:string}){
  const lang=useDashboardLanguage();const c=COPY[lang];const[rows,setRows]=useState<CareAppointment[]>([]);const[busy,setBusy]=useState("");const[error,setError]=useState("");
  const load=useCallback(async()=>{const start=new Date();start.setDate(start.getDate()-60);const end=new Date();end.setDate(end.getDate()+180);const data=await productApi.careAppointments(start.toISOString(),end.toISOString());setRows(data.filter((row)=>!patientId||row.patient_id===patientId))},[patientId]);useEffect(()=>{void load().catch((reason)=>setError(errorMessage(reason)))},[load]);
  async function outcome(id:string,value:"TREATED"|"ATTENDED_NOT_TREATED"|"NO_SHOW"){const note=window.prompt(c.optionalNote)??undefined;setBusy(id);setError("");try{await productApi.recordAppointmentOutcome(id,value,note);await load()}catch(reason){setError(errorMessage(reason))}finally{setBusy("")}}
  return <section className="care-card appointment-context"><header><div><span><CalendarCheck/>{c.outcomeKicker}</span><h2>{c.outcomes}</h2><p>{c.outcomesLead}</p></div><Clock3/></header>{error&&<div className="care-inline-error">{error}</div>}<div className="appointment-context-grid">{rows.slice(0,12).map((appointment)=><article key={appointment.id}><div className="appointment-date"><b>{new Date(appointment.starts_at).getDate()}</b><span>{new Intl.DateTimeFormat(dashboardLocale(lang),{month:"short"}).format(new Date(appointment.starts_at))}</span></div><div><span>{appointment.visit_outcome?dashboardStatus(appointment.visit_outcome,lang):dashboardStatus(appointment.status,lang)}</span><strong>{appointment.patient?patientName(appointment.patient):appointment.reason}</strong><p>{fmt(appointment.starts_at,lang)}</p><small>{appointment.reason}{appointment.tooth_fdi?` · ${c.tooth} ${appointment.tooth_fdi}`:""}</small>{appointment.visit_outcome?<div className="outcome-recorded"><Check/>{c.outcomeRecorded} {fmt(appointment.outcome_recorded_at,lang)}</div>:["APPROVED","PROPOSED","RESCHEDULE_REQUESTED"].includes(appointment.status)&&<div className="outcome-actions"><button disabled={busy===appointment.id} onClick={()=>void outcome(appointment.id,"TREATED")}>{c.treated}</button><button disabled={busy===appointment.id} onClick={()=>void outcome(appointment.id,"ATTENDED_NOT_TREATED")}>{c.notTreated}</button><button disabled={busy===appointment.id} onClick={()=>void outcome(appointment.id,"NO_SHOW")}>{c.noShow}</button></div>}</div></article>)}</div></section>;
}
