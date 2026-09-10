from app.care import sequential_api, sequential_manage_api
from app.care.sequential import _priority
from app.database.models import DentalFinding, FindingReview


def _finding(finding_type: str, confidence: float, review=FindingReview.PENDING):
    return DentalFinding(
        patient_id=None,
        analysis_id=None,
        tooth_code="16",
        finding_type=finding_type,
        description="test",
        source="AI",
        confidence=confidence,
        provenance={},
        review_status=review,
    )


def test_priority_prefers_pathology_urgency_then_confidence():
    urgent = _finding("BONE_RESORPTION", 0.61)
    high = _finding("CARIES", 0.99)
    assert _priority(urgent)[0] == "URGENT"
    assert _priority(high)[0] == "HIGH"
    assert _priority(urgent)[1] > _priority(high)[1]


def test_confirmed_review_is_a_bonus_not_a_generation_requirement():
    pending = _finding("CARIES", 0.80, FindingReview.PENDING)
    confirmed = _finding("CARIES", 0.80, FindingReview.CONFIRMED)
    assert _priority(pending)[1] > 0
    assert _priority(confirmed)[1] > _priority(pending)[1]


def test_sequential_inbound_route_contract():
    route = next(
        item
        for item in sequential_api.router.routes
        if getattr(item, "path", None) == "/care/internal/whatsapp/inbound"
    )
    assert "POST" in route.methods
    assert route.endpoint is sequential_api.sequential_inbound_whatsapp


def test_new_sequential_management_route_contracts():
    paths = {getattr(route, "path", None) for route in sequential_manage_api.router.routes}
    assert "/care/sequential-plans/search" in paths
    assert "/care/plans/{plan_id}/items/{item_id}/sequence-schedule" in paths
    assert "/care/appointments/{appointment_id}/outcome" in {
        getattr(route, "path", None) for route in sequential_api.router.routes
    }
