import hashlib
from datetime import date
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ai_engine.data.license_guard import require_production_allowed
from ai_engine.data.registry import DatasetRegistry


class ModelLifecycle(StrEnum):
    EXPERIMENTAL = "EXPERIMENTAL"
    TRAINED = "TRAINED"
    VALIDATED_INTERNAL = "VALIDATED_INTERNAL"
    VALIDATED_EXTERNAL = "VALIDATED_EXTERNAL"
    PRODUCTION_CANDIDATE = "PRODUCTION_CANDIDATE"
    PRODUCTION_ENABLED = "PRODUCTION_ENABLED"
    DISABLED = "DISABLED"
    DATASET_REQUIRED = "DATASET_REQUIRED"


class ClinicalReviewState(StrEnum):
    NOT_REVIEWED = "NOT_REVIEWED"
    REVIEW_IN_PROGRESS = "REVIEW_IN_PROGRESS"
    APPROVED_FOR_PILOT = "APPROVED_FOR_PILOT"
    REJECTED = "REJECTED"


class ModelManifest(BaseModel):
    model_id: str
    task: str
    architecture: str
    version: str
    training_dataset_ids: list[str]
    checkpoint_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    training_date: date
    validation_metrics: dict[str, float]
    thresholds: dict[str, float]
    input_size: tuple[int, int]
    preprocessing_version: str
    artifact_filename: str
    production_enabled: bool = False
    model_card: str | None = None
    clinical_review_approved: bool = False
    calibration_metrics: dict[str, float] = Field(default_factory=dict)
    onnx_parity_max_abs_error: float | None = None
    lifecycle: ModelLifecycle = ModelLifecycle.EXPERIMENTAL
    clinical_review_state: ClinicalReviewState = ClinicalReviewState.NOT_REVIEWED


class ModelRegistry:
    def __init__(self, path: Path, dataset_registry: DatasetRegistry):
        self.path = path
        self.dataset_registry = dataset_registry

    def load(self) -> list[ModelManifest]:
        if not self.path.is_file():
            return []
        payload = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {"models": []}
        models = [ModelManifest.model_validate(item) for item in payload["models"]]
        for model in models:
            if model.production_enabled:
                for dataset_id in model.training_dataset_ids:
                    require_production_allowed(self.dataset_registry.load(dataset_id))
        return models

    def verified_artifact(self, model: ModelManifest, artifact_dir: Path) -> Path:
        """Return an artifact only after its registered digest is verified."""
        artifact = artifact_dir / model.artifact_filename
        if not artifact.is_file():
            raise FileNotFoundError(f"model artifact is missing: {artifact}")
        digest = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != model.checkpoint_sha256.lower():
            raise ValueError(f"model artifact checksum mismatch: {model.model_id}")
        return artifact
