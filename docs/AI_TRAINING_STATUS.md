# AI training status — 2026-08-13

## Honest capability state

No clinical OPG model has been trained, validated, exported, or approved in this repository. No
production model is enabled. The real provider is fail-closed and emits no clinical findings.

## Lightning CPU preparation audit

- Ubuntu 24.04.4, Python 3.12.11, 4 logical CPU cores, 16.47 GB RAM
- CPU runtime confirmed: PyTorch reports no CUDA device
- 383.6 GB free after retaining 727 MB of audited data
- Reproducible ML extra and CPU-only PyTorch source are locked; GPU installation is documented

## Dataset decision log

Primary Mendeley records and actual files were rechecked. `jrz4nj82zv.1` contains 329 image/mask
pairs under CC BY 4.0, but its masks are semantic rather than instance masks. `73n3kz2k4k.3`
contains only 25 polygon-annotated root-level images (737 instances), 82 empty annotation entries,
and exact duplicates. Patient identifiers are absent. It is not adequate alone for Tooth V1.
MOPG-7 remains excluded under CC BY-NC 4.0.

Tooth V1 therefore remains `DATASET_REQUIRED`. Its Mask R-CNN configuration, evaluation plumbing,
checkpoint metadata, ONNX plumbing, and CPU benchmark harness are implemented, but real training is
blocked until an adequately sized, commercially compatible, patient-groupable instance dataset is
available. Synthetic smoke results are plumbing evidence only.

## Release boundary

`python scripts/validate_ai_release.py` is the authoritative pre-release evidence gate. It currently
fails intentionally. A passing gate is necessary but not sufficient for clinical deployment;
external validation, clinician review, privacy review, monitoring, rollback rehearsal, and applicable
medical-device/regulatory assessment remain required.
