import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import {
  Archive,
  CalendarClock,
  Check,
  ChevronRight,
  CircleUserRound,
  Download,
  FileImage,
  Folder,
  FolderOpen,
  HeartPulse,
  Mail,
  MessageCircle,
  MoreHorizontal,
  Phone,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  UserRound,
  X,
} from "lucide-react";

import { API_BASE_URL, api, errorMessage } from "../api/client";
import {
  productApi,
  type BranchSummary,
  type CareConversation,
  type CareMessage,
  type CarePlan,
  type CarePlanItem,
  type CareSettings,
  type PatientCreateInput,
} from "../api/product";
import type { Patient, PatientProfile, XRay } from "../api/types";
import { dashboardFinding, dashboardLocale, dashboardStatus, type DashboardLang } from "./dashboardI18n";
import "./clinical-workspace-redesign.css";

type Mode = "patients" | "plans" | "messages";
type Lang = DashboardLang;

const COPY = {
  en: {
    patients: "Patient drive",
    patientsLead: "One folder per patient. Open a folder to view identity and OPG files side by side.",
    folders: "Patient folders",
    searchPatients: "Search patient folders",
    newPatient: "New patient",
    folderEmpty: "No patient folders match your search.",
    selectFolder: "Open a patient folder",
    selectFolderLead: "Choose a patient from the folder list to open the clinical workspace.",
    patientDetails: "Patient details",
    opgFiles: "OPG files",
    opgFilesLead: "Uploaded OPG studies for this patient",
    patientNumber: "Patient ID",
    dateOfBirth: "Date of birth",
    sex: "Sex",
    phone: "Phone",
    whatsapp: "WhatsApp",
    email: "Email",
    status: "Status",
    created: "Created",
    files: "files",
    download: "Download",
    delete: "Delete",
    deleteUnavailable: "X-ray deletion is not exposed by the current API. No backend was changed.",
    noOpg: "No OPG files have been uploaded for this patient.",
    openAnalysis: "Open in OPG + AI",
    close: "Close",
    create: "Create patient",
    firstName: "First name",
    lastName: "Last name",
    branch: "Branch",
    followups: "Follow-up workspace",
    followupsLead: "A clear clinical sequence: review the case, confirm dates, then approve outreach.",
    searchCases: "Search follow-up cases",
    noCases: "No follow-up cases found.",
    selectCase: "Select a follow-up case",
    selectCaseLead: "Choose a patient on the left to review the care sequence.",
    caseOverview: "Case overview",
    sequence: "Tooth sequence",
    nextAction: "Next action",
    approve: "Approve outreach",
    reject: "Reject",
    pause: "Pause",
    resume: "Resume",
    complete: "Complete plan",
    markDone: "Done",
    stepReview: "Review",
    stepSchedule: "Schedule",
    stepOutreach: "Outreach",
    stepComplete: "Complete",
    targetDate: "Follow-up date",
    conversations: "Conversations",
    conversationsLead: "Patient WhatsApp conversations in a familiar, focused workspace.",
    searchChats: "Search conversations",
    noChats: "No patient conversations yet.",
    chooseChat: "Choose a conversation",
    chooseChatLead: "Select a patient from the conversation list.",
    patient: "Patient",
    ai: "Teta2",
    refresh: "Refresh",
    loading: "Loading…",
  },
  hy: {
    patients: "Պացիենտների պահոց",
    patientsLead: "Յուրաքանչյուր պացիենտ՝ առանձին թղթապանակով։ Բացեք թղթապանակը՝ տվյալներն ու OPG ֆայլերը կողք կողքի տեսնելու համար։",
    folders: "Պացիենտների թղթապանակներ",
    searchPatients: "Փնտրել պացիենտներին",
    newPatient: "Նոր պացիենտ",
    folderEmpty: "Համապատասխան պացիենտ չի գտնվել։",
    selectFolder: "Բացեք պացիենտի թղթապանակը",
    selectFolderLead: "Ձախ ցանկից ընտրեք պացիենտին։",
    patientDetails: "Պացիենտի տվյալներ",
    opgFiles: "OPG ֆայլեր",
    opgFilesLead: "Այս պացիենտի վերբեռնված OPG պատկերները",
    patientNumber: "Պացիենտի համար",
    dateOfBirth: "Ծննդյան ամսաթիվ",
    sex: "Սեռ",
    phone: "Հեռախոս",
    whatsapp: "WhatsApp",
    email: "Էլ․ փոստ",
    status: "Կարգավիճակ",
    created: "Ստեղծված է",
    files: "ֆայլ",
    download: "Ներբեռնել",
    delete: "Ջնջել",
    deleteUnavailable: "OPG-ի ջնջման endpoint ներկայիս API-ում չկա։ Backend-ը չի փոփոխվել։",
    noOpg: "Այս պացիենտի համար OPG դեռ չի վերբեռնվել։",
    openAnalysis: "Բացել OPG + ԱԲ-ում",
    close: "Փակել",
    create: "Ստեղծել պացիենտ",
    firstName: "Անուն",
    lastName: "Ազգանուն",
    branch: "Մասնաճյուղ",
    followups: "Հետագա հսկողություն",
    followupsLead: "Պարզ հերթականություն՝ վերանայել, հաստատել ամսաթվերը և հետո հաստատել կապը պացիենտի հետ։",
    searchCases: "Փնտրել հսկողության դեպքերը",
    noCases: "Հսկողության դեպքեր չեն գտնվել։",
    selectCase: "Ընտրեք հսկողության դեպքը",
    selectCaseLead: "Ձախ կողմից ընտրեք պացիենտին։",
    caseOverview: "Դեպքի ամփոփում",
    sequence: "Ատամների հերթականություն",
    nextAction: "Հաջորդ քայլ",
    approve: "Հաստատել կապը",
    reject: "Մերժել",
    pause: "Դադարեցնել",
    resume: "Շարունակել",
    complete: "Ավարտել պլանը",
    markDone: "Կատարված է",
    stepReview: "Վերանայում",
    stepSchedule: "Ժամանակացույց",
    stepOutreach: "Կապ",
    stepComplete: "Ավարտ",
    targetDate: "Հսկողության ամսաթիվ",
    conversations: "Զրույցներ",
    conversationsLead: "Պացիենտների WhatsApp զրույցները՝ պարզ ու ծանոթ միջավայրում։",
    searchChats: "Փնտրել զրույցներում",
    noChats: "Պացիենտների զրույցներ դեռ չկան։",
    chooseChat: "Ընտրեք զրույցը",
    chooseChatLead: "Ձախ ցանկից ընտրեք պացիենտին։",
    patient: "Պացիենտ",
    ai: "Teta2",
    refresh: "Թարմացնել",
    loading: "Բեռնվում է…",
  },
  ru: {
    patients: "Карты пациентов",
    patientsLead: "Каждый пациент — отдельная папка. Откройте ее, чтобы видеть данные и ОПТГ рядом.",
    folders: "Папки пациентов",
    searchPatients: "Поиск пациентов",
    newPatient: "Новый пациент",
    folderEmpty: "Подходящих пациентов не найдено.",
    selectFolder: "Откройте папку пациента",
    selectFolderLead: "Выберите пациента в списке слева.",
    patientDetails: "Данные пациента",
    opgFiles: "Файлы ОПТГ",
    opgFilesLead: "Загруженные ОПТГ этого пациента",
    patientNumber: "ID пациента",
    dateOfBirth: "Дата рождения",
    sex: "Пол",
    phone: "Телефон",
    whatsapp: "WhatsApp",
    email: "Email",
    status: "Статус",
    created: "Создан",
    files: "файлов",
    download: "Скачать",
    delete: "Удалить",
    deleteUnavailable: "Удаление ОПТГ не доступно в текущем API. Backend не изменялся.",
    noOpg: "Для этого пациента еще нет загруженных ОПТГ.",
    openAnalysis: "Открыть в ОПТГ + ИИ",
    close: "Закрыть",
    create: "Создать пациента",
    firstName: "Имя",
    lastName: "Фамилия",
    branch: "Филиал",
    followups: "Планы наблюдения",
    followupsLead: "Понятный процесс: проверьте случай, подтвердите даты и затем одобрите связь с пациентом.",
    searchCases: "Поиск случаев",
    noCases: "Случаи наблюдения не найдены.",
    selectCase: "Выберите случай наблюдения",
    selectCaseLead: "Выберите пациента слева.",
    caseOverview: "Обзор случая",
    sequence: "Последовательность зубов",
    nextAction: "Следующее действие",
    approve: "Одобрить связь",
    reject: "Отклонить",
    pause: "Приостановить",
    resume: "Возобновить",
    complete: "Завершить план",
    markDone: "Готово",
    stepReview: "Проверка",
    stepSchedule: "Расписание",
    stepOutreach: "Связь",
    stepComplete: "Завершение",
    targetDate: "Дата наблюдения",
    conversations: "Диалоги",
    conversationsLead: "WhatsApp-диалоги с пациентами в простом и знакомом интерфейсе.",
    searchChats: "Поиск диалогов",
    noChats: "Диалогов с пациентами пока нет.",
    chooseChat: "Выберите диалог",
    chooseChatLead: "Выберите пациента слева.",
    patient: "Пациент",
    ai: "Teta2",
    refresh: "Обновить",
    loading: "Загрузка…",
  },
} as const;

