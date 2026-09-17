import { useCallback, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  Activity,
  CheckCircle2,
  Clock3,
  KeyRound,
  Mail,
  MessageCircle,
  Phone,
  QrCode,
  RefreshCw,
  ShieldCheck,
  Smartphone,
  UserRound,
  X,
} from "lucide-react";

import { api, errorMessage } from "../api/client";
import type { CurrentUser, WhatsAppConnection } from "../api/types";
import { WHATSAPP_QR_POLL_MS } from "../utils/whatsapp";
import { dashboardRole } from "./dashboardI18n";
import { useDashboardLanguage } from "./useDashboardLanguage";
import "./settings-workspace.css";

type Lang = "en" | "hy" | "ru";

const COPY = {
  en: {
    eyebrow: "CLINIC SETTINGS",
    title: "Workspace settings",
    lead: "Manage your account, subscription, security and clinic WhatsApp connection in one place.",
    account: "Account",
    accountLead: "Signed-in clinic user",
    username: "Username",
    email: "Email",
    role: "Role",
    subscription: "Subscription",
    plan: "Plan",
    status: "Status",
    expires: "Expires",
    whatsapp: "Clinic WhatsApp",
    whatsappLead: "Connect the WhatsApp account used by Teta2 for patient follow-up messages.",
    connected: "Connected",
    disconnected: "Not connected",
    sender: "Connected number",
    connectionState: "Connection state",
    connect: "Connect with QR",
    disconnect: "Disconnect",
    refresh: "Refresh status",
    scanTitle: "Connect clinic WhatsApp",
    scanLead: "Open WhatsApp on the clinic phone and scan this QR code.",
    steps: "WhatsApp → Linked devices → Link a device",
    generating: "Generating QR code…",
    close: "Close",
    safety: "Only the real clinic WhatsApp connection reported by the server is shown here.",
    security: "Security",
    billing: "Subscription & billing",
  },
  hy: {
    eyebrow: "ԿԼԻՆԻԿԱՅԻ ԿԱՐԳԱՎՈՐՈՒՄՆԵՐ",
    title: "Աշխատանքային միջավայրի կարգավորումներ",
    lead: "Կառավարեք հաշիվը, բաժանորդագրությունը, անվտանգությունն ու կլինիկայի WhatsApp կապը մեկ տեղում։",
    account: "Հաշիվ",
    accountLead: "Մուտք գործած կլինիկայի օգտատեր",
    username: "Օգտանուն",
    email: "Էլ․ փոստ",
    role: "Դեր",
    subscription: "Բաժանորդագրություն",
    plan: "Փաթեթ",
    status: "Կարգավիճակ",
    expires: "Ավարտվում է",
    whatsapp: "Կլինիկայի WhatsApp",
    whatsappLead: "Միացրեք WhatsApp հաշիվը, որն Teta2-ը օգտագործում է պացիենտների հետագա հաղորդագրությունների համար։",
    connected: "Միացված է",
    disconnected: "Միացված չէ",
    sender: "Միացված համարը",
    connectionState: "Կապի վիճակ",
    connect: "Միացնել QR-ով",
    disconnect: "Անջատել",
    refresh: "Թարմացնել վիճակը",
    scanTitle: "Միացնել կլինիկայի WhatsApp-ը",
    scanLead: "Կլինիկայի հեռախոսում բացեք WhatsApp-ը և սկանավորեք այս QR կոդը։",
    steps: "WhatsApp → Կապակցված սարքեր → Կապակցել սարք",
    generating: "Ստեղծվում է QR կոդը…",
    close: "Փակել",
    safety: "Այստեղ ցուցադրվում է միայն սերվերի կողմից հաստատված իրական WhatsApp կապը։",
    security: "Անվտանգություն",
    billing: "Բաժանորդագրություն և վճարումներ",
  },
  ru: {
    eyebrow: "НАСТРОЙКИ КЛИНИКИ",
    title: "Настройки рабочего пространства",
    lead: "Управляйте учетной записью, подпиской, безопасностью и подключением WhatsApp клиники в одном месте.",
    account: "Учетная запись",
    accountLead: "Текущий пользователь клиники",
    username: "Имя пользователя",
    email: "Email",
    role: "Роль",
    subscription: "Подписка",
    plan: "Тариф",
    status: "Статус",
    expires: "Действует до",
    whatsapp: "WhatsApp клиники",
    whatsappLead: "Подключите WhatsApp, который Teta2 использует для сообщений пациентам по последующему наблюдению.",
    connected: "Подключен",
    disconnected: "Не подключен",
    sender: "Подключенный номер",
    connectionState: "Состояние подключения",
    connect: "Подключить по QR",
    disconnect: "Отключить",
    refresh: "Обновить статус",
    scanTitle: "Подключить WhatsApp клиники",
    scanLead: "Откройте WhatsApp на телефоне клиники и отсканируйте этот QR-код.",
    steps: "WhatsApp → Связанные устройства → Привязать устройство",
    generating: "Создание QR-кода…",
    close: "Закрыть",
    safety: "Здесь отображается только фактическое подключение WhatsApp, подтвержденное сервером.",
    security: "Безопасность",
    billing: "Подписка и оплата",
  },
} as const;

