import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize_run(config_path: Path, split_path: Path, output: Path, seed: int) -> Path:
    head = Path(".git/HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        commit = (Path(".git") / head.removeprefix("ref: ")).read_text(encoding="utf-8").strip()
    else:
        commit = head
    timestamp = datetime.now(UTC)
    run_id = f"tooth-v1-{timestamp:%Y%m%dT%H%M%SZ}-{commit[:8]}"
    payload = {
        "run_id": run_id,
        "clinical_use": False,
        "git_commit": commit,
        "config_sha256": sha256_path(config_path),
        "split_sha256": sha256_path(split_path),
        "python_version": platform.python_version(),
        "seed": seed,
        "start_time": timestamp.isoformat(),
        "end_time": None,
        "pytorch_version": None,
        "cuda_version": None,
        "gpu": None,
        "dataset_manifest_hashes": {},
        "metrics": {},
        "checkpoint_sha256": None,
    }
    output.mkdir(parents=True, exist_ok=False)
    target = output / "run.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target
