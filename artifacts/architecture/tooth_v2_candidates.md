# Tooth V2 architecture candidates

Status: `CANDIDATES_DEFINED_BENCHMARK_PENDING`; all outputs remain `RESEARCH_ONLY`.

Candidate A is torchvision `maskrcnn_resnet50_fpn_v2`: the measured V1 architecture, now trained on the deduplicated multi-source V2 corpus with stronger OPG-safe photometric augmentation. Candidate B is torchvision `maskrcnn_resnet50_fpn`, a mature comparison with the earlier FPN heads and somewhat lower implementation complexity. Both provide boxes and masks, use the same BSD-3-Clause framework, avoid a new major dependency, and have established PyTorch/ONNX paths.

Candidate A is the provisional recommendation because it has the lowest migration risk and a real V1 reference point. This is not a performance conclusion. Select the final model only after equal-step validation comparison, including mask quality, adjacent-tooth separation, hard cases, peak VRAM, throughput, latency, CPU feasibility, and export parity.

Mask2Former-style systems were not added merely for novelty: this repository does not currently carry a mature compatible implementation, and adding Detectron2/Transformers would materially enlarge dependency and export risk. A deployment-light candidate should be introduced later only with a maintained instance-mask implementation, not by presenting semantic segmentation as equivalent.