function fmtDate(value: string | null, lang: Lang) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(lang === "hy" ? "hy-AM" : lang === "ru" ? "ru-RU" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

function SettingsPanel() {
  const lang = useDashboardLanguage() as Lang;
  const c = COPY[lang];
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [connection, setConnection] = useState<WhatsAppConnection>({
    connected: false,
    connection: "unknown",
    sender: null,
  });
  const [qrOpen, setQrOpen] = useState(false);
  const [qr, setQr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [nextUser, nextConnection] = await Promise.all([api.me(), api.whatsappStatus()]);
      setUser(nextUser);
      setConnection(nextConnection);
      if (nextConnection.connected) {
        setQrOpen(false);
        setQr(null);
      }
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!qrOpen || connection.connected) return;
    let stopped = false;
    let timer = 0;
    const poll = async () => {
      try {
        const next = await api.whatsappQr();
        if (stopped) return;
        setConnection(next);
        setQr(next.qr ?? null);
        if (next.connected) {
          setQrOpen(false);
          setQr(null);
          return;
        }
      } catch (reason) {
        if (!stopped) setError(errorMessage(reason));
      }
      if (!stopped) timer = window.setTimeout(() => void poll(), WHATSAPP_QR_POLL_MS);
    };
    void poll();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
    };
  }, [qrOpen, connection.connected]);

  async function disconnect() {
    setBusy(true);
    setError("");
    try {
      const next = await api.whatsappLogout();
      setConnection(next);
      setQr(null);
      setQrOpen(false);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="settings-pro-shell">
      <section className="settings-pro-intro">
        <div>
          <small>{c.eyebrow}</small>
          <h1>{c.title}</h1>
          <p>{c.lead}</p>
        </div>
        <button type="button" className="settings-refresh" onClick={() => void refresh()}>
          <RefreshCw />
          {c.refresh}
        </button>
      </section>

      <div className="settings-pro-grid">
        <section className="settings-panel settings-account-panel">
          <header>
            <span><UserRound /></span>
            <div><small>{c.accountLead}</small><h2>{c.account}</h2></div>
          </header>
          <dl>
            <div><dt>{c.username}</dt><dd>{user?.username ?? "—"}</dd></div>
            <div><dt>{c.email}</dt><dd>{user?.email ?? "—"}</dd></div>
            <div><dt>{c.role}</dt><dd>{user ? dashboardRole(user.role, lang) : "—"}</dd></div>
          </dl>
        </section>

        <section className={`settings-panel settings-whatsapp-panel ${connection.connected ? "connected" : "disconnected"}`}>
          <header>
            <span className="settings-wa-icon"><MessageCircle /><Phone /></span>
            <div><small>{c.whatsappLead}</small><h2>{c.whatsapp}</h2></div>
            <i className={connection.connected ? "ok" : "off"}>{connection.connected ? c.connected : c.disconnected}</i>
          </header>

          <div className="settings-wa-status">
            <div><Smartphone /><span><small>{c.sender}</small><strong>{connection.sender ?? "—"}</strong></span></div>
            <div><Activity /><span><small>{c.connectionState}</small><strong>{connection.connection || "unknown"}</strong></span></div>
          </div>

          {error && <div className="settings-inline-error">{error}</div>}

          <div className="settings-wa-actions">
            {connection.connected ? (
              <button type="button" className="settings-danger" disabled={busy} onClick={() => void disconnect()}>
                <X />{busy ? "…" : c.disconnect}
              </button>
            ) : (
              <button type="button" className="settings-primary" onClick={() => { setError(""); setQrOpen(true); }}>
                <QrCode />{c.connect}
              </button>
            )}
            <button type="button" className="settings-secondary" onClick={() => void refresh()}>
              <RefreshCw />{c.refresh}
            </button>
          </div>

          <p className="settings-truth-note"><ShieldCheck />{c.safety}</p>
        </section>

        <section className="settings-panel settings-subscription-summary">
          <header>
            <span><Clock3 /></span>
            <div><small>{c.billing}</small><h2>{c.subscription}</h2></div>
          </header>
          <dl>
            <div><dt>{c.plan}</dt><dd>{user?.subscription_plan ?? "—"}</dd></div>
            <div><dt>{c.status}</dt><dd>{user?.subscription_state ?? "—"}</dd></div>
            <div><dt>{c.expires}</dt><dd>{fmtDate(user?.subscription_expires_at ?? null, lang)}</dd></div>
          </dl>
        </section>

        <section className="settings-panel settings-security-summary">
          <header>
            <span><KeyRound /></span>
            <div><small>{c.security}</small><h2>{c.security}</h2></div>
          </header>
          <div className="settings-security-points">
            <div><CheckCircle2 /><span>{user?.email ?? "—"}</span></div>
            <div><Mail /><span>{user ? dashboardRole(user.role, lang) : "—"}</span></div>
          </div>
        </section>
      </div>

      {qrOpen && (
        <div className="settings-qr-backdrop" role="dialog" aria-modal="true" aria-label={c.scanTitle}>
          <div className="settings-qr-modal">
            <button type="button" className="settings-qr-close" aria-label={c.close} onClick={() => setQrOpen(false)}><X /></button>
            <span className="settings-wa-icon large"><MessageCircle /><Phone /></span>
            <small>{c.whatsapp.toUpperCase()}</small>
            <h2>{c.scanTitle}</h2>
            <p>{c.scanLead}</p>
            {qr ? <img src={qr} alt={`${c.whatsapp} QR`} /> : <div className="settings-qr-loading"><RefreshCw />{c.generating}</div>}
            <strong>{c.steps}</strong>
            {error && <div className="settings-inline-error">{error}</div>}
          </div>
        </div>
      )}
    </div>
  );
}

export function SettingsWorkspaceEnhancer() {
  const [host, setHost] = useState<HTMLElement | null>(null);

  useEffect(() => {
    let observer: MutationObserver | null = null;
    const sync = () => {
      const settings = document.querySelector<HTMLElement>(".account-settings");
      if (!settings) {
        setHost(null);
        return;
      }
      let nextHost = settings.querySelector<HTMLElement>("#teta2-settings-pro-host");
      if (!nextHost) {
        nextHost = document.createElement("div");
        nextHost.id = "teta2-settings-pro-host";
        settings.insertBefore(nextHost, settings.firstChild?.nextSibling ?? settings.firstChild);
      }
      settings.classList.add("settings-pro-enabled");
      setHost(nextHost);
    };

    sync();
    observer = new MutationObserver(sync);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      observer.disconnect();
      document.querySelector(".account-settings")?.classList.remove("settings-pro-enabled");
      document.getElementById("teta2-settings-pro-host")?.remove();
    };
  }, []);

  return host ? createPortal(<SettingsPanel />, host) : null;
}
