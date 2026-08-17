import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import type { Patient, WhatsAppConnection, WhatsAppOutreach } from "../api/types";
import {
  WHATSAPP_QR_POLL_MS,
  formatOutreachStatus,
  maskPhone,
  shouldContinueQrPolling
} from "../utils/whatsapp";

interface Props {
  patient: Patient;
  onPatientUpdated(patient: Patient): void;
}

function displayDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString() : "—";
}

export function WhatsAppOutreachCard({ patient, onPatientUpdated }: Props) {
  const [connection, setConnection] = useState<WhatsAppConnection>({
    connected: false,
    connection: "unknown",
    sender: null
  });
  const [phone, setPhone] = useState(patient.whatsapp_phone ?? "");
  const [qrOpen, setQrOpen] = useState(false);
  const [qr, setQr] = useState<string | null>(null);
  const [includeImage, setIncludeImage] = useState(false);
  const [result, setResult] = useState<WhatsAppOutreach | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const refreshStatus = useCallback(async () => {
    const next = await api.whatsappStatus();
    setConnection(next);
    if (next.connected) {
      setQrOpen(false);
      setQr(null);
    }
    return next;
  }, []);

  useEffect(() => {
    setPhone(patient.whatsapp_phone ?? "");
    setResult(null);
  }, [patient.id, patient.whatsapp_phone]);

  useEffect(() => {
    void refreshStatus().catch((reason) => setError(errorMessage(reason)));
  }, [refreshStatus]);

  useEffect(() => {
    if (!shouldContinueQrPolling(qrOpen, connection)) return;
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

  async function savePhone() {
    setBusy("save");
    setError("");
    try {
      onPatientUpdated(await api.savePatientWhatsApp(patient.id, phone || null));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function disconnect() {
    setBusy("logout");
    setError("");
    try {
      await api.whatsappLogout();
      setConnection({ connected: false, connection: "logged_out", sender: null });
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function sendTest() {
    setBusy("send");
    setError("");
    setResult(null);
    try {
      setResult(await api.sendWhatsAppTest(patient.id, includeImage));
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="card whatsapp-card">
      <div className="section-heading">
        <div><p className="eyebrow">Patient monitoring</p><h3>WhatsApp Outreach</h3></div>
        <span className={"connection-dot " + (connection.connected ? "connected" : "")}>
          {connection.connected ? "Connected" : "Disconnected"}
        </span>
      </div>
      <div className="whatsapp-grid">
        <div>
          <span className="field-label">Sender</span>
          <strong>{connection.sender ?? "Not connected"}</strong>
        </div>
        <div>
          <span className="field-label">Patient</span>
          <strong>{maskPhone(patient.whatsapp_phone)}</strong>
        </div>
      </div>
      <div className="whatsapp-phone-row">
        <label>
          WhatsApp number
          <input
            inputMode="tel"
            placeholder="+374..."
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
        </label>
        <button className="button button-secondary" disabled={busy === "save"} onClick={() => void savePhone()}>
          {busy === "save" ? "Saving…" : "Save"}
        </button>
      </div>
      <div className="whatsapp-actions">
        {!connection.connected ? (
          <button className="button button-primary" onClick={() => setQrOpen(true)}>Connect WhatsApp</button>
        ) : (
          <button className="button button-quiet" disabled={busy === "logout"} onClick={() => void disconnect()}>
            Disconnect
          </button>
        )}
        <label className="image-option">
          <input type="checkbox" checked={includeImage} onChange={(event) => setIncludeImage(event.target.checked)} />
          Include DENTAI finding image
        </label>
        <button
          className="button button-accent"
          disabled={!connection.connected || !patient.whatsapp_phone || busy === "send"}
          onClick={() => void sendTest()}
        >
          {busy === "send" ? "Sending…" : "Send WhatsApp test now"}
        </button>
      </div>
      <p className="muted">Finding image is optional and off by default. The full OPG is never sent automatically.</p>
      {error && <div className="error-panel" role="alert">{error}</div>}
      {result && (
        <div className="whatsapp-result" role="status">
          <h4>WhatsApp test</h4>
          <dl>
            <div><dt>Recipient</dt><dd>{maskPhone(patient.whatsapp_phone)}</dd></div>
            <div><dt>Finding</dt><dd>{result.tooth_fdi} · {result.finding_type}</dd></div>
            <div><dt>Recommended check</dt><dd>{displayDate(result.target_followup_at)}</dd></div>
            <div><dt>WhatsApp reminder</dt><dd>{displayDate(result.scheduled_send_at)}</dd></div>
            <div><dt>Status</dt><dd>{formatOutreachStatus(result.status)}</dd></div>
            <div><dt>Message ID</dt><dd>{result.provider_message_id ?? "—"}</dd></div>
            <div><dt>Sent</dt><dd>{displayDate(result.sent_at)}</dd></div>
            <div><dt>Error</dt><dd>{result.safe_error ?? "—"}</dd></div>
          </dl>
        </div>
      )}
      {qrOpen && (
        <div className="qr-backdrop" role="dialog" aria-modal="true" aria-label="Connect clinic WhatsApp">
          <div className="qr-modal">
            <button className="qr-close" aria-label="Close" onClick={() => setQrOpen(false)}>×</button>
            <p className="eyebrow">Secure clinic connection</p>
            <h2>Scan with WhatsApp</h2>
            {qr ? <img src={qr} alt="WhatsApp connection QR code" /> : <div className="qr-loading">Generating QR…</div>}
            <p>Open WhatsApp on the clinic phone, choose Linked devices, and scan this code.</p>
            <small>Connection status refreshes every 3 seconds.</small>
          </div>
        </div>
      )}
    </section>
  );
}
