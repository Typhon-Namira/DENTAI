import type {
  AIAnalysis,
  ApiErrorBody,
  CurrentUser,
  HealthResponse,
  LoginRequest,
  PatientPage,
  PatientProfile,
  ReviewPayload,
  TokenPair,
  XRay,
  XRayDownloadResponse
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
