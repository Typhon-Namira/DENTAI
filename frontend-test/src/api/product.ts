import type { Patient, Role } from "./types";

const SESSION_KEYS = ["teta2-auth", "dentai-test-auth"] as const;

interface StoredSession { accessToken: string; refreshToken: string; }
export interface BranchSummary { id: string; code?: string | null; name: string; is_active?: boolean; [key: string]: unknown; }
export interface DashboardSummary { appointments_awaiting_approval?: number; active_care_plans?: number; active_conversations?: number; followups_due?: number; notification_count?: number; alerts?: Array<{kind:string;entity_id:string;patient_id:string}>; upcoming_appointments?: CareAppointment[]; generated_at?: string; [key: string]: unknown; }
export type FollowUpStatus = "SCHEDULED" | "DUE" | "COMPLETED" | "CANCELLED";
export type FollowUpPriority = "LOW" | "NORMAL" | "HIGH" | "URGENT";
export interface FollowUp { id: string; patient_id: string; doctor_id: string | null; branch_id: string; reason: string; due_at: string; status: FollowUpStatus; priority: FollowUpPriority | string; notes: string | null; created_by?: string; completed_at?: string | null; created_at?: string; updated_at?: string; [key: string]: unknown; }
export interface FollowUpPage { items: FollowUp[]; page: number; page_size: number; }

export interface PatientCreateInput {
  patient_number: string;
  first_name: string;
  last_name: string;
  branch_id: string;
  date_of_birth?: string | null;
  sex?: string | null;
  phone?: string | null;
  whatsapp_phone?: string | null;
  email?: string | null;
}

export interface CareSettings {
  id: string; branch_id: string; timezone: string; working_days: number[]; day_start: string; day_end: string;
  appointment_minutes: number; slot_interval_minutes: number; min_booking_notice_minutes: number; booking_horizon_days: number;
  buffer_minutes: number; preferred_times: unknown[]; blocked_windows: unknown[]; auto_followup_enabled: boolean;
  auto_outreach_after_review: boolean; attach_tooth_image: boolean; default_language: string; booking_instructions: string | null;
}
export interface CarePlanItem { id: string; finding_id: string; tooth_fdi: string; finding_type: string; confidence: number | null; recommended_window: string; target_followup_at: string; status: string; rationale: string; message_preview: string | null; }
export interface CarePlan { id: string; patient_id: string; analysis_id: string; branch_id: string; doctor_id: string | null; status: string; language: string; summary: string | null; created_at: string; items: CarePlanItem[]; }
export interface CareAppointment { id: string; patient_id: string; branch_id: string; doctor_id: string | null; conversation_id: string | null; care_plan_item_id: string | null; starts_at: string; ends_at: string; timezone: string; status: string; source: string; tooth_fdi: string | null; finding_type: string | null; reason: string; doctor_note: string | null; reschedule_count: number; notification_status?:string; notification_attempt_count?:number; notification_error?:string|null; patient?: Patient | null; }
export interface CareConversation { id: string; patient_id: string; care_plan_id: string | null; branch_id: string; whatsapp_phone: string; language: string; status: string; summary: string | null; last_message_at: string | null; patient?: Patient | null; latest_appointment?: CareAppointment | null; }
export interface CareMessage { id: string; conversation_id: string; direction: "IN" | "OUT"; body: string; language: string; status: string; provider_message_id: string | null; created_at: string; }
export interface AvailabilityException { id:string; branch_id:string; doctor_id:string|null; starts_at:string; ends_at:string; kind:"UNAVAILABLE"|"BREAK"; reason:string|null; }

function storedSession(): StoredSession | null {
  for (const key of SESSION_KEYS) {
    const raw = sessionStorage.getItem(key);
    if (!raw) continue;
    try { const parsed = JSON.parse(raw) as Partial<StoredSession>; if (typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string") return { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken }; } catch { /* ignore malformed legacy storage */ }
  }
  return null;
}

async function productRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = storedSession();
  if (!session) throw new Error("Please sign in to continue.");
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${session.accessToken}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers });
  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const body = typeof payload === "object" && payload !== null ? payload as Record<string, unknown> : {};
    const error = body.error && typeof body.error === "object" ? body.error as Record<string, unknown> : {};
    const message = typeof error.message === "string" ? error.message : typeof body.detail === "string" ? body.detail : typeof payload === "string" && payload ? payload : response.statusText;
    throw new Error(message || `Request failed (${response.status}).`);
  }
  return payload as T;
}

