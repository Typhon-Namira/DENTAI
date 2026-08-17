import { mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Boom } from "@hapi/boom";
import makeWASocket, { DisconnectReason, fetchLatestBaileysVersion, useMultiFileAuthState } from "@whiskeysockets/baileys";
import express from "express";
import pino from "pino";
import qrcode from "qrcode";

const logger = pino({ level: process.env.LOG_LEVEL || "info" });
export const SESSION_ROOT = path.resolve(process.env.WHATSAPP_SESSION_DIR || "/app/data/whatsapp_sessions");
const INTERNAL_TOKEN = process.env.WHATSAPP_SERVICE_TOKEN || "";
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
const QR_WAIT_MS = Number(process.env.WHATSAPP_QR_WAIT_MS || 12000);

export const cleanPhone = (value) => String(value || "").replace(/\D/g, "");
export function jidForPhone(value) {
  const digits = cleanPhone(value);
  if (digits.length < 8 || digits.length > 15) throw new Error("invalid_phone");
  return `${digits}@s.whatsapp.net`;
}
export function normalizeAccountId(value) {
  const accountId = String(value || "");
  if (!/^clinic_[0-9a-f]{32}$/.test(accountId)) throw new Error("invalid_account_id");
  return accountId;
}
export function sessionDirFor(accountId, root = SESSION_ROOT) {
  const safeId = normalizeAccountId(accountId);
  const resolvedRoot = path.resolve(root);
  const candidate = path.resolve(resolvedRoot, safeId);
  if (!candidate.startsWith(`${resolvedRoot}${path.sep}`)) throw new Error("invalid_account_id");
  return candidate;
}
export function maskPhone(value) {
  const digits = cleanPhone(value);
  return digits ? `+***${digits.slice(-4)}` : null;
}

