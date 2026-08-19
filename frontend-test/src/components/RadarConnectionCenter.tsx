import { useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";

type Connection = {
  id: string;
  platform: string;
  provider: string;
  status: string;
  account_display?: string | null;
  expires_at?: string | null;
  last_health_at?: string | null;
  last_error_code?: string | null;
};

const META_PENDING_KEY = "dentai-radar-meta-pending";

export function RadarConnectionCenter({ canManage }: { canManage: boolean }) {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [phone, setPhone] = useState("");
  const [telegramId, setTelegramId] = useState<string | null>(null);
  const [telegramNext, setTelegramNext] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    setConnections(await api.radarConnections());
  }

  useEffect(() => {
    void refresh().catch((reason) => setError(errorMessage(reason)));
    const params = new URLSearchParams(window.location.search);
    const oauthCode = params.get("code");
    const oauthState = params.get("state");
    const pendingRaw = sessionStorage.getItem(META_PENDING_KEY);
    if (!oauthCode || !oauthState || !pendingRaw) return;
    try {
      const pending = JSON.parse(pendingRaw) as { connectionId: string; state: string };
      if (pending.state !== oauthState) throw new Error("Meta authorization state mismatch.");
      setBusy("meta-complete");
      api.completeRadarMeta(pending.connectionId, oauthCode, oauthState)
        .then(async () => {
          sessionStorage.removeItem(META_PENDING_KEY);
          params.delete("code");
          params.delete("state");
          const next = window.location.pathname + (params.toString() ? "?" + params : "") + window.location.hash;
          window.history.replaceState({}, "", next);
          await refresh();
        })
        .catch((reason) => setError(errorMessage(reason)))
        .finally(() => setBusy(""));
    } catch (reason) {
      setError(errorMessage(reason));
    }
  }, []);

  async function startMeta(platform: "FACEBOOK" | "INSTAGRAM") {
    setBusy(platform);
    setError("");
    try {
      const result = await api.startRadarMeta(platform);
      sessionStorage.setItem(META_PENDING_KEY, JSON.stringify({ connectionId: result.connection.id, state: result.state }));
      window.location.assign(result.authorization_url);
    } catch (reason) {
      setError(errorMessage(reason));
      setBusy("");
    }
  }

  async function startTelegram() {
    setBusy("TELEGRAM");
    setError("");
    try {
      const result = await api.startRadarTelegram(phone);
      setTelegramId(result.connection.id);
      setTelegramNext(result.next);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function finishTelegram() {
    if (!telegramId) return;
    setBusy("TELEGRAM-COMPLETE");
    setError("");
    try {
      const result = await api.completeRadarTelegram(telegramId, code, password || undefined);
      setTelegramNext(result.next);
      if (result.next === "ACTIVE") {
        setPhone("");
        setCode("");
        setPassword("");
        setTelegramId(null);
        await refresh();
      }
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  async function disconnect(id: string) {
    setBusy(id);
    setError("");
    try {
      await api.disconnectRadarConnection(id);
      await refresh();
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="radar-operations-card">
      <div className="section-heading">
        <div><p className="eyebrow">Authorized access</p><h2>Connection center</h2></div>
        <small>Read-only sessions. Passwords are never retained.</small>
      </div>
      {error && <div className="error-panel" role="alert">{error}</div>}
      <div className="radar-collector-grid">
        {connections.map((connection) => (
          <article key={connection.id} className={connection.status === "ACTIVE" ? "ready" : "attention"}>
            <div><strong>{connection.platform}</strong><span>{connection.account_display || connection.provider} · {connection.status}</span></div>
            {canManage && connection.status !== "DISCONNECTED" && (
              <button type="button" className="button button-secondary" disabled={busy === connection.id} onClick={() => void disconnect(connection.id)}>Disconnect</button>
            )}
          </article>
        ))}
      </div>
      {canManage && (
        <div className="radar-filter-group">
          <button type="button" className="button button-secondary" disabled={Boolean(busy)} onClick={() => void startMeta("INSTAGRAM")}>Connect Instagram</button>
          <button type="button" className="button button-secondary" disabled={Boolean(busy)} onClick={() => void startMeta("FACEBOOK")}>Connect Facebook</button>
          {!telegramId ? (
            <label><span>Telegram phone</span><input value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+374…" /><button type="button" className="button button-secondary" disabled={Boolean(busy) || phone.length < 6} onClick={() => void startTelegram()}>Send login code</button></label>
          ) : (
            <label><span>{telegramNext === "PASSWORD" ? "Telegram 2FA password" : "Telegram login code"}</span>
              {telegramNext !== "PASSWORD" && <input value={code} onChange={(event) => setCode(event.target.value)} placeholder="Login code" />}
              {telegramNext === "PASSWORD" && <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="2FA password" />}
              <button type="button" className="button button-accent" disabled={Boolean(busy)} onClick={() => void finishTelegram()}>Complete Telegram login</button>
            </label>
          )}
        </div>
      )}
    </section>
  );
}
