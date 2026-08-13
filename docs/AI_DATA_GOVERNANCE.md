# AI data governance

Public-data inclusion requires an immutable manifest, exact version, source, license review, commercial-use decision, attribution obligations, archive checksum, and patient-level split key. Unknown or noncommercial material fails closed and cannot enter production training. Research artifacts and production artifacts must use separate roots and registries.

Clinical operational data is not training data. A future export requires clinic authorization, applicable consent/legal basis, de-identification, explicit record inclusion, audit logging, a dataset version, and independent access controls. No live clinic record is automatically sampled or used for online learning. Model manifests bind every checkpoint hash to its training dataset manifests and metrics.

