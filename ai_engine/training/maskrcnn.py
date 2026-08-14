"""Mask R-CNN construction and a reproducible training engine."""

from __future__ import annotations

import os
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torchvision.models import ResNet50_Weights
from torchvision.models.detection import maskrcnn_resnet50_fpn, maskrcnn_resnet50_fpn_v2
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor


def build_maskrcnn(
    num_classes: int = 2,
    pretrained: bool = True,
    min_size: int = 512,
    max_size: int = 1024,
    architecture: str = "maskrcnn_resnet50_fpn_v2",
) -> nn.Module:
    # Tooth V1 config specifies ImageNet backbone initialization, not COCO detector weights.
    weights = None
    backbone_weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
    builders = {
        "maskrcnn_resnet50_fpn": maskrcnn_resnet50_fpn,
        "maskrcnn_resnet50_fpn_v2": maskrcnn_resnet50_fpn_v2,
    }
    if architecture not in builders:
        raise ValueError(f"unsupported mature torchvision architecture: {architecture}")
    model = builders[architecture](
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


def save_checkpoint(
    path: Path,
    model: nn.Module,
    optimizer,
    scheduler,
    epoch: int,
    *,
    training_state: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    numpy_state: Any = np.random.get_state()
    payload = {
        "epoch": epoch,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict() if scheduler else None,
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "numpy_rng": {
            "name": numpy_state[0],
            "keys": numpy_state[1].tolist(),
            "position": numpy_state[2],
            "has_gauss": numpy_state[3],
            "cached_gaussian": numpy_state[4],
        },
        "python_rng": random.getstate(),
        "training_state": training_state or {},
    }
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


def load_checkpoint(
    path: Path, model: nn.Module, optimizer=None, scheduler=None
) -> tuple[int, dict[str, Any]]:
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    if optimizer:
        optimizer.load_state_dict(state["optimizer"])
    if scheduler and state["scheduler"]:
        scheduler.load_state_dict(state["scheduler"])
    torch.set_rng_state(state["torch_rng"])
    if state.get("cuda_rng") is not None and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda_rng"])
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
    return int(state["epoch"]) + 1, state.get("training_state", {})


def _average_precision(entries: list[tuple[float, bool]], positives: int) -> float:
    if positives == 0:
        return 0.0
    entries.sort(key=lambda item: item[0], reverse=True)
    true_positives = np.cumsum([matched for _, matched in entries])
    false_positives = np.cumsum([not matched for _, matched in entries])
    recall = true_positives / positives
    precision = true_positives / np.maximum(true_positives + false_positives, 1)
    recall = np.concatenate(([0.0], recall, [1.0]))
    precision = np.concatenate(([0.0], precision, [0.0]))
    precision = np.maximum.accumulate(precision[::-1])[::-1]
    changes = np.where(recall[1:] != recall[:-1])[0]
    return float(np.sum((recall[changes + 1] - recall[changes]) * precision[changes + 1]))


@torch.no_grad()
def validate(
    model: nn.Module, loader, device: torch.device, max_batches: int | None = None
) -> dict[str, float]:
    model.eval()
    images_seen = detections = positives = 0
    true_positives = false_positives = missed = 0
    mask_dice: list[float] = []
    mask_iou: list[float] = []
    thresholds = [value / 100 for value in range(50, 100, 5)]
    matches: dict[float, list[tuple[float, bool]]] = {value: [] for value in thresholds}
    for batch_index, (images, targets) in enumerate(loader, start=1):
        outputs = model([image.to(device) for image in images])
        images_seen += len(outputs)
        detections += sum(len(output["boxes"]) for output in outputs)
        for output, target in zip(outputs, targets, strict=True):
            predicted_boxes = output["boxes"].detach().cpu()
            scores = output["scores"].detach().cpu()
            expected_boxes = target["boxes"].cpu()
            positives += len(expected_boxes)
            if len(predicted_boxes) and len(expected_boxes):
                from torchvision.ops import box_iou

                ious = box_iou(predicted_boxes, expected_boxes)
            else:
                ious = torch.zeros((len(predicted_boxes), len(expected_boxes)))
            order = scores.argsort(descending=True).tolist()
            for threshold in thresholds:
                claimed: set[int] = set()
                for prediction_index in order:
                    is_match = False
                    if len(expected_boxes):
                        candidates = ious[prediction_index].clone()
                        if claimed:
                            candidates[list(claimed)] = -1
                        best_iou, best_target = candidates.max(dim=0)
                        if float(best_iou) >= threshold:
                            claimed.add(int(best_target))
                            is_match = True
                    matches[threshold].append((float(scores[prediction_index]), is_match))
            claimed_at_50: set[int] = set()
            for prediction_index in order:
                if float(scores[prediction_index]) < 0.5:
                    continue
                candidates = ious[prediction_index].clone()
                if claimed_at_50:
                    candidates[list(claimed_at_50)] = -1
                if len(candidates) and float(candidates.max()) >= 0.5:
                    _, target_index = candidates.max(dim=0)
                    claimed_at_50.add(int(target_index))
                    true_positives += 1
                    if "masks" in output and "masks" in target:
                        predicted_mask = output["masks"][prediction_index, 0].cpu() >= 0.5
                        expected_mask = target["masks"][target_index].cpu().bool()
                        intersection = torch.logical_and(predicted_mask, expected_mask).sum().item()
                        union = torch.logical_or(predicted_mask, expected_mask).sum().item()
                        denominator = predicted_mask.sum().item() + expected_mask.sum().item()
                        mask_dice.append(2 * intersection / denominator if denominator else 1.0)
                        mask_iou.append(intersection / union if union else 1.0)
                else:
                    false_positives += 1
            missed += len(expected_boxes) - len(claimed_at_50)
        if max_batches is not None and batch_index >= max_batches:
            break
    aps = {
        threshold: _average_precision(entries, positives) for threshold, entries in matches.items()
    }
    precision = true_positives / max(true_positives + false_positives, 1)
    recall = true_positives / max(true_positives + missed, 1)
    return {
        "images": float(images_seen),
        "detections": float(detections),
        "map_50": aps[0.5],
        "map_50_95": float(np.mean(list(aps.values()))),
        "precision_50": precision,
        "recall_50": recall,
        "false_positives_per_image": false_positives / max(images_seen, 1),
        "missed_teeth_per_image": missed / max(images_seen, 1),
        "mask_dice": float(np.mean(mask_dice)) if mask_dice else 0.0,
        "mask_iou": float(np.mean(mask_iou)) if mask_iou else 0.0,
    }


def train_one_epoch(
    model: nn.Module,
    loader,
    optimizer,
    device: torch.device,
    accumulation_steps: int = 1,
    amp_dtype: torch.dtype | None = torch.float16,
    max_batches: int | None = None,
) -> dict[str, float]:
    model.train()
    optimizer.zero_grad(set_to_none=True)
    totals: dict[str, float] = {}
    use_amp = amp_dtype is not None and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp and amp_dtype == torch.float16)
    timing = {"dataloader": 0.0, "forward": 0.0, "backward": 0.0, "optimizer": 0.0}
    images_seen = 0
    batch_finished = time.monotonic()
    for step, (images, targets) in enumerate(loader, start=1):
        timing["dataloader"] += time.monotonic() - batch_finished
        images_seen += len(images)
        images = [image.to(device) for image in images]
        targets = move_targets(list(targets), device)
        group_start = ((step - 1) // accumulation_steps) * accumulation_steps + 1
        group_size = min(accumulation_steps, len(loader) - group_start + 1)
        if max_batches is not None:
            group_size = min(group_size, max_batches - group_start + 1)
        started = time.monotonic()
        with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=use_amp):
            losses = model(images, targets)
            loss = sum(losses.values()) / group_size
        if use_amp:
            torch.cuda.synchronize()
        timing["forward"] += time.monotonic() - started
        if not torch.isfinite(loss):
            raise FloatingPointError(f"non-finite training loss at batch {step}: {float(loss)}")
        started = time.monotonic()
        scaler.scale(loss).backward()
        if use_amp:
            torch.cuda.synchronize()
        timing["backward"] += time.monotonic() - started
        final_step = step == len(loader) or (max_batches is not None and step >= max_batches)
        if step % accumulation_steps == 0 or final_step:
            started = time.monotonic()
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
            if use_amp:
                torch.cuda.synchronize()
            timing["optimizer"] += time.monotonic() - started
        for name, value in losses.items():
            totals[name] = totals.get(name, 0.0) + float(value.detach())
        if max_batches is not None and step >= max_batches:
            break
        batch_finished = time.monotonic()
    denominator = min(len(loader), max_batches) if max_batches is not None else len(loader)
    result = {name: value / denominator for name, value in totals.items()}
    elapsed = sum(timing.values())
    result.update(
        {
            "telemetry_dataloader_seconds": timing["dataloader"],
            "telemetry_forward_seconds": timing["forward"],
            "telemetry_backward_seconds": timing["backward"],
            "telemetry_optimizer_seconds": timing["optimizer"],
            "telemetry_images_per_second": images_seen / elapsed if elapsed else 0.0,
        }
    )
    return result
