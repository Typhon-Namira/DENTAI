import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  CalendarCheck,
  Check,
  ChevronRight,
  Clock3,
  HeartPulse,
  MessageCircle,
  Save,
  ShieldCheck,
  Sparkles,
  WandSparkles,
  X
} from "lucide-react";
import { api, errorMessage } from "../api/client";
import {
  productApi,
  type CareAppointment,
  type CareConversation,
  type CareMessage,
  type CarePlan,
  type CarePlanItem
} from "../api/product";
import type { AIAnalysis, Patient, PatientProfile, WhatsAppConnection } from "../api/types";
import { WHATSAPP_QR_POLL_MS } from "../utils/whatsapp";

type View = "none" | "analysis" | "plans" | "messages" | "appointments";
type PlanDraft = Pick<CarePlanItem, "target_followup_at" | "recommended_window" | "rationale" | "message_preview">;

function fmt(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function title(value: string): string {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function patientName(patient: Patient): string {
  return `${patient.first_name} ${patient.last_name}`.trim();
}

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
  const selector = view === "analysis"
    ? ".ai-results-shell"
    : view === "plans"
      ? ".plan-list"
      : view === "messages"
        ? ".chat-workspace"
        : view === "appointments"
          ? ".appointment-board"
          : "";
  if (!selector) return null;
  const anchor = document.querySelector(selector);
  if (!anchor?.parentElement) return null;
  const host = document.createElement("div");
  host.id = id;
  host.className = `care-enhancer-host ${view}`;
  anchor.parentElement.insertBefore(host, anchor);
  return host;
}

export function CareExperienceEnhancer() {
  const [view, setView] = useState<View>("none");
  const [patientId, setPatientId] = useState("");
  const [host, setHost] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const sync = () => {
      const nextView = currentView();
      setView(nextView);
      setPatientId(selectedPatientFromShell());
      setHost(ensureHost(nextView));
    };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
    const timer = window.setInterval(sync, 1000);
    return () => {
      observer.disconnect();
      window.clearInterval(timer);
    };
  }, []);

  if (!host || view === "none") return null;
  if (view === "analysis") return createPortal(<GeneratePlanPanel patientId={patientId} />, host);
  if (view === "plans") return createPortal(<FollowupOrchestrator patientId={patientId} />, host);
  if (view === "messages") return createPortal(<LiveConversationPanel patientId={patientId} />, host);
  return createPortal(<AppointmentContextPanel patientId={patientId} />, host);
}

