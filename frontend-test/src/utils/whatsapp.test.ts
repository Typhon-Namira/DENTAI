import { describe, expect, it } from "vitest";
import {
  WHATSAPP_QR_POLL_MS,
  formatOutreachStatus,
  maskPhone,
  shouldContinueQrPolling
} from "./whatsapp";

describe("WhatsApp UI state", () => {
  it("polls QR every three seconds only while disconnected modal is open", () => {
    expect(WHATSAPP_QR_POLL_MS).toBe(3000);
    expect(shouldContinueQrPolling(true, { connected: false })).toBe(true);
    expect(shouldContinueQrPolling(true, { connected: true })).toBe(false);
    expect(shouldContinueQrPolling(false, { connected: false })).toBe(false);
  });

  it("masks contact numbers and formats delivery states", () => {
    expect(maskPhone("+37493156663")).toBe("+***663");
    expect(formatOutreachStatus("QUEUED")).toBe("Queued");
    expect(formatOutreachStatus("CLAIMED")).toBe("Claimed");
    expect(formatOutreachStatus("SENDING")).toBe("Sending");
    expect(formatOutreachStatus("SEND_UNKNOWN")).toBe("Send Unknown");
    expect(formatOutreachStatus("SENT")).toBe("Sent");
    expect(formatOutreachStatus("FAILED")).toBe("Failed");
  });
});
