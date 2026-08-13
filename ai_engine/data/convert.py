from pydantic import BaseModel

from ai_engine.ontology.canonical import normalize_label


class CanonicalAnnotation(BaseModel):
    image_id: str
    patient_group_id: str
    source_label: str
    canonical_label: str
    tooth_fdi: str | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    polygon: list[tuple[float, float]] | None = None
    reviewer: str | None = None
    review_status: str = "UNREVIEWED"


def convert_annotation(**source) -> CanonicalAnnotation:
    source["canonical_label"] = normalize_label(source["source_label"])
    return CanonicalAnnotation.model_validate(source)
