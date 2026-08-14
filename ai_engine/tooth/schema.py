"""Research-only Tooth V2 to FDI enumeration handoff schema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)


class ToothInstanceOutput(BaseModel):
    instance_id: str
    box_xyxy: tuple[float, float, float, float]
    mask_rle: dict[str, object] | None = None
    centroid: Point
    confidence: float = Field(ge=0, le=1)
    normalized_centroid: Point
    arch_probability_upper: float | None = Field(default=None, ge=0, le=1)
    relative_order: int | None = Field(default=None, ge=0)
    neighbor_instance_ids: list[str] = Field(default_factory=list)


class ToothV2Handoff(BaseModel):
    schema_version: str = "dentai-tooth-fdi-handoff-1.0"
    model_lifecycle: str = "RESEARCH_ONLY"
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    instances: list[ToothInstanceOutput]
