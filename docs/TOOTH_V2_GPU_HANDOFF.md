# Tooth V2 L4 GPU handoff

The Codex process did not have CUDA access (`torch.cuda.is_available() == False`; `nvidia-smi` could not communicate with a driver). No V2 benchmark, hard-case inference, or training was executed here. Run these from the parent Lightning terminal, where the L4 is visible.

First verify the immutable teacher and CUDA:

```bash
sha256sum checkpoints/tooth_v1/best.pt
.venv/bin/python -c "import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0), torch.version.cuda)"
```

Mine TRAIN-only hard cases (never reads the locked test manifest):

```bash
.venv/bin/python -m scripts.mine_tooth_v2_hard_cases --checkpoint checkpoints/tooth_v1/best.pt --manifest data/splits/tooth_v2/train.json
```

Short real-data L4 benchmarks (25 equal batches per candidate):

```bash
nvidia-smi dmon -s pucvmet -d 1 -o DT > artifacts/architecture/l4_candidate_a_dmon.log & DMON_PID=$!
.venv/bin/python -m ai_engine.training.train --config configs/ai/tooth_v2_maskrcnn.yaml --benchmark-batches 25
kill "$DMON_PID"
```

```bash
nvidia-smi dmon -s pucvmet -d 1 -o DT > artifacts/architecture/l4_candidate_b_dmon.log & DMON_PID=$!
.venv/bin/python -m ai_engine.training.train --config configs/ai/tooth_v2_maskrcnn_fpn_v1.yaml --benchmark-batches 25
kill "$DMON_PID"
```

The metrics JSONL records batch size, accumulation, AMP, peak allocated VRAM, CPU maximum RSS, dataloader/forward/backward/optimizer time, throughput, losses, and validation metrics. The `nvidia-smi dmon` logs capture utilization. Do not begin full training if either run has OOM, non-finite loss, unstable loss, or invalid validation output.

Candidate A is only provisional. After comparing equal-step validation and telemetry, run full training only if A remains selected:

```bash
.venv/bin/python -m ai_engine.training.train --config configs/ai/tooth_v2_maskrcnn.yaml
```

Resume explicitly:

```bash
.venv/bin/python -m ai_engine.training.train --config configs/ai/tooth_v2_maskrcnn.yaml --resume checkpoints/tooth_v2/maskrcnn/latest.pt
```

Monitor without changing the run:

```bash
watch -n 2 nvidia-smi
tail -F checkpoints/tooth_v2/maskrcnn/metrics.jsonl
```

Checkpoints are isolated under `checkpoints/tooth_v2/maskrcnn/`; benchmark checkpoints are under its `benchmark/` child. All remain `RESEARCH_ONLY`.