function GeneratePlanPanel({ patientId }: { patientId: string }) {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");

  const load = useCallback(async () => {
    if (!patientId) { setProfile(null); setPlans([]); return; }
    const [patient, patientPlans] = await Promise.all([api.patientProfile(patientId), productApi.carePlans(patientId)]);
    setProfile(patient);
    setPlans(patientPlans);
  }, [patientId]);

  useEffect(() => { void load().catch((reason) => setError(errorMessage(reason))); }, [load]);

  const analysis = useMemo<AIAnalysis | null>(() => {
    if (!profile) return null;
    return [...profile.ai_analyses]
      .filter((item) => item.status === "COMPLETED")
      .sort((a, b) => b.requested_at.localeCompare(a.requested_at))[0] ?? null;
  }, [profile]);
  const confirmed = useMemo(() => analysis ? profile?.findings.filter((finding) => finding.analysis_id === analysis.id && finding.review_status === "CONFIRMED") ?? [] : [], [analysis, profile]);
  const plan = analysis ? plans.find((item) => item.analysis_id === analysis.id) : undefined;
  const ready = analysis?.review_status === "REVIEWED" && confirmed.length > 0;

  async function generate() {
    if (!analysis) return;
    setBusy(true); setError(""); setDone("");
    try {
      const generated = await productApi.generateCarePlan(analysis.id);
      setPlans((current) => [generated, ...current.filter((item) => item.id !== generated.id)]);
      setDone(`Follow-up plan generated for ${generated.items.length} confirmed problem tooth${generated.items.length === 1 ? "" : "s"}.`);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  function openPlans() {
    const button = Array.from(document.querySelectorAll(".care-sidebar nav button")).find((node) => node.getAttribute("aria-label") === "Follow-up plans") as HTMLButtonElement | undefined;
    button?.click();
  }

  if (!patientId || !analysis) return null;
  return <section className="care-flow-banner care-card">
    <div className="flow-orb"><WandSparkles /></div>
    <div className="flow-copy">
      <span>AI FOLLOW-UP ORCHESTRATION</span>
      <h2>{plan && ["PENDING_APPROVAL", "ACTIVE", "PAUSED", "COMPLETED"].includes(plan.status) ? "Follow-up plan ready" : "Generate follow-up plan"}</h2>
      <p>{ready
        ? `${confirmed.length} clinician-confirmed problem tooth${confirmed.length === 1 ? "" : "s"} will be converted into a tooth-level follow-up schedule, message plan and appointment path.`
        : "Review the red AI findings first. Only clinician-confirmed problem teeth are allowed into patient follow-up."}</p>
      <div className="flow-teeth">{confirmed.slice(0, 10).map((finding) => <span key={finding.id}>Tooth {finding.tooth_code} · {title(finding.finding_type)}</span>)}</div>
      {done && <div className="flow-success"><Check />{done}</div>}
      {error && <div className="care-inline-error">{error}</div>}
    </div>
    <div className="flow-actions">
      {plan && ["PENDING_APPROVAL", "ACTIVE", "PAUSED", "COMPLETED"].includes(plan.status)
        ? <button className="care-primary" onClick={openPlans}>Open follow-up plan <ChevronRight /></button>
        : <button className="care-primary" disabled={!ready || busy} onClick={() => void generate()}><Sparkles />{busy ? "Generating…" : "Generate with AI"}</button>}
      <small><ShieldCheck /> Clinician-controlled</small>
    </div>
  </section>;
}

function FollowupOrchestrator({ patientId }: { patientId: string }) {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [drafts, setDrafts] = useState<Record<string, PlanDraft>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    if (!patientId) { setProfile(null); setPlans([]); return; }
    const [p, rows] = await Promise.all([api.patientProfile(patientId), productApi.carePlans(patientId)]);
    setProfile(p); setPlans(rows);
    const next: Record<string, PlanDraft> = {};
    rows.forEach((plan) => plan.items.forEach((item) => {
      next[item.id] = {
        target_followup_at: item.target_followup_at,
        recommended_window: item.recommended_window,
        rationale: item.rationale,
        message_preview: item.message_preview
      };
    }));
    setDrafts(next);
  }, [patientId]);

  useEffect(() => { void load().catch((reason) => setError(errorMessage(reason))); }, [load]);

  function patch(itemId: string, key: keyof PlanDraft, value: string | null) {
    setDrafts((current) => ({ ...current, [itemId]: { ...current[itemId], [key]: value } }));
  }

  async function save(planId: string, item: CarePlanItem) {
    const draft = drafts[item.id]; if (!draft) return;
    setBusy(item.id); setError(""); setNotice("");
    try {
      await productApi.updateCarePlanItem(planId, item.id, {
        target_followup_at: draft.target_followup_at,
        recommended_window: draft.recommended_window,
        rationale: draft.rationale,
        message_preview: draft.message_preview
      });
      setNotice(`Saved follow-up settings for tooth ${item.tooth_fdi}.`);
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(""); }
  }

  async function approve(planId: string) {
    setBusy(planId); setError(""); setNotice("");
    try {
      await productApi.approveCarePlan(planId);
      setNotice("Plan approved. Teta2 Care can now message the patient through the connected clinic WhatsApp and continue the AI conversation.");
      await load();
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(""); }
  }

  const ordered = [...plans].sort((a, b) => b.created_at.localeCompare(a.created_at));
  return <div className="care-followup-enhanced">
    <WhatsAppBridge patient={profile?.patient ?? null} onPatientUpdated={(patient) => setProfile((current) => current ? { ...current, patient } : current)} />
    <section className="care-card followup-command-card">
      <header className="followup-command-head"><div><span><Sparkles /> AI FOLLOW-UP PLAN</span><h2>{profile ? patientName(profile.patient) : "Select a patient"}</h2><p>Review the full tooth-level schedule before activating automated patient outreach.</p></div><div className="followup-command-stats"><b>{ordered.reduce((sum, plan) => sum + plan.items.length, 0)}</b><small>planned teeth</small></div></header>
      {notice && <div className="flow-success"><Check />{notice}</div>}
      {error && <div className="care-inline-error">{error}</div>}
      {!patientId ? <div className="care-empty"><HeartPulse /><p>Select a patient to inspect the follow-up plan.</p></div> : ordered.length === 0 ? <div className="care-empty"><Sparkles /><p>No generated plan for this patient yet. Open OPG + AI and generate it from the reviewed problem teeth.</p></div> : <div className="followup-editor-list">
        {ordered.map((plan) => <article className="followup-plan-editor" key={plan.id}>
          <div className="followup-plan-summary"><div><span className={`clinical-pill ${plan.status.toLowerCase()}`}>{title(plan.status)}</span><strong>{plan.summary ?? "AI-generated tooth-level follow-up plan"}</strong><small>Created {fmt(plan.created_at)} · {plan.items.length} tooth action{plan.items.length === 1 ? "" : "s"}</small></div>{plan.status === "PENDING_APPROVAL" && <button className="care-primary" disabled={!!busy} onClick={() => void approve(plan.id)}><Check />{busy === plan.id ? "Activating…" : "Approve & start AI outreach"}</button>}</div>
          <div className="followup-item-grid">{plan.items.map((item) => {
            const draft = drafts[item.id] ?? { target_followup_at: item.target_followup_at, recommended_window: item.recommended_window, rationale: item.rationale, message_preview: item.message_preview };
            const editable = plan.status === "PENDING_APPROVAL";
            return <section className="followup-tooth-card" key={item.id}>
              <header><span className="tooth-number">{item.tooth_fdi}</span><div><strong>{title(item.finding_type)}</strong><small>{item.confidence == null ? "Clinician confirmed" : `${Math.round(item.confidence * 100)}% AI confidence`}</small></div><i className={`clinical-pill ${item.status.toLowerCase()}`}>{title(item.status)}</i></header>
              <div className="followup-fields">
                <label>Target follow-up<input type="datetime-local" disabled={!editable} value={new Date(draft.target_followup_at).toISOString().slice(0,16)} onChange={(e) => patch(item.id, "target_followup_at", new Date(e.target.value).toISOString())} /></label>
                <label>Recommended window<input disabled={!editable} value={draft.recommended_window} onChange={(e) => patch(item.id, "recommended_window", e.target.value)} /></label>
                <label className="wide">Clinical rationale<textarea disabled={!editable} rows={2} value={draft.rationale} onChange={(e) => patch(item.id, "rationale", e.target.value)} /></label>
                <label className="wide">Planned WhatsApp message<textarea disabled={!editable} rows={3} value={draft.message_preview ?? ""} onChange={(e) => patch(item.id, "message_preview", e.target.value || null)} /></label>
              </div>
              {editable && <button className="care-secondary followup-save" disabled={busy === item.id} onClick={() => void save(plan.id, item)}><Save />{busy === item.id ? "Saving…" : "Save tooth plan"}</button>}
            </section>;
          })}</div>
        </article>)}
      </div>}
    </section>
  </div>;
}

