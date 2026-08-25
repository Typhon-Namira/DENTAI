# DENTAI Unified V5 — Model Card

## Release identity

- Model ID: `dentai-unified-v5`
- Frozen bundle manifest: `artifacts/production/dentai_v5_model_manifest.json`
- Deployment mode: assistive clinician review
- Autonomous diagnosis: not approved
- Clinical review required for AI findings: yes

The frozen manifest is the source of truth for the exact ONNX filenames, SHA-256 digests, operating thresholds, preprocessing contracts, class mappings, validation metrics, and available ONNX export/parity metadata.

## Intended use

DENTAI Unified V5 is intended to assist a qualified dental clinician reviewing panoramic dental X-rays. Its findings are decision-support evidence and must not be treated as an autonomous diagnosis or as a replacement for clinician interpretation.

## Runtime release contract

A production worker must fail closed unless all of the following hold:

1. The registry explicitly enables `dentai-unified-v5` in assistive clinician-review mode.
2. The frozen bundle manifest is present, identifies `dentai-unified-v5`, and has `freeze_status=PRODUCTION_FROZEN`.
3. The manifest contains validation metrics, operating thresholds, and reproducible ONNX export metadata.
4. The deployed artifact directory contains exactly the nine ONNX files named by the frozen manifest.
5. Every deployed ONNX file matches the SHA-256 digest recorded in the frozen manifest.
6. The deployment remains clinician-review-required.

CI validates release metadata and manifest structure. Runtime startup validates the actual deployed model bytes.

## Model components

The bundle contains separate heads for tooth detection, FDI assignment, status gate, tooth status, pathology, deep caries, restoration detection/classification, plus the detector preprocessing ONNX graph. The exact component definitions are recorded in the frozen manifest.

## Validation and limitations

Validation results differ materially by task and class. The frozen manifest must be consulted for exact per-head and per-class metrics before making product decisions.

Known limitations include weaker performance for some pathology classes. In particular, the currently frozen manifest reports substantially lower precision/recall for `BONE_RESORPTION` and `FURCATION_LESION` than for several other classes. These findings therefore require clinician review and must not be interpreted as autonomous clinical conclusions.

The release registry intentionally does **not** claim calibration evidence or autonomous clinical approval when those artifacts are not present. Enabling an autonomous deployment mode requires stronger evidence and is fail-closed by the release validator.

## Confidence semantics

Each displayed finding must use confidence/provenance from the head that produced that finding. A score from one head must not be reused as the score of a different finding type. Product visibility, summaries, and outreach must consume the finding-specific score and provenance.

## Change control

Changing any ONNX file, threshold, preprocessing contract, model version, class mapping, or bundle manifest requires a new frozen release identity and re-validation. Production must never silently accept a modified artifact under the same frozen release.