export function createService(deps = {}) {
  const makeSocket = deps.makeSocket || makeWASocket;
  const authState = deps.authState || useMultiFileAuthState;
  const latestVersion = deps.latestVersion || fetchLatestBaileysVersion;
  const qrToDataURL = deps.qrToDataURL || qrcode.toDataURL;
  const sessionRoot = path.resolve(deps.sessionRoot || SESSION_ROOT);
  const delayMs = deps.delayMs ?? 1400;
  const reconnect = deps.reconnect !== false;
  const states = new Map();
  const app = express();
  app.use(express.json({ limit: "5mb" }));

  function authorized(req, res, next) {
    if (INTERNAL_TOKEN && req.get("authorization") !== `Bearer ${INTERNAL_TOKEN}`) {
      return res.status(401).json({ error: "unauthorized" });
    }
    return next();
  }
  async function startClient(accountId) {
    const safeId = normalizeAccountId(accountId);
    const existing = states.get(safeId);
    if (existing?.socket && existing.connection !== "logged_out") return existing;
    const sessionDir = sessionDirFor(safeId, sessionRoot);
    await mkdir(sessionDir, { recursive: true });
    const { state, saveCreds } = await authState(sessionDir);
    const { version } = await latestVersion();
    const entry = { connection: "connecting", qrDataUrl: null, phone: null, socket: null };
    states.set(safeId, entry);
    const socket = makeSocket({ auth: state, version, printQRInTerminal: false, logger: logger.child({ account: safeId }) });
    entry.socket = socket;
    socket.ev.on("creds.update", saveCreds);
    socket.ev.on("connection.update", async ({ connection, lastDisconnect, qr }) => {
      if (qr) {
        entry.qrDataUrl = await qrToDataURL(qr);
        entry.connection = "qr";
        logger.info({ event: "whatsapp_qr_generated", account: safeId });
      }
      if (connection === "open") {
        entry.connection = "open";
        entry.qrDataUrl = null;
        entry.phone = socket.user?.id?.split(":")[0]?.split("@")[0] || null;
        logger.info({ event: "whatsapp_connected", account: safeId });
      }
      if (connection === "close") {
        const statusCode = new Boom(lastDisconnect?.error).output.statusCode;
        entry.socket = null;
        if (statusCode === DisconnectReason.loggedOut || statusCode === 401) {
          entry.connection = "logged_out";
          entry.qrDataUrl = null;
          await rm(sessionDir, { recursive: true, force: true });
        } else {
          entry.connection = "disconnected";
          if (reconnect) setTimeout(() => void startClient(safeId).catch((error) =>
            logger.warn({ event: "whatsapp_reconnect_failed", account: safeId, error: error.name })
          ), 1500).unref();
        }
      }
    });
    return entry;
  }
  async function entryFor(req) {
    const accountId = normalizeAccountId(req.query.account_id || req.body?.account_id);
    return { accountId, entry: await startClient(accountId) };
  }
  async function waitForQr(accountId, timeoutMs = QR_WAIT_MS) {
    const safeId = normalizeAccountId(accountId);
    const entry = await startClient(safeId);
    const startedAt = Date.now();
    while (!entry.qrDataUrl && entry.connection !== "open" && Date.now() - startedAt < timeoutMs) {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    return entry;
  }

  app.get("/health", (_req, res) => res.json({ status: "ok" }));
  app.use("/whatsapp", authorized);
  app.get("/whatsapp/status", async (req, res) => {
    try {
      const { entry } = await entryFor(req);
      res.json({ connected: entry.connection === "open", connection: entry.connection, sender: maskPhone(entry.phone) });
    } catch (error) {
      res.status(400).json({ error: error.message });
    }
  });
  app.get("/whatsapp/qr", async (req, res) => {
    try {
      const accountId = normalizeAccountId(req.query.account_id);
      const entry = await waitForQr(accountId);
      const payload = { connected: entry.connection === "open", connection: entry.connection, qr: entry.qrDataUrl };
      if (!payload.connected && !payload.qr) return res.status(202).json(payload);
      return res.json(payload);
    } catch (error) {
      return res.status(400).json({ error: error.message });
    }
  });
  app.post("/whatsapp/logout", async (req, res) => {
    try {
      const { accountId, entry } = await entryFor(req);
      if (entry.socket) await entry.socket.logout();
      states.delete(accountId);
      await rm(sessionDirFor(accountId, sessionRoot), { recursive: true, force: true });
      res.json({ connected: false, connection: "logged_out" });
    } catch (error) {
      res.status(400).json({ error: error.message });
    }
  });
  app.get("/whatsapp/validate", async (req, res) => {
    try {
      const { entry } = await entryFor(req);
      if (entry.connection !== "open" || !entry.socket) return res.status(409).json({ error: "not_connected" });
      const jid = jidForPhone(req.query.phone);
      const [result] = await entry.socket.onWhatsApp(jid);
      res.json({ registered: Boolean(result?.exists), jid: result?.exists ? jid : null });
    } catch (error) {
      res.status(400).json({ error: error.message });
    }
  });
  app.post("/whatsapp/send", async (req, res) => {
    try {
      const { entry } = await entryFor(req);
      if (entry.connection !== "open" || !entry.socket) return res.status(409).json({ error: "not_connected" });
      const jid = jidForPhone(req.body.phone);
      const [registration] = await entry.socket.onWhatsApp(jid);
      if (!registration?.exists) return res.status(422).json({ error: "phone_not_on_whatsapp" });
      const message = String(req.body.message || "").trim();
      if (!message) return res.status(400).json({ error: "message_required" });
      await entry.socket.sendPresenceUpdate("composing", jid);
      if (delayMs) await new Promise((resolve) => setTimeout(resolve, delayMs));
      await entry.socket.sendPresenceUpdate("paused", jid);
      let payload = { text: message };
      if (req.body.image_base64) {
        const image = Buffer.from(req.body.image_base64, "base64");
        if (!image.length || image.length > MAX_IMAGE_BYTES) return res.status(413).json({ error: "image_size_invalid" });
        payload = { image, caption: message, mimetype: req.body.image_mime_type || "image/jpeg" };
      }
      const result = await entry.socket.sendMessage(jid, payload);
      res.json({ status: "sent", message_id: result?.key?.id || null, sent_at: new Date().toISOString() });
    } catch (error) {
      logger.warn({ event: "whatsapp_send_failed", error: error.name });
      res.status(502).json({ error: "send_failed" });
    }
  });
  return { app, states, startClient };
}
const isEntryPoint = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isEntryPoint) {
  const { app } = createService();
  const port = Number(process.env.WHATSAPP_SERVICE_PORT || process.env.PORT || 3001);
  const host = INTERNAL_TOKEN ? "0.0.0.0" : "127.0.0.1";
  app.listen(port, host, () => logger.info({ event: "whatsapp_service_started", host, port }));
}
