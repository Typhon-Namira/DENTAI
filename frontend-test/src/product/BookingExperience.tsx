import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { CalendarCheck, Check, Clock3, Copy, ExternalLink, Link2, RefreshCw, ShieldCheck, X } from "lucide-react";

import { API_BASE_URL, api, authenticatedRequest, errorMessage, hasSession } from "../api/client";
import { productApi, type BranchSummary, type CareAppointment } from "../api/product";

import "./booking-experience.css";

type Lang = "en" | "hy" | "ru";

type PublicBooking = {
  clinic_name: string;
  branch_name: string;
  timezone: string;
  working_days: number[];
  day_start: string;
  day_end: string;
  appointment_minutes: number;
  booking_horizon_days: number;
  slots: string[];
  patient: { first_name: string } | null;
  prefilled: boolean;
  languages: Lang[];
};

type ClinicLink = {
  url: string;
  branch_id: string;
  branch_name: string;
  timezone: string;
  working_days: number[];
  day_start: string;
  day_end: string;
  appointment_minutes: number;
  booking_horizon_days: number;
  stable: boolean;
};

const text = {
  en: {
    title: "Book your dental check-up",
    intro: "Choose an available time from the clinic's live schedule. Your request is sent to the doctor for final confirmation.",
    first: "First name", last: "Last name", phone: "WhatsApp / phone", email: "Email (optional)",
    choose: "Choose a time", submit: "Request this appointment", waiting: "Sending request…",
    success: "Time requested", successBody: "Your request is registered. Please wait for the doctor's confirmation; Teta2 will message you as soon as the doctor responds.",
    unavailable: "No bookable times are available right now.", schedule: "Clinic working hours", duration: "Check-up duration",
    doctorApproval: "Doctor confirmation required", back: "Close", appointments: "Appointment requests",
    permanent: "Permanent clinic booking link", permanentLead: "This link stays the same. Available times inside it always follow the current working-hours rules.",
    copy: "Copy link", open: "Open form", pending: "Waiting for doctor", confirmed: "Confirmed & upcoming", approve: "Confirm",
    alternative: "Suggest another range", from: "From", until: "Until", note: "Optional message to patient", sendRange: "Send suggested range",
  },
  hy: {
    title: "Ամրագրեք ատամնաբուժական ստուգումը",
    intro: "Ընտրեք կլինիկայի ընթացիկ ժամանակացույցից ազատ ժամ։ Հարցումը կուղարկվի բժշկին վերջնական հաստատման համար։",
    first: "Անուն", last: "Ազգանուն", phone: "WhatsApp / հեռախոս", email: "Էլ․ փոստ (ըստ ցանկության)",
    choose: "Ընտրեք ժամը", submit: "Ուղարկել ժամի հարցումը", waiting: "Ուղարկվում է…",
    success: "Ժամը գրանցվել է", successBody: "Ձեր հարցումը գրանցվել է։ Սպասեք բժշկի հաստատմանը․ Teta2-ը բժշկի պատասխանից հետո անմիջապես կգրի ձեզ։",
    unavailable: "Այս պահին ամրագրման ազատ ժամ չկա։", schedule: "Կլինիկայի աշխատանքային ժամեր", duration: "Ստուգման տևողություն",
    doctorApproval: "Պահանջվում է բժշկի հաստատում", back: "Փակել", appointments: "Այցի հարցումներ",
    permanent: "Կլինիկայի մշտական ամրագրման հղում", permanentLead: "Այս հղումը չի փոխվում։ Դրա ազատ ժամերը միշտ հաշվարկվում են ընթացիկ աշխատանքային ժամերից։",
    copy: "Պատճենել", open: "Բացել ձևը", pending: "Սպասում է բժշկին", confirmed: "Հաստատված և առաջիկա", approve: "Հաստատել",
    alternative: "Առաջարկել այլ միջակայք", from: "Սկիզբ", until: "Մինչև", note: "Լրացուցիչ հաղորդագրություն", sendRange: "Ուղարկել միջակայքը",
  },
  ru: {
    title: "Запись на стоматологический осмотр",
    intro: "Выберите свободное время из актуального расписания клиники. Запрос будет отправлен врачу для окончательного подтверждения.",
    first: "Имя", last: "Фамилия", phone: "WhatsApp / телефон", email: "Email (необязательно)",
    choose: "Выберите время", submit: "Отправить запрос", waiting: "Отправляем…",
    success: "Время запрошено", successBody: "Запрос зарегистрирован. Дождитесь подтверждения врача — Teta2 сразу напишет вам после его ответа.",
    unavailable: "Сейчас нет доступного времени для записи.", schedule: "Рабочие часы клиники", duration: "Длительность осмотра",
    doctorApproval: "Требуется подтверждение врача", back: "Закрыть", appointments: "Запросы на прием",
    permanent: "Постоянная ссылка для записи", permanentLead: "Ссылка не меняется. Доступные часы в форме всегда рассчитываются по текущему расписанию врача.",
    copy: "Копировать", open: "Открыть форму", pending: "Ожидает врача", confirmed: "Подтвержденные и предстоящие", approve: "Подтвердить",
    alternative: "Предложить другой интервал", from: "С", until: "До", note: "Сообщение пациенту (необязательно)", sendRange: "Отправить интервал",
  },
} as const;

