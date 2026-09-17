import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import {
  ArrowLeft,
  ChevronRight,
  Download,
  FileImage,
  Folder,
  FolderOpen,
  Home,
  Info,
  Plus,
  Search,
  Trash2,
  UserRound,
  X,
} from "lucide-react";

import { API_BASE_URL, api, authenticatedRequest, errorMessage } from "../api/client";
import { productApi, type BranchSummary, type PatientCreateInput } from "../api/product";
import type { Patient, PatientProfile, XRay } from "../api/types";
import { dashboardLocale, dashboardStatus, type DashboardLang } from "./dashboardI18n";
import { useDashboardLanguage } from "./useDashboardLanguage";
import "./patient-drive-explorer.css";

type Lang = DashboardLang;

const COPY = {
  en: {
    drive: "Patient Drive",
    allPatients: "All patients",
    search: "Search patient folders",
    newPatient: "New patient",
    folders: "patient folders",
    empty: "No patient folders found.",
    details: "Patient information",
    opg: "OPG files",
    files: "files",
    download: "Download",
    delete: "Delete",
    deleting: "Deleting…",
    confirmDelete: "Delete this OPG and its derived AI analysis and care plan? This cannot be undone.",
    noFiles: "This patient has no OPG files yet.",
    patientId: "Patient ID",
    dob: "Date of birth",
    sex: "Sex",
    phone: "Phone",
    whatsapp: "WhatsApp",
    email: "Email",
    status: "Status",
    created: "Created",
    create: "Create patient",
    firstName: "First name",
    lastName: "Last name",
    branch: "Branch",
    close: "Cancel",
  },
  hy: {
    drive: "Պացիենտների պահոց",
    allPatients: "Բոլոր պացիենտները",
    search: "Փնտրել պացիենտի թղթապանակը",
    newPatient: "Նոր պացիենտ",
    folders: "թղթապանակ",
    empty: "Պացիենտների թղթապանակներ չեն գտնվել։",
    details: "Պացիենտի տվյալներ",
    opg: "OPG ֆայլեր",
    files: "ֆայլ",
    download: "Ներբեռնել",
    delete: "Ջնջել",
    deleting: "Ջնջվում է…",
    confirmDelete: "Ջնջե՞լ այս OPG-ն և դրանից ստեղծված ԱԲ վերլուծությունն ու հսկողության պլանը։ Գործողությունը հետարկել հնարավոր չէ։",
    noFiles: "Այս պացիենտի համար OPG ֆայլեր չկան։",
    patientId: "Պացիենտի համար",
    dob: "Ծննդյան ամսաթիվ",
    sex: "Սեռ",
    phone: "Հեռախոս",
    whatsapp: "WhatsApp",
    email: "Էլ․ փոստ",
    status: "Կարգավիճակ",
    created: "Ստեղծվել է",
    create: "Ստեղծել պացիենտ",
    firstName: "Անուն",
    lastName: "Ազգանուն",
    branch: "Մասնաճյուղ",
    close: "Չեղարկել",
  },
  ru: {
    drive: "Карты пациентов",
    allPatients: "Все пациенты",
    search: "Поиск папок пациентов",
    newPatient: "Новый пациент",
    folders: "папок",
    empty: "Папки пациентов не найдены.",
    details: "Данные пациента",
    opg: "Файлы ОПТГ",
    files: "файлов",
    download: "Скачать",
    delete: "Удалить",
    deleting: "Удаление…",
    confirmDelete: "Удалить этот ОПТГ вместе с созданными по нему ИИ-анализом и планом наблюдения? Действие нельзя отменить.",
    noFiles: "У этого пациента пока нет файлов ОПТГ.",
    patientId: "ID пациента",
    dob: "Дата рождения",
    sex: "Пол",
    phone: "Телефон",
    whatsapp: "WhatsApp",
    email: "Email",
    status: "Статус",
    created: "Создан",
    create: "Создать пациента",
    firstName: "Имя",
    lastName: "Фамилия",
    branch: "Филиал",
    close: "Отмена",
  },
} as const;

function patientName(patient: Patient) {
  return `${patient.first_name} ${patient.last_name}`.trim();
}

function initials(patient: Patient) {
  return `${patient.first_name[0] ?? ""}${patient.last_name[0] ?? ""}`.toUpperCase();
}

