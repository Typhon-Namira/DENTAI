from dataclasses import dataclass
from pathlib import Path

from ai_engine.data.registry import DatasetRegistry
from ai_engine.models.registry import ModelRegistry


@dataclass(frozen=True)
class ReleaseIssue:
    model_id: str
    code: str
    detail: str


def validate_release(
    registry_path: Path,
    dataset_manifest_dir: Path,
    artifact_dir: Path,
    repository_root: Path = Path("."),
) -> list[ReleaseIssue]:
    """Fail-closed evidence gate for models marked production enabled."""
    datasets = DatasetRegistry(dataset_manifest_dir)
    registry = ModelRegistry(registry_path, datasets)
    issues: list[ReleaseIssue] = []
    try:
        models = registry.load()
    except Exception as exc:
        return [ReleaseIssue("registry", "REGISTRY_INVALID", str(exc))]
    enabled = [model for model in models if model.production_enabled]
    if not enabled:
        return [ReleaseIssue("registry", "NO_PRODUCTION_MODEL", "No model is enabled.")]
    for model in enabled:
        checks = (
            (
                bool(model.validation_metrics),
                "VALIDATION_MISSING",
                "Validation metrics are absent.",
            ),
            (bool(model.thresholds), "THRESHOLDS_MISSING", "Operating thresholds are absent."),
            (
                bool(model.calibration_metrics),
                "CALIBRATION_MISSING",
                "Calibration evidence is absent.",
            ),
            (
                model.onnx_parity_max_abs_error is not None,
                "ONNX_PARITY_MISSING",
                "ONNX parity evidence is absent.",
            ),
            (
                model.clinical_review_approved,
                "CLINICAL_REVIEW_MISSING",
                "Clinical approval is absent.",
            ),
        )
        for passed, code, detail in checks:
            if not passed:
                issues.append(ReleaseIssue(model.model_id, code, detail))
        card = repository_root / model.model_card if model.model_card else None
        if card is None or not card.is_file():
            issues.append(
                ReleaseIssue(model.model_id, "MODEL_CARD_MISSING", "Model card is absent.")
            )
        try:
            registry.verified_artifact(model, artifact_dir)
        except (FileNotFoundError, ValueError) as exc:
            issues.append(ReleaseIssue(model.model_id, "ARTIFACT_INVALID", str(exc)))
    return issues
