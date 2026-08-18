import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, clearSession, errorMessage, hasSession } from "./api/client";
import type {
  AIAnalysis,
  CurrentUser,
  Patient,
  PatientProfile,
  XRay
} from "./api/types";
import { AnalysisResults } from "./components/AnalysisResults";
import { BackendChecks } from "./components/BackendChecks";
import { LoginCard } from "./components/LoginCard";
import { StatusBadge } from "./components/StatusBadge";
import { WhatsAppOutreachCard } from "./components/WhatsAppOutreachCard";
import { XrayUpload } from "./components/XrayUpload";
import { isFindingProductVisible, xrayForAnalysis } from "./utils/opg";

const POLL_INTERVAL_MS = 2_000;
const POLL_TIMEOUT_MS = 5 * 60_000;

type AppSection =
  | "workspace"
  | "patients"
  | "xrays"
  | "history"
  | "followups"
  | "outreach"
  | "settings";

const NAV_ITEMS: Array<{ value: AppSection; label: string; icon: string }> = [
  { value: "workspace", label: "AI Workspace", icon: "✦" },
  { value: "patients", label: "Patients", icon: "◎" },
  { value: "xrays", label: "X-rays", icon: "▣" },
  { value: "history", label: "History", icon: "◴" },
  { value: "followups", label: "Follow-ups", icon: "↻" },
  { value: "outreach", label: "Outreach", icon: "↗" },
  { value: "settings", label: "Settings", icon: "⚙" }
];

function displayDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function patientName(patient: Patient): string {
  return `${patient.first_name} ${patient.last_name}`;
}

function dateOnly(value: string | null | undefined): string {
  return value
    ? new Date(value).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric"
      })
    : "—";
}

function recordDate(record: Record<string, unknown>): string {
  for (const key of ["due_at", "recommended_date", "scheduled_date", "created_at"]) {
    const value = record[key];
    if (typeof value === "string" && value) return displayDate(value);
  }
  return "Date not recorded";
}

function recordStatus(record: Record<string, unknown>): string {
  for (const key of ["status", "priority", "source"]) {
    const value = record[key];
    if (typeof value === "string" && value) return value.replaceAll("_", " ");
  }
  return "Recorded";
}

function PageTitle({ eyebrow, title, copy, action }: {
  eyebrow: string;
  title: string;
  copy: string;
  action?: ReactNode;
}) {
  return (
    <header className="module-titlebar">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{copy}</p>
      </div>
      {action && <div className="module-title-action">{action}</div>}
    </header>
  );
}

