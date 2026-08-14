# Tooth V1 immutable research baseline

`RESEARCH_ONLY`. V1 is frozen; do not modify, overwrite, resume, or retrain `checkpoints/tooth_v1/`.

- Architecture: torchvision Mask R-CNN ResNet-50 FPN V2, ImageNet1K V2 backbone initialization
- Best epoch (zero-based): 7
- Best validation mAP50: 0.714504735529915
- Best validation mAP50:95: 0.3935168571789262
- `best.pt`: SHA-256 `e855eae61a08d932e054777aa815dddbf83cb5e22bd7ca43ce4d0ceaf32da1f5`, 549,336,037 bytes
- `latest.pt`: SHA-256 `88c21d68dd280996cd6932dcab926387d98afff7a52c7733ef7d9ad41e154017`, 549,338,581 bytes, epoch 16
- Primary DENTEX archive SHA-256: `18b2a2dbc5a2b10b0cc6a7677c46a382f4709ab8c9c3bb94f57b74e38e11ffd3`
- Split SHA-256: `2544ad9e38f942f9342d5f5eaaa7af26c377f15ee3aed98ee7de9863db1928a1`
- Config SHA-256: `878fa694c2dc98148fea5bee347f2c1f9dd1d19d0ba0e8dccb479521b05a7244`

The detector/mask heads were randomly initialized; the backbone used ImageNet1K V2 weights. AdamW used learning rate 1e-4 and weight decay 1e-4, with ReduceLROnPlateau (factor 0.5, patience 5). Full augmentation evidence is preserved in the JSON baseline and frozen config.
