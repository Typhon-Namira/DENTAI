from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QualityLevel(StrEnum):
    ACCEPTABLE = "ACCEPTABLE"
    LIMITED = "LIMITED"
    REQUIRES_RETAKE_OR_REVIEW = "REQUIRES_RETAKE_OR_REVIEW"


class ComponentState(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    MODEL_REQUIRED = "MODEL_REQUIRED"
    NOT_RUN = "NOT_RUN"


class UncertaintyLevel(StrEnum):
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    MODERATE_CONFIDENCE = "MODERATE_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"


class ImageQuality(BaseModel):
    image_type: str
    orientation: str
    width: int
    height: int
    blur_score: float
    exposure_mean: float
    contrast_score: float
    cropping_suspected: bool
    gross_artifact: bool
    quality: QualityLevel
    usable_for_analysis: bool
    warnings: list[str] = Field(default_factory=list)


class VisionFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_type: str
    description: str
    tooth_fdi: str | None = Field(default=None, pattern=r"^[1-4][1-8]$")
    raw_score: float | None = Field(default=None, ge=0, le=1)
    calibrated_confidence: float | None = Field(default=None, ge=0, le=1)
    uncertainty: UncertaintyLevel
    uncertainty_reason: str | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    mask_reference: str | None = None
    source_model: str
    model_version: str
    source_image_id: str

    @model_validator(mode="after")
    def require_reason_for_uncertainty(self):
        if self.uncertainty in {UncertaintyLevel.LOW_CONFIDENCE, UncertaintyLevel.NOT_ASSESSABLE}:
            if not self.uncertainty_reason:
                raise ValueError("uncertain findings require uncertainty_reason")
        return self


class ToothObservation(BaseModel):
    fdi: str = Field(pattern=r"^[1-4][1-8]$")
    presence: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    findings: list[VisionFinding] = Field(default_factory=list)


class OPGAnalysisResult(BaseModel):
    analysis_schema_version: str = "opg-1.0"
    image: ImageQuality
    teeth: list[ToothObservation] = Field(default_factory=list)
    edentulous_regions: list[dict] = Field(default_factory=list)
    global_findings: list[VisionFinding] = Field(default_factory=list)
    component_status: dict[str, ComponentState]
    requires_doctor_review: bool = True
    prevention_recommendations: list[dict] = Field(default_factory=list)
    longitudinal_changes: list[dict] = Field(default_factory=list)
    clinical_summary: dict | None = None
    disclaimers: list[str] = Field(
        default_factory=lambda: [
            "AI-generated radiographic decision support; dentist review is required."
        ]
    )

    def findings(self) -> list[VisionFinding]:
        return self.global_findings + [
            finding for tooth in self.teeth for finding in tooth.findings
        ]
