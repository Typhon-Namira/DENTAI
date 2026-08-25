import hashlib
import json
from datetime import date
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ai_engine.data.license_guard import require_production_allowed
from ai_engine.data.registry import DatasetRegistry


class ModelLifecycle(StrEnum):
    EXPERIMENTAL = "EXPERIMENTAL"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    VALIDATION_CANDIDATE = "VALIDATION_CANDIDATE"
    PRODUCTION_ELIGIBLE = "PRODUCTION_ELIGIBLE"
    PRODUCTION = "PRODUCTION"
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


class DeploymentMode(StrEnum):
    ASSISTIVE_CLINICIAN_REVIEW = "ASSISTIVE_CLINICIAN_REVIEW"
    AUTONOMOUS = "AUTONOMOUS"


class ModelManifest(BaseModel):
    model_id: str
    task: str
    architecture: str
    version: str
    training_dataset_ids: list[str] = Field(default_factory=list)
    checkpoint_sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    training_date: date | None = None
    validation_metrics: dict[str, float] = Field(default_factory=dict)
    thresholds: dict[str, float] = Field(default_factory=dict)
    input_size: tuple[int, int] | None = None
    preprocessing_version: str | None = None
    artifact_filename: str | None = None
    bundle_manifest: str | None = None
    production_enabled: bool = False
    model_card: str | None = None
    clinical_review_approved: bool = False
    calibration_metrics: dict[str, float] = Field(default_factory=dict)
    onnx_parity_max_abs_error: float | None = None
    lifecycle: ModelLifecycle = ModelLifecycle.EXPERIMENTAL
    clinical_review_state: ClinicalReviewState = ClinicalReviewState.NOT_REVIEWED
    deployment_mode: DeploymentMode = DeploymentMode.ASSISTIVE_CLINICIAN_REVIEW
    clinical_review_required: bool = True


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
            if model.lifecycle is ModelLifecycle.RESEARCH_ONLY and model.production_enabled:
                raise ValueError(
                    f"research-only model cannot be production enabled: {model.model_id}"
                )
            if model.production_enabled:
                for dataset_id in model.training_dataset_ids:
                    require_production_allowed(self.dataset_registry.load(dataset_id))
        return models

    def verified_artifact(self, model: ModelManifest, artifact_dir: Path) -> Path:
        """Return a single-file artifact only after its registered digest is verified."""
        if not model.artifact_filename or not model.checkpoint_sha256:
            raise ValueError(f"single-file artifact metadata is incomplete: {model.model_id}")
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

    def load_bundle_manifest(self, model: ModelManifest, repository_root: Path) -> dict:
        """Load and structurally validate a frozen multi-artifact release manifest."""
        if not model.bundle_manifest:
            raise ValueError(f"bundle manifest is not configured: {model.model_id}")
        manifest_path = repository_root / model.bundle_manifest
        if not manifest_path.is_file():
            raise FileNotFoundError(f"bundle manifest is missing: {manifest_path}")
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"bundle manifest is invalid: {model.model_id}: {exc}") from exc
        if payload.get("model_version") != model.version:
            raise ValueError(
                f"bundle model_version mismatch: expected={model.version}, "
                f"actual={payload.get('model_version')}"
            )
        if payload.get("freeze_status") != "PRODUCTION_FROZEN":
            raise ValueError(
                f"bundle is not PRODUCTION_FROZEN: {payload.get('freeze_status')!r}"
            )
        return payload

    @staticmethod
    def expected_bundle_artifacts(payload: dict) -> dict[str, str]:
        """Extract the exact nine ONNX filenames and SHA-256 digests from the V5 manifest."""
        try:
            expected = {
                Path(item["onnx_export"]["onnx_path"]).name: item["onnx_export"]["onnx_sha256"]
                for item in payload["models"].values()
            }
            preprocessing = payload["detector_preprocessing"]
            expected[Path(preprocessing["onnx_path"]).name] = preprocessing["sha256"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"bundle artifact metadata is incomplete: {exc}") from exc
        if len(expected) != 9:
            raise ValueError(
                f"DENTAI V5 bundle must contain exactly nine ONNX artifacts, got {len(expected)}"
            )
        for filename, digest in expected.items():
            if not isinstance(digest, str) or len(digest) != 64:
                raise ValueError(f"invalid SHA-256 for bundle artifact: {filename}")
        return expected

    def verified_bundle(
        self,
        model: ModelManifest,
        artifact_dir: Path,
        repository_root: Path,
    ) -> dict[str, Path]:
        """Verify the exact frozen DENTAI V5 artifact set without changing model bytes."""
        payload = self.load_bundle_manifest(model, repository_root)
        expected = self.expected_bundle_artifacts(payload)
        if not artifact_dir.is_dir():
            raise FileNotFoundError(f"model artifact root is missing: {artifact_dir}")
        actual = {path.name for path in artifact_dir.glob("*.onnx")}
        if actual != set(expected):
            raise ValueError(
                "artifact filenames do not exactly match frozen bundle: "
                f"expected={sorted(expected)}, actual={sorted(actual)}"
            )
        verified: dict[str, Path] = {}
        for filename, expected_digest in expected.items():
            path = artifact_dir / filename
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest().lower() != expected_digest.lower():
                raise ValueError(f"bundle artifact checksum mismatch: {filename}")
            verified[filename] = path
        return verified
