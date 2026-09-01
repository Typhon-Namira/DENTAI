import { useEffect, useMemo, useRef, useState } from "react";
import { api, clearSession, errorMessage, hasSession } from "./api/client";
import type { AIAnalysis, CurrentUser, Patient, PatientProfile, XRay } from "./api/types";
import { AnalysisResults } from "./components/AnalysisResults";
import { BackendChecks } from "./components/BackendChecks";
import { PatientRadar } from "./components/PatientRadar";
import { PublicPortal } from "./components/PublicPortal";
import { WhatsAppOutreachCard } from "./components/WhatsAppOutreachCard";
import { XrayUpload } from "./components/XrayUpload";
import { xrayForAnalysis } from "./utils/opg";

type Section = "dashboard" | "workspace" | "patients" | "xrays" | "followups" | "radar" | "outreach" | "settings";

const nav: Array<{ value: Section; label: string; icon: string }> = [
  { value: "dashboard", label: "Dashboard", icon: "⌂" },
  { value: "workspace", label: "AI Workspace", icon: "✦" },
  { value: "patients", label: "My Patients", icon: "◎" },
  { value: "xrays", label: "X-rays", icon: "▣" },
  { value: "followups", label: "Follow-ups", icon: "◷" },
  { value: "radar", label: "Radar AI", icon: "⌁" },
  { value: "outreach", label: "Outreach", icon: "↗" },
  { value: "settings", label: "Settings", icon: "⚙" }
];

function fullName(patient: Patient) { return `${patient.first_name} ${patient.last_name}`; }
function initials(patient: Patient) { return `${patient.first_name[0] ?? ""}${patient.last_name[0] ?? ""}`.toUpperCase(); }
function shortDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
function asRecord(value: unknown): Record<string, unknown> { return (value && typeof value === "object") ? value as Record<string, unknown> : {}; }
function followupDate(item: Record<string, unknown>) {
  const value = item.due_at ?? item.recommended_date ?? item.created_at;
  return typeof value === "string" ? shortDate(value) : "—";
}
function followupReason(item: Record<string, unknown>) {
  const value = item.reason ?? item.summary ?? item.status;
  return typeof value === "string" ? value : "Follow-up";
}