function locale(lang: Lang) { return lang === "hy" ? "hy-AM" : lang === "ru" ? "ru-RU" : "en-US"; }
function formatSlot(value: string, lang: Lang) {
  return new Intl.DateTimeFormat(locale(lang), { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}
function fullName(a: CareAppointment) {
  return a.patient ? `${a.patient.first_name} ${a.patient.last_name}`.trim() : a.reason;
}
function statusLabel(value: string) { return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (x) => x.toUpperCase()); }

async function publicJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message || payload?.detail || "Request failed");
  return payload as T;
}

function PublicBookingPortal({ token }: { token: string }) {
  const initial = localStorage.getItem("teta2-product-language");
  const [lang, setLang] = useState<Lang>(initial === "hy" || initial === "ru" ? initial : "en");
  const t = text[lang];
  const [data, setData] = useState<PublicBooking | null>(null);
  const [slot, setSlot] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try { setData(await publicJson<PublicBooking>(`/api/v1/care/booking/public/${encodeURIComponent(token)}`)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Booking link unavailable"); }
  }, [token]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { document.body.classList.add("booking-open"); return () => document.body.classList.remove("booking-open"); }, []);

  const days = useMemo(() => {
    const result = new Map<string, string[]>();
    for (const value of data?.slots ?? []) {
      const key = new Intl.DateTimeFormat(locale(lang), { weekday: "long", month: "long", day: "numeric" }).format(new Date(value));
      result.set(key, [...(result.get(key) ?? []), value]);
    }
    return [...result.entries()];
  }, [data?.slots, lang]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!slot) return;
    const form = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      await publicJson(`/api/v1/care/booking/public/${encodeURIComponent(token)}`, {
        method: "POST",
        body: JSON.stringify({
          slot,
          language: lang,
          first_name: data?.prefilled ? null : String(form.get("first_name") || "").trim(),
          last_name: data?.prefilled ? null : String(form.get("last_name") || "").trim(),
          phone: data?.prefilled ? null : String(form.get("phone") || "").trim(),
          email: data?.prefilled ? null : (String(form.get("email") || "").trim() || null),
        }),
      });
      setDone(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not request appointment");
      await load();
    } finally { setBusy(false); }
  }

  return <div className="booking-public-shell">
    <header className="booking-public-top"><strong>Teta2</strong><div>{(["en","hy","ru"] as Lang[]).map(x=><button key={x} className={lang===x?"active":""} onClick={()=>{localStorage.setItem("teta2-product-language",x);setLang(x)}}>{x.toUpperCase()}</button>)}</div></header>
    <main className="booking-public-main">
      {done ? <section className="booking-success"><span><Check/></span><h1>{t.success}</h1><p>{t.successBody}</p></section> : <>
        <section className="booking-intro"><span className="booking-kicker"><CalendarCheck/>{t.doctorApproval}</span><h1>{t.title}</h1><p>{t.intro}</p>{data&&<div className="booking-clinic"><strong>{data.clinic_name}</strong><span>{data.branch_name}</span><small>{t.schedule}: {data.day_start}–{data.day_end} · {data.timezone}</small><small>{t.duration}: {data.appointment_minutes} min</small></div>}</section>
        <form className="booking-form" onSubmit={submit}>
          {!data ? <div className="booking-loader"><RefreshCw/>Loading live availability…</div> : <>
            {!data.prefilled&&<div className="booking-fields"><label>{t.first}<input name="first_name" required/></label><label>{t.last}<input name="last_name" required/></label><label>{t.phone}<input name="phone" required placeholder="+374…"/></label><label>{t.email}<input name="email" type="email"/></label></div>}
            {data.prefilled&&data.patient&&<div className="booking-person"><ShieldCheck/><div><small>{data.patient.first_name}</small><strong>{data.clinic_name}</strong></div></div>}
            <div className="booking-slot-head"><div><small>LIVE AVAILABILITY</small><h2>{t.choose}</h2></div><button type="button" onClick={()=>void load()}><RefreshCw/>Refresh</button></div>
            {days.length ? <div className="booking-days">{days.slice(0,14).map(([day,values])=><section key={day}><h3>{day}</h3><div>{values.map(value=><button type="button" key={value} className={slot===value?"selected":""} onClick={()=>setSlot(value)}>{new Intl.DateTimeFormat(locale(lang),{hour:"2-digit",minute:"2-digit"}).format(new Date(value))}</button>)}</div></section>)}</div> : <div className="booking-empty"><Clock3/><p>{t.unavailable}</p></div>}
            {error&&<div className="booking-error">{error}</div>}
            <button className="booking-submit" disabled={!slot||busy}>{busy?t.waiting:t.submit}</button>
          </>}
        </form>
      </>}
    </main>
  </div>;
}

