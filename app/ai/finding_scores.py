"""Resolve DENTAI V5 final findings to the model evidence that produced them.

Product visibility, clinical summaries, clinician review, and outreach all consume the
finding confidence. Never substitute an unrelated head's score: if a final finding cannot
be traced to supporting model evidence, fail closed instead of inventing confidence.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FindingScore:
    score: float
    source_head: str
    evidence_type: str


def _finite_score(value: object, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} score is missing or non-numeric")
    score = float(value)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(f"{context} score must be finite and between 0 and 1")
    return score


def _status_supports(status: str, finding_type: str) -> bool:
    if status == finding_type:
        return True
    return status == "RCT_CROWN" and finding_type in {"CROWN", "ROOT_CANAL_TREATMENT"}


def score_candidates(tooth: dict, finding_type: str) -> list[FindingScore]:
    """Return every direct V5 evidence source supporting a final finding."""
    candidates: list[FindingScore] = []

    status = tooth.get("status_v2") or {}
    prediction = status.get("prediction")
    if isinstance(prediction, str) and _status_supports(prediction, finding_type):
        candidates.append(
            FindingScore(
                _finite_score(status.get("confidence"), context="status_v2"),
                "status_v2",
                prediction,
            )
        )

    for evidence in tooth.get("pathology_evidence") or []:
        if evidence.get("type") == finding_type:
            candidates.append(
                FindingScore(
                    _finite_score(evidence.get("confidence"), context="pathology"),
                    "pathology",
                    finding_type,
                )
            )

    for evidence in tooth.get("restorations") or []:
        if evidence.get("detector_type") == finding_type:
            candidates.append(
                FindingScore(
                    _finite_score(
                        evidence.get("detector_confidence"), context="restoration_detector"
                    ),
                    "restoration_detector",
                    finding_type,
                )
            )

    if finding_type == "DEEP_CARIES":
        deep = tooth.get("deep_caries") or {}
        if deep.get("ran") and deep.get("upgraded"):
            # DEEP_CARIES is a deliberate upgrade of CARIES, so its product confidence
            # must be the deep-caries classifier probability, not the upstream CARIES score.
            candidates = [
                FindingScore(
                    _finite_score(deep.get("probability"), context="deep_caries"),
                    "deep_caries",
                    "DEEP_CARIES",
                )
            ]

    return candidates


def resolve_finding_score(tooth: dict, finding_type: str) -> tuple[FindingScore, list[FindingScore]]:
    """Choose the strongest direct evidence and preserve all supporting score sources."""
    candidates = score_candidates(tooth, finding_type)
    if not candidates:
        raise ValueError(f"No model evidence supports final finding {finding_type!r}")
    selected = max(candidates, key=lambda item: item.score)
    return selected, candidates
