from types import SimpleNamespace

import pytest

from ai_engine.longitudinal.engine import LongitudinalDentalEngine
from ai_engine.schemas import ImageQuality, QualityLevel
from app.ai import providers as provider_module
from app.ai.providers import DENTAIRealOPGProvider


def unresolved_raw_result() -> dict:
    return {
        "version": "dentai-unified-v5",
        "teeth": [
            {
                "tooth_detection": {
                    "instance_id": 7,
                    "bbox_xyxy": [240.56, 381.01, 336.86, 504.73],
                    "confidence": 0.98,
                },
                "fdi": None,
                "fdi_confidence": 0.94,
                "raw_fdi": "37",
                "fdi_was_changed": True,
                "duplicate_cleanup_applied": False,
                "fdi_review_required": True,
                "quadrant_candidates": ["1", "4"],
                "resolved_quadrant": "4",
                "side_constraint_applied": True,
                "side_constraint_overrode_raw_quadrant": True,
                "status_gate": {
                    "prediction": "NON_HEALTHY",
                    "effective_prediction": "NON_HEALTHY",
                },
                "status_v2": {
                    "prediction": "FILLING",
                    "confidence": 0.8945,
                },
                "pathology_evidence": [],
                "restorations": [],
                "deep_caries": {
                    "ran": False,
                    "probability": None,
                    "threshold": 0.65,
                    "upgraded": False,
                    "reason": "NO_CARIES_EVIDENCE",
                },
                "final_findings": ["FILLING"],
                "review_reasons": ["FDI_LOW_CONFIDENCE_OR_UNRESOLVED"],
                "review_required": True,
            }
        ],
        "summary": {
            "teeth": 1,
            "unique_fdi": 0,
            "pathology_detections": 0,
            "restorations": 0,
            "review_required": 1,
            "runtime_seconds": 0.01,
        },
    }


class FakeQuality:
    def analyze(self, _image_bytes: bytes) -> ImageQuality:
        return ImageQuality(
            image_type="OPG",
            orientation="STANDARD",
            width=1200,
            height=684,
            blur_score=0.0,
            exposure_mean=0.5,
            contrast_score=0.5,
            cropping_suspected=False,
            gross_artifact=False,
            quality=QualityLevel.ACCEPTABLE,
            usable_for_analysis=True,
            warnings=[],
        )


class FakeRisk:
    def predict(self, _findings):
        return []


class FakeEngine:
    def analyze_bytes(self, _image_bytes: bytes) -> dict:
        return unresolved_raw_result()


@pytest.mark.asyncio
async def test_real_provider_preserves_unresolved_finding_without_fake_fdi(
    monkeypatch,
) -> None:
    provider = DENTAIRealOPGProvider.__new__(DENTAIRealOPGProvider)
    provider.settings = SimpleNamespace(
        ai_model_artifact_path="/unused/models",
        ai_model_manifest_path="/unused/manifest.json",
    )
    provider.quality = FakeQuality()
    provider.risk = FakeRisk()
    provider.longitudinal = LongitudinalDentalEngine()
    provider.groq = None
    monkeypatch.setattr(provider_module, "_v5_engine", lambda *_args: FakeEngine())

    result = await provider.analyze_xray(
        patient_context={},
        xray_reference="xray-1",
        image_bytes=b"in-memory-protected-bytes",
    )

    assert result.findings[0]["tooth_code"] is None
    assert "unresolved tooth region" in result.findings[0]["description"]
    assert "tooth None" not in result.findings[0]["description"]
    assert result.structured_result["teeth"][0]["fdi"] is None
    assert result.structured_result["teeth"][0]["findings"][0]["tooth_fdi"] is None
    assert result.structured_result["vision_evidence"]["teeth"][0]["raw_fdi"] == "37"
    provenance = result.findings[0]["provenance"]
    assert provenance["raw_fdi"] == "37"
    assert provenance["fdi_review_required"] is True
    assert provenance["tooth_detection_instance_id"] == 7
    assert provenance["side_constraint_overrode_raw_quadrant"] is True
