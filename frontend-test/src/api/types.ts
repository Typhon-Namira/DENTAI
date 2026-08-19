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
  provenance: FindingProvenance | null;
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

export interface XRayDownloadResponse {
  url: string;
  expires_in: number;
}

export interface ReviewPayload {
  decisions: Array<{
    finding_id: string;
    decision: ReviewDecision;
  }>;
}

export interface WhatsAppConnection {
  connected: boolean;
  connection: string;
  sender: string | null;
  qr?: string | null;
}

export type WhatsAppOutreachStatus =
  | "QUEUED"
  | "SCHEDULED"
  | "CLAIMED"
  | "SENDING"
  | "SEND_UNKNOWN"
  | "SENT"
  | "FAILED"
  | "CANCELLED";

export interface WhatsAppOutreach {
  id: string;
  patient_id: string;
  analysis_id: string;
  finding_id: string | null;
  source_finding_ids: string[];
  tooth_fdi: string;
  finding_type: string;
  recommended_window: string;
  target_followup_at: string;
  scheduled_send_at: string;
  message: string;
  language: string;
  status: WhatsAppOutreachStatus;
  provider_message_id: string | null;
  attempt_count: number;
  retry_at: string | null;
  timing_reason: string;
  timing_policy_version: string;
  created_at: string;
  sent_at: string | null;
  failed_at: string | null;
  safe_error: string | null;
}

export type RadarPlatform = "INSTAGRAM" | "FACEBOOK" | "TELEGRAM" | "WEB";
export type RadarTier = "HOT" | "WARM" | "RESEARCH" | "IGNORE";
export type RadarOpportunityStatus = "NEW" | "REVIEWED" | "ARCHIVED";

export interface RadarDashboard {
  hot: number;
  warm: number;
  research: number;
  ignored: number;
  sources_monitored: number;
  new_signals_24h: number;
  new_opportunities_24h: number;
  generated_at: string;
}

export interface RadarSource {
  id: string;
  platform: RadarPlatform;
  external_source_id: string;
  source_type: string;
  name: string;
  handle: string | null;
  source_url: string;
  language_hints: string[];
  location_hint: string | null;
  armenia_relevance: number;
  engagement_score: number;
  dental_signal_probability: number;
  source_score: number;
  priority: "HIGH" | "MEDIUM" | "LOW" | "INACTIVE";
  monitoring_interval_minutes: number;
  is_active: boolean;
  last_polled_at: string | null;
  last_content_at: string | null;
  next_check_at: string | null;
  source_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RadarOpportunity {
  id: string;
  platform: RadarPlatform;
  author_display: string | null;
  author_profile_url: string | null;
  language: string;
  location: string | null;
  treatment: string | null;
  intent: string;
  urgency: string;
  opportunity_score: number;
  tier: RadarTier;
  status: RadarOpportunityStatus;
  first_seen_at: string;
  last_seen_at: string;
  signal_count: number;
  explanation: string;
  evidence_summary: Record<string, unknown>;
  scoring_rule_set: string;
  scoring_rule_version: string;
  created_at: string;
  updated_at: string;
}

export interface RadarOpportunityPage {
  items: RadarOpportunity[];
  total: number;
  limit: number;
  offset: number;
}

export interface RadarSignal {
  id: string;
  source_id: string;
  opportunity_id: string | null;
  platform: RadarPlatform;
  external_signal_id: string | null;
  signal_type: string;
  text: string;
  context_text: string | null;
  source_url: string;
  author_display: string | null;
  language: string;
  location: string | null;
  treatment: string | null;
  intent: string;
  urgency_label: string;
  dental_relevance: number;
  treatment_intent: number;
  location_match: number;
  urgency_score: number;
  recency_score: number;
  recommendation_intent: number;
  classifier_confidence: number;
  opportunity_score: number;
  tier: RadarTier;
  is_candidate: boolean;
  evidence: Record<string, unknown>;
  observed_at: string;
  published_at: string | null;
}

export interface RadarOpportunityDetail {
  opportunity: RadarOpportunity;
  signals: RadarSignal[];
}

export interface RadarOpportunityFilters {
  tier?: string;
  platform?: string;
  language?: string;
  location?: string;
  treatment?: string;
  status?: string;
  minScore?: number;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
  detail?: string;
}