export const productApi = {
  dashboard(_role?: Role) { return productRequest<DashboardSummary>("/api/v1/care/dashboard"); },
  branches() { return productRequest<BranchSummary[]>("/api/v1/branches"); },
  createPatient(body: PatientCreateInput) { return productRequest<Patient>("/api/v1/patients", { method: "POST", body: JSON.stringify(body) }); },
  updatePatient(id:string, body:Partial<Omit<PatientCreateInput,"patient_number"|"branch_id">>) { return productRequest<Patient>(`/api/v1/patients/${encodeURIComponent(id)}`, {method:"PATCH",body:JSON.stringify(body)}); },
  setPatientArchived(id:string, archived:boolean) { return productRequest<Patient>(`/api/v1/patients/${encodeURIComponent(id)}/${archived?"archive":"restore"}`, {method:"POST"}); },
  listFollowUps(status?: FollowUpStatus) { const params = new URLSearchParams({ page: "1", page_size: "100" }); if (status) params.set("status", status); return productRequest<FollowUpPage>(`/api/v1/follow-ups?${params.toString()}`); },
  createFollowUp(patientId: string, body: { reason: string; due_at: string; priority: FollowUpPriority; notes?: string | null; doctor_id?: string | null; }) { return productRequest<FollowUp>(`/api/v1/patients/${encodeURIComponent(patientId)}/follow-ups`, { method: "POST", body: JSON.stringify(body) }); },
  updateFollowUp(followUpId: string, status: FollowUpStatus) { return productRequest<FollowUp>(`/api/v1/follow-ups/${encodeURIComponent(followUpId)}`, { method: "PATCH", body: JSON.stringify({ status }) }); },

  careSettings(branchId: string) { return productRequest<CareSettings>(`/api/v1/care/settings/${encodeURIComponent(branchId)}`); },
  updateCareSettings(branchId: string, body: Omit<CareSettings, "id" | "branch_id">) { return productRequest<CareSettings>(`/api/v1/care/settings/${encodeURIComponent(branchId)}`, { method: "PUT", body: JSON.stringify(body) }); },
  carePlans(patientId?: string) { const query = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : ""; return productRequest<CarePlan[]>(`/api/v1/care/plans${query}`); },
  generateCarePlan(analysisId: string) { return productRequest<CarePlan>(`/api/v1/care/analyses/${encodeURIComponent(analysisId)}/generate-plan`, { method: "POST" }); },
  updateCarePlanItem(planId: string, itemId: string, body: { target_followup_at?: string; recommended_window?: string; rationale?: string; message_preview?: string | null; }) { return productRequest<CarePlanItem>(`/api/v1/care/plans/${encodeURIComponent(planId)}/items/${encodeURIComponent(itemId)}`, { method: "PATCH", body: JSON.stringify(body) }); },
  approveCarePlan(planId: string) { return productRequest<CarePlan>(`/api/v1/care/plans/${encodeURIComponent(planId)}/approve`, { method: "POST" }); },
  transitionCarePlan(planId:string, action:"reject"|"pause"|"resume"|"complete", reason?:string) { return productRequest<CarePlan>(`/api/v1/care/plans/${encodeURIComponent(planId)}/${action}`, {method:"POST",body:JSON.stringify({reason:reason||null})}); },
  completeCarePlanItem(planId:string,itemId:string) { return productRequest<CarePlanItem>(`/api/v1/care/plans/${encodeURIComponent(planId)}/items/${encodeURIComponent(itemId)}/complete`,{method:"POST"}); },
  careAppointments(start: string, end: string, status?: string) { const params = new URLSearchParams({ start, end }); if (status) params.set("status", status); return productRequest<CareAppointment[]>(`/api/v1/care/appointments?${params.toString()}`); },
  requestCareReschedule(appointmentId: string, preferredStart: string | null, doctorNote?: string) { return productRequest<CareAppointment>(`/api/v1/care/appointments/${encodeURIComponent(appointmentId)}/reschedule`, { method: "POST", body: JSON.stringify({ preferred_start: preferredStart, doctor_note: doctorNote || null }) }); },
  confirmCareAppointment(appointmentId: string) { return productRequest<CareAppointment>(`/api/v1/care/appointments/${encodeURIComponent(appointmentId)}/approve`, { method: "POST" }); },
  transitionCareAppointment(appointmentId:string,action:"reject"|"cancel"|"complete",reason?:string) { return productRequest<CareAppointment>(`/api/v1/care/appointments/${encodeURIComponent(appointmentId)}/${action}`,{method:"POST",body:JSON.stringify({reason:reason||null})}); },
  careConversations() { return productRequest<CareConversation[]>("/api/v1/care/conversations"); },
  careConversationMessages(conversationId: string) { return productRequest<CareMessage[]>(`/api/v1/care/conversations/${encodeURIComponent(conversationId)}/messages`); },
  availabilityExceptions(branchId:string) { return productRequest<AvailabilityException[]>(`/api/v1/care/availability/${encodeURIComponent(branchId)}/exceptions`); },
  createAvailabilityException(branchId:string,body:{starts_at:string;ends_at:string;kind:"UNAVAILABLE"|"BREAK";reason?:string|null}) { return productRequest<AvailabilityException>(`/api/v1/care/availability/${encodeURIComponent(branchId)}/exceptions`,{method:"POST",body:JSON.stringify(body)}); },
  deleteAvailabilityException(branchId:string,id:string) { return productRequest<void>(`/api/v1/care/availability/${encodeURIComponent(branchId)}/exceptions/${encodeURIComponent(id)}`,{method:"DELETE"}); },
  availableSlots(branchId:string) { return productRequest<{timezone:string;slots:string[]}>(`/api/v1/care/availability/${encodeURIComponent(branchId)}/slots`); }
};
