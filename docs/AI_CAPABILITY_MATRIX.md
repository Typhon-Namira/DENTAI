# OPG capability matrix

| Capability | Implementation | Dataset/license | Training | Validation | Production enabled |
|---|---|---|---|---|---|
| Image quality gate | Deterministic Pillow/NumPy | Synthetic tests | Not learned | Unit/CPU smoke only | Quality assistance only |
| Tooth segmentation/detection | Registry/interface only | CC BY 4.0 candidates awaiting checksum/review | **Not trained** | None | No (`MODEL_REQUIRED`) |
| FDI numbering | Complete 32-tooth geometry foundation | Synthetic candidates | Not learned | Unit test only | No clinical use |
| Missing-tooth inference | Interface/ontology only | Dataset required | Not trained | None | No |
| Restorations/endodontics | Component boundary/model card | CC BY 4.0 candidate awaiting review | Not trained | None | No |
| Impacted tooth | Component boundary | Dataset required | Not trained | None | No |
| Periapical finding | Component boundary/model card | CC BY 4.0 candidate awaiting review | Not trained | None | No |
| Alveolar bone indicators | Component boundary/model card | Dataset required | Not trained | None | No |
| Recall risk | Rule/policy interface | Unapproved placeholder | Not learned | Unit tested | No interval until clinic approval |
| Longitudinal comparison | New/stable/resolved comparison | Synthetic structures | Not learned | Unit tested | Assistive only |
| Groq summary | Strict optional JSON provider | No image transfer | Not applicable | Schema validation only | When configured |
| Temporal prediction | Interface only | Longitudinal consented data required | **Not trained** | None | No |

No model weights were downloaded, trained, benchmarked, or enabled. There are no clinical metrics or latency claims.

