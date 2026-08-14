"""Research Tooth V1 training entry point; never evaluates the locked test split."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

from ai_engine.training.config import load_training_config
from ai_engine.training.dataset import CanonicalToothInstanceDataset, detection_collate
from ai_engine.training.maskrcnn import (
    build_maskrcnn,
    load_checkpoint,
    save_checkpoint,
    train_one_epoch,
    validate,
)


def synthetic_cpu_smoke(config_path: Path, output_dir: Path) -> Path:
    """Exercise reproducibility plumbing only; this never produces a clinical model."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    images = np.random.default_rng(seed).normal(0.5, 0.15, size=(8, 32, 64)).clip(0, 1)
    masks = images > 0.5
    threshold = float(np.median(images))
    predictions = images >= threshold
    intersection = float(np.logical_and(predictions, masks).sum())
    dice = 2 * intersection / float(predictions.sum() + masks.sum())
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "synthetic-smoke.json"
    artifact.write_text(
        json.dumps(
            {
                "clinical_use": False,
                "purpose": "pipeline smoke test only",
                "seed": seed,
                "threshold": threshold,
                "synthetic_dice": dice,
                "created_at": datetime.now(UTC).isoformat(),
                "python": platform.python_version(),
                "config_sha256": _sha256(config_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return artifact


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit(repository: Path = Path(".")) -> str:
    head = (repository / ".git/HEAD").read_text(encoding="utf-8").strip()
    if not head.startswith("ref: "):
        return head
    reference = repository / ".git" / head.removeprefix("ref: ")
    return reference.read_text(encoding="utf-8").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--resume", type=Path, nargs="?", const=Path("checkpoints/tooth_v1/latest.pt")
    )
    parser.add_argument("--benchmark-batches", type=int, default=0)
    args = parser.parse_args()
    load_training_config(args.config)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if config.get("model_lifecycle") != "RESEARCH_ONLY":
        raise ValueError("this entry point requires explicit RESEARCH_ONLY lifecycle")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; real research training is not started on CPU")
    seed = int(config["training"]["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(bool(config["training"]["deterministic"]), warn_only=True)
    data = config["data"]
    image_dir = Path(data["primary_image_dir"])
    canonical_file = Path(data["primary_canonical_annotations"])
    split_file = Path(data["split_manifest"])
    output_size = (int(data["input_size"][0]), int(data["input_size"][1]))
    train_set = CanonicalToothInstanceDataset(
        image_dir, canonical_file, split_file, "train", output_size, train=True
    )
    validation_set = CanonicalToothInstanceDataset(
        image_dir, canonical_file, split_file, "validation", output_size, train=False
    )
    generator = torch.Generator().manual_seed(seed)
    batch_size = int(config["training"]["batch_size"])
    workers = int(config["training"]["data_loader_workers"])
    train_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=True,
        num_workers=workers,
        collate_fn=detection_collate,
        generator=generator,
        pin_memory=True,
    )
    validation_loader = DataLoader(
        validation_set,
        batch_size=batch_size,
        shuffle=False,
        num_workers=workers,
        collate_fn=detection_collate,
        generator=generator,
        pin_memory=True,
    )
    device = torch.device("cuda")
    model = build_maskrcnn(num_classes=int(config["model"]["num_classes"])).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["optimizer"]["learning_rate"]),
        weight_decay=float(config["optimizer"]["weight_decay"]),
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=float(config["scheduler"]["factor"]),
        patience=int(config["scheduler"]["patience"]),
    )
    checkpoint_dir = Path(config["checkpointing"]["directory"])
    if args.benchmark_batches:
        checkpoint_dir = checkpoint_dir / "benchmark"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config_hash = _sha256(args.config)
    split_hash = _sha256(Path(data["split_manifest"]))
    resume_path = args.resume
    if (
        resume_path is None
        and not args.benchmark_batches
        and config["training"].get("resume") == "auto"
        and (checkpoint_dir / "latest.pt").is_file()
    ):
        resume_path = checkpoint_dir / "latest.pt"
    start_epoch = 0
    best = float("-inf")
    stale = 0
    if resume_path:
        start_epoch, restored = load_checkpoint(resume_path, model, optimizer, scheduler)
        if restored.get("config_sha256") != config_hash:
            raise ValueError("resume checkpoint was created with a different training config")
        if restored.get("split_sha256") != split_hash:
            raise ValueError("resume checkpoint was created with a different data split")
        best = float(restored.get("best", float("-inf")))
        stale = int(restored.get("stale", 0))
    metadata = {
        "status": "RESEARCH_ONLY",
        "started_at": datetime.now(UTC).isoformat(),
        "config": str(args.config),
        "config_sha256": config_hash,
        "split_manifest": data["split_manifest"],
        "split_sha256": split_hash,
        "dataset_ids": data["dataset_ids"],
        "git_commit": _git_commit(),
        "device": torch.cuda.get_device_name(0),
        "resume": str(resume_path) if resume_path else None,
        "start_epoch": start_epoch,
        "benchmark_batches": args.benchmark_batches,
    }
    (checkpoint_dir / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    max_epochs = int(config["training"]["epochs"])
    if args.benchmark_batches:
        max_epochs = min(max_epochs, 1)
    precision = str(config["training"]["mixed_precision"])
    amp_dtype = torch.bfloat16 if precision == "bf16-mixed" else torch.float16
    if precision not in {"bf16-mixed", "16-mixed"}:
        raise ValueError(f"unsupported mixed_precision: {precision}")
    if amp_dtype == torch.bfloat16 and not torch.cuda.is_bf16_supported():
        raise RuntimeError("the configured bf16-mixed precision is unsupported by this CUDA GPU")
    try:
        for epoch in range(start_epoch, max_epochs):
            epoch_started = time.monotonic()
            losses = train_one_epoch(
                model,
                train_loader,
                optimizer,
                device,
                accumulation_steps=int(config["training"]["gradient_accumulation"]),
                amp_dtype=amp_dtype,
                max_batches=args.benchmark_batches or None,
            )
            metrics = validate(
                model, validation_loader, device, max_batches=args.benchmark_batches or None
            )
            score = metrics["map_50_95"]
            if not np.isfinite(score) or not all(np.isfinite(value) for value in losses.values()):
                raise FloatingPointError(f"non-finite epoch metrics at epoch {epoch}")
            scheduler.step(score)
            improved = score > best
            if improved:
                best, stale = score, 0
            else:
                stale += 1
            state = {
                "best": best,
                "stale": stale,
                "config_sha256": config_hash,
                "split_sha256": split_hash,
            }
            record = {
                "event": "epoch_complete",
                "epoch": epoch,
                "duration_seconds": time.monotonic() - epoch_started,
                "learning_rate": optimizer.param_groups[0]["lr"],
                "losses": losses,
                "validation": metrics,
                "best_map_50_95": best,
                "early_stopping_stale_epochs": stale,
            }
            with (checkpoint_dir / "metrics.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
            print(json.dumps(record), flush=True)
            save_checkpoint(
                checkpoint_dir / "latest.pt",
                model,
                optimizer,
                scheduler,
                epoch,
                training_state=state,
            )
            if improved:
                save_checkpoint(
                    checkpoint_dir / "best.pt",
                    model,
                    optimizer,
                    scheduler,
                    epoch,
                    training_state=state,
                )
            if args.benchmark_batches or stale >= int(
                config["training"]["early_stopping_patience"]
            ):
                break
    except (FloatingPointError, torch.cuda.OutOfMemoryError) as error:
        failure = {
            "event": "training_stopped_safely",
            "error_type": type(error).__name__,
            "message": str(error),
            "last_completed_epoch": epoch - 1 if "epoch" in locals() else start_epoch - 1,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        with (checkpoint_dir / "metrics.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(failure) + "\n")
        print(json.dumps(failure), file=sys.stderr, flush=True)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
