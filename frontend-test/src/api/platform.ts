import { API_BASE_URL, ApiError } from "./client";

const ADMIN_SESSION_KEY = "teta2-platform-admin";

export interface PublicPlan {
  code: "TETA2_CARE";
  name: "Teta2 Care";
  price: string;
  currency: string;
  subscription_days: 30;
}

export interface AccessRequestInput {
  clinic_name: string;
  requested_slug: string;
  country: string;
  city: string;
  address?: string;
  website?: string;
  director_name: string;
  work_email: string;
  phone: string;
  branch_count: number;
  dentist_count: number;
  notes?: string;
}

export interface PlatformAccessRequest extends AccessRequestInput {
  id: string;
  plan: string;
  plan_name: string;
  subscription_days: number;
  status: string;
  admin_note?: string | null;
  payment_reference?: string | null;
  payment_proof_note?: string | null;
  payment_instructions_sent_at?: string | null;
  payment_reported_at?: string | null;
  payment_verified_at?: string | null;
  activated_at?: string | null;
  rejected_at?: string | null;
  clinic_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformClinic {
  id: string;
  slug: string;
  name: string;
  is_active: boolean;
  subscription_plan: string;
  subscription_status: string;
  subscription_started_at?: string | null;
  subscription_ends_at?: string | null;
  renewal_count: number;
  subscription_expired: boolean;
  plan_name: string;
  subscription_days: number;
  created_at: string;
  usage?: {
    database?: string;
    patients?: number;
    visits?: number;
    xrays?: number;
    analyses?: number;
    appointments?: number;
  };
}

export interface BillingSettings {
  id: number;
  plan_code: string;
  plan_name: string;
  subscription_days: number;
  price: string;
  currency: string;
  bank_name: string;
  cardholder_name: string;
  card_number: string;
  payment_note: string;
  support_email: string;
  login_url: string;
  updated_at: string;
}

export interface PlatformOverview {
  plan: { code: string; name: string; subscription_days: number };
  clinics: { total: number; active: number; expired_or_suspended: number; expiring_within_7_days: number };
  access_requests: Record<string, number>;
  platform_usage: { patients: number; visits: number; xrays: number; analyses: number; appointments: number };
  tenant_health: { healthy: number; unhealthy: number };
  email_configured: boolean;
  admin_configured: boolean;
}

export interface PlatformHealth {
  control_database: string;
  smtp: string;
  tenant_databases: Array<Record<string, string | number>>;
}

export interface PlatformEvent {
  id: string;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

function adminToken(): string | null {
  return sessionStorage.getItem(ADMIN_SESSION_KEY);
}

export function hasPlatformAdminSession(): boolean {
  return Boolean(adminToken());
}

export function clearPlatformAdminSession(): void {
  sessionStorage.removeItem(ADMIN_SESSION_KEY);
}

async function platformRequest<T>(path: string, init: RequestInit = {}, admin = false): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (admin) {
    const token = adminToken();
    if (!token) throw new ApiError(401, "ADMIN_AUTH_REQUIRED", "Platform admin authentication is required.");
    headers.set("Authorization", `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(API_BASE_URL + path, { ...init, headers });
  } catch (error) {
    throw new ApiError(0, "API_UNAVAILABLE", error instanceof Error ? error.message : "Platform API unavailable");
  }
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    if (admin && response.status === 401) clearPlatformAdminSession();
    const body = typeof payload === "object" && payload !== null ? payload as { error?: { code?: string; message?: string }; detail?: string } : {};
    throw new ApiError(
      response.status,
      body.error?.code || `HTTP_${response.status}`,
      body.error?.message || body.detail || (typeof payload === "string" ? payload : response.statusText)
    );
  }
  return payload as T;
}

export const platformApi = {
  plan() {
    return platformRequest<PublicPlan>("/api/v1/platform/plan");
  },
  requestAccess(body: AccessRequestInput) {
    return platformRequest<{ id: string; status: string; plan: string; subscription_days: number; message: string }>(
      "/api/v1/platform/access-requests",
      { method: "POST", body: JSON.stringify(body) }
    );
  },
  async adminLogin(email: string, password: string) {
    const result = await platformRequest<{ access_token: string; expires_in: number }>(
      "/api/v1/platform/admin/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    );
    sessionStorage.setItem(ADMIN_SESSION_KEY, result.access_token);
    return result;
  },
  overview() {
    return platformRequest<PlatformOverview>("/api/v1/platform/admin/overview", {}, true);
  },
  health() {
    return platformRequest<PlatformHealth>("/api/v1/platform/admin/health", {}, true);
  },
  requests() {
    return platformRequest<PlatformAccessRequest[]>("/api/v1/platform/admin/access-requests", {}, true);
  },
  clinics() {
    return platformRequest<PlatformClinic[]>("/api/v1/platform/admin/clinics", {}, true);
  },
  events() {
    return platformRequest<PlatformEvent[]>("/api/v1/platform/admin/events?limit=200", {}, true);
  },
  billingSettings() {
    return platformRequest<BillingSettings>("/api/v1/platform/admin/billing-settings", {}, true);
  },
  updateBillingSettings(body: Omit<BillingSettings, "id" | "plan_code" | "plan_name" | "subscription_days" | "updated_at">) {
    return platformRequest<BillingSettings>("/api/v1/platform/admin/billing-settings", { method: "PUT", body: JSON.stringify(body) }, true);
  },
  editRequest(id: string, body: Partial<AccessRequestInput> & { admin_note?: string | null }) {
    return platformRequest<PlatformAccessRequest>(`/api/v1/platform/admin/access-requests/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(body) }, true);
  },
  approveRequest(id: string) {
    return platformRequest<{ request: PlatformAccessRequest; email_sent: boolean; email_delivery: string; email_preview?: { subject: string; body: string } | null }>(
      `/api/v1/platform/admin/access-requests/${encodeURIComponent(id)}/approve`, { method: "POST" }, true
    );
  },
  rejectRequest(id: string, reason: string) {
    return platformRequest<PlatformAccessRequest>(`/api/v1/platform/admin/access-requests/${encodeURIComponent(id)}/reject`, { method: "POST", body: JSON.stringify({ reason }) }, true);
  },
  verifyPayment(id: string, payment_reference: string, note?: string) {
    return platformRequest<PlatformAccessRequest>(`/api/v1/platform/admin/access-requests/${encodeURIComponent(id)}/verify-payment`, { method: "POST", body: JSON.stringify({ payment_reference, note }) }, true);
  },
  activate(id: string, body: { tenant_database_url: string; username?: string; first_name: string; last_name: string; branch_name: string; branch_code: string }) {
    return platformRequest<{ clinic: PlatformClinic; email_sent: boolean; email_delivery: string; credentials_preview?: Record<string, string> | null }>(
      `/api/v1/platform/admin/access-requests/${encodeURIComponent(id)}/activate`, { method: "POST", body: JSON.stringify(body) }, true
    );
  },
  renewClinic(id: string, note?: string) {
    return platformRequest<{ clinic: PlatformClinic; renewed_until: string; email_sent: boolean; email_delivery: string }>(
      `/api/v1/platform/admin/clinics/${encodeURIComponent(id)}/renew`, { method: "POST", body: JSON.stringify({ note }) }, true
    );
  },
  suspendClinic(id: string, note?: string) {
    return platformRequest<PlatformClinic>(`/api/v1/platform/admin/clinics/${encodeURIComponent(id)}/suspend`, { method: "POST", body: JSON.stringify({ note }) }, true);
  }
};
