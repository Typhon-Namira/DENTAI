from enum import StrEnum

from pydantic import BaseModel

from ai_engine.schemas import OPGAnalysisResult


class ChangeState(StrEnum):
    NEW = "NEW"
    STABLE = "STABLE"
    RESOLVED = "RESOLVED"
    UNCERTAIN = "UNCERTAIN"


class LongitudinalChange(BaseModel):
    tooth_fdi: str | None
    finding_type: str
    state: ChangeState
    prior_model: str | None = None
    current_model: str | None = None
    caveat: str = "Comparison is assistive; panoramic acquisition geometry can differ."


class LongitudinalDentalEngine:
    """Compares independently produced structured findings; it does not perform inference."""

    def compare(
        self, prior: OPGAnalysisResult, current: OPGAnalysisResult
    ) -> list[LongitudinalChange]:
        def keyed(result: OPGAnalysisResult):
            return {
                (finding.tooth_fdi, finding.finding_type): finding for finding in result.findings()
            }

        old, new = keyed(prior), keyed(current)
        changes = []
        for key in sorted(old.keys() | new.keys(), key=str):
            before, after = old.get(key), new.get(key)
            if before and after:
                state = ChangeState.STABLE
            elif after:
                state = ChangeState.NEW
            else:
                state = ChangeState.RESOLVED
            changes.append(
                LongitudinalChange(
                    tooth_fdi=key[0],
                    finding_type=key[1],
                    state=state,
                    prior_model=before.source_model if before else None,
                    current_model=after.source_model if after else None,
                )
            )
        return changes
