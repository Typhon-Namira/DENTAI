import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from ai_engine.groq.provider import (
    GroqClinicalSummaryProvider,
    summarize_product_findings,
)
from ai_engine.inference.dentai_unified_v5_onnx import Engine, FrozenArtifactError
from ai_engine.longitudinal.engine import LongitudinalDentalEngine
from ai_engine.quality.engine import OPGQualityEngine
from ai_engine.risk.engine import RuleBasedRecallRiskProvider
from ai_engine.schemas import (
    ComponentState,
    OPGAnalysisResult,
    ToothObservation,
    UncertaintyLevel,
    VisionFinding,
)
from app.core.config import get_settings


@dataclass(frozen=True)
class AIProviderResult:
    structured_result: dict
    findings: list[dict]
    provider: str
    model_name: str
    model_version: str
    schema_version: str


class DentalAIProvider(ABC):
    @abstractmethod
    async def analyze_xray(
        self,
        *,
        patient_context: dict,
        xray_reference: str,
        image_bytes: bytes | None = None,
        prior_analysis: dict | None = None,
    ) -> AIProviderResult: ...


class MockDentalAIProvider(DentalAIProvider):
    async def analyze_xray(
        self,
        *,
        patient_context: dict,
        xray_reference: str,
        image_bytes: bytes | None = None,
        prior_analysis: dict | None = None,
    ) -> AIProviderResult:
        finding = {
            "tooth_code": None,
            "finding_type": "REVIEW_REQUIRED",
            "description": "Mock decision-support result; dentist review required.",
            "confidence": None,
            "provenance": {"mock": True, "source_image_id": xray_reference},
        }
        return AIProviderResult(
            {
                "analysis_schema_version": "mock-1.0",
                "mock": True,
                "disclaimer": "Not a diagnosis. Dentist review is required.",
                "findings": [finding],
            },
            [finding],
            "mock",
            "mock-dental-decision-support",
            "1",
            "mock-1.0",
        )


@lru_cache(maxsize=1)
def _v5_engine(model_root: str, manifest_path: str) -> Engine:
    """One immutable ONNX engine per worker process, initialized only after verification."""
    return Engine(model_root=Path(model_root), manifest_path=Path(manifest_path))


class DENTAIRealOPGProvider(DentalAIProvider):
    """Protected-byte DENTAI Unified V5 inference with fail-closed artifact verification."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.quality = OPGQualityEngine()
        self.risk = RuleBasedRecallRiskProvider(Path("configs/ai/risk_policy.yaml"))
        self.longitudinal = LongitudinalDentalEngine()
        self.groq = (
            GroqClinicalSummaryProvider(
                settings.groq_api_key, settings.groq_model, settings.groq_timeout_seconds
            )
            if settings.groq_api_key
            else None
        )

    async def analyze_xray(
        self,
        *,
        patient_context: dict,
        xray_reference: str,
        image_bytes: bytes | None = None,
        prior_analysis: dict | None = None,
    ) -> AIProviderResult:
        if image_bytes is None:
            raise ValueError("real OPG inference requires protected image bytes")
        quality = self.quality.analyze(image_bytes)
        if not quality.usable_for_analysis:
            raise ValueError("radiograph quality gate did not permit DENTAI V5 inference")
        try:
            engine = _v5_engine(
                str(self.settings.ai_model_artifact_path), str(self.settings.ai_model_manifest_path)
            )
            raw = await asyncio.to_thread(engine.analyze_bytes, image_bytes)
        except (FrozenArtifactError, OSError, ValueError) as exc:
            raise RuntimeError("DENTAI V5 inference failed closed") from exc
        teeth = []
        structured_findings: list[dict] = []
        for tooth in raw["teeth"]:
            review = bool(tooth["review_required"])
            confidence = float(tooth["status_v2"]["confidence"])
            uncertainty = (
                UncertaintyLevel.LOW_CONFIDENCE
                if review
                else UncertaintyLevel.MODERATE_CONFIDENCE
            )
            reason = "; ".join(tooth["review_reasons"]) if review else None
            findings = []
            for finding_type in tooth["final_findings"]:
                if finding_type == "HEALTHY":
                    continue
                item = VisionFinding(
                    finding_type=finding_type,
                    description=(
                        f"DENTAI Unified V5 candidate finding for tooth {tooth['fdi']}; "
                        "dentist review required."
                    ),
                    tooth_fdi=tooth["fdi"],
                    raw_score=confidence,
                    calibrated_confidence=confidence, uncertainty=uncertainty,
                    uncertainty_reason=reason,
                    bounding_box=tuple(tooth["tooth_detection"]["bbox_xyxy"]),
                    source_model="DENTAI Unified V5", model_version="dentai-unified-v5",
                    source_image_id=xray_reference,
                )
                findings.append(item)
                structured_findings.append({
                    "tooth_code": item.tooth_fdi,
                    "finding_type": item.finding_type,
                    "description": item.description,
                    "confidence": item.calibrated_confidence,
                    "provenance": {
                        "source_model": item.source_model,
                        "model_version": item.model_version,
                        "raw_score": item.raw_score,
                        "uncertainty": item.uncertainty.value,
                        "uncertainty_reason": item.uncertainty_reason,
                        "bounding_box": list(item.bounding_box or ()),
                        "review_required": review,
                        "review_reasons": tooth["review_reasons"],
                    },
                })
            teeth.append(
                ToothObservation(
                    fdi=tooth["fdi"],
                    presence="PRESENT",
                    confidence=tooth["tooth_detection"]["confidence"],
                    findings=findings,
                )
            )
        result = OPGAnalysisResult(
            image=quality, teeth=teeth,
            component_status={
                name: ComponentState.SUCCESS
                for name in (
                    "tooth",
                    "fdi",
                    "status_gate",
                    "status",
                    "pathology",
                    "deep_caries",
                    "restoration",
                )
            },
        )
        if prior_analysis:
            try:
                prior = OPGAnalysisResult.model_validate(prior_analysis)
            except ValidationError:
                prior = None
            if prior:
                result.longitudinal_changes = [
                    change.model_dump(mode="json")
                    for change in self.longitudinal.compare(prior, result)
                ]
        result.prevention_recommendations = [
            item.model_dump(mode="json") for item in self.risk.predict(result.findings())
        ]
        result.clinical_summary = await summarize_product_findings(
            self.groq,
            structured_findings,
        )
        structured_result = result.model_dump(mode="json")
        # Preserve model evidence and review flags without making it a clinical conclusion.
        structured_result["vision_evidence"] = raw
        return AIProviderResult(
            structured_result,
            structured_findings,
            "real_opg",
            "DENTAI Unified V5",
            "dentai-unified-v5",
            result.analysis_schema_version,
        )


def ai_provider() -> DentalAIProvider:
    provider = get_settings().ai_provider
    if provider == "mock":
        return MockDentalAIProvider()
    if provider == "real_opg":
        return DENTAIRealOPGProvider()
    raise RuntimeError(f"Unsupported AI_PROVIDER: {provider}")
