import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { CalendarClock, Check, ChevronRight, Clock3, FileHeart, MessageCircle, Save, Search, ShieldCheck, Smartphone, UserRound } from "lucide-react";

import { errorMessage } from "../api/client";
import { productApi, type CarePlan, type CarePlanItem, type CareSettings } from "../api/product";

function title(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

function patientName(plan: CarePlan): string {
  const patient = plan.patient;
  return patient ? `${patient.first_name} ${patient.last_name}`.trim() : plan.patient_id;
}

function dateParts(value: string, timeZone: string): Record<string, string> {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    hourCycle: "h23"
  }).formatToParts(new Date(value));
  return Object.fromEntries(parts.map((part) => [part.type, part.value]));
}

function localInputValue(value: string | null | undefined, timeZone: string): string {
  if (!value) return "";
  const p = dateParts(value, timeZone);
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

function formatClinicDate(value: string | null | undefined, timeZone: string, withTime = true): string {
  if (!value) return "Not scheduled";
  return new Intl.DateTimeFormat("en-US", {
    timeZone,
    month: "short", day: "numeric", year: "numeric",
    ...(withTime ? { hour: "numeric", minute: "2-digit" } : {})
  }).format(new Date(value));
}

function zoneOffsetMs(at: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
  }).formatToParts(at);
  const p = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  const wallAsUtc = Date.UTC(Number(p.year), Number(p.month) - 1, Number(p.day), Number(p.hour), Number(p.minute), Number(p.second));
  return wallAsUtc - at.getTime();
}

function clinicLocalToIso(localValue: string, timeZone: string): string {
  const [date, clock] = localValue.split("T");
  const [year, month, day] = date.split("-").map(Number);
  const [hour, minute] = clock.split(":").map(Number);
  const wallUtc = Date.UTC(year, month - 1, day, hour, minute, 0);
  let instant = new Date(wallUtc);
  let offset = zoneOffsetMs(instant, timeZone);
  instant = new Date(wallUtc - offset);
  const corrected = zoneOffsetMs(instant, timeZone);
  if (corrected !== offset) instant = new Date(wallUtc - corrected);
  return instant.toISOString();
}

function ensureHost(): HTMLElement | null {
  if (!document.querySelector(".plan-list")) return null;
  const oldHost = document.getElementById("care-enhancer-plans");
  if (oldHost) oldHost.style.display = "none";
  let host = document.getElementById("followup-case-workspace-host");
  if (host) return host;
  const anchor = document.querySelector(".plan-list");
  if (!anchor?.parentElement) return null;
  host = document.createElement("div");
  host.id = "followup-case-workspace-host";
  anchor.parentElement.insertBefore(host, anchor);
  return host;
}

export function FollowupCaseWorkspace() {
  const [host, setHost] = useState<HTMLElement | null>(null);
  useEffect(() => {
    const sync = () => {
      const active = Boolean(document.querySelector(".plan-list"));
      const oldHost = document.getElementById("care-enhancer-plans");
      if (oldHost) oldHost.style.display = active ? "none" : "";
      setHost(active ? ensureHost() : null);
    };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true });
    const timer = window.setInterval(sync, 700);
    return () => {
      observer.disconnect();
      window.clearInterval(timer);
      const oldHost = document.getElementById("care-enhancer-plans");
      if (oldHost) oldHost.style.display = "";
    };
  }, []);
  return host ? createPortal(<CaseWorkspace />, host) : null;
}

