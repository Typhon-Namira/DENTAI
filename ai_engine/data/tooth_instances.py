"""Non-destructive conversion and visual QA for VIA tooth polygons."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

CONVERSION_VERSION = "via-to-dentai-instance-1.0"


def convert_dentex_instances(root: Path, source_version: str) -> dict[str, Any]:
    """Convert official DENTEX tooth polygons without collapsing disease metadata."""
    sources = {
        "quadrant_enumeration": root / "quadrant_enumeration/train_quadrant_enumeration.json",
        "quadrant_enumeration_disease": root
        / "quadrant-enumeration-disease/train_quadrant_enumeration_disease.json",
    }
    output_images: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for subset, annotation_path in sources.items():
        raw = json.loads(annotation_path.read_text(encoding="utf-8"))
        source_hashes[subset] = hashlib.sha256(annotation_path.read_bytes()).hexdigest()
        images = {int(item["id"]): item for item in raw["images"]}
        quadrants = {int(item["id"]): str(item["name"]) for item in raw["categories_1"]}
        teeth = {int(item["id"]): str(item["name"]) for item in raw["categories_2"]}
        diseases = {int(item["id"]): str(item["name"]) for item in raw.get("categories_3", [])}
        instances_by_image: dict[int, list[dict[str, Any]]] = {image_id: [] for image_id in images}
        for annotation in raw["annotations"]:
            image_id = int(annotation["image_id"])
            polygon_flat = annotation.get("segmentation", [[]])[0]
            polygon = [
                [float(polygon_flat[index]), float(polygon_flat[index + 1])]
                for index in range(0, len(polygon_flat), 2)
            ]
            x, y, width, height = (float(value) for value in annotation["bbox"])
            fdi = (
                quadrants[int(annotation["category_id_1"])]
                + teeth[int(annotation["category_id_2"])]
            )
            disease = (
                diseases.get(int(annotation["category_id_3"]))
                if "category_id_3" in annotation
                else None
            )
            instances_by_image[image_id].append(
                {
                    "source_annotation_id": f"{subset}:{annotation['id']}",
                    "instance_id": f"{subset}:{image_id}:{annotation['id']}",
                    "annotation_type": "polygon_and_bbox",
                    "source_class": fdi,
                    "canonical_class": "TOOTH",
                    "fdi_number": fdi,
                    "bbox_xyxy": [x, y, x + width, y + height],
                    "polygon": polygon,
                    "mask_reference": None,
                    "confidence": None,
                    "source_disease": disease,
                    "source_iscrowd": int(annotation.get("iscrowd", 0)),
                }
            )
        image_dir = annotation_path.parent / "xrays"
        for image_id, image_record in sorted(images.items()):
            image_path = image_dir / image_record["file_name"]
            relative_id = f"{subset}/{image_record['file_name']}"
            output_images.append(
                {
                    "dataset_name": "DENTEX",
                    "dataset_version": source_version,
                    "source_image_id": relative_id,
                    "image_path": (
                        f"{annotation_path.parent.name}/xrays/{image_record['file_name']}"
                    ),
                    "source_case_id": None,
                    "patient_id": None,
                    "patient_independence": "PATIENT_INDEPENDENCE_UNVERIFIED",
                    "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                    "width": int(image_record["width"]),
                    "height": int(image_record["height"]),
                    "provenance": {
                        "annotation_file": str(annotation_path.relative_to(root)),
                        "source_subset": subset,
                        "source_image_numeric_id": image_id,
                    },
                    "instances": instances_by_image[image_id],
                }
            )
    return {
        "schema_version": "dentai-tooth-instances-1.1",
        "converter_version": "dentex-coco-to-dentai-instance-1.0",
        "source_dataset": "DENTEX",
        "source_version": source_version,
        "source_annotation_sha256": source_hashes,
        "images": output_images,
    }


def _canonical_akudental_label(label: str) -> tuple[str, str | None]:
    prefix = label.split(" - ", 1)[0].strip()
    if len(prefix) == 2 and prefix.isdigit() and prefix[0] in "1234" and prefix[1] in "12345678":
        return "TOOTH", prefix
    mapping = {"Filling": "FILLING", "Bridge": "BRIDGE", "Implant": "IMPLANT"}
    return mapping.get(prefix, "UNKNOWN_UNMAPPED"), None


def convert_labelme_instances(
    annotation_dir: Path,
    image_dir: Path,
    source_dataset: str,
    source_version: str,
) -> dict[str, Any]:
    """Convert LabelMe polygons while retaining every source label and identifier."""
    images: list[dict[str, Any]] = []
    for annotation_path in sorted(annotation_dir.glob("*.json")):
        raw = json.loads(annotation_path.read_text(encoding="utf-8"))
        source_name = Path(raw.get("imagePath") or f"{annotation_path.stem}.jpg").name
        candidates = [image_dir / source_name]
        candidates.extend(
            image_dir / f"{annotation_path.stem}{suffix}" for suffix in (".jpg", ".png")
        )
        image_path = next((path for path in candidates if path.is_file()), None)
        if image_path is None:
            continue
        with Image.open(image_path) as image:
            width, height = image.size
        instances = []
        for index, shape in enumerate(raw.get("shapes", [])):
            points = [[float(x), float(y)] for x, y in shape.get("points", [])]
            source_class = str(shape.get("label", "UNKNOWN"))
            canonical_class, fdi = _canonical_akudental_label(source_class)
            if len(points) < 3:
                continue
            xs, ys = [point[0] for point in points], [point[1] for point in points]
            if any(x < 0 or x >= width or y < 0 or y >= height for x, y in points):
                continue
            instances.append(
                {
                    "source_annotation_id": f"{annotation_path.name}:{index}",
                    "instance_id": f"{image_path.name}:{index}",
                    "annotation_type": "polygon",
                    "source_class": source_class,
                    "canonical_class": canonical_class,
                    "fdi_number": fdi,
                    "bbox_xyxy": [min(xs), min(ys), max(xs), max(ys)],
                    "polygon": points,
                    "mask_reference": None,
                    "confidence": None,
                }
            )
        images.append(
            {
                "dataset_name": source_dataset,
                "dataset_version": source_version,
                "source_image_id": image_path.name,
                "source_case_id": None,
                "patient_id": None,
                "patient_independence": "PATIENT_INDEPENDENCE_UNVERIFIED",
                "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "width": width,
                "height": height,
                "provenance": {"annotation_file": annotation_path.name},
                "instances": instances,
            }
        )
    return {
        "schema_version": "dentai-tooth-instances-1.1",
        "converter_version": "labelme-to-dentai-instance-1.0",
        "source_dataset": source_dataset,
        "source_version": source_version,
        "images": images,
    }


def convert_via_instances(
    annotation_file: Path, image_dir: Path, source_dataset: str, source_version: str
) -> dict[str, Any]:
    raw = json.loads(annotation_file.read_text(encoding="utf-8"))
    images: list[dict[str, Any]] = []
    for record in sorted(raw["_via_img_metadata"].values(), key=lambda item: item["filename"]):
        image_path = image_dir / record["filename"]
        if not image_path.is_file() or not record.get("regions"):
            continue
        with Image.open(image_path) as image:
            width, height = image.size
        instances = []
        for index, region in enumerate(record["regions"]):
            shape = region.get("shape_attributes", {})
            xs, ys = shape.get("all_points_x", []), shape.get("all_points_y", [])
            if len(xs) < 3 or len(xs) != len(ys):
                continue
            polygon = [[float(x), float(y)] for x, y in zip(xs, ys, strict=True)]
            if any(x < 0 or x >= width or y < 0 or y >= height for x, y in polygon):
                continue
            instances.append(
                {
                    "instance_id": f"{record['filename']}:{index}",
                    "source_annotation_id": str(index),
                    "polygon": polygon,
                    "bbox_xyxy": [min(xs), min(ys), max(xs), max(ys)],
                    "fdi_label": None,
                    "source_region_attributes": region.get("region_attributes", {}),
                }
            )
        images.append(
            {
                "source_image": record["filename"],
                "source_image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "width": width,
                "height": height,
                "instances": instances,
            }
        )
    return {
        "schema_version": "dentai-tooth-instances-1.0",
        "conversion_version": CONVERSION_VERSION,
        "source_dataset": source_dataset,
        "source_version": source_version,
        "source_annotation_file": annotation_file.name,
        "source_annotation_sha256": hashlib.sha256(annotation_file.read_bytes()).hexdigest(),
        "images": images,
    }


def render_qa_samples(
    canonical: dict[str, Any], image_dir: Path, output_dir: Path, count: int = 5, seed: int = 47
) -> list[Path]:
    candidates = [image for image in canonical["images"] if image["instances"]]
    # Stable hash ordering gives a reproducible QA sample.
    selected = sorted(
        candidates,
        key=lambda item: hashlib.sha256(
            f"{seed}:{item.get('source_image', item.get('source_image_id'))}".encode()
        ).hexdigest(),
    )[:count]
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for record in selected:
        source_image = record.get("source_image", record.get("source_image_id"))
        image = Image.open(image_dir / record.get("image_path", source_image)).convert("RGB")
        draw = ImageDraw.Draw(image, "RGBA")
        for instance in record["instances"]:
            points = [tuple(point) for point in instance["polygon"]]
            draw.polygon(points, fill=(0, 255, 255, 45), outline=(0, 255, 255, 255), width=3)
            fdi = instance.get("fdi_label") or instance.get("fdi_number")
            if fdi:
                draw.text(points[0], fdi, fill=(255, 255, 0, 255))
        target = output_dir / f"qa_{Path(source_image).stem}.jpg"
        image.save(target, quality=92)
        outputs.append(target)
    return outputs


def render_sts_semantic_qa(parquet_dir: Path, output_dir: Path, count: int = 5) -> list[Path]:
    """Render deterministic STS semantic overlays directly from immutable Parquet files."""
    import pyarrow.parquet as pq

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for parquet_path in sorted(parquet_dir.glob("*_labeled-*.parquet")):
        for batch in pq.ParquetFile(parquet_path).iter_batches(batch_size=16):
            for row in batch.to_pylist():
                if not row["labeled"]:
                    continue
                image = Image.open(io.BytesIO(row["image"]["bytes"])).convert("RGB")
                mask = Image.open(io.BytesIO(row["mask"]["bytes"])).convert("L")
                if mask.getbbox() is None:
                    continue
                overlay = Image.new("RGBA", image.size, (0, 255, 255, 0))
                overlay.putalpha(mask.point(lambda value: 90 if value else 0))
                rendered = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
                target = output_dir / f"qa_{row['sample_id']}.jpg"
                rendered.save(target, quality=92)
                outputs.append(target)
                if len(outputs) >= count:
                    return outputs
    return outputs
