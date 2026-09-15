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
  subscription_plan: string | null;
  subscription_state: "ACTIVE" | "FREE_EXPIRED" | "EXPIRED" | "PAYMENT_REVIEW" | string;
  subscription_starts_at: string | null;
  subscription_expires_at: string | null;
  subscription_days_remaining: number | null;
  subscription_seconds_remaining: number | null;
  free_trial_started_at: string | null;
  upgrade_requested_at: string | null;
  entitlements: {
    patient_limit: number | null;
    opg_per_patient_limit: number | null;
    followup_teeth_per_opg_limit: number | null;
  };
}

export interface Patient {
  id: string;
  patient_number: string;
  first_name: string;
  last_name: string;
  date_of_birth: string | null;
  sex: string | null;
  phone: string | null;
  whatsapp_phone: string | null;
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
  total?: number;
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

export interface VisionEvidenceTooth {
  fdi?: string | number | null;
  raw_fdi?: string;
  fdi_confidence?: number;
  fdi_was_changed?: boolean;
  duplicate_cleanup_applied?: boolean;
  fdi_review_required?: boolean;
  quadrant_candidates?: string[];
  resolved_quadrant?: string | null;
  side_constraint_applied?: boolean;
  side_constraint_overrode_raw_quadrant?: boolean;
  tooth_detection?: {
    instance_id?: number;
    bbox_xyxy?: unknown;
  };
}

export interface GroqFindingEvidence {
  evidence_id: string;
  tooth_fdi: string;
  finding_type: string;
  model_score: number;
  review_required: boolean;
  uncertainty: string;
  uncertainty_reason: string | null;
  review_reasons: string[];
  source_model: string;
  model_version: string;
}

export interface GroqToothExplanation {
  tooth_fdi: string;
  evidence_ids: string[];
  headline: string;
  clinical_explanation: string;
  review_explanation: string;
}

export type GroqClinicalSummaryStatus = "AVAILABLE" | "PARTIAL";

export interface GroqClinicalSummary {
  status: GroqClinicalSummaryStatus;
  doctor_summary: string;
  tooth_explanations: GroqToothExplanation[];
  important_changes: string[];
  monitoring_points: string[];
  questions_for_doctor: string[];
  patient_message_draft: string;
  canonical_evidence: Record<string, GroqFindingEvidence>;
  failed_tooth_fdis: string[];
}

export interface AIAnalysisStructuredResult {
  [key: string]: unknown;
  vision_evidence?: {
    teeth?: unknown;
  };
  clinical_summary?: unknown;
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
  structured_result: AIAnalysisStructuredResult | null;
  review_status: ReviewStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface FindingProvenance {
  [key: string]: unknown;
  bounding_box?: [number, number, number, number];
  source_model?: string;
  model_version?: string;
  raw_score?: number;
  uncertainty?: string;
  uncertainty_reason?: string | null;
  review_required?: boolean;
  review_reasons?: string[];
  raw_fdi?: string;
  fdi_confidence?: number;
  fdi_was_changed?: boolean;
  duplicate_cleanup_applied?: boolean;
  fdi_review_required?: boolean;
  tooth_detection_instance_id?: number;
  quadrant_candidates?: string[];
  resolved_quadrant?: string | null;
  side_constraint_applied?: boolean;
  side_constraint_overrode_raw_quadrant?: boolean;
  bbox_xyxy?: [number, number, number, number];
}

export interface DentalFinding {
  id: string;
  analysis_id: string;
  tooth_code: string | null;
  finding_type: string;
  confidence: number | null;
  provenance: FindingProvenance | null;
  review_status: FindingReview;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface PatientProfile {
  patient: Patient;
  assignments: Record<string, unknown>[];
  visits: Record<string, unknown>[];
  xrays: XRay[];
  ai_analyses: AIAnalysis[];
  findings: DentalFinding[];
  future_risk: Record<string, unknown>[];
  future_care: Record<string, unknown>[];
  followups: Record<string, unknown>[];
  care_plans?: Record<string, unknown>[];
  conversations?: Record<string, unknown>[];
  appointments?: Record<string, unknown>[];
}

export interface XRayDownloadResponse {
  url: string;
  expires_in: number;
}

export interface ApiErrorBody {
  detail?: string;
  error?: { code?: string; message?: string; request_id?: string };
}

export interface ReviewPayload {
  decision: ReviewDecision;
}

export interface WhatsAppConnection {
  connected: boolean;
  connection: string;
  sender: string | null;
  qr?: string | null;
}

export interface WhatsAppOutreach {
  id: string;
  patient_id: string;
  finding_id?: string | null;
  status: string;
  message: string;
  scheduled_send_at?: string | null;
  sent_at?: string | null;
  failed_at?: string | null;
  attempt_count?: number;
  provider_message_id?: string | null;
  image_storage_key?: string | null;
  last_error?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface RadarDashboard { [key: string]: unknown; }
export interface RadarOpportunity { id: string; [key: string]: unknown; }
export interface RadarOpportunityDetail extends RadarOpportunity { [key: string]: unknown; }
export interface RadarOpportunityFilters { tier?: string; platform?: string; language?: string; location?: string; treatment?: string; status?: string; minScore?: number; }
export interface RadarOpportunityPage { items: RadarOpportunity[]; [key: string]: unknown; }
export interface RadarSource { id: string; [key: string]: unknown; }
