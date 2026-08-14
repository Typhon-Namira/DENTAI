"""Mask R-CNN construction and a reproducible training engine."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torchvision.models import ResNet50_Weights
from torchvision.models.detection import MaskRCNN_ResNet50_FPN_V2_Weights, maskrcnn_resnet50_fpn_v2
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor


def build_maskrcnn(
    num_classes: int = 2,
    pretrained: bool = True,
    min_size: int = 512,
    max_size: int = 1024,
) -> nn.Module:
    weights = MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT if pretrained else None
    backbone_weights = None if pretrained else None
    if pretrained and weights is None:
        backbone_weights = ResNet50_Weights.DEFAULT
    model = maskrcnn_resnet50_fpn_v2(
        weights=weights,
        weights_backbone=backbone_weights,
        min_size=min_size,
        max_size=max_size,
    )
    box_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(box_features, num_classes)
    mask_features = model.roi_heads.mask_predictor.conv5_mask.in_channels
    model.roi_heads.mask_predictor = MaskRCNNPredictor(mask_features, 256, num_classes)
    return model


def move_targets(targets: list[dict[str, Any]], device: torch.device) -> list[dict[str, Any]]:
    return [
        {
            key: value.to(device) if torch.is_tensor(value) else value
            for key, value in target.items()
        }
        for target in targets
    ]


def save_checkpoint(path: Path, model: nn.Module, optimizer, scheduler, epoch: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    numpy_state: Any = np.random.get_state()
    torch.save(
        {
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict() if scheduler else None,
            "torch_rng": torch.get_rng_state(),
            "numpy_rng": {
                "name": numpy_state[0],
                "keys": numpy_state[1].tolist(),
                "position": numpy_state[2],
                "has_gauss": numpy_state[3],
                "cached_gaussian": numpy_state[4],
            },
            "python_rng": random.getstate(),
        },
        path,
    )


def load_checkpoint(path: Path, model: nn.Module, optimizer=None, scheduler=None) -> int:
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    if optimizer:
        optimizer.load_state_dict(state["optimizer"])
    if scheduler and state["scheduler"]:
        scheduler.load_state_dict(state["scheduler"])
    torch.set_rng_state(state["torch_rng"])
    numpy_rng = state["numpy_rng"]
    np.random.set_state(
        (
            numpy_rng["name"],
            np.asarray(numpy_rng["keys"], dtype=np.uint32),
            numpy_rng["position"],
            numpy_rng["has_gauss"],
            numpy_rng["cached_gaussian"],
        )
    )
    random.setstate(state["python_rng"])
    return int(state["epoch"]) + 1


@torch.no_grad()
def validate(
    model: nn.Module, loader, device: torch.device, max_batches: int | None = None
) -> dict[str, float]:
    model.eval()
    images_seen = detections = 0
    mean_scores: list[float] = []
    for batch_index, (images, _targets) in enumerate(loader, start=1):
        outputs = model([image.to(device) for image in images])
        images_seen += len(outputs)
        detections += sum(len(output["boxes"]) for output in outputs)
        mean_scores.extend(float(score) for output in outputs for score in output["scores"])
        if max_batches is not None and batch_index >= max_batches:
            break
    return {
        "images": float(images_seen),
        "detections": float(detections),
        "mean_score": float(np.mean(mean_scores)) if mean_scores else 0.0,
    }


def train_one_epoch(
    model: nn.Module,
    loader,
    optimizer,
    device: torch.device,
    accumulation_steps: int = 1,
    amp: bool = True,
    max_batches: int | None = None,
) -> dict[str, float]:
    model.train()
    optimizer.zero_grad(set_to_none=True)
    totals: dict[str, float] = {}
    scaler = torch.amp.GradScaler("cuda", enabled=amp and device.type == "cuda")
    for step, (images, targets) in enumerate(loader, start=1):
        images = [image.to(device) for image in images]
        targets = move_targets(list(targets), device)
        with torch.autocast(device_type=device.type, enabled=amp and device.type == "cuda"):
            losses = model(images, targets)
            loss = sum(losses.values()) / accumulation_steps
        scaler.scale(loss).backward()
        final_step = step == len(loader) or (max_batches is not None and step >= max_batches)
        if step % accumulation_steps == 0 or final_step:
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
        for name, value in losses.items():
            totals[name] = totals.get(name, 0.0) + float(value.detach())
        if max_batches is not None and step >= max_batches:
            break
    denominator = min(len(loader), max_batches) if max_batches is not None else len(loader)
    return {name: value / denominator for name, value in totals.items()}
