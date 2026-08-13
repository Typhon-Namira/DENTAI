from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DatasetTier(StrEnum):
    PRODUCTION_ALLOWED = "PRODUCTION_ALLOWED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    PROHIBITED = "PROHIBITED"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


class DatasetManifest(BaseModel):
    dataset_id: str
    name: str
    version: str
    source_url: str
    source_doi: str | None = None
    license: str
    tier: DatasetTier = DatasetTier.UNKNOWN_REVIEW_REQUIRED
    commercial_use_allowed: bool = False
    attribution_required: bool = False
    share_alike_required: bool = False
    modification_allowed: bool = False
    sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")
    tasks: list[str]
    source_labels: dict[str, str] = Field(default_factory=dict)
    patient_group_field: str | None = None
    notes: str = ""


class DatasetRegistry:
    def __init__(self, manifest_dir: Path):
        self.manifest_dir = manifest_dir

    def load(self, dataset_id: str) -> DatasetManifest:
        path = self.manifest_dir / f"{dataset_id}.yaml"
        if not path.is_file():
            raise KeyError(f"dataset is not registered: {dataset_id}")
        return DatasetManifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
