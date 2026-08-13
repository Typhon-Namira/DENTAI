from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import httpx
from pydantic import ValidationError

from ai_engine.data.registry import DatasetRegistry
from ai_engine.groq.provider import GroqClinicalSummaryProvider
from ai_engine.longitudinal.engine import LongitudinalDentalEngine
from ai_engine.models.registry import ModelRegistry
from ai_engine.quality.engine import OPGQualityEngine
from ai_engine.risk.engine import RuleBasedRecallRiskProvider
from ai_engine.schemas import ComponentState, OPGAnalysisResult
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


class DENTAIRealOPGProvider(DentalAIProvider):
    """Fail-closed orchestrator. It emits findings only from registered local model artifacts."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        datasets = DatasetRegistry(Path("ai_engine/data/manifests"))
        self.models = ModelRegistry(Path("configs/ai/models.yaml"), datasets)
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
        enabled_models = [model for model in self.models.load() if model.production_enabled]
        components = {
            name: ComponentState.MODEL_REQUIRED
            for name in (
                "tooth",
                "restoration",
                "endodontic",
                "pathology",
                "periodontal",
                "impaction",
            )
        }
        # No checkpoint is bundled. This intentionally produces no clinical findings.
        for model in enabled_models:
            artifact = self.settings.ai_model_artifact_path / model.artifact_filename
            if not artifact.is_file():
                components[model.task] = ComponentState.FAILED
        result = OPGAnalysisResult(image=quality, component_status=components)
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
        if self.groq:
            try:
                summary = await self.groq.summarize(
                    {
                        "patient_context": patient_context,
                        "current_findings": [],
                        "changes": result.longitudinal_changes,
                        "risk_recommendations": result.prevention_recommendations,
                    }
                )
                result.clinical_summary = summary.model_dump()
            except (httpx.HTTPError, ValidationError, KeyError, TypeError, ValueError):
                # Narrative generation is optional and may never change vision results.
                result.clinical_summary = {"status": "UNAVAILABLE"}
        return AIProviderResult(
            result.model_dump(mode="json"),
            [],
            "real_opg",
            "dentai-opg-orchestrator",
            "0.1.0-untrained",
            result.analysis_schema_version,
        )


def ai_provider() -> DentalAIProvider:
    provider = get_settings().ai_provider
    if provider == "mock":
        return MockDentalAIProvider()
    if provider == "real_opg":
        return DENTAIRealOPGProvider()
    raise RuntimeError(f"Unsupported AI_PROVIDER: {provider}")