export default function Teta2App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [profiles, setProfiles] = useState<Record<string, PatientProfile>>({});
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [selectedXrayId, setSelectedXrayId] = useState("");
  const [selectedAnalysisId, setSelectedAnalysisId] = useState("");
  const [section, setSection] = useState<Section>("dashboard");
  const [restoring, setRestoring] = useState(hasSession());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pollTimer = useRef<number | null>(null);

  const profile = selectedPatientId ? profiles[selectedPatientId] ?? null : null;
  const selectedAnalysis = profile?.ai_analyses.find((item) => item.id === selectedAnalysisId) ?? profile?.ai_analyses[0] ?? null;
  const selectedXray = xrayForAnalysis(selectedAnalysis, profile?.xrays ?? []);
  const selectedFindings = profile?.findings.filter((item) => item.analysis_id === selectedAnalysis?.id) ?? [];

  const recentAnalyses = useMemo(() => {
    return Object.values(profiles)
      .flatMap((p) => p.ai_analyses.map((analysis) => ({ analysis, patient: p.patient })))
      .sort((a, b) => new Date(b.analysis.requested_at).getTime() - new Date(a.analysis.requested_at).getTime())
      .slice(0, 4);
  }, [profiles]);

  const dueFollowups = useMemo(() => {
    return Object.values(profiles)
      .flatMap((p) => p.followups.map((item) => ({ item: asRecord(item), patient: p.patient })))
      .sort((a, b) => String(a.item.due_at ?? "").localeCompare(String(b.item.due_at ?? "")))
      .slice(0, 5);
  }, [profiles]);

  const totalFindings = useMemo(() => Object.values(profiles).reduce((sum, p) => sum + p.findings.length, 0), [profiles]);

  async function loadPatientProfile(patientId: string) {
    const next = await api.patientProfile(patientId);
    setProfiles((current) => ({ ...current, [patientId]: next }));
    return next;
  }

  async function hydrate(currentUser?: CurrentUser) {
    setError("");
    const [me, patientPage] = await Promise.all([currentUser ? Promise.resolve(currentUser) : api.me(), api.listPatients()]);
    setUser(me);
    setPatients(patientPage.items);
    const firstPatients = patientPage.items.slice(0, 6);
    const loaded = await Promise.allSettled(firstPatients.map((patient) => api.patientProfile(patient.id)));
    const nextProfiles: Record<string, PatientProfile> = {};
    loaded.forEach((result) => { if (result.status === "fulfilled") nextProfiles[result.value.patient.id] = result.value; });
    setProfiles((current) => ({ ...current, ...nextProfiles }));
  }

  useEffect(() => {
    if (!hasSession()) { setRestoring(false); return; }
    hydrate().catch((reason) => { clearSession(); setError(errorMessage(reason)); setUser(null); }).finally(() => setRestoring(false));
  }, []);

  useEffect(() => () => { if (pollTimer.current) window.clearTimeout(pollTimer.current); }, []);

  function authenticated(currentUser: CurrentUser) {
    setRestoring(true);
    hydrate(currentUser).catch((reason) => setError(errorMessage(reason))).finally(() => setRestoring(false));
  }

  function openPatient(patientId: string, destination: Section = "workspace") {
    setSelectedPatientId(patientId);
    setSection(destination);
    const cached = profiles[patientId];
    if (cached) {
      setSelectedAnalysisId(cached.ai_analyses[0]?.id ?? "");
      setSelectedXrayId(cached.ai_analyses[0]?.xray_id ?? cached.xrays[0]?.id ?? "");
    } else {
      setBusy(true);
      loadPatientProfile(patientId)
        .then((next) => { setSelectedAnalysisId(next.ai_analyses[0]?.id ?? ""); setSelectedXrayId(next.ai_analyses[0]?.xray_id ?? next.xrays[0]?.id ?? ""); })
        .catch((reason) => setError(errorMessage(reason)))
        .finally(() => setBusy(false));
    }
  }

  async function uploaded(xray: XRay) {
    setSelectedXrayId(xray.id);
    await loadPatientProfile(xray.patient_id);
  }

  function pollAnalysis(patientId: string, analysisId: string, attempt = 0) {
    if (attempt > 150) return;
    pollTimer.current = window.setTimeout(async () => {
      try {
        const next = await loadPatientProfile(patientId);
        const analysis = next.ai_analyses.find((item) => item.id === analysisId);
        if (analysis && ["QUEUED", "PROCESSING"].includes(analysis.status)) pollAnalysis(patientId, analysisId, attempt + 1);
      } catch { pollAnalysis(patientId, analysisId, attempt + 1); }
    }, 2000);
  }

  async function runAnalysis() {
    if (!selectedXrayId || !profile) return;
    setBusy(true); setError("");
    try {
      const analysis = await api.createAnalysis(selectedXrayId);
      setSelectedAnalysisId(analysis.id);
      await loadPatientProfile(profile.patient.id);
      pollAnalysis(profile.patient.id, analysis.id);
    } catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(false); }
  }

  async function logout() {
    try { await api.logout(); } catch { clearSession(); }
    setUser(null); setPatients([]); setProfiles({}); setSelectedPatientId(""); setSection("dashboard");
  }

  if (!user) {
    if (restoring) return <div className="teta-restore-screen"><span className="teta-tooth-mark large">T2</span><strong>Restoring secure clinic session…</strong></div>;
    return <PublicPortal onAuthenticated={authenticated} />;
  }

  const today = new Date().toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
  const userLabel = user.username.replace(/[._-]+/g, " ");

  return (
    <div className="teta-app-shell">
      <aside className="teta-sidebar">
        <div className="teta-side-brand"><span className="teta-tooth-mark">T2</span><div><strong>Teta2</strong><small>AI DENTAL PLATFORM</small></div></div>
        <nav>{nav.map((item) => <button className={section === item.value ? "active" : ""} key={item.value} type="button" onClick={() => setSection(item.value)}><span>{item.icon}</span>{item.label}{item.value === "radar" && <i className="new-dot" />}</button>)}</nav>
        <div className="teta-side-user"><span>{user.username.slice(0, 2).toUpperCase()}</span><div><strong>{userLabel}</strong><small>{user.role}</small></div><button type="button" onClick={() => void logout()}>↗</button></div>
      </aside>

      <header className="teta-topbar">
        <div><strong>{section === "dashboard" ? `Good morning, Dr. ${userLabel} 👋` : nav.find((item) => item.value === section)?.label}</strong><span>{section === "dashboard" ? "Let's analyze, follow up, and plan the best care for your patients." : profile ? fullName(profile.patient) : "Teta2 clinical workspace"}</span></div>
        <div className="teta-top-actions"><span className="teta-top-pill">▥ <b>{user.branch_scope.length || 1} branch{user.branch_scope.length === 1 ? "" : "es"}</b></span><span className="teta-top-pill">□ <b>{today}</b></span><button className="teta-bell" type="button">♢<i /></button></div>
      </header>

      <main className="teta-main">
        {error && <div className="teta-global-error">{error}<button type="button" onClick={() => setError("")}>×</button></div>}
        {busy && <div className="teta-progress-line" />}

        {section === "dashboard" && (
          <div className="teta-dashboard-grid">
            <section className="teta-dashboard-hero cardlike">
              <div className="dashboard-card-heading"><div><span className="teta-kicker">AI Workspace</span><h2>Analyze an OPG in one clinical flow</h2><p>Choose a patient, upload the radiograph, and send it to DENTAI V5.</p></div><span className="dashboard-ai-orb">✦</span></div>
              <div className="dashboard-upload-zone">
                <span className="dashboard-tooth-icon">⌗</span><strong>Drop an X-ray into your patient's workspace</strong><small>Private storage · AI-assisted decision support · clinician review</small>
                <div><button className="teta-primary-button compact" type="button" onClick={() => setSection("workspace")}>Open AI Workspace</button><button className="teta-ghost-button" type="button" onClick={() => setSection("xrays")}>X-ray library</button></div>
              </div>
              <div className="clinical-warning"><span>♢</span><p>AI results are decision-support information, not diagnosis. Please review clinically.</p></div>
            </section>

            <section className="teta-recent-patients cardlike">
              <div className="dashboard-section-title"><h3>Recent Patients</h3><button type="button" onClick={() => setSection("patients")}>View all</button></div>
              <div className="recent-patient-list">{patients.slice(0, 5).map((patient, index) => <button type="button" key={patient.id} onClick={() => openPatient(patient.id)}><span className={`patient-avatar tone-${index % 5}`}>{initials(patient)}</span><div><strong>{fullName(patient)}</strong><small>ID: {patient.patient_number}</small></div><span className="patient-last-visit"><small>Profile</small><b>{profiles[patient.id]?.visits.length ?? 0} visits</b></span><i>›</i></button>)}{patients.length === 0 && <div className="dashboard-empty">No patients yet.</div>}</div>
            </section>

            <section className="teta-recent-analyses cardlike">
              <div className="dashboard-section-title"><h3>Recent Analyses</h3><button type="button" onClick={() => setSection("workspace")}>View all</button></div>
              <div className="analysis-preview-grid">{recentAnalyses.map(({ analysis, patient }, index) => <button key={analysis.id} type="button" onClick={() => { openPatient(patient.id); setSelectedAnalysisId(analysis.id); setSelectedXrayId(analysis.xray_id); }}><div className={`fake-xray xray-${index}`}><span>OPG</span><i /></div><span className={`analysis-state ${analysis.status.toLowerCase()}`}>{analysis.status}</span><strong>{fullName(patient)}</strong><small>{shortDate(analysis.requested_at)}</small></button>)}{recentAnalyses.length === 0 && <div className="dashboard-empty wide">Analyses will appear here after the first OPG is processed.</div>}</div>
            </section>

            <section className="teta-schedule cardlike">
              <div className="dashboard-section-title"><h3>Today's Follow-ups</h3><button type="button" onClick={() => setSection("followups")}>View all</button></div>
              <div className="schedule-list">{dueFollowups.map(({ item, patient }, index) => <button type="button" key={`${patient.id}-${index}`} onClick={() => openPatient(patient.id, "followups")}><b>{followupDate(item)}</b><span><strong>{fullName(patient)}</strong><small>{followupReason(item)}</small></span><i>{String(item.status ?? "DUE")}</i></button>)}{dueFollowups.length === 0 && <div className="dashboard-empty">No follow-ups loaded yet.</div>}</div>
            </section>

            <section className="teta-radar-teaser cardlike">
              <div><span className="teta-kicker">Radar AI</span><h3>Opportunity intelligence for your clinic</h3><p>Review social signals and turn relevant dental needs into an organized contact queue.</p><button className="teta-primary-button compact" type="button" onClick={() => setSection("radar")}>Open Radar AI</button></div><div className="mini-radar"><i /><i /><i /><span>T2</span></div>
            </section>

            <section className="teta-metrics-row">
              <article><span>Patients</span><strong>{patients.length}</strong><small>accessible records</small></article><article><span>AI analyses</span><strong>{recentAnalyses.length}</strong><small>recently loaded</small></article><article><span>Findings</span><strong>{totalFindings}</strong><small>clinical findings</small></article>
            </section>
          </div>
        )}

        {section === "workspace" && (
          <div className="teta-module">
            <ModuleHeader eyebrow="DENTAI V5" title="AI Workspace" copy="Upload an OPG, initialize an analysis, and clinically review each finding." />
            <PatientPicker patients={patients} selected={selectedPatientId} onChange={(id) => openPatient(id, "workspace")} />
            {!profile ? <EmptyState title="Choose a patient" copy="Select a patient to open the AI workspace." /> : <>
              <PatientBanner profile={profile} />
              <div className="workspace-action-grid"><XrayUpload patientId={profile.patient.id} onUploaded={uploaded} /><section className="teta-study-queue cardlike"><div className="dashboard-section-title"><h3>Imaging queue</h3><span>{profile.xrays.length}</span></div><div className="study-list">{profile.xrays.map((xray) => <button className={selectedXrayId === xray.id ? "selected" : ""} type="button" key={xray.id} onClick={() => setSelectedXrayId(xray.id)}><span>XR</span><div><strong>{xray.original_filename}</strong><small>{shortDate(xray.uploaded_at)}</small></div><i>{xray.status}</i></button>)}</div><button className="teta-primary-button" type="button" disabled={!selectedXrayId || user.role !== "DOCTOR" || busy} onClick={() => void runAnalysis()}>{busy ? "Queueing…" : "Run Teta2 V5 Analysis"}</button></section></div>
              {selectedAnalysis ? <AnalysisResults analysis={selectedAnalysis} xray={selectedXray} findings={selectedFindings} role={user.role} onReviewed={async () => { await loadPatientProfile(profile.patient.id); }} /> : <EmptyState title="No analysis selected" copy="Choose an X-ray and run a Teta2 V5 analysis." />}
            </>}
          </div>
        )}

        {section === "patients" && <div className="teta-module"><ModuleHeader eyebrow="Clinical records" title="My Patients" copy="Open a longitudinal patient profile and continue directly into imaging or follow-up." /><section className="teta-patient-grid">{patients.map((patient, index) => <button type="button" key={patient.id} onClick={() => openPatient(patient.id)}><span className={`patient-avatar big tone-${index % 5}`}>{initials(patient)}</span><div><strong>{fullName(patient)}</strong><small>{patient.patient_number}</small><p>{profiles[patient.id]?.ai_analyses.length ?? 0} AI analyses · {profiles[patient.id]?.findings.length ?? 0} findings</p></div><i>Open ›</i></button>)}</section></div>}

        {section === "xrays" && <div className="teta-module"><ModuleHeader eyebrow="Imaging library" title="X-rays" copy="Manage radiographs per patient and open a study in the AI workspace." /><PatientPicker patients={patients} selected={selectedPatientId} onChange={(id) => openPatient(id, "xrays")} />{!profile ? <EmptyState title="Choose a patient" copy="Select a patient to view or upload radiographs." /> : <div className="workspace-action-grid"><XrayUpload patientId={profile.patient.id} onUploaded={uploaded} /><section className="teta-xray-library cardlike">{profile.xrays.map((xray) => <button type="button" key={xray.id} onClick={() => { setSelectedXrayId(xray.id); setSection("workspace"); }}><span>XR</span><div><strong>{xray.original_filename}</strong><small>{xray.mime_type} · {(xray.size_bytes / 1024 / 1024).toFixed(1)} MB</small></div><i>{xray.status}</i></button>)}</section></div>}</div>}

        {section === "followups" && <div className="teta-module"><ModuleHeader eyebrow="Smart Recall" title="Follow-ups" copy="Keep monitoring, return visits, and care continuity visible in one timeline." /><PatientPicker patients={patients} selected={selectedPatientId} onChange={(id) => openPatient(id, "followups")} />{!profile ? <EmptyState title="Choose a patient" copy="Select a patient to inspect follow-up history." /> : <div className="followup-layout"><section className="cardlike teta-followup-list"><div className="dashboard-section-title"><h3>Patient timeline</h3><span>{profile.followups.length}</span></div>{profile.followups.map((item, index) => { const row = asRecord(item); return <article key={index}><b>{index + 1}</b><div><strong>{followupReason(row)}</strong><small>{followupDate(row)}</small></div><i>{String(row.status ?? "SCHEDULED")}</i></article>; })}{profile.followups.length === 0 && <div className="dashboard-empty">No follow-ups stored for this patient.</div>}</section><section className="followup-stats"><article><span>Future risk</span><strong>{profile.future_risk.length}</strong></article><article><span>Care plan</span><strong>{profile.future_care.length}</strong></article><article><span>Visits</span><strong>{profile.visits.length}</strong></article></section></div>}</div>}

        {section === "radar" && <div className="teta-module radar-module"><ModuleHeader eyebrow="Opportunity intelligence" title="Radar AI" copy="Discover and triage social signals from people who may be looking for dental care." /><PatientRadar role={user.role} /></div>}

        {section === "outreach" && <div className="teta-module"><ModuleHeader eyebrow="Patient communication" title="Outreach" copy="Manage clinic follow-up communication without leaving the patient context." /><PatientPicker patients={patients} selected={selectedPatientId} onChange={(id) => openPatient(id, "outreach")} />{!profile ? <EmptyState title="Choose a patient" copy="Select a patient to manage WhatsApp outreach." /> : <WhatsAppOutreachCard patient={profile.patient} onPatientUpdated={(patient) => { setPatients((current) => current.map((p) => p.id === patient.id ? patient : p)); setProfiles((current) => current[patient.id] ? { ...current, [patient.id]: { ...current[patient.id], patient } } : current); }} />}</div>}

        {section === "settings" && <div className="teta-module"><ModuleHeader eyebrow="Clinic workspace" title="Settings & System" copy="Backend diagnostics and authenticated clinic context." /><div className="settings-grid"><section className="cardlike settings-card"><h3>Backend status</h3><BackendChecks /></section><section className="cardlike settings-card"><h3>Authenticated context</h3><dl><div><dt>User</dt><dd>{user.email}</dd></div><div><dt>Role</dt><dd>{user.role}</dd></div><div><dt>Clinic ID</dt><dd>{user.clinic_id}</dd></div><div><dt>Branch scope</dt><dd>{user.branch_scope.length}</dd></div></dl></section></div></div>}
      </main>
      <footer className="teta-app-footer">Teta2 · Teeth Evaluation & Treatment AI Assistant · clinician review required</footer>
    </div>
  );
}

