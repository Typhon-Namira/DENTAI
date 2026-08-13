# Tooth model card

- Status: `DATASET_REQUIRED`; no production checkpoint bundled.
- Intended use: tooth segmentation/detection and FDI mapping assistance on OPG images.
- Non-intended use: diagnosis, pediatric numbering without validation, surgical planning.
- Candidate data: registered CC BY 4.0 tooth datasets after checksum and ethics/license review.
- Architecture candidate: permissive torchvision/MONAI segmentation; not selected or trained.
- Metrics/thresholds: none. No performance claim.
- Failure modes: missing/impacted teeth, mixed dentition, restorations, implants, positioning and projection artifacts.