function WhatsAppBridge({ patient, onPatientUpdated }: { patient: Patient | null; onPatientUpdated: (patient: Patient) => void }) {
  const [connection, setConnection] = useState<WhatsAppConnection>({ connected: false, connection: "unknown", sender: null });
  const [phone, setPhone] = useState("");
  const [qrOpen, setQrOpen] = useState(false);
  const [qr, setQr] = useState<string | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const status = useCallback(async () => { const next = await api.whatsappStatus(); setConnection(next); if (next.connected) { setQrOpen(false); setQr(null); } return next; }, []);
  useEffect(() => { setPhone(patient?.whatsapp_phone ?? ""); }, [patient?.id, patient?.whatsapp_phone]);
  useEffect(() => { void status().catch((reason) => setError(errorMessage(reason))); }, [status]);
  useEffect(() => {
    if (!qrOpen || connection.connected) return;
    let stopped = false; let timer = 0;
    const poll = async () => {
      try { const next = await api.whatsappQr(); if (stopped) return; setConnection(next); setQr(next.qr ?? null); if (next.connected) { setQrOpen(false); setQr(null); return; } }
      catch (reason) { if (!stopped) setError(errorMessage(reason)); }
      if (!stopped) timer = window.setTimeout(() => void poll(), WHATSAPP_QR_POLL_MS);
    };
    void poll();
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [qrOpen, connection.connected]);

  async function savePhone() {
    if (!patient) return; setBusy("phone"); setError("");
    try { onPatientUpdated(await api.savePatientWhatsApp(patient.id, phone || null)); }
    catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(""); }
  }
  async function disconnect() {
    setBusy("disconnect"); setError("");
    try { await api.whatsappLogout(); setConnection({ connected: false, connection: "logged_out", sender: null }); }
    catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(""); }
  }

  return <section className="care-card whatsapp-bridge">
    <div className="whatsapp-mark"><MessageCircle /></div>
    <div className="whatsapp-bridge-copy"><span>WHATSAPP DELIVERY</span><strong>{connection.connected ? "Clinic WhatsApp connected" : "Connect clinic WhatsApp"}</strong><small>{connection.connected ? `Sender: ${connection.sender ?? "linked device"}. AI follow-up will use this account after plan approval.` : "Scan the QR with the clinic phone. This uses the existing secure linked-device workflow."}</small>{error && <em>{error}</em>}</div>
    {patient && <label className="whatsapp-patient-number">Patient number<input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+374..." /><button disabled={busy === "phone"} onClick={() => void savePhone()}>{busy === "phone" ? "…" : "Save"}</button></label>}
    <div className="whatsapp-bridge-actions"><span className={connection.connected ? "connected" : ""}><i />{connection.connected ? "Connected" : "Disconnected"}</span>{connection.connected ? <button className="care-secondary" disabled={busy === "disconnect"} onClick={() => void disconnect()}>Disconnect</button> : <button className="care-primary whatsapp-connect" onClick={() => setQrOpen(true)}>Connect with QR</button>}</div>
    {qrOpen && <div className="care-qr-backdrop" role="dialog" aria-modal="true"><div className="care-qr-modal"><button className="care-qr-close" aria-label="Close" onClick={() => setQrOpen(false)}><X /></button><div className="whatsapp-mark large"><MessageCircle /></div><span>WHATSAPP LINKED DEVICE</span><h2>Scan with the clinic phone</h2>{qr ? <img src={qr} alt="WhatsApp QR code" /> : <div className="care-qr-loading"><Activity />Generating secure QR…</div>}<p>WhatsApp → Linked devices → Link a device → scan this code.</p></div></div>}
  </section>;
}

