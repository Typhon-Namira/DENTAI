import type {
  AIAnalysis,
  ApiErrorBody,
  CurrentUser,
  HealthResponse,
  LoginRequest,
  Patient,
  PatientPage,
  PatientProfile,
  RadarDashboard,
  RadarOpportunity,
  RadarOpportunityDetail,
  RadarOpportunityFilters,
  RadarOpportunityPage,
  RadarSource,
  ReviewPayload,
  TokenPair,
  XRay,
  XRayDownloadResponse,
  WhatsAppConnection,
  WhatsAppOutreach
} from "./types";

const rawBaseUrl = import.meta.env.VITE_DENTAI_API_BASE_URL?.trim() ?? "";
export const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");
const SESSION_KEY = "dentai-test-auth";

interface StoredSession {
  accessToken: string;
  refreshToken: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, code: string, message: string, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

function getSession(): StoredSession | null {
  const value = sessionStorage.getItem(SESSION_KEY);
  if (!value) return null;

  try {
    const parsed = JSON.parse(value) as Partial<StoredSession>;
    if (typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string") {
      return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken };
    }
  } catch {
    sessionStorage.removeItem(SESSION_KEY);
  }
  return null;
}

function saveSession(tokens: TokenPair): void {
  sessionStorage.setItem(
    SESSION_KEY,
    JSON.stringify({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token })
  );
}

export function hasSession(): boolean {
  return getSession() !== null;
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  authenticated = true
): Promise<T> {
  const headers = new Headers(init.headers);
  const session = getSession();

  if (authenticated) {
    if (!session) {
      throw new ApiError(401, "NOT_AUTHENTICATED", "Please sign in to continue.");
    }
    headers.set("Authorization", "Bearer " + session.accessToken);
  }

  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(API_BASE_URL + path, { ...init, headers });
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const body: ApiErrorBody =
      typeof payload === "object" && payload !== null ? payload as ApiErrorBody : {};
    const code = body.error?.code ?? "HTTP_" + response.status;
    const message =
      body.error?.message ??
      body.detail ??
      (typeof payload === "string" && payload ? payload : response.statusText);
    throw new ApiError(response.status, code, message, body.error?.request_id);
  }

  return payload as T;
}

function radarQuery(filters: RadarOpportunityFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.tier) params.set("tier", filters.tier);
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.language) params.set("language", filters.language);
  if (filters.location) params.set("location", filters.location);
  if (filters.treatment) params.set("treatment", filters.treatment);
  if (filters.status) params.set("status", filters.status);
  if (typeof filters.minScore === "number") params.set("min_score", String(filters.minScore));
  params.set("limit", "100");
  return params.toString();
}

export const api = {
  health(signal?: AbortSignal) {
    return request<HealthResponse>("/health", { signal }, false);
  },

  ready(signal?: AbortSignal) {
    return request<HealthResponse>("/ready", { signal }, false);
  },

  async login(body: LoginRequest) {
    const tokens = await request<TokenPair>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify(body) },
      false
    );
    saveSession(tokens);
    return tokens;
  },

  me(signal?: AbortSignal) {
    return request<CurrentUser>("/api/v1/auth/me", { signal });
  },

  async logout() {
    const session = getSession();
    if (!session) return;

    try {
      await request<void>("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: session.refreshToken })
      });
    } finally {
      clearSession();
    }
  },

  listPatients(signal?: AbortSignal) {
    return request<PatientPage>("/api/v1/patients?page=1&page_size=100", { signal });
  },

  patientProfile(patientId: string, signal?: AbortSignal) {
    return request<PatientProfile>(
      "/api/v1/patients/" + encodeURIComponent(patientId) + "/profile",
      { signal }
    );
  },

  uploadXray(patientId: string, file: File) {
    const body = new FormData();
    body.append("file", file);
    return request<XRay>(
      "/api/v1/xrays/patients/" + encodeURIComponent(patientId),
      { method: "POST", body }
    );
  },

  xrayDownload(xrayId: string) {
    return request<XRayDownloadResponse>(
      "/api/v1/xrays/" + encodeURIComponent(xrayId) + "/download"
    );
  },

  createAnalysis(xrayId: string) {
    return request<AIAnalysis>("/api/v1/ai-analyses", {
      method: "POST",
      body: JSON.stringify({ xray_id: xrayId })
    });
  },

  whatsappStatus() {
    return request<WhatsAppConnection>("/api/v1/whatsapp/status");
  },

  whatsappQr() {
    return request<WhatsAppConnection>("/api/v1/whatsapp/qr");
  },

  whatsappLogout() {
    return request<WhatsAppConnection>("/api/v1/whatsapp/logout", { method: "POST" });
  },

  savePatientWhatsApp(patientId: string, whatsappPhone: string | null) {
    return request<Patient>("/api/v1/whatsapp/patients/" + encodeURIComponent(patientId), {
      method: "PATCH",
      body: JSON.stringify({ whatsapp_phone: whatsappPhone })
    });
  },

  sendWhatsAppTest(patientId: string, includeImage: boolean) {
    return request<WhatsAppOutreach>(
      "/api/v1/whatsapp/patients/" + encodeURIComponent(patientId) + "/test",
      { method: "POST", body: JSON.stringify({ include_image: includeImage }) }
    );
  },

  patientWhatsAppOutreach(patientId: string) {
    return request<{ items: WhatsAppOutreach[] }>(
      "/api/v1/whatsapp/patients/" + encodeURIComponent(patientId) + "/outreach"
    );
  },

  radarDashboard(signal?: AbortSignal) {
    return request<RadarDashboard>("/api/v1/radar/dashboard", { signal });
  },

  radarSources(signal?: AbortSignal) {
    return request<RadarSource[]>("/api/v1/radar/sources?active=true&limit=200", { signal });
  },

  radarOpportunities(filters: RadarOpportunityFilters = {}, signal?: AbortSignal) {
    return request<RadarOpportunityPage>(
      "/api/v1/radar/opportunities?" + radarQuery(filters),
      { signal }
    );
  },

  radarOpportunity(opportunityId: string, signal?: AbortSignal) {
    return request<RadarOpportunityDetail>(
      "/api/v1/radar/opportunities/" + encodeURIComponent(opportunityId),
      { signal }
    );
  },

  updateRadarOpportunity(opportunityId: string, status: "NEW" | "REVIEWED" | "ARCHIVED") {
    return request<RadarOpportunity>(
      "/api/v1/radar/opportunities/" + encodeURIComponent(opportunityId),
      { method: "PATCH", body: JSON.stringify({ status }) }
    );
  },

  reviewAnalysis(analysisId: string, body: ReviewPayload) {
    return request<AIAnalysis>(
      "/api/v1/ai-analyses/" + encodeURIComponent(analysisId) + "/review",
      { method: "POST", body: JSON.stringify(body) }
    );
  }
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code + ": " + error.message;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}
