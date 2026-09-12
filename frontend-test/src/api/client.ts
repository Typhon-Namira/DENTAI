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

export function resolveApiBaseUrl(value: string | undefined): string {
  const candidate = (value ?? "").trim().replace(/\/$/, "");
  if (!candidate) return "";
  if (/^(?:https?:\/\/)?api-domain(?::|\/|$)/i.test(candidate) || /\.example(?::|\/|$)/i.test(candidate)) {
    return "";
  }
  if (candidate.startsWith("/")) return candidate;
  try {
    const url = new URL(candidate);
    return url.protocol === "https:" || url.protocol === "http:" ? candidate : "";
  } catch {
    return "";
  }
}

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_DENTAI_API_BASE_URL);
const SESSION_KEY = "dentai-test-auth";
const LEGACY_SESSION_KEY = "teta2-auth";
const SESSION_KEYS = [SESSION_KEY, LEGACY_SESSION_KEY] as const;

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

function parseStoredSession(value: string): StoredSession | null {
  try {
    const parsed = JSON.parse(value) as Partial<StoredSession>;
    if (typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string") {
      return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken };
    }
  } catch {
    return null;
  }
  return null;
}

function getSession(): StoredSession | null {
  for (const key of SESSION_KEYS) {
    const value = sessionStorage.getItem(key);
    if (!value) continue;
    const parsed = parseStoredSession(value);
    if (!parsed) {
      sessionStorage.removeItem(key);
      continue;
    }
    if (key !== SESSION_KEY) {
      sessionStorage.setItem(SESSION_KEY, value);
      sessionStorage.removeItem(key);
    }
    return parsed;
  }
  return null;
}

function saveSession(tokens: TokenPair): StoredSession {
  const stored = { accessToken: tokens.access_token, refreshToken: tokens.refresh_token };
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(stored));
  sessionStorage.removeItem(LEGACY_SESSION_KEY);
  return stored;
}

export function hasSession(): boolean {
  return getSession() !== null;
}

export function clearSession(): void {
  for (const key of SESSION_KEYS) sessionStorage.removeItem(key);
}

let refreshPromise: Promise<StoredSession | null> | null = null;