function AnalysisTimeline({ analysis, hasXray }: { analysis: AIAnalysis | null; hasXray: boolean }) {
  const states = [
    { label: "Uploaded", active: hasXray, failed: false },
    { label: "Queued", active: Boolean(analysis), failed: false },
    {
      label: "Processing",
      active: analysis?.status === "PROCESSING" || analysis?.status === "COMPLETED",
      failed: false
    },
    {
      label: analysis?.status === "FAILED" ? "Failed" : "Ready",
      active: analysis?.status === "COMPLETED" || analysis?.status === "FAILED",
      failed: analysis?.status === "FAILED"
    }
  ];

  return (
    <ol className="analysis-timeline pro-timeline" aria-label="Analysis progress">
      {states.map((state) => (
        <li className={(state.active ? "active " : "") + (state.failed ? "failed" : "")} key={state.label}>
          <span aria-hidden="true">{state.active ? "✓" : ""}</span>
          {state.label}
        </li>
      ))}
    </ol>
  );
}

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [selectedXrayId, setSelectedXrayId] = useState("");
  const [selectedAnalysisId, setSelectedAnalysisId] = useState("");
  const [section, setSection] = useState<AppSection>("workspace");
  const [showImagingTools, setShowImagingTools] = useState(false);
  const [loading, setLoading] = useState(false);
  const [patientsError, setPatientsError] = useState("");
  const [workspaceError, setWorkspaceError] = useState("");
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [pollMessage, setPollMessage] = useState("");
  const pollDeadline = useRef(0);

  const selectedAnalysis = useMemo(
    () => profile?.ai_analyses.find((item) => item.id === selectedAnalysisId) ?? null,
    [profile, selectedAnalysisId]
  );
  const analysisFindings = useMemo(
    () => profile?.findings.filter((item) => item.analysis_id === selectedAnalysisId) ?? [],
    [profile, selectedAnalysisId]
  );
  const visibleFindings = useMemo(
    () => analysisFindings.filter(isFindingProductVisible),
    [analysisFindings]
  );
  const pendingVisibleFindings = useMemo(
    () => visibleFindings.filter((item) => item.review_status === "PENDING"),
    [visibleFindings]
  );
  const analysisXray = useMemo(
    () => xrayForAnalysis(selectedAnalysis, profile?.xrays ?? []),
    [profile?.xrays, selectedAnalysis]
  );

  async function loadPatients(signal?: AbortSignal) {
    setPatientsError("");
    try {
      const response = await api.listPatients(signal);
      setPatients(response.items);
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) {
        setPatientsError(errorMessage(reason));
      }
    }
  }

  async function loadProfile(patientId: string, signal?: AbortSignal) {
    setWorkspaceError("");
    const next = await api.patientProfile(patientId, signal);
    setProfile(next);
    return next;
  }

  useEffect(() => {
    if (!hasSession()) return;
    const controller = new AbortController();
    setLoading(true);
    Promise.all([api.me(controller.signal), api.listPatients(controller.signal)])
      .then(([currentUser, patientPage]) => {
        setUser(currentUser);
        setPatients(patientPage.items);
      })
      .catch((reason) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          clearSession();
          setPatientsError(errorMessage(reason));
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedPatientId) {
      setProfile(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    loadProfile(selectedPatientId, controller.signal)
      .then((next) => {
        const latest = next.ai_analyses[0] ?? null;
        setSelectedXrayId(latest?.xray_id ?? next.xrays[0]?.id ?? "");
        setSelectedAnalysisId(latest?.id ?? "");
        setShowImagingTools(!latest);
      })
      .catch((reason) => {
        if (!(reason instanceof DOMException && reason.name === "AbortError")) {
          setWorkspaceError(errorMessage(reason));
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [selectedPatientId]);

  useEffect(() => {
    if (
      !selectedPatientId ||
      !selectedAnalysisId ||
      !selectedAnalysis ||
      !["QUEUED", "PROCESSING"].includes(selectedAnalysis.status)
    ) return;

    let stopped = false;
    let timer = 0;
    if (!pollDeadline.current) pollDeadline.current = Date.now() + POLL_TIMEOUT_MS;

    async function poll() {
      if (stopped) return;
      if (Date.now() >= pollDeadline.current) {
        setPollMessage("Polling stopped after 5 minutes. Refresh the patient profile to continue.");
        pollDeadline.current = 0;
        return;
      }
      try {
        const next = await api.patientProfile(selectedPatientId);
        if (stopped) return;
        setProfile(next);
        const current = next.ai_analyses.find((item) => item.id === selectedAnalysisId);
        if (!current || ["QUEUED", "PROCESSING"].includes(current.status)) {
          timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
        } else {
          pollDeadline.current = 0;
          setPollMessage(current.status === "COMPLETED" ? "Analysis completed." : "Analysis failed.");
        }
      } catch (reason) {
        if (!stopped) {
          setPollMessage(errorMessage(reason));
          timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
        }
      }
    }

    timer = window.setTimeout(() => void poll(), POLL_INTERVAL_MS);
    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [selectedPatientId, selectedAnalysisId, selectedAnalysis?.status]);

  function authenticated(currentUser: CurrentUser) {
    setUser(currentUser);
    void loadPatients();
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      clearSession();
    }
    pollDeadline.current = 0;
    setUser(null);
    setPatients([]);
    setSelectedPatientId("");
    setProfile(null);
    setSelectedXrayId("");
    setSelectedAnalysisId("");
    setSection("workspace");
  }

  function choosePatient(patientId: string, destination: AppSection = "workspace") {
    pollDeadline.current = 0;
    setSelectedPatientId(patientId);
    setSelectedAnalysisId("");
    setSection(destination);
  }

  async function uploaded(xray: XRay) {
    setSelectedXrayId(xray.id);
    const next = await loadProfile(xray.patient_id);
    const stored = next.xrays.find((item) => item.id === xray.id);
    if (!stored) {
      setWorkspaceError("Upload succeeded, but the X-ray is not yet visible in the patient profile.");
    }
  }

  async function runAnalysis() {
    if (!selectedXrayId) return;
    setAnalysisBusy(true);
    setWorkspaceError("");
    setPollMessage("");
    try {
      const analysis = await api.createAnalysis(selectedXrayId);
      setSelectedAnalysisId(analysis.id);
      setShowImagingTools(false);
      setSection("workspace");
      pollDeadline.current = Date.now() + POLL_TIMEOUT_MS;
      setProfile((current) => current
        ? {
            ...current,
            ai_analyses: [
              analysis,
              ...current.ai_analyses.filter((item) => item.id !== analysis.id)
            ]
          }
        : current
      );
    } catch (reason) {
      setWorkspaceError(errorMessage(reason));
    } finally {
      setAnalysisBusy(false);
    }
  }

  if (!user) {
    return (
      <>
        <header className="public-header">
          <div className="brand"><span>D</span>DENTAI</div>
          <BackendChecks />
        </header>
        {loading ? <div className="page-loader">Restoring secure session…</div> : <LoginCard onAuthenticated={authenticated} />}
        {patientsError && <div className="floating-error">{patientsError}</div>}
      </>
    );
  }

  const currentDate = new Date().toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric"
  });
  const branchLabel = user.branch_scope.length === 1
    ? "1 assigned branch"
    : `${user.branch_scope.length} assigned branches`;

  const patientSelector = (
    <label className="patient-switcher">
      <span>Patient</span>
      <select
        value={selectedPatientId}
        onChange={(event) => choosePatient(event.target.value, section)}
      >
        <option value="">Select patient…</option>
        {patients.map((patient) => (
          <option key={patient.id} value={patient.id}>{patientName(patient)} · {patient.patient_number}</option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="pro-shell">
      <aside className="pro-nav" aria-label="Primary navigation">
        <div className="pro-brand">
          <span className="pro-brand-mark" aria-hidden="true">D</span>
          <div><strong>DENTAI</strong><small>AI Dental Platform</small></div>
        </div>
        <nav>
          {NAV_ITEMS.map((item) => (
            <button
              className={section === item.value ? "active" : ""}
              key={item.value}
              type="button"
              onClick={() => setSection(item.value)}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              <span>{item.label}</span>
              {item.value === "workspace" && pendingVisibleFindings.length > 0 && (
                <i>{pendingVisibleFindings.length}</i>
              )}
            </button>
          ))}
        </nav>
        <div className="pro-nav-user">
          <span className="avatar">{user.username.slice(0, 2).toUpperCase()}</span>
          <div><strong>{user.username}</strong><small>{user.role}</small></div>
          <button type="button" onClick={() => void logout()} aria-label="Log out">↗</button>
        </div>
      </aside>

      <header className="pro-header">
        <div>
          <strong>{section === "workspace" ? "Clinical AI workspace" : NAV_ITEMS.find((item) => item.value === section)?.label}</strong>
          <span>{profile ? patientName(profile.patient) : "No patient selected"}</span>
        </div>
        <div className="pro-header-actions">
          <div className="header-pill"><span>▥</span><strong>{branchLabel}</strong></div>
          <div className="header-pill"><span>□</span><strong>{currentDate}</strong></div>
          <button className="notification-button" type="button" aria-label="Notifications">♢<i /></button>
        </div>
      </header>

      <main className="pro-main">
        {workspaceError && <div className="error-panel" role="alert">{workspaceError}</div>}
        {loading && <div className="loading-bar" aria-label="Loading" />}

        {section === "workspace" && (
          <>
            <PageTitle
              eyebrow="DENTAI V5"
              title="AI Workspace"
              copy="One focused clinical surface for imaging, AI findings, and clinician review."
              action={patientSelector}
            />

            {!profile ? (
              <section className="patient-picker-grid" aria-label="Choose a patient">
                {patients.map((patient) => (
                  <button key={patient.id} type="button" onClick={() => choosePatient(patient.id)}>
                    <span className="avatar">{patient.first_name.charAt(0)}{patient.last_name.charAt(0)}</span>
                    <span><strong>{patientName(patient)}</strong><small>{patient.patient_number}</small></span>
                    <span>›</span>
                  </button>
                ))}
                {patients.length === 0 && <div className="card empty-inline">No accessible patients.</div>}
              </section>
            ) : (
              <>
                <section className="patient-context-strip">
                  <div className="patient-context-main">
                    <span className="avatar large">{profile.patient.first_name.charAt(0)}{profile.patient.last_name.charAt(0)}</span>
                    <div>
                      <h2>{patientName(profile.patient)}</h2>
                      <p>ID {profile.patient.patient_number} · DOB {dateOnly(profile.patient.date_of_birth)} · {profile.patient.sex || "Sex not recorded"}</p>
                    </div>
                  </div>
                  <div className="patient-context-metrics">
                    <span><strong>{profile.xrays.length}</strong>X-rays</span>
                    <span><strong>{profile.ai_analyses.length}</strong>Analyses</span>
                    <span><strong>{visibleFindings.length}</strong>Findings</span>
                    <span><strong>{pendingVisibleFindings.length}</strong>To review</span>
                  </div>
                  <button className="button button-quiet" type="button" onClick={() => setShowImagingTools((value) => !value)}>
                    {showImagingTools ? "Close imaging" : "+ New X-ray"}
                  </button>
                </section>

                {showImagingTools && (
                  <section className="imaging-drawer card">
                    <div className="imaging-drawer-grid">
                      <XrayUpload patientId={profile.patient.id} onUploaded={uploaded} />
                      <div className="imaging-queue-panel">
                        <div className="section-heading compact-heading">
                          <div><p className="eyebrow">Imaging queue</p><h3>Select a study</h3></div>
                          <span className="count-badge">{profile.xrays.length}</span>
                        </div>
                        <div className="compact-study-list">
                          {profile.xrays.slice(0, 5).map((xray) => (
                            <button
                              className={xray.id === selectedXrayId ? "selected" : ""}
                              key={xray.id}
                              type="button"
                              onClick={() => setSelectedXrayId(xray.id)}
                            >
                              <span className="record-icon">XR</span>
                              <span><strong>{xray.original_filename}</strong><small>{dateOnly(xray.uploaded_at)}</small></span>
                              <StatusBadge value={xray.status} />
                            </button>
                          ))}
                        </div>
                        <AnalysisTimeline analysis={selectedAnalysis} hasXray={Boolean(selectedXrayId)} />
                        <button
                          className="button button-accent wide-button"
                          type="button"
                          disabled={!selectedXrayId || user.role !== "DOCTOR" || analysisBusy}
                          onClick={() => void runAnalysis()}
                        >
                          {analysisBusy ? "Queueing analysis…" : "Run DENTAI V5 Analysis"}
                        </button>
                        {pollMessage && <p className="poll-message" role="status">{pollMessage}</p>}
                      </div>
                    </div>
                  </section>
                )}

                {selectedAnalysis ? (
                  <AnalysisResults
                    analysis={selectedAnalysis}
                    xray={analysisXray}
                    findings={analysisFindings}
                    role={user.role}
                    onReviewed={async () => { await loadProfile(profile.patient.id); }}
                  />
                ) : (
                  <section className="workspace-quiet-state card">
                    <span>✦</span>
                    <div><h3>No analysis selected</h3><p>Open imaging, choose an X-ray, and run DENTAI V5.</p></div>
                    <button className="button button-accent" type="button" onClick={() => setShowImagingTools(true)}>Open imaging</button>
                  </section>
                )}
              </>
            )}
          </>
        )}

        {section === "patients" && (
          <>
            <PageTitle eyebrow="Clinical records" title="Patients" copy="Patient identity and clinical context live here — separate from the AI viewer." />
            {patientsError && <div className="error-panel">{patientsError}</div>}
            <section className="patient-directory">
              {patients.map((patient) => (
                <article className={patient.id === selectedPatientId ? "selected" : ""} key={patient.id}>
                  <span className="avatar large">{patient.first_name.charAt(0)}{patient.last_name.charAt(0)}</span>
                  <div><h3>{patientName(patient)}</h3><p>ID {patient.patient_number}</p></div>
                  <StatusBadge value={patient.status} />
                  <button className="button button-secondary" type="button" onClick={() => choosePatient(patient.id, "workspace")}>Open workspace</button>
                </article>
              ))}
            </section>
          </>
        )}

        {section === "xrays" && (
          <>
            <PageTitle eyebrow="Imaging library" title="X-rays" copy="Upload and manage radiographs without mixing them into clinical history." action={patientSelector} />
            {!profile ? <section className="card empty-inline">Select a patient to view imaging.</section> : (
              <div className="module-two-column">
                <XrayUpload patientId={profile.patient.id} onUploaded={uploaded} />
                <section className="card">
                  <div className="section-heading"><div><p className="eyebrow">Studies</p><h3>Stored X-rays</h3></div><span className="count-badge">{profile.xrays.length}</span></div>
                  <div className="record-grid">
                    {profile.xrays.map((xray) => (
                      <button className={"record-card" + (xray.id === selectedXrayId ? " selected" : "")} key={xray.id} type="button" onClick={() => setSelectedXrayId(xray.id)}>
                        <span className="record-icon">XR</span>
                        <span><strong>{xray.original_filename}</strong><small>{xray.mime_type} · {(xray.size_bytes / 1024 / 1024).toFixed(2)} MB</small></span>
                        <StatusBadge value={xray.status} />
                      </button>
                    ))}
                  </div>
                </section>
              </div>
            )}
          </>
        )}

        {section === "history" && (
          <>
            <PageTitle eyebrow="Longitudinal record" title="History" copy="Previous analyses and visits are kept out of the active AI review surface." action={patientSelector} />
            {!profile ? <section className="card empty-inline">Select a patient to view history.</section> : (
              <div className="history-pro-grid">
                <section className="card">
                  <div className="section-heading"><div><p className="eyebrow">Analysis history</p><h3>Previous AI analyses</h3></div><span className="count-badge">{profile.ai_analyses.length}</span></div>
                  <div className="analysis-table history-analysis-table">
                    {profile.ai_analyses.map((analysis) => (
                      <button
                        className={analysis.id === selectedAnalysisId ? "selected" : ""}
                        key={analysis.id}
                        type="button"
                        onClick={() => {
                          setSelectedAnalysisId(analysis.id);
                          setSelectedXrayId(analysis.xray_id);
                          setSection("workspace");
                        }}
                      >
                        <span><strong>{analysis.model_name}</strong><small>{displayDate(analysis.requested_at)}</small></span>
                        <StatusBadge value={analysis.status} />
                      </button>
                    ))}
                  </div>
                </section>
                <section className="card">
                  <div className="section-heading"><div><p className="eyebrow">Visits</p><h3>Recorded visits</h3></div><span className="count-badge">{profile.visits.length}</span></div>
                  <div className="followup-list">
                    {profile.visits.map((item, index) => (
                      <article key={index}><span className="followup-number">{index + 1}</span><div><strong>{recordStatus(item)}</strong><small>{recordDate(item)}</small></div></article>
                    ))}
                    {profile.visits.length === 0 && <div className="empty-inline">No visits recorded.</div>}
                  </div>
                </section>
              </div>
            )}
          </>
        )}

        {section === "followups" && (
          <>
            <PageTitle eyebrow="Monitoring" title="Follow-ups" copy="Planned monitoring and return visits in a dedicated timeline." action={patientSelector} />
            {!profile ? <section className="card empty-inline">Select a patient to view follow-ups.</section> : (
              <div className="followup-pro-layout">
                <section className="card">
                  <div className="section-heading"><div><p className="eyebrow">Timeline</p><h3>Planned monitoring</h3></div><span className="count-badge">{profile.followups.length}</span></div>
                  <div className="followup-list">
                    {profile.followups.map((item, index) => (
                      <article key={index}><span className="followup-number">{index + 1}</span><div><strong>{recordStatus(item)}</strong><small>{recordDate(item)}</small></div></article>
                    ))}
                    {profile.followups.length === 0 && <div className="empty-inline">No follow-up records are currently stored.</div>}
                  </div>
                </section>
                <div className="followup-summary-grid">
                  <article className="card"><span>Risk</span><strong>{profile.future_risk.length}</strong><small>Future-risk records</small></article>
                  <article className="card"><span>Care</span><strong>{profile.future_care.length}</strong><small>Care timeline items</small></article>
                  <article className="card"><span>Visits</span><strong>{profile.visits.length}</strong><small>Recorded visits</small></article>
                </div>
              </div>
            )}
          </>
        )}

        {section === "outreach" && (
          <>
            <PageTitle eyebrow="Patient communication" title="Outreach" copy="WhatsApp connection, test delivery, and reminder communication belong here." action={patientSelector} />
            {!profile ? <section className="card empty-inline">Select a patient to manage outreach.</section> : (
              <div className="outreach-pro-layout">
                <section className="outreach-intro-card">
                  <div className="outreach-orbit" aria-hidden="true"><span>↗</span><i /><i /></div>
                  <div><p className="eyebrow">Clinic outreach</p><h2>WhatsApp follow-up</h2><p>Connect the clinic sender once, then manage patient reminders from a focused communication surface.</p></div>
                </section>
                <WhatsAppOutreachCard
                  patient={profile.patient}
                  onPatientUpdated={(patient) => {
                    setProfile((current) => current ? { ...current, patient } : current);
                    setPatients((current) => current.map((item) => item.id === patient.id ? patient : item));
                  }}
                />
              </div>
            )}
          </>
        )}

        {section === "settings" && (
          <>
            <PageTitle eyebrow="Workspace settings" title="Settings" copy="System checks and technical context stay outside the clinical workflow." />
            <div className="settings-pro-grid">
              <section className="card technical-card"><div className="section-heading"><div><p className="eyebrow">System status</p><h3>Backend diagnostics</h3></div></div><BackendChecks /></section>
              <section className="card technical-card">
                <div className="section-heading"><div><p className="eyebrow">Access scope</p><h3>Authenticated context</h3></div></div>
                <dl className="technical-definition-grid">
                  <div><dt>Clinic</dt><dd>{user.clinic_id}</dd></div>
                  <div><dt>Role</dt><dd>{user.role}</dd></div>
                  <div><dt>Branch scope</dt><dd>{user.branch_scope.length ? user.branch_scope.join(", ") : "No branches"}</dd></div>
                  <div><dt>Patient</dt><dd>{profile?.patient.id ?? "None selected"}</dd></div>
                </dl>
              </section>
              {profile && <details className="card raw-json technical-fold"><summary>Advanced patient profile data</summary><pre>{JSON.stringify(profile, null, 2)}</pre></details>}
            </div>
          </>
        )}
      </main>

      <footer className="pro-footer">AI-assisted clinical decision support · clinician review required</footer>
    </div>
  );
}
