# Tooth V2 dataset forensic audit

The repository contains 11 locally audited OPG datasets plus three authorization-gated sources. Only DENTEX and AKUDENTAL currently provide compatible gold tooth-instance polygons with FDI labels. They form the V2 gold corpus; semantic-mask datasets remain pretraining/external-domain candidates, and pathology/classification datasets remain difficult-domain image pools. Their labels were not reinterpreted as teeth.

After decoded-pixel duplicate grouping and removal of alternate supervision copies, the corpus contains **1,385 unique OPGs**, **28,827 tooth instances**, and **28,827 FDI-labelled instances**. It is split deterministically into 1,108 train, 139 validation, and 138 locked test OPGs. Exactly 260 duplicate supervision records were removed. Near-duplicate threshold analysis was not completed; 256-bit perceptual hashes are retained for review. Patient/case identity is unavailable, so the only defensible status is `PATIENT_INDEPENDENCE_UNVERIFIED`.

Detailed dimensions, intensity/color modes, corrupt paths, annotation distributions, duplicate groups, and per-record hashes remain in each existing `artifacts/data_audit/*.json` source audit. InReDD is absent locally and requires PhysioNet contributor approval. No access or labels were invented.
