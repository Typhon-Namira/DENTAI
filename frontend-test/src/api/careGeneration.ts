import { API_BASE_URL } from "./client";
import type { CarePlan } from "./product";

const SESSION_KEYS = ["teta2-auth", "dentai-test-auth"] as const;

export interface GenerationCandidate {
  finding_id: string;
  tooth_fdi: string;
  finding_type: string;
  finding_types: string[];
  confidence: number | null;
  review_status: string;
  review_recommended: boolean;
  priority_level: string;
  priority_score: number;
}

export interface GenerationReadiness {
  analysis_id: string;
  ready: boolean;
  candidate_count: number;
  confirmed_count: number;
  review_recommended_count: number;
  candidates: GenerationCandidate[];
}

function accessToken(): string {
  for (const key of SESSION_KEYS) {
    const raw = sessionStorage.getItem(key);
    if (!raw) continue;
    try {
      const parsed = JSON.parse(raw) as { accessToken?: unknown };
      if (typeof parsed.accessToken === "string" && parsed.accessToken) return parsed.accessToken;
    } catch {
      // Ignore malformed legacy session storage and try the next supported key.
    }
  }
  throw new Error("Please sign in to continue.");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken()}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(API_BASE_URL + path, { ...init, headers });
  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const object = typeof payload === "object" && payload !== null
      ? payload as Record<string, unknown>
      : {};
    const nested = typeof object.error === "object" && object.error !== null
      ? object.error as Record<string, unknown>
      : {};
    const message = typeof nested.message === "string"
      ? nested.message
      : typeof object.detail === "string"
        ? object.detail
        : typeof payload === "string" && payload
          ? payload
          : `Request failed (${response.status}).`;
    const error = new Error(message) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return payload as T;
}

export const careGenerationApi = {
  readiness(analysisId: string) {
    return request<GenerationReadiness>(
      `/api/v1/care/analyses/${encodeURIComponent(analysisId)}/generation-readiness`
    );
  },
  generate(analysisId: string) {
    return request<CarePlan>(
      `/api/v1/care/analyses/${encodeURIComponent(analysisId)}/generate-plan`,
      { method: "POST" }
    );
  }
};
