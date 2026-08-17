from ai_engine.longitudinal.engine import ChangeState, LongitudinalDentalEngine
from ai_engine.schemas import (
    ComponentState,
    ImageQuality,
    OPGAnalysisResult,
    QualityLevel,
    ToothObservation,
    UncertaintyLevel,
    VisionFinding,
)


def _finding(
    finding_type: str,
    tooth_fdi: str | None,
    *,
    source_image_id: str,
    raw_fdi_trace: str | None = None,
) -> VisionFinding:
    unresolved = tooth_fdi is None
    trace = f"; raw candidate {raw_fdi_trace}" if raw_fdi_trace else ""
    return VisionFinding(
        finding_type=finding_type,
        description=f"Model-generated finding{trace}",
        tooth_fdi=tooth_fdi,
        raw_score=0.87,
        calibrated_confidence=0.84,
        uncertainty=(
            UncertaintyLevel.LOW_CONFIDENCE if unresolved else UncertaintyLevel.MODERATE_CONFIDENCE
        ),
        uncertainty_reason=("FDI_LOW_CONFIDENCE_OR_UNRESOLVED" if unresolved else None),
        bounding_box=(10.0, 20.0, 40.0, 60.0),
        source_model="DENTAI Unified V5",
        model_version="dentai-unified-v5",
        source_image_id=source_image_id,
    )


def _analysis(findings: list[VisionFinding]) -> OPGAnalysisResult:
    return OPGAnalysisResult(
        image=ImageQuality(
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
        ),
        teeth=[
            ToothObservation(
                fdi=finding.tooth_fdi,
                presence="PRESENT",
                confidence=0.95,
                findings=[finding],
            )
            for finding in findings
        ],
        component_status={"fdi": ComponentState.SUCCESS},
    )


def test_unresolved_findings_are_excluded_from_tooth_specific_matching():
    current = _analysis(
        [
            _finding("DEEP_CARIES", None, source_image_id="region-a"),
            _finding("DEEP_CARIES", None, source_image_id="region-b"),
        ]
    )

    assert len(current.findings()) == 2
    assert LongitudinalDentalEngine().compare(_analysis([]), current) == []


def test_resolved_findings_keep_existing_new_stable_resolved_semantics():
    prior = _analysis(
        [
            _finding("FILLING", "36", source_image_id="prior-36"),
            _finding("DEEP_CARIES", "37", source_image_id="prior-37"),
        ]
    )
    current = _analysis(
        [
            _finding("FILLING", "36", source_image_id="current-36"),
            _finding("CROWN", "38", source_image_id="current-38"),
        ]
    )

    changes = LongitudinalDentalEngine().compare(prior, current)
    states = {(change.tooth_fdi, change.finding_type): change.state for change in changes}

    assert states == {
        ("36", "FILLING"): ChangeState.STABLE,
        ("37", "DEEP_CARIES"): ChangeState.RESOLVED,
        ("38", "CROWN"): ChangeState.NEW,
    }


def test_raw_fdi_trace_is_never_used_as_longitudinal_identity():
    prior = _analysis(
        [
            _finding(
                "DEEP_CARIES",
                None,
                source_image_id="prior-region",
                raw_fdi_trace="37",
            )
        ]
    )
    current = _analysis(
        [
            _finding(
                "DEEP_CARIES",
                None,
                source_image_id="current-region",
                raw_fdi_trace="37",
            )
        ]
    )

    assert LongitudinalDentalEngine().compare(prior, current) == []


def test_mixed_resolved_and_unresolved_analyses_do_not_crash():
    prior = _analysis(
        [
            _finding("FILLING", "36", source_image_id="prior-36"),
            _finding("DEEP_CARIES", None, source_image_id="prior-unresolved"),
        ]
    )
    current = _analysis(
        [
            _finding("FILLING", "36", source_image_id="current-36"),
            _finding("CROWN", None, source_image_id="current-unresolved"),
        ]
    )

    changes = LongitudinalDentalEngine().compare(prior, current)

    assert len(changes) == 1
    assert changes[0].tooth_fdi == "36"
    assert changes[0].finding_type == "FILLING"
    assert changes[0].state == ChangeState.STABLE
