from abc import ABC, abstractmethod
from pathlib import Path

import yaml
from pydantic import BaseModel

from ai_engine.schemas import VisionFinding


class RecallRecommendation(BaseModel):
    risk_level: str
    recall_priority: str
    recommended_window_days: dict[str, int] | None
    reason_codes: list[str]
    requires_doctor_approval: bool = True
    policy_approved: bool


class DentalRiskPredictionProvider(ABC):
    @abstractmethod
    def predict(self, findings: list[VisionFinding]) -> list[RecallRecommendation]: ...


class RuleBasedRecallRiskProvider(DentalRiskPredictionProvider):
    def __init__(self, policy_path: Path):
        self.policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))

    def predict(self, findings: list[VisionFinding]) -> list[RecallRecommendation]:
        recommendations = []
        rules = self.policy.get("rules", {})
        approved = bool(self.policy.get("clinician_approved", False))
        for finding in findings:
            rule = rules.get(finding.finding_type)
            if not rule:
                continue
            recommendations.append(
                RecallRecommendation(
                    risk_level=rule["risk_level"],
                    recall_priority=rule["recall_priority"],
                    recommended_window_days=rule.get("recommended_window_days")
                    if approved
                    else None,
                    reason_codes=[rule["reason_code"]],
                    policy_approved=approved,
                )
            )
        return recommendations


class LearnedLongitudinalRiskProvider(DentalRiskPredictionProvider):
    def predict(self, findings: list[VisionFinding]) -> list[RecallRecommendation]:
        raise NotImplementedError("No validated longitudinal prediction model is available")
