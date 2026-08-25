from dataclasses import dataclass
from pathlib import Path

from ai_engine.data.registry import DatasetRegistry
from ai_engine.models.registry import DeploymentMode, ModelLifecycle, ModelRegistry


@dataclass(frozen=True)
class ReleaseIssue:
    model_id: str
    code: str
    detail: str


def _manifest_has_validation_evidence(payload: dict) -> bool:
    try:
        models = payload["models"]
        return bool(models) and all(
            bool(item.get("checkpoint_metric_metadata")) for item in models.values()
        )
    except (KeyError, TypeError, AttributeError):
        return False


def _manifest_has_thresholds(payload: dict) -> bool:
    thresholds = payload.get("thresholds")
    return isinstance(thresholds, dict) and bool(thresholds)


def _manifest_has_onnx_export_evidence(payload: dict) -> bool:
    """Require reproducible ONNX export metadata for every frozen V5 head."""
    try:
        exports = [item["onnx_export"] for item in payload["models"].values()]
        preprocessing = payload["detector_preprocessing"]
    except (KeyError, TypeError, AttributeError):
        return False
    if not exports:
        return False
    required = ("onnx_path", "onnx_sha256", "providers", "opset")
    if not all(all(export.get(key) is not None for key in required) for export in exports):
        return False
    return all(preprocessing.get(key) is not None for key in ("onnx_path", "sha256", "operation"))


def _manifest_has_full_onnx_parity(payload: dict) -> bool:
    """Stronger proof reserved for autonomous deployment."""
    try:
        exports = [item["onnx_export"] for item in payload["models"].values()]
    except (KeyError, TypeError, AttributeError):
        return False
    if not exports:
        return False
    for export in exports:
        if export.get("prediction_agreement") is True:
            continue
        if export.get("max_abs_logit_difference") is None:
            return False
    return True


def validate_release(
    registry_path: Path,
    dataset_manifest_dir: Path,
    artifact_dir: Path,
    repository_root: Path = Path("."),
    *,
    verify_artifacts: bool = True,
) -> list[ReleaseIssue]:
    """Fail-closed evidence gate for models marked production enabled.

    Assistive clinician-review deployments require frozen bundle identity,
    validation evidence, operating thresholds, ONNX export metadata and an
    explicit model card. Runtime startup additionally verifies every ONNX byte.
    Autonomous deployment remains blocked without calibration, full parity and
    explicit clinical approval.
    """
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
        if model.lifecycle is ModelLifecycle.RESEARCH_ONLY:
            issues.append(
                ReleaseIssue(
                    model.model_id,
                    "RESEARCH_ONLY_MODEL",
                    "Research-only lineage cannot pass the production release gate.",
                )
            )

        bundle_payload: dict | None = None
        if model.bundle_manifest:
            try:
                bundle_payload = registry.load_bundle_manifest(model, repository_root)
            except (FileNotFoundError, ValueError) as exc:
                issues.append(ReleaseIssue(model.model_id, "BUNDLE_MANIFEST_INVALID", str(exc)))

        has_validation = bool(model.validation_metrics)
        has_thresholds = bool(model.thresholds)
        has_export_evidence = model.onnx_parity_max_abs_error is not None
        if bundle_payload is not None:
            has_validation = has_validation or _manifest_has_validation_evidence(bundle_payload)
            has_thresholds = has_thresholds or _manifest_has_thresholds(bundle_payload)
            has_export_evidence = has_export_evidence or _manifest_has_onnx_export_evidence(
                bundle_payload
            )

        checks = (
            (has_validation, "VALIDATION_MISSING", "Validation metrics are absent."),
            (has_thresholds, "THRESHOLDS_MISSING", "Operating thresholds are absent."),
            (
                has_export_evidence,
                "ONNX_EXPORT_EVIDENCE_MISSING",
                "ONNX export/reproducibility evidence is absent.",
            ),
            (
                model.clinical_review_required,
                "CLINICIAN_REVIEW_NOT_REQUIRED",
                "Production AI findings must require clinician review.",
            ),
        )
        for passed, code, detail in checks:
            if not passed:
                issues.append(ReleaseIssue(model.model_id, code, detail))

        if model.deployment_mode is DeploymentMode.AUTONOMOUS:
            full_parity = model.onnx_parity_max_abs_error is not None
            if bundle_payload is not None:
                full_parity = full_parity or _manifest_has_full_onnx_parity(bundle_payload)
            autonomous_checks = (
                (
                    bool(model.calibration_metrics),
                    "CALIBRATION_MISSING",
                    "Autonomous deployment requires calibration evidence.",
                ),
                (
                    full_parity,
                    "ONNX_PARITY_MISSING",
                    "Autonomous deployment requires full ONNX parity evidence.",
                ),
                (
                    model.clinical_review_approved,
                    "CLINICAL_REVIEW_MISSING",
                    "Autonomous deployment requires explicit clinical approval.",
                ),
            )
            for passed, code, detail in autonomous_checks:
                if not passed:
                    issues.append(ReleaseIssue(model.model_id, code, detail))

        card = repository_root / model.model_card if model.model_card else None
        if card is None or not card.is_file():
            issues.append(
                ReleaseIssue(model.model_id, "MODEL_CARD_MISSING", "Model card is absent.")
            )

        if verify_artifacts:
            try:
                if model.bundle_manifest:
                    registry.verified_bundle(model, artifact_dir, repository_root)
                else:
                    registry.verified_artifact(model, artifact_dir)
            except (FileNotFoundError, ValueError) as exc:
                issues.append(ReleaseIssue(model.model_id, "ARTIFACT_INVALID", str(exc)))
    return issues


def require_release(
    registry_path: Path,
    dataset_manifest_dir: Path,
    artifact_dir: Path,
    repository_root: Path = Path("."),
) -> None:
    """Raise before production inference if release evidence or artifacts fail."""
    issues = validate_release(
        registry_path,
        dataset_manifest_dir,
        artifact_dir,
        repository_root,
        verify_artifacts=True,
    )
    if issues:
        detail = "; ".join(f"{item.code}: {item.detail}" for item in issues)
        raise RuntimeError(f"AI_RELEASE_GATE_FAILED: {detail}")
