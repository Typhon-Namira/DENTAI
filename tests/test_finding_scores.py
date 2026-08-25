import pytest

from app.ai.finding_scores import resolve_finding_score


def base_tooth() -> dict:
    return {
        "status_v2": {"prediction": "CARIES", "confidence": 0.91},
        "pathology_evidence": [],
        "restorations": [],
        "deep_caries": {"ran": False, "probability": None, "upgraded": False},
    }


def test_pathology_score_is_not_replaced_by_status_score() -> None:
    tooth = base_tooth()
    tooth["pathology_evidence"] = [
        {"type": "BONE_RESORPTION", "confidence": 0.52}
    ]

    selected, sources = resolve_finding_score(tooth, "BONE_RESORPTION")

    assert selected.score == pytest.approx(0.52)
    assert selected.source_head == "pathology"
    assert [source.score for source in sources] == [pytest.approx(0.52)]


def test_strong_pathology_score_is_not_suppressed_by_status_score() -> None:
    tooth = base_tooth()
    tooth["status_v2"] = {"prediction": "CARIES", "confidence": 0.48}
    tooth["pathology_evidence"] = [
        {"type": "APICAL_PERIODONTITIS", "confidence": 0.87}
    ]

    selected, _ = resolve_finding_score(tooth, "APICAL_PERIODONTITIS")

    assert selected.score == pytest.approx(0.87)
    assert selected.source_head == "pathology"


def test_deep_caries_uses_upgrade_probability() -> None:
    tooth = base_tooth()
    tooth["deep_caries"] = {
        "ran": True,
        "probability": 0.76,
        "upgraded": True,
    }

    selected, sources = resolve_finding_score(tooth, "DEEP_CARIES")

    assert selected.score == pytest.approx(0.76)
    assert selected.source_head == "deep_caries"
    assert len(sources) == 1


def test_multiple_direct_sources_are_preserved_and_strongest_is_selected() -> None:
    tooth = base_tooth()
    tooth["pathology_evidence"] = [{"type": "CARIES", "confidence": 0.74}]

    selected, sources = resolve_finding_score(tooth, "CARIES")

    assert selected.score == pytest.approx(0.91)
    assert {source.source_head for source in sources} == {"status_v2", "pathology"}


def test_untraceable_final_finding_fails_closed() -> None:
    with pytest.raises(ValueError, match="No model evidence supports"):
        resolve_finding_score(base_tooth(), "ROOT_FRAGMENT")