async function refreshSession(): Promise<StoredSession | null> {
  const session = getSession();
  if (!session) return null;
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(API_BASE_URL + "/api/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({ refresh_token: session.refreshToken })
      });
      if (!response.ok) {
        if (response.status === 400 || response.status === 401 || response.status === 403) {
          clearSession();
        }
        return null;
      }
      const payload = await response.json() as TokenPair;
      if (typeof payload.access_token !== "string" || typeof payload.refresh_token !== "string") {
        clearSession();
        return null;
      }
      return saveSession(payload);
    } catch {
      return null;
    }
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function fetchWithNetworkRetry(
  path: string,
  init: RequestInit,
  headers: Headers,
  networkAttempts: number,
  timeoutMs: number
): Promise<Response> {
  let response: Response | undefined;
  let lastNetworkError: unknown;
  for (let attempt = 1; attempt <= networkAttempts; attempt += 1) {
    const timeout = new AbortController();
    const timer = globalThis.setTimeout(() => timeout.abort(), timeoutMs);
    const abort = () => timeout.abort();
    init.signal?.addEventListener("abort", abort, { once: true });
    try {
      response = await fetch(API_BASE_URL + path, { ...init, headers, signal: timeout.signal });
      break;
    } catch (error) {
      lastNetworkError = error;
      if (init.signal?.aborted || attempt === networkAttempts) break;
      await new Promise((resolve) => globalThis.setTimeout(resolve, 250 * attempt));
    } finally {
      globalThis.clearTimeout(timer);
      init.signal?.removeEventListener("abort", abort);
    }
  }
  if (!response) {
    const detail = lastNetworkError instanceof Error ? lastNetworkError.message : "Network request failed";
    throw new ApiError(0, "API_UNAVAILABLE", `The clinic service is temporarily unavailable. Please retry. (${detail})`);
  }
  return response;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  authenticated = true,
  networkAttempts = 1,
  timeoutMs = 20_000
): Promise<T> {
  const headers = new Headers(init.headers);
  const session = getSession();
  if (authenticated) {
    if (!session) throw new ApiError(401, "NOT_AUTHENTICATED", "Please sign in to continue.");
    headers.set("Authorization", "Bearer " + session.accessToken);
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response = await fetchWithNetworkRetry(path, init, headers, networkAttempts, timeoutMs);
  if (authenticated && response.status === 401) {
    const refreshed = await refreshSession();
    if (refreshed) {
      headers.set("Authorization", "Bearer " + refreshed.accessToken);
      response = await fetchWithNetworkRetry(path, init, headers, 1, timeoutMs);
    }
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const body: ApiErrorBody =
      typeof payload === "object" && payload !== null ? payload as ApiErrorBody : {};
    const code = body.error?.code ?? "HTTP_" + response.status;
    const message = body.error?.message ?? body.detail ??
      (typeof payload === "string" && payload ? payload : response.statusText);
    throw new ApiError(response.status, code, message, body.error?.request_id);
  }
  return payload as T;
}

export function authenticatedRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(path, init);
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
  health(signal?: AbortSignal) { return request<HealthResponse>("/health", { signal }, false); },
  ready(signal?: AbortSignal) { return request<HealthResponse>("/ready", { signal }, false); },

  async login(body: LoginRequest) {
    const tokens = await request<TokenPair>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify(body) },
      false,
      3,
      8_000
    );
    saveSession(tokens);
    return tokens;
  },

  me(signal?: AbortSignal) { return request<CurrentUser>("/api/v1/auth/me", { signal }); },

  changePassword(currentPassword: string, newPassword: string) {
    return request<void>("/api/v1/auth/password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
  },

  async logout() {
    const session = getSession();
    if (!session) return;
    try {
      await request<void>("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: session.refreshToken })
      }, false);
    } finally {
      clearSession();
    }
  },

  listPatients(signal?: AbortSignal, status = "ACTIVE") {
    return request<PatientPage>(`/api/v1/patients?page=1&page_size=100&status=${encodeURIComponent(status)}`, { signal });
  },
  patientProfile(patientId: string, signal?: AbortSignal) {
    return request<PatientProfile>("/api/v1/patients/" + encodeURIComponent(patientId) + "/profile", { signal });
  },
  uploadXray(patientId: string, file: File) {
    const body = new FormData();
    body.append("file", file);
    return request<XRay>("/api/v1/xrays/patients/" + encodeURIComponent(patientId), { method: "POST", body });
  },
  xrayDownload(xrayId: string) {
    return request<XRayDownloadResponse>("/api/v1/xrays/" + encodeURIComponent(xrayId) + "/download");
  },
  createAnalysis(xrayId: string) {
    return request<AIAnalysis>("/api/v1/ai-analyses", { method: "POST", body: JSON.stringify({ xray_id: xrayId }) });
  },
  retryAnalysis(analysisId: string) {
    return request<AIAnalysis>("/api/v1/ai-analyses/" + encodeURIComponent(analysisId) + "/retry", { method: "POST" });
  },

  whatsappStatus() { return request<WhatsAppConnection>("/api/v1/whatsapp/status"); },
  whatsappQr() { return request<WhatsAppConnection>("/api/v1/whatsapp/qr"); },
  whatsappLogout() { return request<WhatsAppConnection>("/api/v1/whatsapp/logout", { method: "POST" }); },
  savePatientWhatsApp(patientId: string, whatsappPhone: string | null) {
    return request<Patient>("/api/v1/whatsapp/patients/" + encodeURIComponent(patientId), {
      method: "PATCH", body: JSON.stringify({ whatsapp_phone: whatsappPhone })
    });
  },
  sendWhatsAppTest(patientId: string, includeImage: boolean) {
    return request<WhatsAppOutreach>("/api/v1/whatsapp/patients/" + encodeURIComponent(patientId) + "/test", {
      method: "POST", body: JSON.stringify({ include_image: includeImage })
    });
  },
  patientWhatsAppOutreach(patientId: string) {
    return request<{ items: WhatsAppOutreach[] }>("/api/v1/whatsapp/patients/" + encodeURIComponent(patientId) + "/outreach");
  },

  radarDashboard(signal?: AbortSignal) {
    return request<RadarDashboard>("/api/v1/radar/dashboard", { signal });
  },
  radarRuntime(signal?: AbortSignal) {
    return request<{
      worker_expected: boolean;
      active_sources: number;
      due_sources: number;
      unhealthy_sources: number;
      action_required_sources: number;
      last_success_at: string | null;
      llm_semantic_refinement: boolean;
      collectors: Record<string, { ready?: boolean; mode?: string; detail?: string; configured?: boolean; reachable?: boolean }>;
      sources: Record<string, {
        state: string;
        collector: string | null;
        last_error_code: string | null;
        last_error: string | null;
        last_signal_count: number;
        last_new_signal_count: number;
        consecutive_failures: number;
        last_success_at: string | null;
        last_duration_ms: number | null;
        source_revision: string | null;
        claimed_by: string | null;
      }>;
    }>("/api/v1/radar/runtime", { signal });
  },
  radarSources(signal?: AbortSignal) {
    return request<RadarSource[]>("/api/v1/radar/sources?limit=200", { signal });
  },
  createRadarSource(body: {
    platform: string;
    source_type: string;
    name: string;
    source_url: string;
    handle?: string | null;
    location_hint?: string | null;
    armenia_relevance?: number;
    engagement_score?: number;
    dental_signal_probability?: number;
  }) {
    return request<RadarSource>("/api/v1/radar/sources", { method: "POST", body: JSON.stringify(body) });
  },
  runRadarSource(sourceId: string) {
    return request<{
      source_id: string;
      status: string;
      collector?: string | null;
      signals_seen: number;
      new_signals: number;
      candidate_signals: number;
      duration_ms?: number | null;
      error_code?: string | null;
      error?: string | null;
      retryable?: boolean | null;
    }>("/api/v1/radar/sources/" + encodeURIComponent(sourceId) + "/run", { method: "POST" });
  },
  updateRadarSource(sourceId: string, body: { is_active?: boolean }) {
    return request<RadarSource>("/api/v1/radar/sources/" + encodeURIComponent(sourceId), {
      method: "PATCH", body: JSON.stringify(body)
    });
  },
  radarOpportunities(filters: RadarOpportunityFilters = {}, signal?: AbortSignal) {
    return request<RadarOpportunityPage>("/api/v1/radar/opportunities?" + radarQuery(filters), { signal });
  },
  radarOpportunity(opportunityId: string, signal?: AbortSignal) {
    return request<RadarOpportunityDetail>("/api/v1/radar/opportunities/" + encodeURIComponent(opportunityId), { signal });
  },
  updateRadarOpportunity(opportunityId: string, status: "NEW" | "REVIEWED" | "ARCHIVED") {
    return request<RadarOpportunity>("/api/v1/radar/opportunities/" + encodeURIComponent(opportunityId), {
      method: "PATCH", body: JSON.stringify({ status })
    });
  },
  radarConnections(signal?: AbortSignal) {
    return request<Array<{
      id: string; platform: string; provider: string; status: string; account_display?: string | null;
      expires_at?: string | null; last_health_at?: string | null; last_error_code?: string | null; metadata?: Record<string, unknown>;
    }>>("/api/v1/radar/connections", { signal });
  },
  startRadarMeta(platform: "FACEBOOK" | "INSTAGRAM") {
    return request<{ connection: { id: string }; authorization_url: string; state: string }>(
      "/api/v1/radar/connections/meta/start",
      { method: "POST", body: JSON.stringify({ platform }) }
    );
  },
  completeRadarMeta(connectionId: string, code: string, state: string) {
    return request<unknown>("/api/v1/radar/connections/" + encodeURIComponent(connectionId) + "/meta/complete", {
      method: "POST", body: JSON.stringify({ code, state })
    });
  },
  startRadarTelegram(phone: string) {
    return request<{ connection: { id: string; status: string }; next: string }>(
      "/api/v1/radar/connections/telegram/start",
      { method: "POST", body: JSON.stringify({ phone }) }
    );
  },
  completeRadarTelegram(connectionId: string, code: string, password?: string) {
    return request<{ connection: { id: string; status: string }; next: string }>(
      "/api/v1/radar/connections/" + encodeURIComponent(connectionId) + "/telegram/complete",
      { method: "POST", body: JSON.stringify({ code, password: password || null }) }
    );
  },
  disconnectRadarConnection(connectionId: string) {
    return request<unknown>("/api/v1/radar/connections/" + encodeURIComponent(connectionId), { method: "DELETE" });
  },
  radarMetrics(signal?: AbortSignal) {
    return request<{ signals_24h: number; candidates_24h: number; candidate_yield: number }>("/api/v1/radar/metrics", { signal });
  },
  radarCalibration(signal?: AbortSignal) {
    return request<{ sample_size: number; ready_for_recalibration: boolean; policy: string }>("/api/v1/radar/calibration", { signal });
  },
  recordRadarOutcome(opportunityId: string, outcome: string) {
    return request<unknown>("/api/v1/radar/opportunities/" + encodeURIComponent(opportunityId) + "/outcomes", {
      method: "POST", body: JSON.stringify({ outcome, metadata: {} })
    });
  },

  reviewAnalysis(analysisId: string, body: ReviewPayload) {
    return request<AIAnalysis>("/api/v1/ai-analyses/" + encodeURIComponent(analysisId) + "/review", {
      method: "POST", body: JSON.stringify(body)
    });
  }
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.code + ": " + error.message;
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}