function AppointmentManager({ branches }: { branches: BranchSummary[] }) {
  const stored = localStorage.getItem("teta2-product-language");
  const lang: Lang = stored === "hy" || stored === "ru" ? stored : "en";
  const t = text[lang];
  const [branchId, setBranchId] = useState(branches[0]?.id ?? "");
  const [link, setLink] = useState<ClinicLink | null>(null);
  const [appointments, setAppointments] = useState<CareAppointment[]>([]);
  const [busy, setBusy] = useState("");
  const [rangeFor, setRangeFor] = useState("");
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!branchId) return;
    const now = new Date(); const end = new Date(); end.setDate(end.getDate()+90);
    try {
      const [l,a] = await Promise.all([
        authenticatedRequest<ClinicLink>(`/api/v1/care/booking/link/${branchId}`),
        authenticatedRequest<CareAppointment[]>(`/api/v1/care/appointments?start=${encodeURIComponent(now.toISOString())}&end=${encodeURIComponent(end.toISOString())}`),
      ]);
      setLink(l); setAppointments(a.filter(x=>x.branch_id===branchId)); setError("");
    } catch (reason) { setError(errorMessage(reason)); }
  }, [branchId]);
  useEffect(()=>{void refresh()},[refresh]);
  useEffect(()=>{if(branches.length&&!branchId)setBranchId(branches[0].id)},[branches,branchId]);

  async function approve(id:string){setBusy(id);setError("");try{await authenticatedRequest(`/api/v1/care/booking/appointments/${id}/approve`,{method:"POST"});await refresh();}catch(e){setError(errorMessage(e));}finally{setBusy("")}}
  async function suggest(id:string){if(!rangeStart||!rangeEnd)return;setBusy(id);setError("");try{await authenticatedRequest(`/api/v1/care/booking/appointments/${id}/suggest-range`,{method:"POST",body:JSON.stringify({starts_at:new Date(rangeStart).toISOString(),ends_at:new Date(rangeEnd).toISOString(),note:note||null})});setRangeFor("");setRangeStart("");setRangeEnd("");setNote("");await refresh();}catch(e){setError(errorMessage(e));}finally{setBusy("")}}

  const pending=appointments.filter(x=>x.status==="PROPOSED");
  const confirmed=appointments.filter(x=>x.status!=="PROPOSED"&&x.status!=="RESCHEDULED").sort((a,b)=>a.starts_at.localeCompare(b.starts_at));
  return <div className="booking-admin-stack">
    <section className="booking-admin-link">
      <div className="booking-admin-link-head"><span><Link2/></span><div><small>BOOKING PORTAL</small><h2>{t.permanent}</h2><p>{t.permanentLead}</p></div></div>
      {branches.length>1&&<label>Branch<select value={branchId} onChange={e=>setBranchId(e.target.value)}>{branches.map(b=><option value={b.id} key={b.id}>{b.name}</option>)}</select></label>}
      {link&&<><div className="booking-link-value"><code>{link.url}</code><button onClick={()=>void navigator.clipboard.writeText(link.url)}><Copy/>{t.copy}</button><a href={link.url} target="_blank" rel="noreferrer"><ExternalLink/>{t.open}</a></div><div className="booking-link-rules"><span><Clock3/>{link.day_start}–{link.day_end}</span><span>{link.appointment_minutes} min</span><span>{link.timezone}</span><span>EN · HY · RU</span></div></>}
    </section>
    {error&&<div className="booking-admin-error">{error}<button onClick={()=>setError("")}><X/></button></div>}
    <section className="booking-admin-board"><header><div><small>DOCTOR APPROVAL</small><h2>{t.pending}</h2></div><button onClick={()=>void refresh()}><RefreshCw/>Refresh</button></header>{pending.length?pending.map(a=><article key={a.id}><time><b>{new Date(a.starts_at).getDate()}</b><span>{new Intl.DateTimeFormat(locale(lang),{month:"short"}).format(new Date(a.starts_at))}</span></time><div className="booking-request-main"><strong>{fullName(a)}</strong><small>{formatSlot(a.starts_at,lang)} · {a.timezone}</small><small>{a.reason}</small></div><span className="booking-pending-pill">{t.doctorApproval}</span><div className="booking-request-actions"><button disabled={!!busy} onClick={()=>setRangeFor(rangeFor===a.id?"":a.id)}>{t.alternative}</button><button className="confirm" disabled={!!busy} onClick={()=>void approve(a.id)}><Check/>{busy===a.id?"…":t.approve}</button></div>{rangeFor===a.id&&<div className="booking-range-form"><label>{t.from}<input type="datetime-local" value={rangeStart} onChange={e=>setRangeStart(e.target.value)}/></label><label>{t.until}<input type="datetime-local" value={rangeEnd} onChange={e=>setRangeEnd(e.target.value)}/></label><label className="wide">{t.note}<input value={note} onChange={e=>setNote(e.target.value)}/></label><button className="wide" disabled={!rangeStart||!rangeEnd||!!busy} onClick={()=>void suggest(a.id)}>{t.sendRange}</button></div>}</article>):<div className="booking-admin-empty"><Check/>No appointment requests are waiting.</div>}</section>
    <section className="booking-admin-board"><header><div><small>CALENDAR</small><h2>{t.confirmed}</h2></div></header>{confirmed.length?confirmed.map(a=><article key={a.id}><time><b>{new Date(a.starts_at).getDate()}</b><span>{new Intl.DateTimeFormat(locale(lang),{month:"short"}).format(new Date(a.starts_at))}</span></time><div className="booking-request-main"><strong>{fullName(a)}</strong><small>{formatSlot(a.starts_at,lang)} · {a.timezone}</small></div><span className={`booking-status ${a.status.toLowerCase()}`}>{statusLabel(a.status)}</span></article>):<div className="booking-admin-empty"><CalendarCheck/>No upcoming appointments yet.</div>}</section>
  </div>;
}

