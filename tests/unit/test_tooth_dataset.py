import json
from pathlib import Path

import torch
from PIL import Image

from ai_engine.data.tooth_instances import (
    convert_labelme_instances,
    convert_via_instances,
    render_qa_samples,
)
from ai_engine.training.dataset import (
    CanonicalToothInstanceDataset,
    ViaToothInstanceDataset,
    detection_collate,
)
from ai_engine.training.maskrcnn import load_checkpoint, save_checkpoint


def test_via_dataset_builds_detection_target(tmp_path: Path):
    Image.new("RGB", (20, 10)).save(tmp_path / "case.jpg")
    annotation = {
        "_via_img_metadata": {
            "case": {
                "filename": "case.jpg",
                "regions": [
                    {
                        "shape_attributes": {
                            "all_points_x": [2, 8, 8, 2],
                            "all_points_y": [2, 2, 7, 7],
                        }
                    }
                ],
            }
        }
    }
    path = tmp_path / "annotations.json"
    path.write_text(json.dumps(annotation), encoding="utf-8")
    dataset = ViaToothInstanceDataset(tmp_path, path, output_size=(10, 5))
    image, target = dataset[0]
    assert image.shape == (3, 5, 10)
    assert target["masks"].shape == (1, 5, 10)
    assert target["boxes"].tolist() == [[1.0, 1.0, 4.0, 3.5]]
    assert target["labels"].tolist() == [1]
    assert detection_collate([(image, target)])[0][0] is image


def test_checkpoint_uses_restricted_loader_and_restores_training_state(tmp_path: Path):
    model = torch.nn.Linear(2, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1)
    path = tmp_path / "checkpoint.pt"
    save_checkpoint(path, model, optimizer, scheduler, epoch=3)
    original = {name: value.clone() for name, value in model.state_dict().items()}
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
    assert load_checkpoint(path, model, optimizer, scheduler) == 4
    assert all(torch.equal(model.state_dict()[name], value) for name, value in original.items())


def test_canonical_conversion_and_visual_qa(tmp_path: Path):
    Image.new("RGB", (20, 10)).save(tmp_path / "case.jpg")
    source = tmp_path / "via.json"
    source.write_text(
        json.dumps(
            {
                "_via_img_metadata": {
                    "case": {
                        "filename": "case.jpg",
                        "regions": [
                            {
                                "shape_attributes": {
                                    "all_points_x": [2, 8, 8, 2],
                                    "all_points_y": [2, 2, 7, 7],
                                }
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    converted = convert_via_instances(source, tmp_path, "fixture", "1")
    assert converted["images"][0]["instances"][0]["bbox_xyxy"] == [2, 2, 8, 7]
    assert converted["images"][0]["instances"][0]["fdi_label"] is None
    assert len(render_qa_samples(converted, tmp_path, tmp_path / "qa", count=1)) == 1


def test_labelme_canonical_dataset_preserves_fdi_and_filters_non_teeth(tmp_path: Path):
    Image.new("RGB", (20, 10)).save(tmp_path / "case.jpg")
    (tmp_path / "case.json").write_text(
        json.dumps(
            {
                "imagePath": "case.jpg",
                "shapes": [
                    {"label": "11 - Tooth", "points": [[2, 2], [8, 2], [8, 7], [2, 7]]},
                    {"label": "Filling", "points": [[3, 3], [4, 3], [4, 4]]},
                ],
            }
        ),
        encoding="utf-8",
    )
    canonical = convert_labelme_instances(tmp_path, tmp_path, "fixture", "1")
    canonical_path = tmp_path / "canonical.json"
    canonical_path.write_text(json.dumps(canonical), encoding="utf-8")
    dataset = CanonicalToothInstanceDataset(tmp_path, canonical_path, output_size=(10, 5))
    image, target = dataset[0]
    assert image.shape == (3, 5, 10)
    assert target["boxes"].tolist() == [[1.0, 1.0, 4.0, 3.5]]
    assert target["fdi_numbers"] == ["11"]
    assert target["source_dataset"] == "fixture"
