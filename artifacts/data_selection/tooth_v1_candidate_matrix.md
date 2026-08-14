# Tooth V1 dataset candidate matrix

Reviewed 2026-08-14. Scores are an engineering rubric (`high`, `medium`, `low`), not a
clinical-quality score. Search snippets were not accepted as evidence; decisions use the linked
primary record or its authoritative data-use statement.

| Candidate | License / state | Actual useful labels | Grouping and duplication | Engineering fit | Recommendation |
|---|---|---|---|---|---|
| Panoramic Dental Xray Dataset V3 ([Mendeley](https://doi.org/10.17632/73n3kz2k4k.3)) | CC BY 4.0; `PRODUCTION_ALLOWED` | Audited root subset: 107 OPGs, 25 annotated, 772 polygons (737 after invalid/duplicate filtering), no FDI | No patient IDs; 11 duplicate-image groups; source-hash grouping required | Mask R-CNN: low; FDI: none | Limited smoke/pilot only |
| Dental panoramic pixel-level segmentation V1 ([Mendeley](https://doi.org/10.17632/jrz4nj82zv.1)) | CC BY 4.0; `PRODUCTION_ALLOWED` | 329 OPGs with binary semantic masks; zero gold tooth instances | No published patient IDs; filenames retain source lineage | Semantic pretraining: medium; Mask R-CNN labels: none | Optional semantic pretraining only; never describe masks as instances |
| InReDD-Dataset-PAN924 v1.0.0 ([PhysioNet](https://doi.org/10.13026/85hv-ct26)) | PhysioNet Contributor Review Health Data Use Agreement 1.5.0; `RESEARCH_ONLY_ACCESS_REQUIRED` | 924 OPGs; 20,033 tooth boxes; 200 OPGs/4,621 polygon masks; FDI and tooth conditions | Random image identifiers; patient linkage unproven; duplicates unaudited | Mask R-CNN: high for 200 masks; detector/FDI: high for 924 | Request credentialing, GCP training, DUA acceptance, and contributor approval |
| TL-pano v2026-02-20 ([Zenodo](https://doi.org/10.5281/zenodo.18715533)) | CC BY-NC-SA 2.0 and explicit non-commercial-only statement; `RESEARCH_ONLY` | 197 annotated + 114 unannotated OPGs; 5,725 tooth polygons with quadrant/type-derived FDI | Patient IDs not published; restricted access | Technically high, commercially prohibited | Exclude from production directories/training |
| AKUDENTAL ([author repository](https://github.com/melihoz/AKUDENTAL), commit `92e2cc3`) | CC BY-NC-SA 4.0; `RESEARCH_ONLY` | Audited 333 OPGs; 8,821 FDI tooth polygons plus 1,136 filling/bridge/implant polygons | No exact duplicates; patient IDs absent; locked 233/58/42 hash-grouped split | Mask R-CNN/FDI: high | Primary research Tooth V1 gold instance source; weights inherit `RESEARCH_ONLY` |
| OdontoAI Open Panoramic Radiographs ([author repository](https://github.com/IvisionLab/OdontoAI-Open-Panoramic-Radiographs)) | No explicit commercial license located; request access; `UNKNOWN_REVIEW_REQUIRED` | 4,000 OPGs; 850 manual and 3,150 HITL; only 2,000 annotations released; permanent/deciduous and FDI | Manual vs HITL distinguishable in documentation; patient IDs/duplicates unverified | Mask R-CNN/FDI: high if rights are granted | Seek written commercial permission and exact terms first |
| STS-2D-Tooth ([Zenodo](https://doi.org/10.5281/zenodo.10597292), pinned HF mirror) | CC BY 4.0; `PRODUCTION_ALLOWED` | Audited 4,000 OPGs; 898 nonempty semantic masks; no instances/FDI | 369 exact duplicate groups/854 entries; hash-grouped split; patient IDs absent | Semantic/SSL: high; Mask R-CNN labels: none | Auxiliary semantic pretraining/SSL only; never instance ground truth |
| DENTEX ([official HF release](https://huggingface.co/datasets/ibrahimhamamci/DENTEX)) | CC BY-NC-SA 4.0; `RESEARCH_ONLY` | Audited 2,032 task images; 24,396 valid polygons; 21,624 FDI tooth polygons across 1,339 FDI task images | 618 exact duplicate groups across supervision levels are hash-grouped; patient IDs not exposed | Mask R-CNN/FDI: high; pathology association: high | Primary research Tooth V1 source; weights inherit `RESEARCH_ONLY` |
| Published YOLO FDI weights ([Mendeley](https://doi.org/10.17632/83k2rtz4bc.1)) | Record CC BY 4.0; framework and underlying private training-data rights unclear; `UNKNOWN_REVIEW_REQUIRED` | Weights report 1,061 OPGs/29,012 mask+box annotations; source images/labels not released there | Training split reported, patient grouping unknown | Transfer: unknown | Do not use weights without written weight/data lineage clearance |

## Decision

`MULTI_DATASET_RESEARCH_READY`.

STS supplies semantic/representation pretraining; DENTEX and AKUDENTAL supply genuine tooth polygons
and FDI; and the small V3 corpus may add localization-only gold polygons after duplicate filtering.
DENTEX also supplies pathology association labels. These supervision streams remain separate. Semantic masks never become
instance ground truth, and box-only cases do not enter mask evaluation. Gold validation/test data are
human annotated and source-hash-group locked. **Patient-level independence is not proven**, so results
are internal research validation, not external clinical validation. Checkpoints using AKUDENTAL or
DENTEX inherit `RESEARCH_ONLY`.