function ClinicBookingEnhancer() {
  const [host, setHost] = useState<HTMLElement | null>(null);
  const [branches, setBranches] = useState<BranchSummary[]>([]);

  useEffect(()=>{
    if(!hasSession()) return;
    void Promise.all([api.me(),productApi.branches()]).then(([,rows])=>setBranches(rows)).catch(()=>undefined);
  },[]);

  useEffect(()=>{
    if(!hasSession()) return;
    let lastSaved: Element | null = null;
    const reconcile=()=>{
      // Booking integration must not mutate global clinical navigation or dashboard metrics.
      const board=document.querySelector<HTMLElement>(".appointment-board");
      if(board){
        board.style.display="none";
        let mount=document.querySelector<HTMLElement>("#teta2-booking-admin-mount");
        if(!mount){mount=document.createElement("div");mount.id="teta2-booking-admin-mount";board.parentElement?.insertBefore(mount,board);}
        setHost(mount);
      } else setHost(null);
      const saved=document.querySelector(".schedule-card .saved");
      if(saved&&saved!==lastSaved){
        lastSaved=saved;
        window.setTimeout(()=>{
          const appointmentButton=[...document.querySelectorAll<HTMLButtonElement>(".care-sidebar nav button")].find(button=>{
            const value=(button.textContent||"").toLowerCase();
            return value.includes("appointments")||value.includes("այց")||value.includes("прием");
          });
          appointmentButton?.click();
        },450);
      }
    };
    reconcile(); const observer=new MutationObserver(reconcile); observer.observe(document.body,{childList:true,subtree:true});
    return()=>observer.disconnect();
  },[]);

  return host&&branches.length?createPortal(<AppointmentManager branches={branches}/>,host):null;
}

export function BookingExperience() {
  const match=window.location.pathname.match(/^\/book\/([^/]+)$/);
  if(match) return <PublicBookingPortal token={decodeURIComponent(match[1])}/>;
  return <ClinicBookingEnhancer/>;
}