# AI training status — 2026-08-13

## Honest capability state

No clinical OPG model has been trained, validated, exported, or approved in this repository. No
production model is enabled. The real provider is fail-closed and emits no clinical findings.

## Environment audit

- Python 3.12.13, Windows, 8 logical CPU cores
- No detected PyTorch, torchvision, ONNX, ONNX Runtime, OpenCV, MONAI, or verified CUDA stack
- Approximately 1.28 GB of free system-drive space at audit time

This is insufficient to safely retain the selected archive, extracted images, a CPU training stack,
checkpoints, and evaluation artifacts. Download and training were therefore not attempted. Synthetic
smoke results are plumbing evidence only and are never clinical evidence.

## Dataset decision log

Current Mendeley records were manually rechecked. The tooth segmentation dataset
`jrz4nj82zv.1` reports 329 panoramic images with pixel masks and CC BY 4.0. Its registry remains
`UNKNOWN_REVIEW_REQUIRED` because the distributable archive has not been downloaded and hashed.
MOPG-7 remains `RESEARCH_ONLY` under CC BY-NC 4.0. Derived or augmented images must share a
patient/source lineage group before splitting to prevent leakage.

## Release boundary

`python scripts/validate_ai_release.py` is the authoritative pre-release evidence gate. It currently
fails intentionally. A passing gate is necessary but not sufficient for clinical deployment;
external validation, clinician review, privacy review, monitoring, rollback rehearsal, and applicable
medical-device/regulatory assessment remain required.
