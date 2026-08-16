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
import { XrayUpload } from "./components/XrayUpload";

const POLL_INTERVAL_MS = 2_000;
const POLL_TIMEOUT_MS = 5 * 60_000;

function displayDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function patientName(patient: Patient): string {
  return patient.first_name + " " + patient.last_name;
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
    { label: analysis?.status === "FAILED" ? "Failed" : "Completed", active: analysis?.status === "COMPLETED" || analysis?.status === "FAILED", failed: analysis?.status === "FAILED" }
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
        setSelectedXrayId(next.xrays[0]?.id ?? "");
        const latest = next.ai_analyses[0] ?? null;
        setSelectedAnalysisId(latest?.id ?? "");
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
      pollDeadline.current = Date.now() + POLL_TIMEOUT_MS;
      setProfile((current) => current
        ? { ...current, ai_analyses: [analysis, ...current.ai_analyses.filter((item) => item.id !== analysis.id)] }
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

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand"><span>D</span>DENTAI <small>Test Console</small></div>
        <div className="user-summary">
          <div>
            <strong>{user.username}</strong>
            <span>{user.email} · {user.role}</span>
          </div>
          <button className="button button-quiet" type="button" onClick={() => void logout()}>Log out</button>
        </div>
      </header>

      <BackendChecks />

      <aside className="patient-sidebar">
        <div className="sidebar-heading">
          <div>
            <p className="eyebrow">Authorized records</p>
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
              <span><strong>{patientName(patient)}</strong><small>{patient.patient_number}</small></span>
              <span className="chevron">›</span>
            </button>
          ))}
          {patients.length === 0 && <div className="empty-inline">No accessible patients.</div>}
        </div>
        <div className="scope-card">
          <span>Clinic</span><strong>{user.clinic_id}</strong>
          <span>Branch scope</span><strong>{user.branch_scope.length ? user.branch_scope.join(", ") : "No branches"}</strong>
        </div>
      </aside>

      <main className="workspace">
        {!profile ? (
          <section className="card empty-state hero-empty">
            <span className="empty-icon" aria-hidden="true">⌁</span>
            <h1>Select a patient</h1>
            <p>Choose an authorized patient to inspect X-rays, analyses, and findings.</p>
          </section>
        ) : (
          <>
            <section className="patient-hero">
              <div>
                <p className="eyebrow">Patient profile</p>
                <h1>{patientName(profile.patient)}</h1>
                <div className="patient-facts">
                  <span>ID {profile.patient.patient_number}</span>
                  <span>DOB {displayDate(profile.patient.date_of_birth)}</span>
                  <span>{profile.patient.sex || "Sex not recorded"}</span>
                  <StatusBadge value={profile.patient.status} />
                </div>
              </div>
              <button className="button button-secondary" type="button" onClick={() => void loadProfile(profile.patient.id)}>
                Refresh profile
              </button>
            </section>

            {workspaceError && <div className="error-panel" role="alert">{workspaceError}</div>}
            {loading && <div className="loading-bar" aria-label="Loading" />}

            <XrayUpload patientId={profile.patient.id} onUploaded={uploaded} />

            <section className="card">
              <div className="section-heading">
                <div><p className="eyebrow">Imaging</p><h3>X-rays</h3></div>
                <span className="count-badge">{profile.xrays.length}</span>
              </div>
              {profile.xrays.length === 0 ? (
                <div className="empty-inline">No X-rays have been uploaded for this patient.</div>
              ) : (
                <div className="record-grid">
                  {profile.xrays.map((xray) => (
                    <button
                      className={"record-card" + (xray.id === selectedXrayId ? " selected" : "")}
                      key={xray.id}
                      type="button"
                      onClick={() => setSelectedXrayId(xray.id)}
                    >
                      <span className="record-icon">XR</span>
                      <span><strong>{xray.original_filename}</strong><small>{xray.mime_type} · {(xray.size_bytes / 1024 / 1024).toFixed(2)} MB</small></span>
                      <StatusBadge value={xray.status} />
                    </button>
                  ))}
                </div>
              )}

              <div className="analysis-action">
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

            <section className="card">
              <div className="section-heading">
                <div><p className="eyebrow">History</p><h3>AI analyses</h3></div>
                <span className="count-badge">{profile.ai_analyses.length}</span>
              </div>
              {profile.ai_analyses.length === 0 ? (
                <div className="empty-inline">No AI analyses for this patient.</div>
              ) : (
                <div className="analysis-table">
                  {profile.ai_analyses.map((analysis) => (
                    <button
                      className={analysis.id === selectedAnalysisId ? "selected" : ""}
                      key={analysis.id}
                      type="button"
                      onClick={() => setSelectedAnalysisId(analysis.id)}
                    >
                      <span><strong>{analysis.model_name}</strong><small>{displayDate(analysis.requested_at)}</small></span>
                      <span>{analysis.model_version}</span>
                      <StatusBadge value={analysis.status} />
                    </button>
                  ))}
                </div>
              )}
            </section>

            <AnalysisResults
              analysis={selectedAnalysis}
              findings={analysisFindings}
              role={user.role}
              onReviewed={() => loadProfile(profile.patient.id)}
            />
          </>
        )}
      </main>

      <footer className="clinical-footer">
        AI-assisted clinical decision support. Findings require clinician review.
      </footer>
    </div>
  );
}