function CaseWorkspace() {
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [query, setQuery] = useState("");
  const [settings, setSettings] = useState<Record<string, CareSettings>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    const next = await productApi.sequentialCarePlans();
    setPlans(next);
    setSelectedId((current) => current && next.some((p) => p.id === current) ? current : next[0]?.id ?? "");
    const branchIds = [...new Set(next.map((p) => p.branch_id))];
    const rows = await Promise.all(branchIds.map(async (id) => [id, await productApi.careSettings(id)] as const));
    setSettings(Object.fromEntries(rows));
  }, []);

  useEffect(() => { void load().catch((reason) => setError(errorMessage(reason))); }, [load]);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return plans;
    return plans.filter((plan) => {
      const patient = plan.patient;
      const hay = `${patientName(plan)} ${patient?.patient_number ?? ""} ${patient?.whatsapp_phone ?? ""} ${plan.status}`.toLowerCase();
      return hay.includes(term);
    });
  }, [plans, query]);
  const selected = plans.find((plan) => plan.id === selectedId) ?? visible[0];
  const zone = selected ? settings[selected.branch_id]?.timezone ?? "UTC" : "UTC";

  async function approve(planId: string) {
    setBusy(planId); setError(""); setNotice("");
    try {
      await productApi.approveSequentialCarePlan(planId);
      setNotice("Follow-up activated. The first outreach is scheduled; later teeth stay locked to the sequence.");
      await load();
    } catch (reason) { setError(errorMessage(reason)); } finally { setBusy(""); }
  }

  async function saveFirstStart(plan: CarePlan, item: CarePlanItem, localValue: string) {
    setBusy(`start-${item.id}`); setError(""); setNotice("");
    try {
      const iso = clinicLocalToIso(localValue, settings[plan.branch_id]?.timezone ?? "UTC");
      await productApi.updateSequenceSchedule(plan.id, item.id, iso);
      setNotice(`First WhatsApp outreach rescheduled to ${formatClinicDate(iso, settings[plan.branch_id]?.timezone ?? "UTC")}.`);
      await load();
    } catch (reason) { setError(errorMessage(reason)); } finally { setBusy(""); }
  }

  return <section className="followup-case-shell">
    <header className="followup-case-topbar">
      <div><span>FOLLOW-UP CASES</span><h2>Patient follow-up workspace</h2><p>One patient = one organized case file. All dates are shown in the clinic timezone.</p></div>
      <div className="case-timezone"><Clock3/><div><small>Clinic timezone</small><b>{zone}</b></div></div>
    </header>
    {notice && <div className="case-notice"><Check/>{notice}</div>}
    {error && <div className="care-inline-error case-error">{error}</div>}
    <div className="followup-case-grid">
      <aside className="case-index">
        <label className="case-search"><Search/><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search patient, ID or WhatsApp"/></label>
        <div className="case-index-list">
          {visible.map((plan) => {
            const first = [...plan.items].sort((a,b)=>(a.sequence_order ?? 999)-(b.sequence_order ?? 999))[0];
            const tz = settings[plan.branch_id]?.timezone ?? "UTC";
            return <button key={plan.id} className={plan.id === selected?.id ? "active" : ""} onClick={() => setSelectedId(plan.id)}>
              <span className="case-avatar">{plan.patient?.first_name?.[0] ?? "P"}{plan.patient?.last_name?.[0] ?? ""}</span>
              <span className="case-index-copy"><b>{patientName(plan)}</b><small>{plan.patient?.patient_number ?? "Patient"} · {plan.items.length} tooth{plan.items.length === 1 ? "" : "s"}</small><em>{first?.conversation_start_at ? `Next: ${formatClinicDate(first.conversation_start_at, tz)}` : title(first?.status ?? plan.status)}</em></span>
              <ChevronRight/>
            </button>;
          })}
          {!visible.length && <div className="case-empty">No matching patient cases.</div>}
        </div>
      </aside>
      <main className="case-file">
        {selected ? <PatientCase plan={selected} careSettings={settings[selected.branch_id]} busy={busy} onApprove={approve} onSaveFirstStart={saveFirstStart}/> : <div className="case-empty large"><FileHeart/><p>No follow-up case selected.</p></div>}
      </main>
    </div>
  </section>;
}

