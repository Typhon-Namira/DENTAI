# Research OPG acquisition status

Verified 2026-08-14 from primary records. `RESEARCH_ONLY` data are permitted for this phase but
remain barred from production model lineage.

| Dataset | Access | License | Local state | Technical role |
|---|---|---|---|---|
| InReDD-PAN924 v1.0.0 | Contributor Review | PhysioNet Health Data Use Agreement 1.5.0 | Blocked: credentialing, recognized GCP training, DUA and contributor project approval required | 20,033 tooth boxes; 4,621 FDI masks |
| DENTEX | Public official Hugging Face release | CC BY-NC-SA 4.0 | Downloaded, checksum-verified, extracted, audited and converted at `7b27ccc8` | 21,624 FDI tooth polygons; pathology labels |
| OdontoAI | Publisher email request | Research-only grant; no redistribution/modification/commercial use | Blocked: a professor must email `lrebouca@ufba.br` from an institutional account with the signed request PDF | Tooth instances and FDI |
| AKUDENTAL | Public official Git repository | CC BY-NC-SA 4.0 | Downloaded/audited at commit `92e2cc3` | Primary research tooth instances/FDI |
| TL-pano | Zenodo restricted access | CC BY-NC-SA 2.0 plus non-commercial research statement | Blocked: depositor approval required | Tooth polygons/FDI |
| STS-2D-Tooth | Public Zenodo; pinned HF packaging | CC BY 4.0 | Four Parquet objects downloaded, checksum verified and audited | Semantic/SSL adult and child OPGs |
| Panoramic Dental Xray V3 | Public Mendeley | CC BY 4.0 | Downloaded/audited | Small localization-only instance supplement |
| Tooth Segmentation V1 | Public Mendeley | CC BY 4.0 | Downloaded/audited | Semantic auxiliary supervision |
| MOPG-7 v2 | Public Mendeley | CC BY-NC 4.0 | Downloaded/audited | Tooth condition boxes |
| Restorative/endodontic | Public Mendeley | CC BY 4.0 | Downloaded/audited | Restoration and endodontic polygons |
| Apicoectomy | Public Mendeley | CC BY 4.0 | Downloaded/audited | Endodontic/pathology boxes |
| Kennedy | Public Mendeley | CC BY 4.0 | Downloaded/audited; class meanings unresolved | `UNKNOWN_UNMAPPED` boxes |
| Dental Implant Dataset | Public Mendeley | CC BY 4.0 | Archive checksum verified and extracted | Implant-type classification |

No authentication, DUA, restricted repository, or institutional approval was bypassed.
