from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class TrainingDataConfig(BaseModel):
    dataset_ids: list[str] = Field(min_length=1)
    split_manifest: Path
    minimum_annotated_training_cases: int = Field(ge=1)
    input_size: tuple[int, int]
    channels: int = Field(ge=1, le=3)
    normalization: dict[str, list[float]]


class ToothTrainingConfig(BaseModel):
    schema_version: str
    task: str
    capability_state: str
    clinical_review_state: str
    model: dict
    data: TrainingDataConfig
    augmentation: dict
    optimizer: dict
    scheduler: dict
    training: dict
    losses: dict
    evaluation: dict
    checkpointing: dict

    @model_validator(mode="after")
    def enforce_safety(self):
        if self.task != "tooth_instance_segmentation":
            raise ValueError("Tooth V1 must remain an instance segmentation task")
        if self.clinical_review_state == "APPROVED_FOR_PILOT":
            raise ValueError("training configuration cannot grant clinical approval")
        if self.augmentation.get("horizontal_flip_probability", 0) != 0:
            raise ValueError("horizontal flips require explicit FDI-aware label remapping")
        return self


def load_training_config(path: Path) -> ToothTrainingConfig:
    return ToothTrainingConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
