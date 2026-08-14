from pydantic import BaseModel

from ai_engine.ontology.canonical import normalize_label


class CanonicalAnnotation(BaseModel):
    schema_version: str = "dentai-annotation-1.0"
    source_dataset: str
    source_version: str
    image_id: str
    source_image_id: str
    patient_group_id: str
    source_label: str
    canonical_label: str
    tooth_fdi: str | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    polygon: list[tuple[float, float]] | None = None
    original_annotation: dict
    transformed_annotation: dict
    provenance: dict[str, str]
    reviewer: str | None = None
    review_status: str = "UNREVIEWED"


def convert_annotation(**source) -> CanonicalAnnotation:
    source["canonical_label"] = normalize_label(source["source_label"])
    return CanonicalAnnotation.model_validate(source)
