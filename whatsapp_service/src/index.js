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
const CARE_CALLBACK_URL = process.env.TETA2_CARE_CALLBACK_URL || "";
const CARE_STATUS_CALLBACK_URL = process.env.TETA2_CARE_STATUS_CALLBACK_URL ||
  CARE_CALLBACK_URL.replace(/\/inbound$/, "/status");
const MAX_IMAGE_BYTES = 3 * 1024 * 1024;
const QR_WAIT_MS = Number(process.env.WHATSAPP_QR_WAIT_MS || 12000);
const DELIVERY_CONFIRM_TIMEOUT_MS = Number(process.env.WHATSAPP_DELIVERY_CONFIRM_TIMEOUT_MS || 20000);
const INBOUND_BUFFER_WATCHDOG_MS = Number(process.env.WHATSAPP_INBOUND_BUFFER_WATCHDOG_MS || 30000);

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

function phoneFromPnJid(value) {
  const jid = String(value || "");
  if (!jid.endsWith("@s.whatsapp.net")) return null;
  const digits = jid.split("@")[0].split(":")[0].replace(/\D/g, "");
  return digits.length >= 8 && digits.length <= 15 ? `+${digits}` : null;
}

export async function resolveInboundPhone(message, socket = null) {
  const key = message?.key || {};
  const directCandidates = [
    key.remoteJid,
    key.remoteJidAlt,
    key.participantPn,
    key.participantAlt,
    key.senderPn,
    key.senderAlt,
    message?.participantPn,
    message?.senderPn
  ];
  for (const candidate of directCandidates) {
    const phone = phoneFromPnJid(candidate);
    if (phone) return phone;
  }

  const lidCandidates = [key.remoteJid, key.participant].filter((jid) =>
    String(jid || "").endsWith("@lid")
  );
  const mapper = socket?.signalRepository?.lidMapping?.getPNForLID;
  if (typeof mapper === "function") {
    for (const lid of lidCandidates) {
      try {
        const mapped = await mapper.call(socket.signalRepository.lidMapping, lid);
        const phone = phoneFromPnJid(mapped);
        if (phone) return phone;
      } catch (error) {
        logger.debug({ event: "care_inbound_lid_mapping_failed", error: error?.name || "Error" });
      }
    }
  }
  return null;
}

export async function resolveOutboundJid(socket, phone) {
  const pnJid = jidForPhone(phone);
  const [registration] = await socket.onWhatsApp(pnJid);
  if (!registration?.exists) return { exists: false, jid: pnJid, pnJid };

  const registeredJid = registration.jid || pnJid;
  const mapper = socket?.signalRepository?.lidMapping?.getLIDForPN;
  if (typeof mapper === "function") {
    for (const candidate of [registeredJid, pnJid]) {
      try {
        const mapped = await mapper.call(socket.signalRepository.lidMapping, candidate);
        if (mapped && String(mapped).endsWith("@lid")) {
          return { exists: true, jid: mapped, pnJid: registeredJid };
        }
      } catch (error) {
        logger.debug({ event: "care_outbound_lid_mapping_failed", error: error?.name || "Error" });
      }
    }
  }
  return { exists: true, jid: registeredJid, pnJid: registeredJid };
}

function messageText(message) {
  const content = message?.message || {};
  return String(
    content.conversation ||
    content.extendedTextMessage?.text ||
    content.imageMessage?.caption ||
    content.videoMessage?.caption ||
    ""
  ).trim();
}

function jidDomain(value) {
  const jid = String(value || "");
  const at = jid.lastIndexOf("@");
  return at >= 0 ? jid.slice(at + 1) : "unknown";
}

function messageStatus(value) {
  return ({ 1: "QUEUED", 2: "SENT", 3: "DELIVERED", 4: "READ", 5: "READ" })[Number(value)] || null;
}

function statusRank(value) {
  return ({ QUEUED: 1, SENT: 2, DELIVERED: 3, READ: 4, FAILED: -1 })[value] ?? 0;
}

