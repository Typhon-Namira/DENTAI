import { useEffect, useMemo, useRef, useState } from "react";
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

type WorkspaceTab = "overview" | "findings" | "history" | "followups" | "technical";

const WORKSPACE_TABS: Array<{ value: WorkspaceTab; label: string }> = [
  { value: "overview", label: "Overview" },
  { value: "findings", label: "Findings" },
  { value: "history", label: "History" },
  { value: "followups", label: "Follow-ups" },
  { value: "technical", label: "Technical" }
];

function displayDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function patientName(patient: Patient): string {
  return patient.first_name + " " + patient.last_name;
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
      label: analysis?.status === "FAILED" ? "Failed" : "Completed",
      active: analysis?.status === "COMPLETED" || analysis?.status === "FAILED",
      failed: analysis?.status === "FAILED"
    }
  ];

  return (
    <ol className="analysis-timeline" aria-label="Analysis progress">
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
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("overview");
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
        setActiveTab("overview");
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
    setActiveTab("overview");
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
      setActiveTab("findings");
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
        {loading ? (
          <div className="page-loader">Restoring secure session…</div>
        ) : (
          <LoginCard onAuthenticated={authenticated} />
        )}
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

  return (
    <div className="app-shell redesign-shell">
      <aside className="primary-nav" aria-label="Primary navigation">
        <div className="nav-brand">
          <span className="nav-brand-mark" aria-hidden="true">D</span>
          <div><strong>DENTAI</strong><small>AI Dental Platform</small></div>
        </div>
        <nav className="nav-menu">
          <button
            className={activeTab === "overview" ? "active" : ""}
            type="button"
            onClick={() => setActiveTab("overview")}
          ><span>⌂</span>AI Workspace</button>
          <button type="button" onClick={() => setActiveTab("overview")}><span>◎</span>My Patients</button>
          <button
            className={activeTab === "history" ? "active" : ""}
            type="button"
            onClick={() => setActiveTab("history")}
          ><span>▣</span>X-rays</button>
          <button
            className={activeTab === "followups" ? "active" : ""}
            type="button"
            onClick={() => setActiveTab("followups")}
          ><span>↻</span>Follow-ups</button>
          <button
            className={activeTab === "technical" ? "active" : ""}
            type="button"
            onClick={() => setActiveTab("technical")}
          ><span>⚙</span>Settings</button>
        </nav>
        <div className="nav-user-card">
          <span className="avatar">{user.username.slice(0, 2).toUpperCase()}</span>
          <div><strong>{user.username}</strong><small>{user.role}</small></div>
          <button type="button" onClick={() => void logout()} aria-label="Log out">↗</button>
        </div>
      </aside>

      <header className="app-header dashboard-header">
        <div>
          <p className="dashboard-greeting">Good day, {user.username} 👋</p>
          <span>Analyze, review, and plan follow-up care without hunting through technical history.</span>
        </div>
        <div className="dashboard-header-actions">
          <div className="header-pill"><span>▥</span><strong>{branchLabel}</strong></div>
          <div className="header-pill"><span>□</span><strong>{currentDate}</strong></div>
          <button className="notification-button" type="button" aria-label="Notifications">♢<i /></button>
        </div>
      </header>

      <aside className="patient-sidebar" id="patient-list">
        <div className="sidebar-heading">
          <div>
            <p className="eyebrow">My patients</p>
            <h2>Patients</h2>
          </div>
          <span className="count-badge">{patients.length}</span>
        </div>
        {patientsError && <div className="error-panel">{patientsError}</div>}
        <div className="patient-list">
          {patients.map((patient) => (
            <button
              className={"patient-row" + (patient.id === selectedPatientId ? " selected" : "")}
              key={patient.id}
              type="button"
              onClick={() => {
                pollDeadline.current = 0;
                setSelectedPatientId(patient.id);
                setSelectedAnalysisId("");
              }}
            >
              <span className="avatar">{patient.first_name.charAt(0)}{patient.last_name.charAt(0)}</span>
              <span><strong>{patientName(patient)}</strong><small>ID · {patient.patient_number}</small></span>
              <span className="chevron">›</span>
            </button>
          ))}
          {patients.length === 0 && <div className="empty-inline">No accessible patients.</div>}
        </div>
        <div className="sidebar-help">
          <strong>Cleaner workflow</strong>
          <span>Select a patient, then use the tabs to keep findings, history, follow-ups, and technical data separate.</span>
        </div>
      </aside>

      <main className="workspace">
        {!profile ? (
          <section className="dashboard-empty card">
            <div className="dashboard-empty-icon" aria-hidden="true">⌁</div>
            <p className="eyebrow">AI Workspace</p>
            <h1>Select a patient to begin</h1>
            <p>
              The workspace stays intentionally quiet until a patient is selected. Choose a patient from the left to upload an X-ray, review findings, or manage follow-ups.
            </p>
            <div className="empty-stat-row">
              <div><strong>{patients.length}</strong><span>Accessible patients</span></div>
              <div><strong>5</strong><span>Focused workspace tabs</span></div>
              <div><strong>1</strong><span>Clinical task at a time</span></div>
            </div>
          </section>
        ) : (
          <>
            <section className="patient-hero dashboard-patient-hero">
              <div>
                <p className="eyebrow">Patient workspace</p>
                <h1>{patientName(profile.patient)}</h1>
                <div className="patient-facts">
                  <span>ID {profile.patient.patient_number}</span>
                  <span>DOB {dateOnly(profile.patient.date_of_birth)}</span>
                  <span>{profile.patient.sex || "Sex not recorded"}</span>
                  <StatusBadge value={profile.patient.status} />
                </div>
              </div>
              <div className="patient-hero-actions">
                <button className="button button-secondary" type="button" onClick={() => void loadProfile(profile.patient.id)}>
                  Refresh
                </button>
                <button className="button button-accent" type="button" onClick={() => setActiveTab("overview")}>
                  Upload X-ray
                </button>
              </div>
            </section>

            {workspaceError && <div className="error-panel" role="alert">{workspaceError}</div>}
            {loading && <div className="loading-bar" aria-label="Loading" />}

            <section className="workspace-stats" aria-label="Patient summary">
              <article><span className="stat-icon">XR</span><div><strong>{profile.xrays.length}</strong><small>X-rays</small></div></article>
              <article><span className="stat-icon">AI</span><div><strong>{profile.ai_analyses.length}</strong><small>Analyses</small></div></article>
              <article><span className="stat-icon">✓</span><div><strong>{visibleFindings.length}</strong><small>Visible findings</small></div></article>
              <article><span className="stat-icon">↻</span><div><strong>{profile.followups.length}</strong><small>Follow-ups</small></div></article>
            </section>

            <div className="workspace-tabs" role="tablist" aria-label="Patient workspace sections">
              {WORKSPACE_TABS.map((tab) => (
                <button
                  className={activeTab === tab.value ? "active" : ""}
                  key={tab.value}
                  type="button"
                  role="tab"
                  aria-selected={activeTab === tab.value}
                  onClick={() => setActiveTab(tab.value)}
                >
                  {tab.label}
                  {tab.value === "findings" && pendingVisibleFindings.length > 0 && (
                    <span>{pendingVisibleFindings.length}</span>
                  )}
                </button>
              ))}
            </div>

            {activeTab === "overview" && (
              <div className="tab-panel overview-panel" role="tabpanel">
                <div className="overview-grid">
                  <XrayUpload patientId={profile.patient.id} onUploaded={uploaded} />
                  <WhatsAppOutreachCard
                    patient={profile.patient}
                    onPatientUpdated={(patient) => {
                      setProfile((current) => current ? { ...current, patient } : current);
                      setPatients((current) => current.map((item) => item.id === patient.id ? patient : item));
                    }}
                  />
                </div>

                <section className="card imaging-card" id="imaging-card">
                  <div className="section-heading compact-heading">
                    <div><p className="eyebrow">Imaging</p><h3>Choose an X-ray and run analysis</h3></div>
                    <span className="count-badge">{profile.xrays.length}</span>
                  </div>
                  {profile.xrays.length === 0 ? (
                    <div className="empty-inline">Upload the first X-ray for this patient.</div>
                  ) : (
                    <div className="record-grid compact-record-grid">
                      {profile.xrays.slice(0, 6).map((xray) => (
                        <button
                          className={"record-card" + (xray.id === selectedXrayId ? " selected" : "")}
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
                  )}
                  <div className="analysis-action clean-analysis-action">
                    <AnalysisTimeline analysis={selectedAnalysis} hasXray={Boolean(selectedXrayId)} />
                    <button
                      className="button button-accent"
                      type="button"
                      disabled={!selectedXrayId || user.role !== "DOCTOR" || analysisBusy}
                      onClick={() => void runAnalysis()}
                    >
                      {analysisBusy ? "Queueing analysis…" : "Run DENTAI V5 Analysis"}
                    </button>
                    {user.role !== "DOCTOR" && <p className="muted">A Doctor role is required to request analysis.</p>}
                    {pollMessage && <p className="poll-message" role="status">{pollMessage}</p>}
                  </div>
                </section>

                <section className="clinical-note-card">
                  <span aria-hidden="true">◇</span>
                  <div>
                    <strong>Decision-support workspace</strong>
                    <p>Only resolved product-visible findings are shown in the normal clinical view. Technical evidence remains available separately.</p>
                  </div>
                </section>
              </div>
            )}

            {activeTab === "findings" && (
              <div className="tab-panel" role="tabpanel">
                <AnalysisResults
                  analysis={selectedAnalysis}
                  xray={analysisXray}
                  findings={analysisFindings}
                  role={user.role}
                  onReviewed={async () => { await loadProfile(profile.patient.id); }}
                />
              </div>
            )}

            {activeTab === "history" && (
              <div className="tab-panel history-panel" role="tabpanel">
                <section className="card">
                  <div className="section-heading">
                    <div><p className="eyebrow">Analysis history</p><h3>Recent AI analyses</h3></div>
                    <span className="count-badge">{profile.ai_analyses.length}</span>
                  </div>
                  {profile.ai_analyses.length === 0 ? (
                    <div className="empty-inline">No AI analyses for this patient.</div>
                  ) : (
                    <div className="analysis-table history-analysis-table">
                      {profile.ai_analyses.map((analysis) => (
                        <button
                          className={analysis.id === selectedAnalysisId ? "selected" : ""}
                          key={analysis.id}
                          type="button"
                          onClick={() => {
                            setSelectedAnalysisId(analysis.id);
                            setSelectedXrayId(analysis.xray_id);
                            setActiveTab("findings");
                          }}
                        >
                          <span><strong>{analysis.model_name}</strong><small>{displayDate(analysis.requested_at)}</small></span>
                          <span>v{analysis.model_version}</span>
                          <StatusBadge value={analysis.status} />
                        </button>
                      ))}
                    </div>
                  )}
                </section>

                <section className="card">
                  <div className="section-heading">
                    <div><p className="eyebrow">Imaging history</p><h3>Stored X-rays</h3></div>
                    <span className="count-badge">{profile.xrays.length}</span>
                  </div>
                  <div className="record-grid">
                    {profile.xrays.map((xray) => (
                      <button
                        className={"record-card" + (xray.id === selectedXrayId ? " selected" : "")}
                        key={xray.id}
                        type="button"
                        onClick={() => {
                          setSelectedXrayId(xray.id);
                          setActiveTab("overview");
                        }}
                      >
                        <span className="record-icon">XR</span>
                        <span><strong>{xray.original_filename}</strong><small>{xray.mime_type} · {(xray.size_bytes / 1024 / 1024).toFixed(2)} MB</small></span>
                        <StatusBadge value={xray.status} />
                      </button>
                    ))}
                  </div>
                </section>
              </div>
            )}

            {activeTab === "followups" && (
              <div className="tab-panel followup-panel" role="tabpanel">
                <section className="card">
                  <div className="section-heading">
                    <div><p className="eyebrow">Follow-up timeline</p><h3>Planned monitoring and return visits</h3></div>
                    <span className="count-badge">{profile.followups.length}</span>
                  </div>
                  {profile.followups.length === 0 ? (
                    <div className="empty-inline">No follow-up records are currently stored for this patient.</div>
                  ) : (
                    <div className="followup-list">
                      {profile.followups.map((item, index) => (
                        <article key={index}>
                          <span className="followup-number">{index + 1}</span>
                          <div><strong>{recordStatus(item)}</strong><small>{recordDate(item)}</small></div>
                        </article>
                      ))}
                    </div>
                  )}
                </section>
                <div className="followup-summary-grid">
                  <article className="card"><span>Risk</span><strong>{profile.future_risk.length}</strong><small>Stored future-risk records</small></article>
                  <article className="card"><span>Care</span><strong>{profile.future_care.length}</strong><small>Planned care timeline items</small></article>
                  <article className="card"><span>Visits</span><strong>{profile.visits.length}</strong><small>Recorded visits</small></article>
                </div>
              </div>
            )}

            {activeTab === "technical" && (
              <div className="tab-panel technical-panel" role="tabpanel">
                <section className="card technical-card">
                  <div className="section-heading">
                    <div><p className="eyebrow">System status</p><h3>Backend and tenant diagnostics</h3></div>
                  </div>
                  <BackendChecks />
                </section>
                <section className="card technical-card">
                  <div className="section-heading">
                    <div><p className="eyebrow">Access scope</p><h3>Authenticated context</h3></div>
                  </div>
                  <dl className="technical-definition-grid">
                    <div><dt>Clinic</dt><dd>{user.clinic_id}</dd></div>
                    <div><dt>Role</dt><dd>{user.role}</dd></div>
                    <div><dt>Branch scope</dt><dd>{user.branch_scope.length ? user.branch_scope.join(", ") : "No branches"}</dd></div>
                    <div><dt>Patient ID</dt><dd>{profile.patient.id}</dd></div>
                    <div><dt>Selected analysis</dt><dd>{selectedAnalysis?.id ?? "None"}</dd></div>
                    <div><dt>Selected X-ray</dt><dd>{selectedXrayId || "None"}</dd></div>
                  </dl>
                </section>
                <details className="card raw-json technical-fold">
                  <summary>Raw patient profile JSON</summary>
                  <pre>{JSON.stringify(profile, null, 2)}</pre>
                </details>
              </div>
            )}
          </>
        )}
      </main>

      <footer className="clinical-footer">
        AI-assisted clinical decision support. Findings require clinician review.
      </footer>
    </div>
  );
}
