import hashlib
from pathlib import Path

import yaml

from ai_engine.data.registry import DatasetRegistry
from ai_engine.models.registry import ModelRegistry
from ai_engine.release import validate_release


def test_empty_registry_fails_closed(tmp_path: Path):
    registry = tmp_path / "models.yaml"
    registry.write_text("models: []\n", encoding="utf-8")
    issues = validate_release(registry, tmp_path, tmp_path)
    assert [issue.code for issue in issues] == ["NO_PRODUCTION_MODEL"]


def test_artifact_digest_is_enforced(tmp_path: Path):
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"checkpoint")
    manifest = {
        "model_id": "tooth-v1",
        "task": "tooth",
        "architecture": "test",
        "version": "1",
        "training_dataset_ids": [],
        "checkpoint_sha256": hashlib.sha256(b"different").hexdigest(),
        "training_date": "2026-08-13",
        "validation_metrics": {"dice": 0.9},
        "thresholds": {"mask": 0.5},
        "input_size": [512, 512],
        "preprocessing_version": "1",
        "artifact_filename": artifact.name,
    }
    registry_path = tmp_path / "models.yaml"
    registry_path.write_text(yaml.safe_dump({"models": [manifest]}), encoding="utf-8")
    registry = ModelRegistry(registry_path, DatasetRegistry(tmp_path))
    model = registry.load()[0]
    try:
        registry.verified_artifact(model, tmp_path)
    except ValueError as exc:
        assert "checksum mismatch" in str(exc)
    else:
        raise AssertionError("a mismatched artifact was accepted")


def test_research_only_model_cannot_be_production_enabled(tmp_path: Path):
    manifest = {
        "model_id": "research-tooth-v1",
        "task": "tooth",
        "architecture": "maskrcnn",
        "version": "1",
        "training_dataset_ids": [],
        "checkpoint_sha256": hashlib.sha256(b"research").hexdigest(),
        "training_date": "2026-08-14",
        "validation_metrics": {},
        "thresholds": {},
        "input_size": [1024, 512],
        "preprocessing_version": "1",
        "artifact_filename": "research.pt",
        "lifecycle": "RESEARCH_ONLY",
        "production_enabled": True,
    }
    registry_path = tmp_path / "models.yaml"
    registry_path.write_text(yaml.safe_dump({"models": [manifest]}), encoding="utf-8")
    issues = validate_release(registry_path, tmp_path, tmp_path)
    assert issues[0].code == "REGISTRY_INVALID"
    assert "research-only model cannot be production enabled" in issues[0].detail
