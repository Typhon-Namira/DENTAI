from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from ai_engine.product.risk_followup import FollowupEngine
from app.core.config import get_settings

PRODUCT_SCORE_THRESHOLD = 0.60


@dataclass(frozen=True)
class FollowupTiming:
    finding_type: str
    tooth_fdi: str
    recommended_window: str
    target_followup_at: datetime
    scheduled_send_at: datetime
    timing_reason: str
    policy_rule_id: str
    policy_version: str
    clinic_timezone: str


class FollowupTimingEngine:
    def __init__(self, policy_path: str = "config/dentai_followup_rules.json") -> None:
        self.engine = FollowupEngine(policy_path)

    def calculate(self, *, finding_type: str, tooth_fdi: str, analysis_at: datetime,
                  review_required: bool = False, lead_days: int | None = None,
                  timezone_name: str | None = None, send_hour: int | None = None) -> FollowupTiming:
        if not tooth_fdi or len(tooth_fdi) != 2 or tooth_fdi[0] not in "1234" or tooth_fdi[1] not in "12345678":
            raise ValueError("A resolved permanent FDI tooth is required.")
        settings = get_settings()
        zone_name = timezone_name or settings.whatsapp_followup_timezone
        zone = ZoneInfo(zone_name)
        local_analysis = analysis_at.astimezone(zone)
        recommendation = self.engine.recommend(
            {"fdi": tooth_fdi, "final_findings": [{"type": finding_type}], "review_required": review_required},
            analysis_date=local_analysis.date(),
        )
        target_date: date = recommendation.target_followup_date
        hour = settings.whatsapp_send_hour if send_hour is None else send_hour
        target_local = datetime(target_date.year, target_date.month, target_date.day, hour, tzinfo=zone)
        lead = settings.whatsapp_reminder_lead_days if lead_days is None else lead_days
        scheduled_local = target_local - timedelta(days=lead)
        window = recommendation.followup_window
        return FollowupTiming(
            finding_type=finding_type, tooth_fdi=tooth_fdi,
            recommended_window=f"{window.min_months}–{window.max_months} months",
            target_followup_at=target_local.astimezone(UTC),
            scheduled_send_at=scheduled_local.astimezone(UTC),
            timing_reason="; ".join(recommendation.reasons),
            policy_rule_id=",".join(recommendation.rule_ids),
            policy_version=recommendation.rule_version, clinic_timezone=zone_name,
        )


def eligible_finding(tooth_code: str | None, confidence: float | None) -> bool:
    return (
        tooth_code is not None and len(tooth_code) == 2
        and tooth_code[0] in "1234" and tooth_code[1] in "12345678"
        and confidence is not None and confidence >= PRODUCT_SCORE_THRESHOLD
    )