function PatientCase({ plan, careSettings, busy, onApprove, onSaveFirstStart }: {
  plan: CarePlan; careSettings?: CareSettings; busy: string;
  onApprove: (planId: string) => Promise<void>;
  onSaveFirstStart: (plan: CarePlan, item: CarePlanItem, localValue: string) => Promise<void>;
}) {
  const zone = careSettings?.timezone ?? "UTC";
  const items = [...plan.items].sort((a,b)=>(a.sequence_order ?? 999)-(b.sequence_order ?? 999));
  const first = items[0];
  const [firstStart, setFirstStart] = useState(localInputValue(first?.conversation_start_at, zone));
  useEffect(() => setFirstStart(localInputValue(first?.conversation_start_at, zone)), [first?.conversation_start_at, zone]);
  const canEditStart = Boolean(first && ["PENDING_APPROVAL", "ACTIVE"].includes(plan.status) && !["CONTACTED", "BOOKED", "COMPLETED", "NO_SHOW"].includes(first.status));

  return <article className="patient-case-file">
    <header className="case-file-head">
      <div className="case-patient"><span><UserRound/></span><div><small>PATIENT FOLLOW-UP FILE</small><h3>{patientName(plan)}</h3><p>{plan.patient?.patient_number ?? "Patient"} · <Smartphone/> {plan.patient?.whatsapp_phone ?? "WhatsApp not registered"}</p></div></div>
      <div className="case-file-actions"><span className={`case-status ${plan.status.toLowerCase()}`}>{title(plan.status)}</span>{plan.status === "PENDING_APPROVAL" && <button className="care-primary" disabled={Boolean(busy)} onClick={() => void onApprove(plan.id)}><Check/>Approve outreach</button>}</div>
    </header>

    <section className="case-summary-strip">
      <div><small>Teeth in plan</small><b>{items.length}</b></div>
      <div><small>Current tooth</small><b>{first ? `#${first.tooth_fdi}` : "—"}</b></div>
      <div><small>First outreach</small><b>{first?.conversation_start_at ? formatClinicDate(first.conversation_start_at, zone) : "Not scheduled"}</b></div>
      <div><small>Timezone</small><b>{zone}</b></div>
    </section>

    {first && <section className="first-contact-card">
      <div className="first-contact-copy"><CalendarClock/><div><small>FIRST WHATSAPP OUTREACH</small><h4>{canEditStart ? "Doctor can change this before the first message is sent" : "Scheduled outreach"}</h4><p>This controls when the AI sends the opening WhatsApp message for the first priority tooth.</p></div></div>
      <div className="first-contact-editor"><input type="datetime-local" value={firstStart} disabled={!canEditStart} onChange={(e)=>setFirstStart(e.target.value)}/><span>{zone}</span>{canEditStart && <button className="care-secondary" disabled={!firstStart || busy === `start-${first.id}`} onClick={()=>void onSaveFirstStart(plan, first, firstStart)}><Save/>{busy === `start-${first.id}` ? "Saving…" : "Save send time"}</button>}</div>
    </section>}

    <section className="case-sequence">
      <header><div><small>TREATMENT FOLLOW-UP SEQUENCE</small><h4>Tooth-by-tooth plan</h4></div><span><ShieldCheck/>Later teeth unlock only after the previous outcome.</span></header>
      <div className="case-tooth-list">{items.map((item, index) => <ToothRow key={item.id} item={item} index={index} zone={zone}/>)}</div>
    </section>
  </article>;
}

function ToothRow({ item, index, zone }: { item: CarePlanItem; index: number; zone: string }) {
  const active = index === 0 || item.status !== "WAITING_PREVIOUS_TOOTH";
  return <article className={`case-tooth-row ${active ? "active" : "waiting"}`}>
    <div className="case-tooth-order">{item.sequence_order ?? index + 1}</div>
    <div className="case-tooth-badge">{item.tooth_fdi}</div>
    <div className="case-tooth-main"><div><b>{title(item.finding_type)}</b><span className={`case-status compact ${item.status.toLowerCase()}`}>{title(item.status)}</span></div><p>{item.rationale ? title(item.rationale) : "Clinical follow-up"}</p><div className="case-tooth-meta"><span><Clock3/>Outreach: {item.conversation_start_at ? formatClinicDate(item.conversation_start_at, zone) : "After previous tooth outcome"}</span><span><CalendarClock/>Clinical target: {formatClinicDate(item.target_followup_at, zone, false)}</span>{item.outcome && <span><Check/>Outcome: {title(item.outcome)}</span>}</div></div>
    <div className="case-message-preview"><MessageCircle/><span>{item.message_preview ?? "Opening message will be prepared before outreach."}</span></div>
  </article>;
}
