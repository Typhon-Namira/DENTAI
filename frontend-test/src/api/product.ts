import type { Patient, Role } from "./types";

const SESSION_KEYS = ["teta2-auth", "dentai-test-auth"] as const;

interface StoredSession {
  accessToken: string;
  refreshToken: string;
}

export interface BranchSummary {
  id: string;
  code?: string | null;
  name: string;
  is_active?: boolean;
  [key: string]: unknown;
}

export interface DashboardSummary {
  patient_count?: number;
  doctor_count?: number;
  manager_count?: number;
  branch_count?: number;
  ai_analysis_count?: number;
  followup_count?: number;
  authorized_patient_count?: number;
  authorized_doctor_count?: number;
  assigned_patient_count?: number;
  followups_due?: number;
  recent_xrays?: unknown[];
  recent_ai_analyses?: unknown[];
  [key: string]: unknown;
}

export type FollowUpStatus = "SCHEDULED" | "DUE" | "COMPLETED" | "CANCELLED";
export type FollowUpPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";

export interface FollowUp {
  id: string;
  patient_id: string;
  doctor_id: string | null;
  branch_id: string;
  reason: string;
  due_at: string;
  status: FollowUpStatus;
  priority: FollowUpPriority | string;
  notes: string | null;
  created_by?: string;
  completed_at?: string | null;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
}

export interface FollowUpPage {
  items: FollowUp[];
  page: number;
  page_size: number;
}

function storedSession(): StoredSession | null {
  for (const key of SESSION_KEYS) {
    const raw = sessionStorage.getItem(key);
    if (!raw) continue;
    try {
      const parsed = JSON.parse(raw) as Partial<StoredSession>;
      if (typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string") {
        return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken };
      }
    } catch {
      // Ignore malformed legacy storage and continue to the next key.
    }
  }
  return null;
}

async function productRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = storedSession();
  if (!session) throw new Error("Please sign in to continue.");
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${session.accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const body = typeof payload === "object" && payload !== null ? payload as Record<string, unknown> : {};
    const error = body.error && typeof body.error === "object" ? body.error as Record<string, unknown> : {};
    const message = typeof error.message === "string"
      ? error.message
      : typeof body.detail === "string"
        ? body.detail
        : typeof payload === "string" && payload
          ? payload
          : response.statusText;
    throw new Error(message || `Request failed (${response.status}).`);
  }
  return payload as T;
}

export const productApi = {
  dashboard(role: Role) {
    return productRequest<DashboardSummary>(`/api/v1/dashboard/${role.toLowerCase()}`);
  },

  branches() {
    return productRequest<BranchSummary[]>("/api/v1/branches");
  },

  createPatient(body: {
    patient_number: string;
    first_name: string;
    last_name: string;
    branch_id: string;
  }) {
    return productRequest<Patient>("/api/v1/patients", {
      method: "POST",
      body: JSON.stringify(body)
    });
  },

  listFollowUps(status?: FollowUpStatus) {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (status) params.set("status", status);
    return productRequest<FollowUpPage>(`/api/v1/follow-ups?${params.toString()}`);
  },

  createFollowUp(patientId: string, body: {
    reason: string;
    due_at: string;
    priority: FollowUpPriority;
    notes?: string | null;
    doctor_id?: string | null;
  }) {
    return productRequest<FollowUp>(`/api/v1/patients/${encodeURIComponent(patientId)}/follow-ups`, {
      method: "POST",
      body: JSON.stringify(body)
    });
  },

  updateFollowUp(followUpId: string, status: FollowUpStatus) {
    return productRequest<FollowUp>(`/api/v1/follow-ups/${encodeURIComponent(followUpId)}`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });
  }
};
