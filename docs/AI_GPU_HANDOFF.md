# Tooth V1 GPU handoff

Status on 2026-08-14: research data are ready, but this Studio is CPU-only (`nvidia-smi` is absent
and `torch.cuda.is_available()` is false). No real training was started and the locked test split has
not been evaluated. All DENTEX/AKUDENTAL-derived checkpoints must remain `RESEARCH_ONLY`.

The primary corpus is official DENTEX at pinned commit `7b27ccc8`, converted to 21,624 FDI tooth
polygons. Its locked, SHA-256-grouped manifest contains 933 train, 193 validation and 186 test images
with nonempty tooth annotations. Patient independence cannot be proven. AKUDENTAL is a separately
locked auxiliary instance/FDI corpus; STS-2D-Tooth and Tooth Segmentation V1 are semantic/SSL
auxiliaries and must never be represented as gold instances.

## Exact next commands

Run from the repository root after switching this Lightning Studio to a GPU:

```bash
nvidia-smi
.venv/bin/python -c "import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0), torch.cuda.get_device_properties(0).total_memory)"
UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python uv sync --frozen --extra dev --extra ml --python /home/zeus/miniconda3/envs/cloudspace/bin/python
UV_CACHE_DIR=.uv-cache uv pip install --upgrade torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -c "from pathlib import Path; from ai_engine.data.verify import verify_checksum; verify_checksum(Path('data/raw/dentex/hf-7b27ccc8/training_data.zip'),'18b2a2dbc5a2b10b0cc6a7677c46a382f4709ab8c9c3bb94f57b74e38e11ffd3'); print('DENTEX archive verified')"
.venv/bin/python -m ai_engine.training.train --config configs/ai/tooth_v1.yaml --benchmark-batches 5
.venv/bin/python -m ai_engine.training.train --config configs/ai/tooth_v1.yaml
.venv/bin/python -m ai_engine.training.train --config configs/ai/tooth_v1.yaml --resume checkpoints/tooth_v1/latest.pt
```

The five-batch command is the mandatory GPU benchmark. Record peak VRAM, batch latency,
images/second, estimated epoch duration and checkpoint size before the full command. Evaluation must
select checkpoints on validation only; the locked test set is final-only. ONNX export and CPU
benchmark follow only after a best checkpoint exists; the current export helper is
`ai_engine.models.export.export_onnx`, and must be called through the checkpoint-specific wrapper
added for that trained model rather than a guessed generic command.

## Resource choice

- Minimum viable: T4 16 GB, 32 GB system RAM, 80 GB free disk, 1024x512, batch 1,
  accumulation 8, FP16 AMP.
- Recommended best-credit choice: L4 24 GB, 32-64 GB RAM, at least 100 GB free disk, batch 2,
  accumulation 4, BF16/FP16 selected by the benchmark.

L40S or A100 are reasonable only when their measured throughput per credit beats L4. H100 is not
justified for this corpus before benchmarking. Current free disk is about 312 GB. A full Mask R-CNN
checkpoint including optimizer state is expected to be approximately 175-350 MB; the untrained CPU
smoke checkpoint measured 176 MB. Do not estimate training duration until the GPU benchmark.

Mask R-CNN ResNet-50 FPN V2 remains primary because the selected gold data contain polygons and the
architecture has mature transfer learning. A MobileNetV3 Faster R-CNN remains the lightweight,
box-only CPU comparator. Semantic U-Net plus watershed is an auxiliary experiment, not equivalent
instance supervision.