function ModuleHeader({ eyebrow, title, copy }: { eyebrow: string; title: string; copy: string }) {
  return <header className="teta-module-header"><div><span className="teta-kicker">{eyebrow}</span><h1>{title}</h1><p>{copy}</p></div></header>;
}

function PatientPicker({ patients, selected, onChange }: { patients: Patient[]; selected: string; onChange: (id: string) => void }) {
  return <label className="teta-patient-picker"><span>Patient</span><select value={selected} onChange={(event) => onChange(event.target.value)}><option value="">Select patient…</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{fullName(patient)} · {patient.patient_number}</option>)}</select></label>;
}

function PatientBanner({ profile }: { profile: PatientProfile }) {
  return <section className="teta-patient-banner"><span className="patient-avatar big">{initials(profile.patient)}</span><div><h2>{fullName(profile.patient)}</h2><p>ID {profile.patient.patient_number} · {profile.patient.sex || "Sex not recorded"}</p></div><div className="patient-banner-stats"><span><b>{profile.xrays.length}</b>X-rays</span><span><b>{profile.ai_analyses.length}</b>Analyses</span><span><b>{profile.findings.length}</b>Findings</span><span><b>{profile.followups.length}</b>Follow-ups</span></div></section>;
}

function EmptyState({ title, copy }: { title: string; copy: string }) {
  return <section className="teta-empty-state cardlike"><span>✦</span><h3>{title}</h3><p>{copy}</p></section>;
}
