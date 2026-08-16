# DENTAI Product Intelligence V2

## Purpose and immutable AI boundary

V2 extends Product Intelligence V1; it does not replace it. The frozen DENTAI Unified V5 ONNX CPU engine remains the inference dependency. V2 does not change checkpoints, model weights, calibrated thresholds, ONNX graphs, detector geometry, or resolver behavior. Complete raw AI output is copied into an append-only analysis record before product presentation and doctor corrections are added.

DENTAI is clinical decision support. It reports current radiographic findings and configurable monitoring/reassessment recommendations. It does **not** guarantee future disease, predict an exact occurrence date, or replace dentist review. Preferred language is “review recommended,” “risk signal,” “monitoring suggested,” and “reassessment target.”

## Repository integration

The repository contains a FastAPI backend with signed-token clinic resolution, authorization dependencies, X-ray object-storage references, clinical routes, and audit logging. It does not contain a checked-in frontend application. Accordingly, V2 adds product/domain services, dashboard-ready JSON, typed API contracts, and additive SQL. It intentionally does not create a disconnected demo page or claim a rendered frontend.

The existing backend uses physically resolved clinic databases, while `dentai_product_v1.sql` describes a shared-database RLS-compatible deployment. `dentai_product_v2.sql` is an additive migration for the latter. Either deployment must retain a trusted clinic context; no client-supplied clinic ID may establish authorization.

## Identity extraction and states

`identity_v2.py` defines the replaceable `IdentityExtractor` boundary. OCR adapters return structured fields with value, normalized value, confidence, source region, and source. Raw OCR text is supported but classified as restricted clinical data and must not enter ordinary logs. A DICOM adapter reads standard metadata when optional `pydicom` is installed. The no-op extractor produces no identity and never fabricates one.

V2 states are:

- `IDENTITY_FOUND`: verified identity information is available.
- `IDENTITY_NOT_FOUND`: no usable identity evidence.
- `IDENTITY_REVIEW_REQUIRED`: weak, name-only, ambiguous, or conflicting evidence.
- `IDENTITY_MATCHED_EXISTING`: a strong exact clinic/DICOM/external identifier matches within the active clinic.
- `IDENTITY_NEW_PATIENT_CANDIDATE`: sufficiently strong nonmatching information; creation still requires verification.

Exact clinic-local ID has priority. Name alone never auto-associates. A name conflicting with an exact identifier forces review. Matching searches only the active clinic. A study may be explicitly assigned after operator confirmation; V2 never merges patients automatically.

## Patient, study, and analysis model

`PatientProfile` stores only stable internal ID, clinic ID, display name, clinic-local identifier, optional DOB, identity state/confidence, and timestamps. Names are not primary keys.

Studies retain immutable object-storage metadata, checksum, study date, identity state, and optional patient association. Analyses retain study/patient association, model and manifest identifiers, thresholds, timestamp, full raw AI output, and product output. New analyses append; historical AI evidence is never edited. Doctor corrections are separate records.

## Longitudinal and tooth history

Timeline queries are tenant-scoped and sort immutable studies chronologically. Tooth history uses resolved FDI and retains finding, status, and restoration evidence per analysis. Structurally compatible changes can be new, resolved, persistent, improved, or progressed. Confidence-only changes remain `STABLE_WITH_CONFIDENCE_CHANGE`. Unknown/incompatible finding transitions are `CHANGE_UNCERTAIN`; V2 does not invent progression.

## Dashboard presentation contract

`dashboard.py` produces `dentai-dashboard-v2` JSON for the future workstation:

- Left: patient and analysis summary.
- Center: primary OPG viewer with selectable teeth.
- Right: clinical intelligence and ordered priorities.
- Bottom: tooth history and follow-up timeline.

Default toggles show teeth, FDI, pathology, restorations, and status. Confidence and debug are off. Each selected tooth exposes structured evidence, review state, follow-up, and deterministic dentist-facing explanations. The dashboard never guesses an uncertain patient: it displays “Identity requires review” or “Patient not identified.”

No frontend source tree exists in this repository, so rendered responsive UI, pointer/zoom behavior, and visual QA remain future frontend work. The JSON contract and 32-tooth Image-111 dashboard fixture are validated.

## Clinical intelligence and explanations

Overall assessment counts teeth, urgent/high findings, review cases, follow-up candidates, restorations, and pathology. Priority sorting is urgent review, high, medium/routine review, then monitoring. `explanations.py` deterministically maps structured findings to cautious technical text for dentists. It uses no LLM and never converts confidence into certainty.

