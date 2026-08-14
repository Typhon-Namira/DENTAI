import argparse
import hashlib
import json
import platform
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import yaml

from ai_engine.data.license_guard import require_production_allowed
from ai_engine.data.registry import DatasetRegistry
from ai_engine.training.config import load_training_config


def synthetic_cpu_smoke(config_path: Path, output_dir: Path) -> Path:
    """Exercises reproducibility/artifact plumbing only; it does not produce a clinical model."""
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
    payload = {
        "clinical_use": False,
        "purpose": "pipeline smoke test only",
        "seed": seed,
        "threshold": threshold,
        "synthetic_dice": dice,
        "created_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
    }
    artifact.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return artifact


def validate_training_preflight(config_path: Path, repository_root: Path = Path(".")) -> dict:
    config = load_training_config(config_path)
    registry = DatasetRegistry(repository_root / "ai_engine/data/manifests")
    for dataset_id in config.data.dataset_ids:
        require_production_allowed(registry.load(dataset_id))
    split = repository_root / config.data.split_manifest
    if not split.is_file():
        raise FileNotFoundError(f"locked split is missing: {split}")
    if config.capability_state == "DATASET_REQUIRED":
        raise RuntimeError(
            "DATASET_REQUIRED: adequate audited tooth-instance cases are not available"
        )
    return {
        "device": "cuda" if __import__("torch").cuda.is_available() else "cpu",
        "validated": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["synthetic_cpu_smoke"], required=False)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("training_artifacts"))
    args = parser.parse_args()
    if args.task == "synthetic_cpu_smoke":
        print(synthetic_cpu_smoke(args.config, args.output_dir))
    else:
        print(json.dumps(validate_training_preflight(args.config), indent=2))


if __name__ == "__main__":
    main()
