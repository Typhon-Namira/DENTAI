import json
from pathlib import Path

import pytest
from PIL import Image

from ai_engine.data.tooth_v2 import (
    deterministic_split,
    normalized_image_hash,
    stable_json_hash,
    validate_no_leakage,
)
from ai_engine.tooth.schema import Point, ToothInstanceOutput, ToothV2Handoff
from ai_engine.training.hard_cases import HardCaseSignals, bounded_weights, hard_case_score


def _record(identifier: str, image_hash: str) -> dict:
    return {
        "canonical_image_id": identifier,
        "image_sha256": image_hash,
        "normalized_image_sha256": image_hash,
        "source_dataset": "test",
        "instances": [],
    }


def test_split_is_deterministic_and_groups_duplicates() -> None:
    records = [_record("a", "same"), _record("b", "same")] + [
        _record(str(index), str(index)) for index in range(20)
    ]
    first = deterministic_split(records, seed=47)
    second = deterministic_split(records, seed=47)
    assert first == second
    assert first["a"] == first["b"]
    validate_no_leakage(records, first)


def test_leakage_validator_rejects_duplicate_crossing() -> None:
    records = [_record("a", "same"), _record("b", "same")]
    with pytest.raises(ValueError, match="crosses splits"):
        validate_no_leakage(records, {"a": "train", "b": "test"})


def test_normalized_hash_ignores_encoding(tmp_path: Path) -> None:
    image = Image.new("L", (32, 16), 127)
    png, bmp = tmp_path / "image.png", tmp_path / "image.bmp"
    image.save(png)
    image.save(bmp)
    assert normalized_image_hash(png) == normalized_image_hash(bmp)


def test_hard_case_score_and_bounded_weights() -> None:
    easy = hard_case_score(HardCaseSignals())
    severe = hard_case_score(
        HardCaseSignals(false_negatives=4, merged_teeth=2, mean_matched_iou=0.1)
    )
    assert easy == 0
    assert severe > 0.7
    weights = bounded_weights([0.1] * 20 + [0.9])
    assert len(weights) == 21
    assert weights[-1] > weights[0]


def test_fdi_handoff_schema_is_research_only() -> None:
    instance = ToothInstanceOutput(
        instance_id="tooth-1",
        box_xyxy=(1, 2, 3, 4),
        centroid=Point(x=2, y=3),
        normalized_centroid=Point(x=0.2, y=0.3),
        confidence=0.9,
    )
    payload = ToothV2Handoff(image_width=10, image_height=10, instances=[instance])
    assert payload.model_lifecycle == "RESEARCH_ONLY"
    assert stable_json_hash(json.loads(payload.model_dump_json()))


def test_v1_and_v2_checkpoint_directories_are_isolated() -> None:
    config = Path("configs/ai/tooth_v2_maskrcnn.yaml").read_text(encoding="utf-8")
    assert "checkpoints/tooth_v2/maskrcnn" in config
    assert "checkpoints/tooth_v1" not in config


def test_v1_baseline_hash_matches_frozen_file() -> None:
    baseline = json.loads(Path("artifacts/baselines/tooth_v1/tooth_v1_baseline.json").read_text())
    assert (
        baseline["best_checkpoint"]["sha256"]
        == "e855eae61a08d932e054777aa815dddbf83cb5e22bd7ca43ce4d0ceaf32da1f5"
    )