function formatDate(value: string | null | undefined, lang: Lang, time = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(dashboardLocale(lang), {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...(time ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function fileSize(value: number) {
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function NewPatientDialog({
  lang,
  branches,
  onClose,
  onCreated,
}: {
  lang: Lang;
  branches: BranchSummary[];
  onClose: () => void;
  onCreated: (patient: Patient) => void;
}) {
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
      onCreated(await productApi.createPatient(form));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <div className="pde-dialog-backdrop" role="dialog" aria-modal="true">
      <form className="pde-dialog" onSubmit={submit}>
        <header><h2>{c.create}</h2><button type="button" onClick={onClose}><X /></button></header>
        <div className="pde-form-grid">
          <label>{c.patientId}<input required value={form.patient_number} onChange={(e) => setForm((x) => ({ ...x, patient_number: e.target.value }))} /></label>
          <label>{c.branch}<select required value={form.branch_id} onChange={(e) => setForm((x) => ({ ...x, branch_id: e.target.value }))}>{branches.map((branch) => <option key={branch.id} value={branch.id}>{branch.name}</option>)}</select></label>
          <label>{c.firstName}<input required value={form.first_name} onChange={(e) => setForm((x) => ({ ...x, first_name: e.target.value }))} /></label>
          <label>{c.lastName}<input required value={form.last_name} onChange={(e) => setForm((x) => ({ ...x, last_name: e.target.value }))} /></label>
          <label>{c.phone}<input value={form.phone ?? ""} onChange={(e) => setForm((x) => ({ ...x, phone: e.target.value || null }))} /></label>
          <label>{c.whatsapp}<input value={form.whatsapp_phone ?? ""} onChange={(e) => setForm((x) => ({ ...x, whatsapp_phone: e.target.value || null }))} /></label>
          <label className="wide">{c.email}<input type="email" value={form.email ?? ""} onChange={(e) => setForm((x) => ({ ...x, email: e.target.value || null }))} /></label>
        </div>
        {error && <div className="pde-error">{error}</div>}
        <footer><button type="button" onClick={onClose}>{c.close}</button><button className="primary" disabled={busy}>{busy ? "…" : c.create}</button></footer>
      </form>
    </div>,
    document.body,
  );
}

function PatientDrive({ lang }: { lang: Lang }) {
  const c = COPY[lang];
  const [patients, setPatients] = useState<Patient[]>([]);
  const [branches, setBranches] = useState<BranchSummary[]>([]);
  const [openedId, setOpenedId] = useState("");
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState("");
  const [creating, setCreating] = useState(false);

  const loadPatients = useCallback(async () => {
    setLoading(true);
    try {
      const [page, branchRows] = await Promise.all([
        api.listPatients(undefined, "ALL"),
        productApi.branches(),
      ]);
      setPatients(page.items);
      setBranches(branchRows);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProfile = useCallback(async (patientId: string) => {
    setError("");
    setProfile(await api.patientProfile(patientId));
  }, []);

  useEffect(() => { void loadPatients(); }, [loadPatients]);
  useEffect(() => {
    if (!openedId) { setProfile(null); return; }
    void loadProfile(openedId).catch((reason) => setError(errorMessage(reason)));
  }, [loadProfile, openedId]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return patients.filter((patient) =>
      `${patientName(patient)} ${patient.patient_number} ${patient.phone ?? ""}`
        .toLowerCase()
        .includes(needle),
    );
  }, [patients, query]);

  async function downloadXray(xray: XRay) {
    try {
      const response = await api.xrayDownload(xray.id);
      const href = /^https?:\/\//i.test(response.url) ? response.url : `${API_BASE_URL}${response.url}`;
      window.open(href, "_blank", "noopener,noreferrer");
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }

  async function deleteXray(xray: XRay) {
    if (!window.confirm(c.confirmDelete)) return;
    setDeleting(xray.id);
    setError("");
    try {
      await authenticatedRequest<void>(`/api/v1/xrays/${encodeURIComponent(xray.id)}`, { method: "DELETE" });
      if (openedId) await loadProfile(openedId);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setDeleting("");
    }
  }

  const openedPatient = profile?.patient ?? patients.find((patient) => patient.id === openedId) ?? null;

  return (
    <div className="pde-window">
      <div className="pde-titlebar"><strong>{c.drive}</strong><span>{patients.length} {c.folders}</span></div>
      <div className="pde-commandbar">
        <button className="pde-icon-button" disabled={!openedId} onClick={() => setOpenedId("")} title={c.allPatients}><ArrowLeft /></button>
        <div className="pde-address">
          <Home />
          <span>{c.drive}</span>
          {openedPatient && <><ChevronRight /><strong>{patientName(openedPatient)}</strong></>}
        </div>
        <label className="pde-search"><Search /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={c.search} /></label>
        <button className="pde-new" onClick={() => setCreating(true)}><Plus />{c.newPatient}</button>
      </div>

      {error && <div className="pde-error">{error}<button onClick={() => setError("")}><X /></button></div>}

      {!openedId ? (
        <main className="pde-folder-view">
          <header><strong>{c.allPatients}</strong><span>{visible.length} {c.folders}</span></header>
          {loading ? <div className="pde-loading">…</div> : visible.length ? (
            <div className="pde-folder-grid">
              {visible.map((patient) => (
                <button key={patient.id} className="pde-folder" onDoubleClick={() => setOpenedId(patient.id)} onClick={() => setOpenedId(patient.id)}>
                  <Folder />
                  <span><strong>{patientName(patient)}</strong><small>{patient.patient_number}</small></span>
                </button>
              ))}
            </div>
          ) : <div className="pde-empty"><FolderOpen /><p>{c.empty}</p></div>}
        </main>
      ) : profile ? (
        <main className="pde-open-folder">
          <section className="pde-patient-pane">
            <div className="pde-profile-head"><span>{initials(profile.patient)}</span><div><small>{c.details}</small><h2>{patientName(profile.patient)}</h2><p>{profile.patient.patient_number}</p></div></div>
            <dl>
              <div><dt>{c.patientId}</dt><dd>{profile.patient.patient_number}</dd></div>
              <div><dt>{c.dob}</dt><dd>{formatDate(profile.patient.date_of_birth, lang)}</dd></div>
              <div><dt>{c.sex}</dt><dd>{profile.patient.sex || "—"}</dd></div>
              <div><dt>{c.status}</dt><dd>{dashboardStatus(profile.patient.status, lang)}</dd></div>
              <div><dt>{c.phone}</dt><dd>{profile.patient.phone || "—"}</dd></div>
              <div><dt>{c.whatsapp}</dt><dd>{profile.patient.whatsapp_phone || "—"}</dd></div>
              <div className="wide"><dt>{c.email}</dt><dd>{profile.patient.email || "—"}</dd></div>
              <div className="wide"><dt>{c.created}</dt><dd>{formatDate(profile.patient.created_at, lang, true)}</dd></div>
            </dl>
          </section>

          <section className="pde-files-pane">
            <header><div><FileImage /><span><strong>{c.opg}</strong><small>{profile.xrays.length} {c.files}</small></span></div></header>
            {profile.xrays.length ? (
              <div className="pde-file-grid">
                {[...profile.xrays].sort((a, b) => b.uploaded_at.localeCompare(a.uploaded_at)).map((xray) => (
                  <article className="pde-file" key={xray.id}>
                    <button className="pde-file-open" onClick={() => void downloadXray(xray)}>
                      <span className="pde-file-icon"><FileImage /></span>
                      <strong title={xray.original_filename}>{xray.original_filename}</strong>
                      <small>{formatDate(xray.uploaded_at, lang, true)} · {fileSize(xray.size_bytes)}</small>
                    </button>
                    <div className="pde-file-actions">
                      <button title={c.download} onClick={() => void downloadXray(xray)}><Download /></button>
                      <button className="danger" disabled={deleting === xray.id} title={c.delete} onClick={() => void deleteXray(xray)}><Trash2 /></button>
                    </div>
                  </article>
                ))}
              </div>
            ) : <div className="pde-empty"><FileImage /><p>{c.noFiles}</p></div>}
          </section>
        </main>
      ) : <div className="pde-loading">…</div>}

      <div className="pde-statusbar"><Info /><span>{openedPatient ? patientName(openedPatient) : `${visible.length} ${c.folders}`}</span></div>

      {creating && <NewPatientDialog lang={lang} branches={branches} onClose={() => setCreating(false)} onCreated={(patient) => { setCreating(false); setPatients((rows) => [patient, ...rows]); setOpenedId(patient.id); }} />}
    </div>
  );
}

export function PatientDriveExplorer() {
  const lang = useDashboardLanguage();
  const [host, setHost] = useState<HTMLElement | null>(null);

  useEffect(() => {
    let main: HTMLElement | null = null;
    let observer: MutationObserver | null = null;

    const sync = () => {
      main = document.querySelector<HTMLElement>(".care-main");
      if (!main) { setHost(null); return; }
      const patientsActive = Boolean(main.querySelector(".patients-page"));
      main.classList.toggle("pde-active", patientsActive);
      let mount = main.querySelector<HTMLElement>("#teta2-patient-drive-host");
      if (!patientsActive) {
        mount?.remove();
        setHost(null);
        return;
      }
      if (!mount) {
        mount = document.createElement("div");
        mount.id = "teta2-patient-drive-host";
        main.appendChild(mount);
      }
      setHost(mount);
    };

    sync();
    const root = document.querySelector<HTMLElement>(".care-main");
    if (root) {
      observer = new MutationObserver(sync);
      observer.observe(root, { childList: true });
    }
    return () => {
      observer?.disconnect();
      main?.classList.remove("pde-active");
      document.getElementById("teta2-patient-drive-host")?.remove();
    };
  }, []);

  return host ? createPortal(<PatientDrive lang={lang} />, host) : null;
}
