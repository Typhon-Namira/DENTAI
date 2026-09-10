from app.care.generation_engine import (
    group_pathological_teeth,
    is_pathological_finding,
    review_recommended,
)
from app.database.models import DentalFinding, FindingReview


def _finding(
    finding_type: str,
    confidence: float | None,
    *,
    tooth: str = "38",
    review: FindingReview = FindingReview.PENDING,
) -> DentalFinding:
    return DentalFinding(
        patient_id=None,
        analysis_id=None,
        tooth_code=tooth,
        finding_type=finding_type,
        description="test",
        source="AI",
        confidence=confidence,
        provenance={},
        review_status=review,
    )


def test_low_confidence_red_pathology_is_eligible_for_draft_plan():
    finding = _finding("CARIES", 0.47)
    assert is_pathological_finding(finding)
    assert review_recommended(finding)


def test_restorative_and_rejected_findings_do_not_enter_plan():
    assert not is_pathological_finding(_finding("FILLING", 0.99))
    assert not is_pathological_finding(
        _finding("CARIES", 0.99, review=FindingReview.REJECTED)
    )


def test_multiple_pathologies_on_same_tooth_create_one_candidate():
    candidates = group_pathological_teeth(
        [
            _finding("CARIES", 0.58, tooth="38"),
            _finding("APICAL_PERIODONTITIS", 0.47, tooth="38"),
            _finding("CARIES", 0.80, tooth="33"),
        ]
    )
    assert len(candidates) == 2
    tooth_38 = next(candidate for candidate in candidates if candidate.tooth_fdi == "38")
    assert len(tooth_38.findings) == 2
    assert tooth_38.primary.finding_type == "APICAL_PERIODONTITIS"


def test_unresolved_or_invalid_tooth_is_not_eligible():
    assert not is_pathological_finding(_finding("CARIES", 0.80, tooth="?"))
    assert not is_pathological_finding(_finding("CARIES", 0.80, tooth="55"))