export function createService(deps = {}) {
  const makeSocket = deps.makeSocket || makeWASocket;
  const authState = deps.authState || useMultiFileAuthState;
  const latestVersion = deps.latestVersion || fetchLatestBaileysVersion;
  const qrToDataURL = deps.qrToDataURL || qrcode.toDataURL;
  const sessionRoot = path.resolve(deps.sessionRoot || SESSION_ROOT);
  const delayMs = deps.delayMs ?? 1400;
  const reconnect = deps.reconnect !== false;
  const deliveryConfirmTimeoutMs = deps.deliveryConfirmTimeoutMs ?? DELIVERY_CONFIRM_TIMEOUT_MS;
  const inboundBufferWatchdogMs = deps.inboundBufferWatchdogMs ?? INBOUND_BUFFER_WATCHDOG_MS;
  const states = new Map();
  const diagnostics = new Map();
  const deliveryStates = new Map();
  const deliveryWaiters = new Map();
  const app = express();
  app.use(express.json({ limit: "5mb" }));

  function authorized(req, res, next) {
    if (INTERNAL_TOKEN && req.get("authorization") !== `Bearer ${INTERNAL_TOKEN}`) {
      return res.status(401).json({ error: "unauthorized" });
    }
    return next();
  }

  function noteDiagnostic(accountId, patch) {
    const current = diagnostics.get(accountId) || {
      upsert_count: 0,
      inbound_candidate_count: 0,
      forwarded_count: 0,
      unresolved_count: 0,
      callback_rejected_count: 0,
      forced_buffer_flush_count: 0,
      delivery_update_count: 0,
      last_upsert_at: null,
      last_upsert_type: null,
      last_remote_jid_domain: null,
      last_forwarded_at: null,
      last_callback_status: null,
      last_delivery_status: null,
      last_delivery_at: null,
      last_send_target_domain: null
    };
    diagnostics.set(accountId, { ...current, ...patch });
    return diagnostics.get(accountId);
  }

  async function postStatus(accountId, providerMessageId, status) {
    if (!CARE_STATUS_CALLBACK_URL || !providerMessageId || !status) return;
    try {
      const response = await fetch(CARE_STATUS_CALLBACK_URL, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(INTERNAL_TOKEN ? { authorization: `Bearer ${INTERNAL_TOKEN}` } : {})
        },
        body: JSON.stringify({ account_id: accountId, provider_message_id: providerMessageId, status })
      });
      if (!response.ok) logger.warn({ event: "care_status_callback_rejected", account: accountId, status: response.status });
    } catch (error) {
      logger.warn({ event: "care_status_callback_unavailable", account: accountId, error: error?.name || "Error" });
    }
  }

  function noteDelivery(accountId, providerMessageId, status) {
    if (!providerMessageId || !status) return;
    const previous = deliveryStates.get(providerMessageId);
    if (!previous || statusRank(status) >= statusRank(previous.status)) {
      deliveryStates.set(providerMessageId, { status, at: Date.now() });
    }
    const current = diagnostics.get(accountId) || {};
    noteDiagnostic(accountId, {
      delivery_update_count: (current.delivery_update_count || 0) + 1,
      last_delivery_status: status,
      last_delivery_at: new Date().toISOString()
    });
    const waiter = deliveryWaiters.get(providerMessageId);
    if (waiter && statusRank(status) >= statusRank("SENT")) {
      deliveryWaiters.delete(providerMessageId);
      clearTimeout(waiter.timer);
      waiter.resolve(status);
    }
    void postStatus(accountId, providerMessageId, status);
  }

  function waitForConfirmedDelivery(providerMessageId) {
    const known = deliveryStates.get(providerMessageId);
    if (known && statusRank(known.status) >= statusRank("SENT")) return Promise.resolve(known.status);
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        deliveryWaiters.delete(providerMessageId);
        resolve(null);
      }, deliveryConfirmTimeoutMs);
      timer.unref?.();
      deliveryWaiters.set(providerMessageId, { resolve, timer });
    });
  }

  async function forwardInbound(accountId, message, socket) {
    if (!CARE_CALLBACK_URL || message?.key?.fromMe) return;
    const text = messageText(message);
    if (!text) return;
    const before = diagnostics.get(accountId) || {};
    noteDiagnostic(accountId, {
      inbound_candidate_count: (before.inbound_candidate_count || 0) + 1,
      last_remote_jid_domain: jidDomain(message?.key?.remoteJid)
    });
    const phone = await resolveInboundPhone(message, socket);
    if (!phone) {
      const current = diagnostics.get(accountId) || {};
      noteDiagnostic(accountId, { unresolved_count: (current.unresolved_count || 0) + 1 });
      logger.warn({
        event: "care_inbound_phone_unresolved",
        account: accountId,
        message_id: message?.key?.id || null,
        remote_jid_domain: jidDomain(message?.key?.remoteJid),
        has_remote_jid_alt: Boolean(message?.key?.remoteJidAlt),
        has_participant_pn: Boolean(message?.key?.participantPn),
        has_participant_alt: Boolean(message?.key?.participantAlt)
      });
      return;
    }
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        const response = await fetch(CARE_CALLBACK_URL, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            ...(INTERNAL_TOKEN ? { authorization: `Bearer ${INTERNAL_TOKEN}` } : {})
          },
          body: JSON.stringify({ account_id: accountId, phone, text, message_id: message?.key?.id || null })
        });
        const responseText = await response.text().catch(() => "");
        noteDiagnostic(accountId, { last_callback_status: response.status });
        if (response.ok) {
          const current = diagnostics.get(accountId) || {};
          noteDiagnostic(accountId, {
            forwarded_count: (current.forwarded_count || 0) + 1,
            last_forwarded_at: new Date().toISOString()
          });
          logger.info({ event: "care_inbound_forwarded", account: accountId, message_id: message?.key?.id || null, attempt });
          return;
        }
        if (response.status < 500) {
          const current = diagnostics.get(accountId) || {};
          noteDiagnostic(accountId, { callback_rejected_count: (current.callback_rejected_count || 0) + 1 });
          logger.warn({
            event: "care_inbound_callback_rejected",
            account: accountId,
            status: response.status,
            response: responseText.slice(0, 240)
          });
          return;
        }
        logger.warn({ event: "care_inbound_callback_server_error", account: accountId, status: response.status, attempt });
      } catch (error) {
        logger.warn({ event: "care_inbound_callback_unavailable", account: accountId, attempt, error: error?.name || "Error" });
      }
      if (attempt < 3) await new Promise((resolve) => setTimeout(resolve, 250 * attempt));
    }
    logger.error({ event: "care_inbound_callback_failed", account: accountId, message_id: message?.key?.id || null });
  }

  async function startClient(accountId) {
    const safeId = normalizeAccountId(accountId);
    const existing = states.get(safeId);
    if (existing?.socket && existing.connection !== "logged_out") return existing;
    const sessionDir = sessionDirFor(safeId, sessionRoot);
    await mkdir(sessionDir, { recursive: true });
    const { state, saveCreds } = await authState(sessionDir);
    const { version } = await latestVersion();
    const entry = { connection: "connecting", qrDataUrl: null, phone: null, socket: null, bufferWatchdog: null };
    states.set(safeId, entry);
    const socket = makeSocket({ auth: state, version, printQRInTerminal: false, logger: logger.child({ account: safeId }) });
    entry.socket = socket;
    socket.ev.on("creds.update", saveCreds);
    socket.ev.on("messages.upsert", ({ messages, type }) => {
      const current = diagnostics.get(safeId) || {};
      noteDiagnostic(safeId, {
        upsert_count: (current.upsert_count || 0) + (messages?.length || 0),
        last_upsert_at: new Date().toISOString(),
        last_upsert_type: type || null,
        last_remote_jid_domain: messages?.[0] ? jidDomain(messages[0]?.key?.remoteJid) : current.last_remote_jid_domain || null
      });
      logger.info({
        event: "care_messages_upsert",
        account: safeId,
        type: type || null,
        count: messages?.length || 0,
        remote_jid_domain: messages?.[0] ? jidDomain(messages[0]?.key?.remoteJid) : null,
        from_me: messages?.[0]?.key?.fromMe ?? null
      });
      for (const message of messages || []) void forwardInbound(safeId, message, socket);
    });
    socket.ev.on("messages.update", (updates) => {
      for (const item of updates || []) {
        const providerMessageId = item?.key?.id;
        const status = messageStatus(item?.update?.status ?? item?.status);
        if (!providerMessageId || !item?.key?.fromMe || !status) continue;
        noteDelivery(safeId, providerMessageId, status);
      }
    });
    socket.ev.on("message-receipt.update", (updates) => {
      for (const item of updates || []) {
        const providerMessageId = item?.key?.id;
        if (!providerMessageId || !item?.key?.fromMe) continue;
        const receipt = item?.receipt || {};
        const status = receipt.readTimestamp || receipt.playedTimestamp ? "READ" : receipt.receiptTimestamp ? "DELIVERED" : null;
        if (status) noteDelivery(safeId, providerMessageId, status);
      }
    });
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
        if (entry.bufferWatchdog) clearTimeout(entry.bufferWatchdog);
        entry.bufferWatchdog = setTimeout(() => {
          try {
            if (typeof socket.ev?.isBuffering === "function" && socket.ev.isBuffering()) {
              const flushed = typeof socket.ev.flush === "function" ? socket.ev.flush() : false;
              const current = diagnostics.get(safeId) || {};
              noteDiagnostic(safeId, { forced_buffer_flush_count: (current.forced_buffer_flush_count || 0) + (flushed ? 1 : 0) });
              logger.warn({ event: "whatsapp_inbound_buffer_forced_flush", account: safeId, flushed });
            }
          } catch (error) {
            logger.warn({ event: "whatsapp_inbound_buffer_watchdog_failed", account: safeId, error: error?.name || "Error" });
          }
        }, inboundBufferWatchdogMs);
        entry.bufferWatchdog.unref?.();
      }
      if (connection === "close") {
        if (entry.bufferWatchdog) clearTimeout(entry.bufferWatchdog);
        entry.bufferWatchdog = null;
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
  app.get("/whatsapp/diagnostics", async (req, res) => {
    try {
      const accountId = normalizeAccountId(req.query.account_id);
      const entry = await startClient(accountId);
      res.json({
        account_id: accountId,
        connection: entry.connection,
        event_buffering: typeof entry.socket?.ev?.isBuffering === "function" ? entry.socket.ev.isBuffering() : null,
        ...(diagnostics.get(accountId) || {})
      });
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
      const target = await resolveOutboundJid(entry.socket, req.query.phone);
      res.json({ registered: target.exists, jid: target.exists ? target.jid : null });
    } catch (error) {
      res.status(400).json({ error: error.message });
    }
  });
  app.post("/whatsapp/send", async (req, res) => {
    try {
      const { accountId, entry } = await entryFor(req);
      if (entry.connection !== "open" || !entry.socket) return res.status(409).json({ error: "not_connected" });
      const target = await resolveOutboundJid(entry.socket, req.body.phone);
      if (!target.exists) return res.status(422).json({ error: "phone_not_on_whatsapp" });
      const message = String(req.body.message || "").trim();
      if (!message) return res.status(400).json({ error: "message_required" });
      if (String(target.jid).endsWith("@lid") && typeof entry.socket.assertSessions === "function") {
        try {
          await entry.socket.assertSessions([target.jid], true);
        } catch (error) {
          logger.warn({ event: "whatsapp_lid_session_refresh_failed", account: accountId, error: error?.name || "Error" });
        }
      }
      noteDiagnostic(accountId, { last_send_target_domain: jidDomain(target.jid) });
      await entry.socket.sendPresenceUpdate("composing", target.jid);
      if (delayMs) await new Promise((resolve) => setTimeout(resolve, delayMs));
      await entry.socket.sendPresenceUpdate("paused", target.jid);
      let payload = { text: message };
      if (req.body.image_base64) {
        const image = Buffer.from(req.body.image_base64, "base64");
        if (!image.length || image.length > MAX_IMAGE_BYTES) return res.status(413).json({ error: "image_size_invalid" });
        payload = { image, caption: message, mimetype: req.body.image_mime_type || "image/jpeg" };
      }
      const result = await entry.socket.sendMessage(target.jid, payload);
      const providerMessageId = result?.key?.id || null;
      if (!providerMessageId) return res.status(502).json({ error: "provider_message_id_missing" });
      const confirmedStatus = await waitForConfirmedDelivery(providerMessageId);
      if (!confirmedStatus) {
        logger.warn({ event: "whatsapp_delivery_unconfirmed", account: accountId, message_id: providerMessageId, target_domain: jidDomain(target.jid) });
        return res.status(504).json({ error: "delivery_unconfirmed", message_id: providerMessageId });
      }
      res.json({ status: confirmedStatus.toLowerCase(), message_id: providerMessageId, sent_at: new Date().toISOString() });
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