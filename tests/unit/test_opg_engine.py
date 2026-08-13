from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ai_engine.data.license_guard import DatasetLicenseError, require_production_allowed
from ai_engine.data.registry import DatasetManifest, DatasetRegistry, DatasetTier
from ai_engine.data.split import patient_level_split
from ai_engine.evaluation.metrics import expected_calibration_error, segmentation_metrics
from ai_engine.longitudinal.engine import ChangeState, LongitudinalDentalEngine
from ai_engine.quality.engine import OPGQualityEngine
from ai_engine.risk.engine import RuleBasedRecallRiskProvider
from ai_engine.schemas import (
    ComponentState,
    ImageQuality,
    OPGAnalysisResult,
    QualityLevel,
    UncertaintyLevel,
    VisionFinding,
)
from ai_engine.tooth.fdi import ToothCandidate, assign_fdi
from ai_engine.training.train import synthetic_cpu_smoke
from app.ai.providers import DENTAIRealOPGProvider


def synthetic_opg() -> bytes:
    x = np.linspace(25, 225, 1024, dtype=np.uint8)
    pixels = np.tile(x, (512, 1))
    pixels[180:330, 100:924:40] = 245
    stream = BytesIO()
    Image.fromarray(pixels).save(stream, format="PNG")
    return stream.getvalue()


def quality() -> ImageQuality:
    return ImageQuality(
        image_type="PANORAMIC",
        orientation="LANDSCAPE",
        width=1024,
        height=512,
        blur_score=10,
        exposure_mean=120,
        contrast_score=40,
        cropping_suspected=False,
        gross_artifact=False,
        quality=QualityLevel.ACCEPTABLE,
        usable_for_analysis=True,
    )


def finding(kind: str) -> VisionFinding:
    return VisionFinding(
        finding_type=kind,
        description="AI-detected radiographic observation requiring dentist review.",
        tooth_fdi="46",
        raw_score=0.8,
        calibrated_confidence=None,
        uncertainty=UncertaintyLevel.MODERATE_CONFIDENCE,
        source_model="test-model",
        model_version="test",
        source_image_id="synthetic",
    )


def test_quality_gate_accepts_synthetic_panorama_and_rejects_tiny_image():
    engine = OPGQualityEngine()
    assert engine.analyze(synthetic_opg()).image_type == "PANORAMIC"
    tiny = BytesIO()
    Image.new("L", (20, 20), 128).save(tiny, format="PNG")
    assert engine.analyze(tiny.getvalue()).usable_for_analysis is False


def test_license_guard_fails_closed_and_group_split_prevents_leakage():
    manifest = DatasetManifest(
        dataset_id="research",
        name="Research",
        version="1",
        source_url="https://example.invalid",
        license="CC-BY-NC-4.0",
        tier=DatasetTier.RESEARCH_ONLY,
        tasks=["benchmark"],
    )
    with pytest.raises(DatasetLicenseError):
        require_production_allowed(manifest)
    split = patient_level_split(["patient-a", "patient-a", "patient-b"])
    assert split["patient-a"] in {"train", "validation", "test"}
    registry = DatasetRegistry(Path("ai_engine/data/manifests"))
    assert registry.load("mopg7_v1").tier == DatasetTier.RESEARCH_ONLY


def test_fdi_complete_arch_mapping_and_incomplete_arch_fails_closed():
    candidates = [ToothCandidate(index / 16, 0.25, 0.9) for index in range(16)]
    mapped = assign_fdi(candidates)
    assert [label for _, label in mapped] == [
        "18",
        "17",
        "16",
        "15",
        "14",
        "13",
        "12",
        "11",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "27",
        "28",
    ]
    assert assign_fdi(candidates[:-1]) == []


def test_risk_policy_has_no_unapproved_intervals_and_longitudinal_is_structured():
    risk = RuleBasedRecallRiskProvider(Path("configs/ai/risk_policy.yaml"))
    recommendation = risk.predict([finding("PERIAPICAL_LESION")])[0]
    assert recommendation.policy_approved is False
    assert recommendation.recommended_window_days is None
    prior = OPGAnalysisResult(
        image=quality(),
        component_status={"pathology": ComponentState.SUCCESS},
        global_findings=[finding("PERIAPICAL_LESION")],
    )
    current = OPGAnalysisResult(
        image=quality(),
        component_status={"pathology": ComponentState.SUCCESS},
        global_findings=[finding("PERIAPICAL_LESION"), finding("CARIES_SUSPECTED")],
    )
    changes = LongitudinalDentalEngine().compare(prior, current)
    assert {item.state for item in changes} == {ChangeState.STABLE, ChangeState.NEW}


@pytest.mark.asyncio
async def test_real_provider_quality_runs_but_missing_models_never_fake_findings():
    result = await DENTAIRealOPGProvider().analyze_xray(
        patient_context={}, xray_reference="synthetic", image_bytes=synthetic_opg()
    )
    assert result.provider == "real_opg"
    assert result.findings == []
    assert set(result.structured_result["component_status"].values()) == {"MODEL_REQUIRED"}


def test_evaluation_and_cpu_training_smoke(tmp_path: Path):
    expected = np.array([1, 1, 0, 0])
    predicted = np.array([1, 0, 0, 0])
    assert segmentation_metrics(predicted, expected)["dice"] == pytest.approx(2 / 3)
    assert expected_calibration_error(np.array([0.9, 0.1]), np.array([1, 0])) < 0.11
    artifact = synthetic_cpu_smoke(Path("configs/ai/synthetic_smoke.yaml"), tmp_path)
    assert artifact.is_file()
    assert '"clinical_use": false' in artifact.read_text(encoding="utf-8")
