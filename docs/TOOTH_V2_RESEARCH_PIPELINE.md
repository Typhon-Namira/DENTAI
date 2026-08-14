# Tooth AI V2 research pipeline

Tooth V2 is a `RESEARCH_ONLY` tooth-instance localization/segmentation foundation. It does not classify pathology, make autonomous diagnoses, establish clinical validity, or modify the production release gate.

The canonical handoff is:

`Tooth V2 → ToothInstanceOutput[] → future FDI Enumeration Engine`

Each instance exposes an ID, box, optional COCO-style mask RLE, pixel and normalized centroid, confidence, optional upper-arch probability, relative order, and neighboring instance IDs. FDI classification is deliberately downstream: gold FDI is retained as supervision/provenance, but incomplete or abnormal arches are not forced through a geometric enumerator.

Build/rebuild the deterministic corpus with:

```bash
.venv/bin/python -m scripts.build_tooth_v2
```

The builder references originals without changing them, hashes decoded normalized pixels, removes alternate exact supervision copies, keeps patient/case groups atomic when identifiers exist, writes train/validation/locked-test manifests, and records `PATIENT_INDEPENDENCE_UNVERIFIED` when identifiers do not exist.

Model export remains a post-training preparation step. Load a validated `checkpoints/tooth_v2/maskrcnn/best.pt`, export to an experimental path under `model_artifacts/`, run ONNX structural validation and PyTorch/ONNX parity on a fixed evaluation batch, then run the existing CPU benchmark harness. Do not register, quantize, or release the model unless parity and accuracy comparisons exist. `.gitignore` excludes checkpoints, raw/canonical images, and ONNX/PT weights.
