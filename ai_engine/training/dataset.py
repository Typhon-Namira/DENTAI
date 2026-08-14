"""Torch datasets for audited tooth-instance annotations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from PIL import Image, ImageDraw
from torch import Tensor
from torch.utils.data import Dataset
from torchvision.transforms import functional as F


class ViaToothInstanceDataset(Dataset):
    """Load VIA polygons without altering source images or annotations.

    Empty VIA entries are excluded: they are not negative examples because the source
    documentation does not establish that an empty entry means a tooth-free OPG.
    """

    def __init__(
        self,
        image_dir: Path,
        annotation_file: Path,
        image_ids: set[str] | None = None,
        output_size: tuple[int, int] | None = None,
        train: bool = False,
    ) -> None:
        self.image_dir = image_dir
        self.output_size = output_size
        self.train = train
        raw = json.loads(annotation_file.read_text(encoding="utf-8"))
        records = raw["_via_img_metadata"].values()
        self.records = [
            record
            for record in records
            if record.get("regions")
            and (image_ids is None or record["filename"] in image_ids)
            and (image_dir / record["filename"]).is_file()
        ]
        self.records.sort(key=lambda record: record["filename"])

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[Tensor, dict[str, Any]]:
        record = self.records[index]
        image = Image.open(self.image_dir / record["filename"]).convert("RGB")
        width, height = image.size
        masks: list[Tensor] = []
        boxes: list[list[float]] = []
        source_ids: list[str] = []
        for region_index, region in enumerate(record["regions"]):
            shape = region.get("shape_attributes", {})
            xs, ys = shape.get("all_points_x", []), shape.get("all_points_y", [])
            if len(xs) < 3 or len(xs) != len(ys):
                continue
            points = [(float(x), float(y)) for x, y in zip(xs, ys, strict=True)]
            if any(x < 0 or x >= width or y < 0 or y >= height for x, y in points):
                continue
            mask_image = Image.new("L", (width, height))
            ImageDraw.Draw(mask_image).polygon(points, fill=1)
            mask = torch.from_numpy(__import__("numpy").array(mask_image, dtype="uint8"))
            if not mask.any():
                continue
            boxes.append([min(xs), min(ys), max(xs), max(ys)])
            masks.append(mask)
            source_ids.append(f"{record['filename']}:{region_index}")
        if not masks:
            raise ValueError(f"no valid tooth polygons in {record['filename']}")

        image_tensor = F.pil_to_tensor(image).float().div(255)
        mask_tensor = torch.stack(masks)
        box_tensor = torch.tensor(boxes, dtype=torch.float32)
        if self.output_size:
            out_w, out_h = self.output_size
            sx, sy = out_w / width, out_h / height
            image_tensor = F.resize(image_tensor, [out_h, out_w], antialias=True)
            mask_tensor = F.resize(
                mask_tensor, [out_h, out_w], interpolation=F.InterpolationMode.NEAREST
            )
            box_tensor *= torch.tensor([sx, sy, sx, sy])
        if self.train:
            # Photometric-only augmentation preserves anatomy and FDI laterality.
            image_tensor = F.adjust_contrast(image_tensor, 0.95 + 0.1 * torch.rand(1).item())
            image_tensor = F.adjust_brightness(image_tensor, 0.96 + 0.08 * torch.rand(1).item())

        area = (box_tensor[:, 2] - box_tensor[:, 0]) * (box_tensor[:, 3] - box_tensor[:, 1])
        target: dict[str, Any] = {
            "boxes": box_tensor,
            "masks": mask_tensor.to(torch.uint8),
            "labels": torch.ones(len(masks), dtype=torch.int64),
            "image_id": torch.tensor([index], dtype=torch.int64),
            "area": area,
            "iscrowd": torch.zeros(len(masks), dtype=torch.int64),
            "source_image": record["filename"],
            "source_dataset": "panoramic_dental_xray_73n3kz2k4k_v3",
            "source_annotation_ids": source_ids,
        }
        return image_tensor, target


class CanonicalToothInstanceDataset(Dataset):
    """Load DENTAI canonical polygons, retaining source and FDI metadata."""

    def __init__(
        self,
        image_dir: Path,
        canonical_file: Path,
        split_file: Path | None = None,
        split: str | None = None,
        output_size: tuple[int, int] | None = None,
        train: bool = False,
    ) -> None:
        self.image_dir = image_dir
        self.output_size = output_size
        self.train = train
        payload = json.loads(canonical_file.read_text(encoding="utf-8"))
        allowed: set[str] | None = None
        if split_file is not None:
            if split is None:
                raise ValueError("split is required with split_file")
            split_payload = json.loads(split_file.read_text(encoding="utf-8"))
            allowed = {
                record["image_id"]
                for record in split_payload["records"]
                if record["split"] == split
            }
        self.records = [
            record
            for record in payload["images"]
            if record.get("instances")
            and (allowed is None or record["source_image_id"] in allowed)
            and (image_dir / record.get("image_path", record["source_image_id"])).is_file()
        ]
        self.records.sort(key=lambda record: record["source_image_id"])

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[Tensor, dict[str, Any]]:
        record = self.records[index]
        image = Image.open(
            self.image_dir / record.get("image_path", record["source_image_id"])
        ).convert("RGB")
        width, height = image.size
        masks: list[Tensor] = []
        boxes: list[list[float]] = []
        source_ids: list[str] = []
        fdi_numbers: list[str | None] = []
        for instance in record["instances"]:
            if instance.get("canonical_class") != "TOOTH" or not instance.get("polygon"):
                continue
            mask_image = Image.new("L", (width, height))
            ImageDraw.Draw(mask_image).polygon(instance["polygon"], fill=1)
            mask = torch.from_numpy(__import__("numpy").array(mask_image, dtype="uint8"))
            box = [float(value) for value in instance["bbox_xyxy"]]
            if not mask.any() or box[2] <= box[0] or box[3] <= box[1]:
                continue
            masks.append(mask)
            boxes.append(box)
            source_ids.append(instance["source_annotation_id"])
            fdi_numbers.append(instance.get("fdi_number"))
        if not masks:
            raise ValueError(f"no valid tooth polygons in {record['source_image_id']}")
        image_tensor = F.pil_to_tensor(image).float().div(255)
        mask_tensor = torch.stack(masks)
        box_tensor = torch.tensor(boxes, dtype=torch.float32)
        if self.output_size:
            out_w, out_h = self.output_size
            image_tensor = F.resize(image_tensor, [out_h, out_w], antialias=True)
            mask_tensor = F.resize(
                mask_tensor, [out_h, out_w], interpolation=F.InterpolationMode.NEAREST
            )
            box_tensor *= torch.tensor([out_w / width, out_h / height] * 2)
        if self.train:
            image_tensor = F.adjust_contrast(image_tensor, 0.95 + 0.1 * torch.rand(1).item())
            image_tensor = F.adjust_brightness(image_tensor, 0.96 + 0.08 * torch.rand(1).item())
        area = (box_tensor[:, 2] - box_tensor[:, 0]) * (box_tensor[:, 3] - box_tensor[:, 1])
        return image_tensor, {
            "boxes": box_tensor,
            "masks": mask_tensor.to(torch.uint8),
            "labels": torch.ones(len(masks), dtype=torch.int64),
            "image_id": torch.tensor([index], dtype=torch.int64),
            "area": area,
            "iscrowd": torch.zeros(len(masks), dtype=torch.int64),
            "source_image": record["source_image_id"],
            "source_dataset": record["dataset_name"],
            "source_annotation_ids": source_ids,
            "fdi_numbers": fdi_numbers,
        }


def detection_collate(batch: list[tuple[Tensor, dict[str, Any]]]):
    return tuple(zip(*batch, strict=True))
