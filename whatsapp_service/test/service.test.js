import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { mkdtemp } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { cleanPhone, createService, jidForPhone, normalizeAccountId, sessionDirFor } from "../src/index.js";

const A = "clinic_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const B = "clinic_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
function fakes() {
  const sockets = [];
  return {
    sockets,
    authState: async () => ({ state: { creds: {}, keys: {} }, saveCreds: async () => {} }),
    latestVersion: async () => ({ version: [2, 3000, 1] }),
    qrToDataURL: async (qr) => `data:image/png;base64,${qr}`,
    makeSocket: () => {
      const ev = new EventEmitter();
      const socket = {
        ev, user: null, logout: async () => {},
        onWhatsApp: async (jid) => [{ exists: true, jid }],
        sendPresenceUpdate: async () => {},
        sendMessage: async () => ({ key: { id: "wamid-test" } })
      };
      sockets.push(socket); return socket;
    },
    delayMs: 0, reconnect: false
  };
}
test("phone normalization and WhatsApp JID", () => {
  assert.equal(cleanPhone("+374 93 156 663"), "37493156663");
  assert.equal(jidForPhone("+37493156663"), "37493156663@s.whatsapp.net");
});
test("clinic sessions are isolated and traversal is rejected", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "dentai-wa-"));
  assert.notEqual(sessionDirFor(A, root), sessionDirFor(B, root));
  assert.throws(() => normalizeAccountId("../clinic_a"), /invalid_account_id/);
});
test("QR update is converted to a data URL in the clinic session", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "dentai-wa-"));
  const deps = { ...fakes(), sessionRoot: root };
  const service = createService(deps);
  const entry = await service.startClient(A);
  deps.sockets[0].ev.emit("connection.update", { qr: "clinic-a-qr" });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(entry.connection, "qr");
  assert.equal(entry.qrDataUrl, "data:image/png;base64,clinic-a-qr");
  assert.equal(sessionDirFor(A, root).endsWith(A), true);
});
test("connected fake validates and sends with provider message id", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "dentai-wa-"));
  const deps = { ...fakes(), sessionRoot: root };
  const service = createService(deps);
  const entry = await service.startClient(A);
  deps.sockets[0].user = { id: "37499111222:1@s.whatsapp.net" };
  deps.sockets[0].ev.emit("connection.update", { connection: "open" });
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(entry.connection, "open");
  const [registered] = await entry.socket.onWhatsApp(jidForPhone("+37493156663"));
  assert.equal(registered.exists, true);
  const result = await entry.socket.sendMessage(jidForPhone("+37493156663"), { text: "test" });
  assert.equal(result.key.id, "wamid-test");
});
