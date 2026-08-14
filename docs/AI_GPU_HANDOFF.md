# Tooth V1 GPU handoff

The checked-in `ml` extra resolves CPU-only PyTorch wheels so CPU preparation does not duplicate a
CUDA runtime. On a Lightning GPU machine, create a dedicated training environment and replace only
PyTorch/torchvision using the official wheel index matching the exposed CUDA driver. For CUDA 12.8:

```bash
UV_CACHE_DIR=.uv-cache uv sync --frozen --extra dev --extra ml
UV_CACHE_DIR=.uv-cache uv pip install --upgrade torch==2.8.0 torchvision==0.23.0 \
  --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_properties(0))"
python -m ai_engine.training.train --config configs/ai/tooth_v1.yaml
```

Do not execute the last command while `capability_state: DATASET_REQUIRED`. Recommended eventual
hardware for Mask R-CNN at 1024×512 is one NVIDIA GPU with 24 GB VRAM, 32 GB system RAM, 8 CPU
cores, and 80 GB free persistent storage. A 16 GB GPU may be feasible at batch size 1 with gradient
accumulation, but must be measured; no training-time estimate is claimed before an adequate dataset
and a GPU smoke benchmark exist.