function currentLang(): Lang {
  const value = localStorage.getItem("teta2-product-language");
  return value === "hy" || value === "ru" ? value : "en";
}

function patientName(patient: Patient) {
  return `${patient.first_name} ${patient.last_name}`.trim();
}

function initials(patient: Patient) {
  return `${patient.first_name[0] ?? ""}${patient.last_name[0] ?? ""}`.toUpperCase();
}

function fmt(value: string | null | undefined, lang: Lang, time = true) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(dashboardLocale(lang), {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...(time ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function dateParts(value: string, timeZone: string): Record<string, string> {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(value));
  return Object.fromEntries(parts.map((part) => [part.type, part.value]));
}

function clinicInputValue(value: string | null | undefined, timeZone: string): string {
  if (!value) return "";
  const p = dateParts(value, timeZone);
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
}

function zoneOffsetMs(at: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(at);
  const p = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return Date.UTC(
    Number(p.year),
    Number(p.month) - 1,
    Number(p.day),
    Number(p.hour),
    Number(p.minute),
    Number(p.second),
  ) - at.getTime();
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

function bytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "—";
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function detectMode(main: HTMLElement): Mode | null {
  if (main.querySelector(".patients-page")) return "patients";
  if (main.querySelector(".plan-list")) return "plans";
  if (main.querySelector(".chat-workspace")) return "messages";
  return null;
}

function WorkspaceFrame({ title, lead, children }: { title: string; lead: string; children: React.ReactNode }) {
  return (
    <div className="cwr-page">
      <header className="cwr-page-head">
        <div>
          <h1>{title}</h1>
          <p>{lead}</p>
        </div>
      </header>
      {children}
    </div>
  );
}

function EmptyState({ icon, title, lead }: { icon: React.ReactNode; title: string; lead: string }) {
  return (
    <div className="cwr-empty">
      <span>{icon}</span>
      <strong>{title}</strong>
      <p>{lead}</p>
    </div>
  );
}

function NewPatientModal({ lang, branches, onClose, onCreated }: { lang: Lang; branches: BranchSummary[]; onClose: () => void; onCreated: (patient: Patient) => void }) {
  const c = COPY[lang];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState<PatientCreateInput>({
    patient_number: "",
    first_name: "",
    last_name: "",
    branch_id: branches[0]?.id ?? "",
    phone: null,
    whatsapp_phone: null,
    email: null,
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const patient = await productApi.createPatient(form);
      onCreated(patient);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <div className="cwr-modal-backdrop" role="dialog" aria-modal="true">
      <form className="cwr-modal" onSubmit={submit}>
        <header><div><small>{c.newPatient}</small><h2>{c.create}</h2></div><button type="button" onClick={onClose}><X /></button></header>
        <div className="cwr-form-grid">
          <label>{c.patientNumber}<input required value={form.patient_number} onChange={(e) => setForm((x) => ({ ...x, patient_number: e.target.value }))} /></label>
          <label>{c.branch}<select required value={form.branch_id} onChange={(e) => setForm((x) => ({ ...x, branch_id: e.target.value }))}>{branches.map((branch) => <option value={branch.id} key={branch.id}>{branch.name}</option>)}</select></label>
          <label>{c.firstName}<input required value={form.first_name} onChange={(e) => setForm((x) => ({ ...x, first_name: e.target.value }))} /></label>
          <label>{c.lastName}<input required value={form.last_name} onChange={(e) => setForm((x) => ({ ...x, last_name: e.target.value }))} /></label>
          <label>{c.phone}<input value={form.phone ?? ""} onChange={(e) => setForm((x) => ({ ...x, phone: e.target.value || null }))} /></label>
          <label>{c.whatsapp}<input value={form.whatsapp_phone ?? ""} onChange={(e) => setForm((x) => ({ ...x, whatsapp_phone: e.target.value || null }))} /></label>
          <label className="wide">{c.email}<input type="email" value={form.email ?? ""} onChange={(e) => setForm((x) => ({ ...x, email: e.target.value || null }))} /></label>
        </div>
        {error && <div className="cwr-error">{error}</div>}
        <footer><button type="button" className="cwr-secondary" onClick={onClose}>{c.close}</button><button className="cwr-primary" disabled={busy}>{busy ? c.loading : c.create}</button></footer>
      </form>
    </div>,
    document.body,
  );
}

function PatientsWorkspace({ lang }: { lang: Lang }) {
  const c = COPY[lang];
  const [patients, setPatients] = useState<Patient[]>([]);
  const [branches, setBranches] = useState<BranchSummary[]>([]);
  const [selected, setSelected] = useState("");
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState("");

  const loadPatients = useCallback(async () => {
    setLoading(true);
    try {
      const [page, branchRows] = await Promise.all([api.listPatients(undefined, "ALL"), productApi.branches()]);
      setPatients(page.items);
      setBranches(branchRows);
      setSelected((value) => value || page.items[0]?.id || "");
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadPatients(); }, [loadPatients]);
  useEffect(() => {
    if (!selected) { setProfile(null); return; }
    let active = true;
    void api.patientProfile(selected).then((value) => { if (active) setProfile(value); }).catch((reason) => setError(errorMessage(reason)));
    return () => { active = false; };
  }, [selected]);

  const visible = useMemo(() => patients.filter((patient) => `${patientName(patient)} ${patient.patient_number} ${patient.phone ?? ""}`.toLowerCase().includes(query.trim().toLowerCase())), [patients, query]);

  async function downloadXray(xray: XRay) {
    try {
      const response = await api.xrayDownload(xray.id);
      const href = /^https?:\/\//i.test(response.url) ? response.url : `${API_BASE_URL}${response.url}`;
      window.open(href, "_blank", "noopener,noreferrer");
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  return (
    <WorkspaceFrame title={c.patients} lead={c.patientsLead}>
      <div className="cwr-drive-toolbar">
        <label><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={c.searchPatients} /></label>
        <button className="cwr-primary" onClick={() => setCreating(true)}><Plus />{c.newPatient}</button>
      </div>
      {error && <div className="cwr-error">{error}<button onClick={() => setError("")}><X /></button></div>}
      {notice && <div className="cwr-notice">{notice}<button onClick={() => setNotice("")}><X /></button></div>}
      <div className="cwr-drive">
        <aside className="cwr-folders">
          <div className="cwr-section-label"><Folder />{c.folders}<span>{visible.length}</span></div>
          <div className="cwr-folder-list">
            {loading ? <div className="cwr-loading">{c.loading}</div> : visible.length ? visible.map((patient) => (
              <button key={patient.id} className={selected === patient.id ? "active" : ""} onClick={() => setSelected(patient.id)}>
                <span className="cwr-folder-icon">{selected === patient.id ? <FolderOpen /> : <Folder />}</span>
                <div><strong>{patientName(patient)}</strong><small>{patient.patient_number}</small></div>
                <ChevronRight />
              </button>
            )) : <div className="cwr-list-empty">{c.folderEmpty}</div>}
          </div>
        </aside>
        <section className="cwr-drive-content">
          {!profile ? <EmptyState icon={<FolderOpen />} title={c.selectFolder} lead={c.selectFolderLead} /> : (
            <div className="cwr-patient-folder">
              <section className="cwr-patient-profile">
                <div className="cwr-profile-hero">
                  <span>{initials(profile.patient)}</span>
                  <div><small>{c.patientDetails}</small><h2>{patientName(profile.patient)}</h2><p>{profile.patient.patient_number}</p></div>
                </div>
                <dl>
                  <div><dt>{c.patientNumber}</dt><dd>{profile.patient.patient_number}</dd></div>
                  <div><dt>{c.dateOfBirth}</dt><dd>{fmt(profile.patient.date_of_birth, lang, false)}</dd></div>
                  <div><dt>{c.sex}</dt><dd>{profile.patient.sex || "—"}</dd></div>
                  <div><dt>{c.status}</dt><dd>{dashboardStatus(profile.patient.status, lang)}</dd></div>
                  <div><dt>{c.phone}</dt><dd>{profile.patient.phone || "—"}</dd></div>
                  <div><dt>{c.whatsapp}</dt><dd>{profile.patient.whatsapp_phone || "—"}</dd></div>
                  <div className="wide"><dt>{c.email}</dt><dd>{profile.patient.email || "—"}</dd></div>
                  <div className="wide"><dt>{c.created}</dt><dd>{fmt(profile.patient.created_at, lang)}</dd></div>
                </dl>
                <div className="cwr-profile-stats">
                  <div><FileImage /><strong>{profile.xrays.length}</strong><small>OPG</small></div>
                  <div><Sparkles /><strong>{profile.ai_analyses.length}</strong><small>AI</small></div>
                  <div><HeartPulse /><strong>{profile.followups.length}</strong><small>Follow-up</small></div>
                </div>
              </section>
              <section className="cwr-opg-explorer">
                <header><div><small>{c.opgFiles}</small><h3>{profile.xrays.length} {c.files}</h3><p>{c.opgFilesLead}</p></div><button className="cwr-secondary" onClick={() => document.querySelector<HTMLButtonElement>('.care-sidebar nav button[aria-label*="OPG"], .care-sidebar nav button[aria-label*="ОПТГ"]')?.click()}><Sparkles />{c.openAnalysis}</button></header>
                <div className="cwr-file-grid">
                  {profile.xrays.length ? [...profile.xrays].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at)).map((xray) => (
                    <article className="cwr-file" key={xray.id}>
                      <div className="cwr-file-preview"><FileImage /></div>
                      <div className="cwr-file-meta"><strong title={xray.original_filename}>{xray.original_filename}</strong><small>{fmt(xray.uploaded_at, lang)} · {bytes(xray.size_bytes)}</small><span>{dashboardStatus(xray.status, lang)}</span></div>
                      <div className="cwr-file-actions">
                        <button title={c.download} onClick={() => void downloadXray(xray)}><Download /></button>
                        <button className="danger" title={c.deleteUnavailable} onClick={() => setNotice(c.deleteUnavailable)}><Trash2 /></button>
                      </div>
                    </article>
                  )) : <EmptyState icon={<FileImage />} title={c.opgFiles} lead={c.noOpg} />}
                </div>
              </section>
            </div>
          )}
        </section>
      </div>
      {creating && <NewPatientModal lang={lang} branches={branches} onClose={() => setCreating(false)} onCreated={(patient) => { setCreating(false); setPatients((rows) => [patient, ...rows]); setSelected(patient.id); }} />}
    </WorkspaceFrame>
  );
}

function planStage(plan: CarePlan) {
  if (["COMPLETED", "REJECTED"].includes(plan.status)) return 4;
  if (["ACTIVE", "PAUSED"].includes(plan.status)) return 3;
  if (plan.status === "PENDING_APPROVAL") return 2;
  return 1;
}

function PlansWorkspace({ lang }: { lang: Lang }) {
  const c = COPY[lang];
  const [plans, setPlans] = useState<CarePlan[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selected, setSelected] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [careSettings, setCareSettings] = useState<Record<string, CareSettings>>({});
  const pendingDateSave = useRef<Promise<boolean> | null>(null);

  const reload = useCallback(async () => {
    try {
      const [planRows, patientPage] = await Promise.all([productApi.carePlans(), api.listPatients(undefined, "ALL")]);
      const branchIds = [...new Set(planRows.map((plan) => plan.branch_id))];
      const settingRows = await Promise.all(
        branchIds.map(async (branchId) => [branchId, await productApi.careSettings(branchId)] as const),
      );
      setPlans(planRows);
      setPatients(patientPage.items);
      setCareSettings(Object.fromEntries(settingRows));
      setSelected((value) => value && planRows.some((plan) => plan.id === value) ? value : planRows[0]?.id || "");
    } catch (reason) { setError(errorMessage(reason)); }
  }, []);
  useEffect(() => { void reload(); }, [reload]);

  const named = useMemo(() => plans.map((plan) => ({ plan, patient: patients.find((patient) => patient.id === plan.patient_id) ?? plan.patient ?? null })), [plans, patients]);
  const visible = named.filter(({ plan, patient }) => `${patient ? patientName(patient) : plan.patient_id} ${plan.summary ?? ""} ${plan.status}`.toLowerCase().includes(query.trim().toLowerCase()));
  const current = named.find(({ plan }) => plan.id === selected) ?? null;

  async function action(type: "approve" | "reject" | "pause" | "resume" | "complete") {
    if (!current) return;
    if (type === "approve" && pendingDateSave.current) {
      const saved = await pendingDateSave.current;
      if (!saved) return;
    }
    setBusy(type); setError("");
    try {
      if (type === "approve") {
        const isSequential = current.plan.items.some((item) => (item.sequence_order ?? 0) > 0);
        if (isSequential) await productApi.approveSequentialCarePlan(current.plan.id);
        else await productApi.approveCarePlan(current.plan.id);
      } else {
        await productApi.transitionCarePlan(current.plan.id, type);
      }
      await reload();
    } catch (reason) { setError(errorMessage(reason)); } finally { setBusy(""); }
  }

  async function updateDate(item: CarePlanItem, value: string): Promise<boolean> {
    if (!current || !value) return false;
    setBusy(item.id); setError("");
    try {
      const zone = careSettings[current.plan.branch_id]?.timezone ?? "UTC";
      await productApi.updateCarePlanItem(current.plan.id, item.id, { target_followup_at: clinicLocalToIso(value, zone) });
      await reload();
      return true;
    } catch (reason) {
      setError(errorMessage(reason));
      return false;
    } finally {
      setBusy("");
    }
  }

  function queueDateUpdate(item: CarePlanItem, value: string) {
    const task = updateDate(item, value);
    pendingDateSave.current = task;
    void task.finally(() => {
      if (pendingDateSave.current === task) pendingDateSave.current = null;
    });
  }

  async function completeItem(item: CarePlanItem) {
    if (!current) return;
    setBusy(item.id); setError("");
    try { await productApi.completeCarePlanItem(current.plan.id, item.id); await reload(); }
    catch (reason) { setError(errorMessage(reason)); }
    finally { setBusy(""); }
  }

  const stage = current ? planStage(current.plan) : 1;
  const steps = [c.stepReview, c.stepSchedule, c.stepOutreach, c.stepComplete];

  return (
    <WorkspaceFrame title={c.followups} lead={c.followupsLead}>
      {error && <div className="cwr-error">{error}<button onClick={() => setError("")}><X /></button></div>}
      <div className="cwr-followup-shell">
        <aside className="cwr-case-list">
          <label className="cwr-search"><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={c.searchCases} /></label>
          <div>{visible.length ? visible.map(({ plan, patient }) => (
            <button key={plan.id} className={selected === plan.id ? "active" : ""} onClick={() => setSelected(plan.id)}>
              <span className="cwr-case-avatar">{patient ? initials(patient) : "PT"}</span>
              <div><strong>{patient ? patientName(patient) : plan.patient_id}</strong><small>{plan.items.length} teeth · {dashboardStatus(plan.status, lang)}</small></div>
              <ChevronRight />
            </button>
          )) : <div className="cwr-list-empty">{c.noCases}</div>}</div>
        </aside>
        <section className="cwr-followup-main">
          {!current ? <EmptyState icon={<HeartPulse />} title={c.selectCase} lead={c.selectCaseLead} /> : <>
            <header className="cwr-case-head">
              <div><small>{c.caseOverview}</small><h2>{current.patient ? patientName(current.patient) : current.plan.patient_id}</h2><p>{current.plan.summary || `${current.plan.items.length} tooth follow-up items`}</p></div>
              <span className={`cwr-status ${current.plan.status.toLowerCase()}`}>{dashboardStatus(current.plan.status, lang)}</span>
            </header>
            <div className="cwr-stepper">{steps.map((label, index) => <div className={stage >= index + 1 ? "done" : ""} key={label}><span>{stage > index + 1 ? <Check /> : index + 1}</span><strong>{label}</strong></div>)}</div>
            <section className="cwr-sequence-card">
              <div className="cwr-sequence-head"><div><small>{c.sequence}</small><h3>{current.plan.items.length} teeth</h3></div><strong>{c.nextAction}: {stage < 3 ? c.approve : current.plan.status === "ACTIVE" ? c.pause : c.resume}</strong></div>
              <div className="cwr-tooth-sequence">
                {[...current.plan.items].sort((a, b) => (a.sequence_order ?? 999) - (b.sequence_order ?? 999)).map((item, index) => (
                  <article key={item.id}>
                    <div className="cwr-tooth-index"><span>{item.tooth_fdi}</span><i>{item.sequence_order ?? index + 1}</i></div>
                    <div className="cwr-tooth-copy"><strong>{dashboardFinding(item.finding_type, lang)}</strong><p>{item.rationale}</p><small>{dashboardStatus(item.status, lang)}{item.priority_level ? ` · ${item.priority_level}` : ""}</small></div>
                    <label>{c.targetDate}<input key={item.target_followup_at} type="datetime-local" disabled={current.plan.status !== "PENDING_APPROVAL" || busy === item.id} defaultValue={clinicInputValue(item.target_followup_at, careSettings[current.plan.branch_id]?.timezone ?? "UTC")} onBlur={(e) => { if (e.target.value) queueDateUpdate(item, e.target.value); }} /></label>
                    {["ACTIVE", "PAUSED"].includes(current.plan.status) && item.status !== "COMPLETED" ? <button className="cwr-secondary compact" disabled={busy === item.id} onClick={() => void completeItem(item)}><Check />{c.markDone}</button> : <span className={`cwr-status ${item.status.toLowerCase()}`}>{dashboardStatus(item.status, lang)}</span>}
                  </article>
                ))}
              </div>
            </section>
            <footer className="cwr-plan-actions">
              {current.plan.status === "PENDING_APPROVAL" && <><button className="cwr-secondary danger" disabled={!!busy} onClick={() => void action("reject")}>{c.reject}</button><button className="cwr-primary" disabled={!!busy} onClick={() => void action("approve")}><Check />{busy ? c.loading : c.approve}</button></>}
              {current.plan.status === "ACTIVE" && <><button className="cwr-secondary" disabled={!!busy} onClick={() => void action("pause")}>{c.pause}</button><button className="cwr-primary" disabled={!!busy} onClick={() => void action("complete")}>{c.complete}</button></>}
              {current.plan.status === "PAUSED" && <button className="cwr-primary" disabled={!!busy} onClick={() => void action("resume")}>{c.resume}</button>}
            </footer>
          </>}
        </section>
      </div>
    </WorkspaceFrame>
  );
}

function ConversationsWorkspace({ lang }: { lang: Lang }) {
  const c = COPY[lang];
  const [conversations, setConversations] = useState<CareConversation[]>([]);
  const [selected, setSelected] = useState("");
  const [messages, setMessages] = useState<CareMessage[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    try {
      const rows = await productApi.careConversations();
      setConversations(rows);
      setSelected((value) => value && rows.some((row) => row.id === value) ? value : rows[0]?.id || "");
    } catch (reason) { setError(errorMessage(reason)); }
  }, []);
  useEffect(() => { void reload(); }, [reload]);
  useEffect(() => {
    if (!selected) { setMessages([]); return; }
    setLoading(true);
    void productApi.careConversationMessages(selected).then(setMessages).catch((reason) => setError(errorMessage(reason))).finally(() => setLoading(false));
  }, [selected]);

  const visible = conversations.filter((row) => `${row.patient ? patientName(row.patient) : row.whatsapp_phone} ${row.summary ?? ""}`.toLowerCase().includes(query.trim().toLowerCase()));
  const current = conversations.find((row) => row.id === selected) ?? null;

  return (
    <WorkspaceFrame title={c.conversations} lead={c.conversationsLead}>
      {error && <div className="cwr-error">{error}<button onClick={() => setError("")}><X /></button></div>}
      <div className="cwr-wa-shell">
        <aside className="cwr-wa-sidebar">
          <header><div><strong>{c.conversations}</strong><button title={c.refresh} onClick={() => void reload()}><RefreshCw /></button></div><label><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={c.searchChats} /></label></header>
          <div className="cwr-wa-list">{visible.length ? visible.map((row) => (
            <button className={selected === row.id ? "active" : ""} key={row.id} onClick={() => setSelected(row.id)}>
              <span className="cwr-wa-avatar">{row.patient ? initials(row.patient) : "PT"}</span>
              <div><div><strong>{row.patient ? patientName(row.patient) : row.whatsapp_phone}</strong><time>{fmt(row.last_message_at, lang)}</time></div><p>{row.summary || row.whatsapp_phone}</p></div>
            </button>
          )) : <div className="cwr-wa-empty">{c.noChats}</div>}</div>
        </aside>
        <section className="cwr-wa-chat">
          {!current ? <EmptyState icon={<MessageCircle />} title={c.chooseChat} lead={c.chooseChatLead} /> : <>
            <header className="cwr-wa-chat-head"><div className="cwr-wa-avatar">{current.patient ? initials(current.patient) : "PT"}</div><div><strong>{current.patient ? patientName(current.patient) : current.whatsapp_phone}</strong><small>{current.whatsapp_phone} · {dashboardStatus(current.status, lang)}</small></div><button><MoreHorizontal /></button></header>
            <div className="cwr-wa-messages">
              {loading ? <div className="cwr-loading">{c.loading}</div> : messages.map((message) => (
                <article key={message.id} className={message.direction === "OUT" ? "out" : "in"}>
                  <p>{message.body}</p>
                  <footer><span>{message.direction === "OUT" ? c.ai : c.patient}</span><time>{fmt(message.created_at, lang)}</time>{message.direction === "OUT" && <Check />}</footer>
                </article>
              ))}
            </div>
            <footer className="cwr-wa-footer"><ShieldCheck /><span>{dashboardStatus(current.status, lang)}</span></footer>
          </>}
        </section>
      </div>
    </WorkspaceFrame>
  );
}

export function ClinicalWorkspaceRedesign() {
  const [host, setHost] = useState<HTMLElement | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [lang, setLang] = useState<Lang>(() => currentLang());

  useEffect(() => {
    const onLanguage = () => setLang(currentLang());
    window.addEventListener("teta2-language-change", onLanguage);
    return () => window.removeEventListener("teta2-language-change", onLanguage);
  }, []);

  useEffect(() => {
    let main: HTMLElement | null = null;
    let observer: MutationObserver | null = null;
    let bodyObserver: MutationObserver | null = null;

    const sync = () => {
      main = document.querySelector<HTMLElement>(".care-main");
      if (!main) { setHost(null); setMode(null); return; }
      const nextMode = detectMode(main);
      setMode(nextMode);
      main.classList.toggle("cwr-active", Boolean(nextMode));
      let nextHost = main.querySelector<HTMLElement>("#teta2-clinical-redesign-host");
      if (nextMode) {
        if (!nextHost) {
          nextHost = document.createElement("div");
          nextHost.id = "teta2-clinical-redesign-host";
          nextHost.className = "cwr-host";
          main.appendChild(nextHost);
        }
        setHost(nextHost);
      } else {
        nextHost?.remove();
        setHost(null);
      }
    };

    const attach = () => {
      const nextMain = document.querySelector<HTMLElement>(".care-main");
      if (!nextMain) return false;
      main = nextMain;
      sync();
      observer = new MutationObserver(sync);
      observer.observe(nextMain, { childList: true });
      return true;
    };

    if (!attach()) {
      bodyObserver = new MutationObserver(() => { if (attach()) bodyObserver?.disconnect(); });
      bodyObserver.observe(document.body, { childList: true, subtree: true });
    }

    return () => {
      observer?.disconnect();
      bodyObserver?.disconnect();
      main?.classList.remove("cwr-active");
      document.getElementById("teta2-clinical-redesign-host")?.remove();
    };
  }, []);

  if (!host || !mode) return null;
  if (mode === "patients") return createPortal(<PatientsWorkspace lang={lang} />, host);
  if (mode === "plans") return createPortal(<PlansWorkspace lang={lang} />, host);
  return createPortal(<ConversationsWorkspace lang={lang} />, host);
}