## Explainable follow-up

`config/dentai_followup_rules.json` now carries rule-set/version metadata and stable rule IDs. Every per-tooth recommendation retains priority, window, target, reasons, source findings, FDI, rule IDs/version, status, and doctor-override state. Dates are deterministic reassessment targets, not predicted clinical events. Completion creates an auditable status transition without rewriting the original recommendation.

## Doctor review and Learning Vault

Supported doctor actions include confirm, reject, correct, add finding/note, modify status, and modify FDI. Each record stores reviewer, timestamp, original evidence snapshot, action, corrected value, and notes. Patient confirmation/assignment and follow-up completion are separate audited workflows.

Doctor review creates a Learning Vault candidate with source study/analysis references, model version, correction payload, reviewer, verification/de-identification state, and policy eligibility. It does not update production weights. Training eligibility stays false until verification, de-identification, and policy requirements succeed. Direct patient demographics are excluded from Learning Vault records.

## Database, tenancy, storage, and audit

`database/schema/dentai_product_v2.sql` extends V1 with identity candidates/reviews, product outputs, tooth history snapshots, explainable follow-up events, and Learning Vault records. It adds follow-up rule provenance and completion fields. Every patient-related table contains `clinic_id`, enables RLS, and checks `app.current_clinic_id`. Ordinary clinic roles must not receive `BYPASSRLS` or table-owner credentials.

Original images remain in provider-neutral object storage. PostgreSQL stores provider, bucket, key, SHA-256, MIME type, and size—not large image blobs. Immutable triggers reject update/delete for original studies, analyses, prediction evidence, product outputs, tooth snapshots, Learning Vault evidence, and audit rows.

Authentication must precede tenant selection. The backend derives clinic context from a validated token/server-side registry, authorizes the actor, and only then opens/query-scopes clinical storage. Audit events record identity decisions, patient/study creation, analysis, doctor review, follow-up completion, and Learning Vault changes without logging raw OCR/PII payloads.

## API boundaries

`schemas.py` defines JSON contracts for:

- `POST /studies`, `POST /studies/{study_id}/analyze`, `GET /studies/{study_id}`
- `GET /studies/{study_id}/overlay`, `GET /studies/{study_id}/dashboard`
- `GET /patients/{patient_id}`, timeline, and per-FDI tooth history
- identity review and explicit patient assignment
- doctor review
- study follow-ups and follow-up completion
- reminders and Learning Vault status

These are transport contracts, not newly exposed unauthenticated routes. Wiring them to FastAPI requires the production PostgreSQL repository, migrations, authorization checks, and transactional audit writes.

## Acceptance and performance

`product_intelligence_v2_acceptance.py` executes two real ONNX analyses of Image 111 and a synthetic two-clinic workflow. The recorded run produced 32 teeth/32 unique FDI for both OPGs, explicit confirmation for the name-only second study, a two-study timeline, two FDI-36 history entries, an immutable doctor correction, completed follow-up, Learning Vault record, audit events, and enforced cross-clinic denial.

Measured on the acceptance host with four ONNX CPU threads:

- Standalone image decode/preprocessing diagnostic: about 0.048 s.
- No-op OCR: about 0.00001 s (not representative of a real OCR provider).
- ONNX model load: about 3.18 s.
- ONNX inference: about 9.89 s/image mean over two runs.
- Product intelligence plus reference-store persistence: about 0.083 s for the synthetic workflow.
- Total measured two-OPG work: about 19.87 s, excluding model load.

No live PostgreSQL was configured, so database network/transaction latency is explicitly unavailable; in-memory reference-store timing must not be represented as PostgreSQL performance. A production OCR provider was also not configured.

## Known limitations and deployment gate

- No rendered frontend exists here; only dashboard-ready backend presentation data is complete.
- API contracts are not wired to a production PostgreSQL adapter in this phase.
- Live PostgreSQL migrations/RLS and transaction behavior require integration testing.
- OCR quality, latency, burned-in-text coverage, and DICOM pixel conversion require configured providers/dependencies.
- Follow-up defaults require clinic governance and are not universal clinical schedules.
- Identity encryption/key management, consent/retention policy, backup/restore, and threat-model testing remain deployment work.
- Clinical validation remains required before clinical deployment. DENTAI must not be described as clinically validated based on repository acceptance tests.
- Railway packaging is intentionally not created in V2.