function LiveConversationPanel({ patientId }: { patientId: string }) {
  const [conversations, setConversations] = useState<CareConversation[]>([]);
  const [selected, setSelected] = useState("");
  const [messages, setMessages] = useState<CareMessage[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const rows = (await productApi.careConversations()).filter((row) => !patientId || row.patient_id === patientId);
    setConversations(rows);
    const id = selected && rows.some((row) => row.id === selected) ? selected : rows[0]?.id ?? "";
    if (id !== selected) setSelected(id);
    if (id) setMessages(await productApi.careConversationMessages(id)); else setMessages([]);
  }, [patientId, selected]);

  useEffect(() => { void load().catch((reason) => setError(errorMessage(reason))); const timer = window.setInterval(() => void load().catch(()=>undefined), 5000); return () => window.clearInterval(timer); }, [load]);
  const conversation = conversations.find((row) => row.id === selected) ?? null;
  const appointment = conversation?.latest_appointment ?? null;

  return <section className="care-card enhanced-conversation">
    <header><div><span><MessageCircle /> LIVE AI CONVERSATION</span><h2>{conversation?.patient ? patientName(conversation.patient) : "Patient conversation"}</h2><p>{conversation?.summary ?? "Every WhatsApp message in this Care thread is mirrored here."}</p></div><div className="conversation-live"><i />Live sync · 5s</div></header>
    {error && <div className="care-inline-error">{error}</div>}
    {appointment && <div className={`conversation-appointment ${appointment.status === "PROPOSED" ? "pending" : ""}`}><CalendarCheck /><div><span>{appointment.status === "PROPOSED" ? "APPOINTMENT AWAITING DOCTOR APPROVAL" : "CONVERSATION APPOINTMENT"}</span><strong>{fmt(appointment.starts_at)}</strong><small>{appointment.reason}{appointment.tooth_fdi ? ` · Tooth ${appointment.tooth_fdi}` : ""}{appointment.finding_type ? ` · ${title(appointment.finding_type)}` : ""}</small></div><b>{title(appointment.status)}</b></div>}
    <div className="enhanced-thread">{messages.length ? messages.map((message) => <article key={message.id} className={message.direction === "OUT" ? "ai" : "patient"}><div><span>{message.direction === "OUT" ? <><Sparkles /> Teta2 Care AI</> : "Patient"}</span><time>{fmt(message.created_at)}</time></div><p>{message.body}</p><small>{title(message.status)}</small></article>) : <div className="care-empty"><MessageCircle /><p>No messages for the selected patient yet.</p></div>}</div>
  </section>;
}

