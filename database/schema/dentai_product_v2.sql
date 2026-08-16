-- DENTAI Product Intelligence V2 additive migration.
-- Apply after dentai_product_v1.sql. This file never replaces V1 tables.
BEGIN;

ALTER TABLE followup_plans ADD COLUMN IF NOT EXISTS source_findings jsonb NOT NULL DEFAULT '[]';
ALTER TABLE followup_plans ADD COLUMN IF NOT EXISTS rule_ids jsonb NOT NULL DEFAULT '[]';
ALTER TABLE followup_plans ADD COLUMN IF NOT EXISTS rule_version text NOT NULL DEFAULT '1.0';
ALTER TABLE followup_plans ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'OPEN';
ALTER TABLE followup_plans ADD COLUMN IF NOT EXISTS completed_at timestamptz;
ALTER TABLE followup_plans ADD COLUMN IF NOT EXISTS completed_by text;

CREATE TABLE IF NOT EXISTS identity_candidates (
 candidate_id text PRIMARY KEY,
 clinic_id text NOT NULL REFERENCES clinics,
 study_id text NOT NULL REFERENCES opg_studies,
 state text NOT NULL,
 extracted_fields_encrypted text,
 normalized_match_tokens_hmac jsonb NOT NULL DEFAULT '{}',
 raw_ocr_text_encrypted text,
 provider text NOT NULL,
 confidence numeric NOT NULL CHECK (confidence BETWEEN 0 AND 1),
 source_regions jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS identity_reviews (
 identity_review_id text PRIMARY KEY,
 clinic_id text NOT NULL REFERENCES clinics,
 study_id text NOT NULL REFERENCES opg_studies,
 candidate_id text REFERENCES identity_candidates,
 patient_id text REFERENCES patients,
 action text NOT NULL CHECK (action IN ('CONFIRM','REJECT','ASSIGN_EXISTING','CREATE_VERIFIED_PATIENT','CORRECT')),
 previous_reference text,
 new_reference text,
 reviewed_by text NOT NULL,
 reviewed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product_intelligence_outputs (
 product_output_id text PRIMARY KEY,
 clinic_id text NOT NULL REFERENCES clinics,
 analysis_id text NOT NULL UNIQUE REFERENCES dental_analyses,
 schema_version text NOT NULL DEFAULT 'dentai-product-v2',
 overlay jsonb NOT NULL,
 clinical_intelligence jsonb NOT NULL,
 longitudinal_comparison jsonb,
 created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tooth_history_snapshots (
 tooth_history_id text PRIMARY KEY,
 clinic_id text NOT NULL REFERENCES clinics,
 patient_id text NOT NULL REFERENCES patients,
 study_id text NOT NULL REFERENCES opg_studies,
 analysis_id text NOT NULL REFERENCES dental_analyses,
 fdi text NOT NULL,
 findings jsonb NOT NULL,
 status_evidence jsonb NOT NULL,
 restoration_evidence jsonb NOT NULL,
 change_state text NOT NULL DEFAULT 'UNKNOWN',
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE (analysis_id,fdi)
);

CREATE TABLE IF NOT EXISTS follow_up_events (
 follow_up_event_id text PRIMARY KEY,
 clinic_id text NOT NULL REFERENCES clinics,
 patient_id text NOT NULL REFERENCES patients,
 study_id text NOT NULL REFERENCES opg_studies,
 analysis_id text NOT NULL REFERENCES dental_analyses,
 tooth_fdi text,
 priority text NOT NULL,
 target_date date NOT NULL,
 reasons jsonb NOT NULL,
 source_findings jsonb NOT NULL,
 rule_ids jsonb NOT NULL,
 rule_version text NOT NULL,
 status text NOT NULL DEFAULT 'OPEN',
 completed_at timestamptz,
 completed_by text,
 created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_vault_records (
 learning_vault_id text PRIMARY KEY,
 clinic_id text NOT NULL REFERENCES clinics,
 source_study_id text NOT NULL REFERENCES opg_studies,
 source_analysis_id text NOT NULL REFERENCES dental_analyses,
 source_model_version text NOT NULL REFERENCES model_versions,
 doctor_review_id text REFERENCES doctor_reviews,
 correction_payload jsonb NOT NULL,
 verification_status text NOT NULL,
 deidentification_status text NOT NULL,
 deidentified_image_id text REFERENCES opg_images,
 training_eligibility boolean NOT NULL DEFAULT false,
 consent_or_policy_reference text,
 created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_identity_candidates_clinic_study ON identity_candidates(clinic_id,study_id);
CREATE INDEX IF NOT EXISTS ix_identity_reviews_clinic_study ON identity_reviews(clinic_id,study_id);
CREATE INDEX IF NOT EXISTS ix_tooth_history_patient_fdi ON tooth_history_snapshots(clinic_id,patient_id,fdi,created_at);
CREATE INDEX IF NOT EXISTS ix_follow_up_events_clinic_status_target ON follow_up_events(clinic_id,status,target_date);

DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['identity_candidates','identity_reviews','product_intelligence_outputs','tooth_history_snapshots','follow_up_events','learning_vault_records'] LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',t);
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname=current_schema() AND tablename=t AND policyname=t||'_clinic_isolation') THEN
   EXECUTE format('CREATE POLICY %I ON %I USING (clinic_id = current_setting(''app.current_clinic_id'', true)) WITH CHECK (clinic_id = current_setting(''app.current_clinic_id'', true))',t||'_clinic_isolation',t);
  END IF;
 END LOOP;
END $$;

-- Immutable clinical evidence: application roles append but cannot mutate these records.
CREATE OR REPLACE FUNCTION dentai_reject_immutable_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION '% is append-only',TG_TABLE_NAME; END $$;
DO $$ DECLARE t text; trigger_name text; BEGIN
 FOREACH t IN ARRAY ARRAY['opg_studies','dental_analyses','tooth_predictions','finding_predictions','product_intelligence_outputs','tooth_history_snapshots','learning_vault_records','audit_log'] LOOP
  trigger_name='trg_'||t||'_immutable';
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname=trigger_name) THEN
   EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I FOR EACH ROW EXECUTE FUNCTION dentai_reject_immutable_mutation()',trigger_name,t);
  END IF;
 END LOOP;
END $$;

-- Authentication is outside RLS: the backend must authenticate first, set
-- app.current_clinic_id from trusted token context, and authorize the actor.
-- Ordinary clinic roles receive no BYPASSRLS and no direct table-owner credentials.
COMMIT;
