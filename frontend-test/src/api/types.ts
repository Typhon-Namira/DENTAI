export type Role = "DIRECTOR" | "MANAGER" | "DOCTOR";
export type AIStatus = "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
export type ReviewStatus = "UNREVIEWED" | "REVIEWED";
export type FindingReview = "PENDING" | "CONFIRMED" | "REJECTED";
export type ReviewDecision = Exclude<FindingReview, "PENDING">;

export interface HealthResponse {
  status: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface LoginRequest {
  clinic_slug: string;
  identifier: string;
  password: string;
}

export interface CurrentUser {
  id: string;
  clinic_id: string;
  username: string;
  email: string;
  role: Role;
  branch_scope: string[];
}

export interface Patient {
  id: string;
  patient_number: string;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  sex: string | null;
  phone: string | null;
  email: string | null;
  branch_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface PatientPage {
  items: Patient[];
  page: number;
  page_size: number;
}

export interface XRay {
  id: string;
  patient_id: string;
  uploaded_by: string;
  branch_id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  captured_at: string | null;
  uploaded_at: string;
}

export interface AIAnalysis {
  id: string;
  patient_id: string;
  xray_id: string;
  requested_by: string;
  status: AIStatus;
  provider: string;
  model_name: string;
  model_version: string;
  analysis_schema_version: string;
  requested_at: string;
  processing_started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_code: string | null;
  attempt_count: number;
  max_attempts: number;
  worker_id: string | null;
  claimed_at: string | null;
  heartbeat_at: string | null;
  retry_at: string | null;
  structured_result: Record<string, unknown> | null;
  review_status: ReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface DentalFinding {
  id: string;
  patient_id: string;
  analysis_id: string | null;
  tooth_code: string | null;
  finding_type: string;
  description: string;
  source: string;
  confidence: number | null;
  provenance: Record<string, unknown> | null;
  review_status: FindingReview;
  confirmed_by: string | null;
  confirmed_at: string | null;
  created_at: string;
}

export interface PatientProfile {
  patient: Patient;
  assignments: Array<Record<string, unknown>>;
  visits: Array<Record<string, unknown>>;
  xrays: XRay[];
  ai_analyses: AIAnalysis[];
  findings: DentalFinding[];
  future_risk: Array<Record<string, unknown>>;
  future_care: Array<Record<string, unknown>>;
  followups: Array<Record<string, unknown>>;
}

export interface ReviewPayload {
  decisions: Array<{
    finding_id: string;
    decision: ReviewDecision;
  }>;
  clinical_notes?: string | null;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
  detail?: string;
}