function AppointmentContextPanel({ patientId }: { patientId: string }) {
  const [rows, setRows] = useState<CareAppointment[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    const start = new Date(); start.setDate(start.getDate() - 30);
    const end = new Date(); end.setDate(end.getDate() + 120);
    const data = await productApi.careAppointments(start.toISOString(), end.toISOString());
    setRows(data.filter((row) => !patientId || row.patient_id === patientId));
  }, [patientId]);
  useEffect(() => { void load().catch((reason) => setError(errorMessage(reason))); }, [load]);
  const pending = rows.filter((row) => row.status === "PROPOSED");
  if (!patientId && pending.length === 0) return null;
  return <section className="care-card appointment-context">
    <header><div><span><CalendarCheck /> CONVERSATION → APPOINTMENT</span><h2>{pending.length ? `${pending.length} patient-accepted time${pending.length === 1 ? "" : "s"} need review` : "Conversation-linked appointment details"}</h2><p>Times proposed by the AI conversation stay clinician-gated. Review the patient, tooth, reason and originating conversation before approval.</p></div><Clock3 /></header>
    {error && <div className="care-inline-error">{error}</div>}
    <div className="appointment-context-grid">{rows.slice(0,6).map((item) => <article key={item.id}><div className="appointment-date"><b>{new Date(item.starts_at).getDate()}</b><span>{new Intl.DateTimeFormat("en-US",{month:"short"}).format(new Date(item.starts_at))}</span></div><div><span>{item.status === "PROPOSED" ? "AWAITING DOCTOR" : title(item.status)}</span><strong>{item.patient ? patientName(item.patient) : item.reason}</strong><p>{fmt(item.starts_at)} → {fmt(item.ends_at)}</p><small>{item.reason}</small><div className="appointment-chips">{item.tooth_fdi && <i>Tooth {item.tooth_fdi}</i>}{item.finding_type && <i>{title(item.finding_type)}</i>}<i>Source: {item.source}</i>{item.conversation_id && <i>AI conversation linked</i>}</div></div></article>)}</div>
  </section>;
}
