import { API_BASE_URL, ApiError } from "../api/client";
import type { Patient } from "../api/types";

const SESSION_KEY = "dentai-test-auth";

function accessToken(): string {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) throw new ApiError(401, "NOT_AUTHENTICATED", "Please sign in to continue.");
  try {
    const parsed = JSON.parse(raw) as { accessToken?: unknown };
    if (typeof parsed.accessToken === "string" && parsed.accessToken) return parsed.accessToken;
  } catch {
    // handled below
  }
  throw new ApiError(401, "NOT_AUTHENTICATED", "Please sign in to continue.");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${accessToken()}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(API_BASE_URL + path, { ...init, headers });
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const body = typeof payload === "object" && payload !== null ? payload as { error?: { code?: string; message?: string; request_id?: string }; detail?: string } : {};
    throw new ApiError(
      response.status,
      body.error?.code ?? `HTTP_${response.status}`,
      body.error?.message ?? body.detail ?? (typeof payload === "string" ? payload : response.statusText),
      body.error?.request_id
    );
  }
  return payload as T;
}

export interface BranchRecord {
  id: string;
  name: string;
  code?: string;
  is_active?: boolean;
}

export interface FollowUpRecord {
  id: string;
  patient_id: string;
  doctor_id?: string | null;
  branch_id: string;
  reason: string;
  due_at: string;
  status: "SCHEDULED" | "DUE" | "COMPLETED" | "CANCELLED" | string;
  priority: string;
  notes?: string | null;
  created_at?: string;
  completed_at?: string | null;
}

export type DashboardRecord = Record<string, number | string | unknown[]>;

export const v5Api = {
  branches() {
    return request<BranchRecord[]>("/api/v1/branches");
  },
  dashboard(role: string) {
    return request<DashboardRecord>(`/api/v1/dashboard/${encodeURIComponent(role.toLowerCase())}`);
  },
  createPatient(body: { patient_number: string; first_name: string; last_name: string; branch_id: string }) {
    return request<Patient>("/api/v1/patients", { method: "POST", body: JSON.stringify(body) });
  },
  listFollowUps(status?: string) {
    const query = status ? `?status=${encodeURIComponent(status)}&page=1&page_size=100` : "?page=1&page_size=100";
    return request<{ items: FollowUpRecord[]; page: number; page_size: number }>("/api/v1/follow-ups" + query);
  },
  updateFollowUp(id: string, status: "SCHEDULED" | "DUE" | "COMPLETED" | "CANCELLED") {
    return request<FollowUpRecord>(`/api/v1/follow-ups/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ status }) });
  }
};
