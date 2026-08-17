export const WHATSAPP_QR_POLL_MS = 3_000;

export function maskPhone(value: string | null | undefined): string {
  if (!value) return "Not saved";
  const digits = value.replace(/\D/g, "");
  return digits.length >= 3 ? "+***" + digits.slice(-3) : "+***";
}

export function shouldContinueQrPolling(
  modalOpen: boolean,
  status: { connected: boolean; qr?: string | null }
): boolean {
  return modalOpen && !status.connected;
}

export function formatOutreachStatus(value: string): string {
  return value.charAt(0) + value.slice(1).toLowerCase();
}
