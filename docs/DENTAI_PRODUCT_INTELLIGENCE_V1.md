# DENTAI Product Intelligence V1

## Scope and safety boundary

This layer sits above the frozen DENTAI Unified V5 ONNX inference engine. It turns immutable model evidence into patient-case, overlay, review, follow-up, longitudinal, and learning-domain objects. It does not retrain a model, change thresholds, deliver messages, or persist records by itself.

**DENTAI V5 DOES NOT CURRENTLY PREDICT AN EXACT FUTURE DISEASE OCCURRENCE DATE.** It reports present radiographic findings and configurable follow-up prioritization. The dates emitted by the follow-up engine are reassessment scheduling targets derived deterministically from product rules; they are not predictions of failure, symptoms, or progression. A doctor can override the risk level, window, or target date. A future validated longitudinal/time-to-event model would be required for patient-specific event prediction.

## Architecture

The case orchestrator in `ai_engine/product/analyze_case.py` performs:

1. File-type detection and identity extraction.
2. Tenant-scoped candidate patient matching.
3. Frozen ONNX V5 analysis from the original panoramic image.
4. Frontend-ready overlay and per-tooth side-panel construction.
5. Configurable risk and reassessment scheduling.
6. FDI-keyed comparison with an optional previous immutable exam.
7. Review and Learning Vault readiness summaries.

It never creates or merges a patient when identity confirmation is required. The clinical workflow must explicitly confirm, correct, select an existing patient, or create a new one.

## Patient identity

DICOM extraction supports standard PatientName, PatientID, birth date, sex, study date/time and UID, accession, institution, and equipment fields. `pydicom` is an optional runtime adapter. Image OCR uses the `IdentityOCRProvider` interface; the no-op provider is safe by default, and a local Tesseract adapter is available when its optional dependencies are installed.

All extracted fields retain source, confidence, and verification state. OCR and DICOM values begin unverified. OCR output is never authoritative and raw OCR strings should not be written to ordinary application logs. Matching returns ranked candidates using clinic patient ID, DICOM/external IDs, and normalized demographic evidence. It never silently merges ambiguous records. Stable internal IDs use time-sortable, ULID-shaped identifiers such as `PAT-01...`; names are not keys.

Dental patterns such as implants, crowns, and root canal treatment are only a secondary consistency warning. A conflict asks an operator to verify identity and never reassigns a patient.

## Interactive analysis

`opg_overlay.py` preserves original-pixel coordinates and exposes independent toggles for tooth numbers/boxes, findings, restorations, risk, review markers, and changes since the previous exam. Each tooth carries raw status, pathology, restoration, and deep-caries evidence alongside fused findings. Side-panel objects contain current findings, evidence, confidence, review status, doctor verification, reassessment, comparison, and notes without generating a clinical narrative.

## Risk, follow-up, and reminders

`config/dentai_followup_rules.json` is a product-default policy, not a universal clinical guideline. Default windows are 0–1 month for urgent review, 1–3 high, 3–6 medium, 6–12 low, and 12 months routine. Experimental/review findings force review prioritization. Target dates use the end of the configured interval and calendar-month arithmetic. Every output stores reasons and whether a doctor overrode it.

Reminder entities support SMS, email, WhatsApp, and in-app channels. V1 only schedules data through a provider interface; it sends no external messages.

## Longitudinal records

Every study and analysis is immutable and records its model version, manifest hash, thresholds, and timestamp. Comparisons align teeth by resolved FDI and return new, resolved, persistent, changed, restoration, and missing-tooth observations. Confidence movement alone is `STABLE_WITH_CONFIDENCE_CHANGE`; it does not imply progression.

## Doctor feedback and Learning Vault

Doctor actions—confirm, reject, correct, add finding, add note—are separate immutable records containing a snapshot of original AI output. They never overwrite predictions. Label states are UNLABELED, AI_PRELABELED, NEEDS_REVIEW, HUMAN_CORRECTED, VERIFIED, and TRAIN_READY. TRAIN_READY requires the verification policy.

The Learning Vault stores only a link to the source case, model/version and policy states. It must reference a separate de-identified derivative and must not copy name, DOB, contact details, or clinical identifiers. AI output is never automatically ground truth.

## Privacy asset boundaries

- Clinical original: clinic-controlled, immutable diagnostic asset.
- PHI metadata and OCR identity: restricted clinical identity data, encrypted/protected separately.
- De-identified training derivative: separate copy with DICOM PHI removed, direct identifiers replaced, and burned-in text redacted.
- Learning label: de-identified verification/training metadata only.

Never place PII in training filenames, model logs, Learning Vault labels, or training-oriented debug dumps. De-identification never destroys or edits the clinical original.

## Database and tenancy

`database/schema/dentai_product_v1.sql` is provider-neutral PostgreSQL/Supabase-compatible DDL. Image bytes stay in object storage; PostgreSQL stores provider, bucket, key, checksum, MIME type, and size. All clinical tenant tables carry `clinic_id` and have RLS-compatible policies based on `app.current_clinic_id`. Normal clinic roles must not bypass RLS; a backend service role may do so only for explicit authorized operations.

The audit log is logically append-only. Identity confirmation/change, AI analysis, doctor review, follow-up changes, reminder scheduling, exports/deletes, and learning eligibility changes must append events with request and actor context. Application roles receive no update/delete permission on audit rows.

## API contracts and future backend integration

Typed, JSON-serializable request/response contracts for patients, studies, analysis, overlay, identity confirmation, reviews, timelines, follow-ups, reminders, and learning status live in `schemas.py`. They deliberately do not select a web framework or database provider.

Railway packaging is intentionally outside this phase. A future service can bind these contracts and SQL to authenticated routes, object storage, transactions, and RLS, then call the existing ONNX CPU engine. Before production use it must add secrets management, encryption, retention/deletion policy, consent policy, authorization testing, DICOM/OCR runtime dependencies, monitoring, backups, and external clinical validation.
