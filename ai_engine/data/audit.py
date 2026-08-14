import argparse
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import cast

import numpy as np
from PIL import Image, UnidentifiedImageError

from ai_engine.data.split import patient_level_split, write_locked_split
from ai_engine.data.verify import sha256_file


def _perceptual_hash(image: Image.Image) -> str:
    pixels = np.asarray(image.convert("L").resize((16, 16)), dtype=np.float32)
    return hashlib.sha256((pixels > pixels.mean()).tobytes()).hexdigest()


def audit_semantic_dataset(root: Path, dataset_id: str, version: str, output: Path) -> dict:
    images = sorted((root / "images").glob("*"))
    masks = sorted((root / "masks").glob("*"))
    mask_by_stem = {p.name.split("_png.rf.")[0]: p for p in masks}
    rows: list[dict[str, object]] = []
    corrupt: list[dict[str, str]] = []
    empty: list[str] = []
    exact: defaultdict[str, list[str]] = defaultdict(list)
    dimensions: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    formats: Counter[str] = Counter()
    for path in images:
        source_id = path.name.split("_png.rf.")[0]
        try:
            with Image.open(path) as image:
                image.load()
                dimensions[f"{image.width}x{image.height}"] += 1
                modes[image.mode] += 1
                formats[image.format or path.suffix.lower()] += 1
                perceptual = _perceptual_hash(image)
        except (OSError, UnidentifiedImageError) as exc:
            corrupt.append({"path": str(path), "error": str(exc)})
            continue
        digest = sha256_file(path)
        exact[digest].append(path.name)
        mask = mask_by_stem.get(source_id)
        annotation_count = 0
        if mask:
            with Image.open(mask) as m:
                values = np.asarray(m)
                annotation_count = int(np.any(values > 0))
                if not annotation_count:
                    empty.append(mask.name)
        rows.append(
            {
                "image_id": path.name,
                "source_image_id": source_id,
                "group_id": source_id,
                "image_sha256": digest,
                "perceptual_hash": perceptual,
                "mask": mask.name if mask else None,
                "annotation_count": annotation_count,
            }
        )
    duplicate_groups = [v for v in exact.values() if len(v) > 1]
    split_map = patient_level_split([str(r["group_id"]) for r in rows])
    split_records = [
        {
            "image_id": str(r["image_id"]),
            "group_id": str(r["group_id"]),
            "split": split_map[str(r["group_id"])],
        }
        for r in rows
    ]
    split_path = Path("data/splits") / dataset_id / version / "split.json"
    split_hash = write_locked_split(split_records, split_path, 47)
    report = {
        "dataset_id": dataset_id,
        "version": version,
        "actual_image_count": len(images),
        "actual_mask_count": len(masks),
        "readable_image_count": len(rows),
        "corrupt_files": corrupt,
        "unmatched_images": [r["image_id"] for r in rows if not r["mask"]],
        "empty_annotations": empty,
        "dimensions": dict(dimensions),
        "color_modes": dict(modes),
        "file_types": dict(formats),
        "exact_duplicate_groups": duplicate_groups,
        "near_duplicate_method": "16x16 mean-threshold perceptual hash; candidates require human review",  # noqa: E501
        "patient_identifier": "one reported patient per source filename",
        "scanner_site_metadata": "not provided",
        "annotation_format": "binary PNG semantic mask",
        "class_distribution": {"TOOTH": sum(cast(int, r["annotation_count"]) for r in rows)},
        "split_manifest": str(split_path),
        "split_sha256": split_hash,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = output.with_suffix(".md")
    md.write_text(
        f"# {dataset_id} data audit\n\n- Images: {len(images)}\n- Masks: {len(masks)}\n- Corrupt: {len(corrupt)}\n- Empty masks: {len(empty)}\n- Exact duplicate groups: {len(duplicate_groups)}\n- Annotation: binary semantic tooth mask; **not instance masks**.\n- Patient grouping: source filename, based on publisher's one-patient-per-image statement.\n- Split SHA-256: `{split_hash}`\n\nThis audit is technical evidence, not clinical validation.\n",  # noqa: E501
        encoding="utf-8",
    )
    return report


def audit_via_dataset(root: Path, dataset_id: str, version: str, output: Path) -> dict:
    payload = json.loads((root / "annotations.json").read_text(encoding="utf-8"))
    metadata = payload["_via_img_metadata"]
    rows: list[dict[str, object]] = []
    exact: defaultdict[str, list[str]] = defaultdict(list)
    corrupt: list[dict[str, str]] = []
    for path in sorted(root.glob("*.jpg")):
        try:
            with Image.open(path) as image:
                image.load()
                width, height, mode = image.width, image.height, image.mode
        except (OSError, UnidentifiedImageError) as exc:
            corrupt.append({"path": str(path), "error": str(exc)})
            continue
        digest = sha256_file(path)
        exact[digest].append(path.name)
        entry = next((value for value in metadata.values() if value["filename"] == path.name), None)
        regions = entry["regions"] if entry else []
        rows.append(
            {
                "image_id": path.name,
                "source_image_id": path.stem,
                "group_id": digest,
                "image_sha256": digest,
                "width": width,
                "height": height,
                "mode": mode,
                "annotation_count": len(regions),
            }
        )
    split_map = patient_level_split([str(row["group_id"]) for row in rows])
    split_records = [
        {
            "image_id": str(row["image_id"]),
            "group_id": str(row["group_id"]),
            "split": split_map[str(row["group_id"])],
        }
        for row in rows
    ]
    split_path = Path("data/splits") / dataset_id / version / "split.json"
    split_hash = write_locked_split(split_records, split_path, 47)
    duplicates = [names for names in exact.values() if len(names) > 1]
    report = {
        "dataset_id": dataset_id,
        "version": version,
        "actual_image_count": len(rows),
        "annotation_count": sum(cast(int, row["annotation_count"]) for row in rows),
        "annotated_image_count": sum(cast(int, row["annotation_count"]) > 0 for row in rows),
        "empty_annotation_count": sum(cast(int, row["annotation_count"]) == 0 for row in rows),
        "corrupt_files": corrupt,
        "exact_duplicate_groups": duplicates,
        "grouping_rule": "exact source-derived SHA-256 (patient/case identifiers absent)",
        "leakage_uncertainty": "Patient identity is unavailable; cross-image same-patient leakage cannot be excluded.",  # noqa: E501
        "annotation_format": "VGG Image Annotator JSON polylines; one region per visible tooth",
        "scanner_site_metadata": "dataset-level only",
        "split_manifest": str(split_path),
        "split_sha256": split_hash,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(
        f"# {dataset_id} data audit\n\n- Images: {len(rows)}\n- Annotated images: {report['annotated_image_count']}\n"  # noqa: E501
        f"- Empty annotation entries: {report['empty_annotation_count']}\n- Tooth polygon instances: {report['annotation_count']}\n"  # noqa: E501
        f"- Exact duplicate groups: {len(duplicates)}\n- Grouping: exact image SHA-256 because patient IDs are absent.\n"  # noqa: E501
        f"- Split SHA-256: `{split_hash}`\n\nThe annotated subset is insufficient alone for professional Tooth V1 training. "  # noqa: E501
        "Unknown patient identity remains a documented leakage limitation.\n",
        encoding="utf-8",
    )
    return report


def audit_yolo_dataset(
    root: Path, dataset_id: str, version: str, class_names: list[str], output: Path
) -> dict:
    """Audit YOLO detection trees with sibling image/label directories."""
    image_paths = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        and "images" in path.parts
    )
    rows: list[dict[str, object]] = []
    exact: defaultdict[str, list[str]] = defaultdict(list)
    perceptual: defaultdict[str, list[str]] = defaultdict(list)
    corrupt: list[dict[str, str]] = []
    invalid_boxes: list[dict[str, object]] = []
    classes: Counter[str] = Counter()
    annotation_types: Counter[str] = Counter()
    dimensions: Counter[str] = Counter()
    for path in image_paths:
        try:
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                dimensions[f"{width}x{height}"] += 1
                phash = _perceptual_hash(image)
        except (OSError, UnidentifiedImageError) as exc:
            corrupt.append({"path": str(path), "error": str(exc)})
            continue
        digest = sha256_file(path)
        exact[digest].append(str(path.relative_to(root)))
        perceptual[phash].append(str(path.relative_to(root)))
        parts = list(path.parts)
        image_index = len(parts) - 1 - parts[::-1].index("images")
        parts[image_index] = "labels"
        label_path = Path(*parts).with_suffix(".txt")
        annotations = 0
        if label_path.is_file():
            for line_number, line in enumerate(label_path.read_text().splitlines(), start=1):
                fields = line.split()
                if len(fields) < 5:
                    invalid_boxes.append({"file": str(label_path), "line": line_number})
                    continue
                try:
                    class_id = int(fields[0])
                    coordinates = list(map(float, fields[1:]))
                except ValueError:
                    invalid_boxes.append({"file": str(label_path), "line": line_number})
                    continue
                valid_class = 0 <= class_id < len(class_names)
                if len(coordinates) == 4:
                    cx, cy, box_width, box_height = coordinates
                    valid_geometry = (
                        all(0 <= value <= 1 for value in coordinates)
                        and box_width > 0
                        and box_height > 0
                        and cx - box_width / 2 >= 0
                        and cy - box_height / 2 >= 0
                        and cx + box_width / 2 <= 1
                        and cy + box_height / 2 <= 1
                    )
                    annotation_type = "bbox"
                else:
                    valid_geometry = (
                        len(coordinates) >= 6
                        and len(coordinates) % 2 == 0
                        and all(0 <= value <= 1 for value in coordinates)
                    )
                    annotation_type = "polygon"
                if not valid_class or not valid_geometry:
                    invalid_boxes.append({"file": str(label_path), "line": line_number})
                    continue
                classes[class_names[class_id]] += 1
                annotation_types[annotation_type] += 1
                annotations += 1
        rows.append(
            {
                "image_id": str(path.relative_to(root)),
                "image_sha256": digest,
                "perceptual_hash": phash,
                "width": width,
                "height": height,
                "annotation_count": annotations,
            }
        )
    split_map = patient_level_split(sorted(exact))
    split_records = [
        {
            "image_id": str(row["image_id"]),
            "group_id": str(row["image_sha256"]),
            "split": split_map[str(row["image_sha256"])],
        }
        for row in rows
    ]
    split_path = Path("data/splits") / dataset_id / version / "split.json"
    split_hash = write_locked_split(split_records, split_path, 47)
    exact_groups = [group for group in exact.values() if len(group) > 1]
    near_groups = [group for group in perceptual.values() if len(group) > 1]
    report = {
        "dataset_id": dataset_id,
        "version": version,
        "total_images": len(image_paths),
        "readable_images": len(rows),
        "corrupt_images": corrupt,
        "annotation_count": sum(classes.values()),
        "class_distribution": dict(classes),
        "annotation_type_distribution": dict(annotation_types),
        "empty_annotations": sum(cast(int, row["annotation_count"]) == 0 for row in rows),
        "invalid_boxes": invalid_boxes,
        "dimensions": dict(dimensions),
        "exact_duplicate_groups": exact_groups,
        "perceptual_hash_candidate_groups": near_groups,
        "patient_independence": "PATIENT_INDEPENDENCE_UNVERIFIED",
        "grouping_rule": "exact image SHA-256; source patient/case identifiers unavailable",
        "split_manifest": str(split_path),
        "split_sha256": split_hash,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(
        f"# {dataset_id} data audit\n\n- Images: {len(image_paths)}\n"
        f"- Readable: {len(rows)}\n- Valid YOLO boxes: {sum(classes.values())}\n"
        f"- Empty annotations: {report['empty_annotations']}\n"
        f"- Invalid/out-of-bounds boxes: {len(invalid_boxes)}\n"
        f"- Exact duplicate groups: {len(exact_groups)}\n"
        f"- Equal perceptual-hash candidate groups: {len(near_groups)}\n"
        f"- Classes: {dict(classes)}\n- Split SHA-256: `{split_hash}`\n\n"
        "**PATIENT_INDEPENDENCE_UNVERIFIED**: exact-hash grouping does not prove "
        "patient independence.\n",
        encoding="utf-8",
    )
    return report


def audit_sts_parquet(root: Path, dataset_id: str, version: str, output: Path) -> dict:
    """Audit the pinned STS 2D Parquet mirror without materializing another image copy."""
    import pyarrow.parquet as pq
    from scipy import ndimage

    rows: list[dict[str, object]] = []
    exact: defaultdict[str, list[str]] = defaultdict(list)
    perceptual: defaultdict[str, list[str]] = defaultdict(list)
    dimensions: Counter[str] = Counter()
    corrupt: list[dict[str, str]] = []
    empty_masks: list[str] = []
    misaligned_masks: list[str] = []
    disconnected: Counter[str] = Counter()
    for parquet_path in sorted(root.glob("*.parquet")):
        parquet = pq.ParquetFile(parquet_path)
        for batch in parquet.iter_batches(batch_size=16):
            for item in batch.to_pylist():
                sample_id = str(item["sample_id"])
                try:
                    image_bytes = item["image"]["bytes"]
                    with Image.open(io.BytesIO(image_bytes)) as image:
                        image.load()
                        width, height = image.size
                        dimensions[f"{width}x{height}"] += 1
                        phash = _perceptual_hash(image)
                    digest = hashlib.sha256(image_bytes).hexdigest()
                    exact[digest].append(sample_id)
                    perceptual[phash].append(sample_id)
                    mask_valid = None
                    components = None
                    if item["labeled"]:
                        mask_bytes = item["mask"]["bytes"]
                        with Image.open(io.BytesIO(mask_bytes)) as mask_image:
                            mask_image.load()
                            if mask_image.size != (width, height):
                                misaligned_masks.append(sample_id)
                            values = np.asarray(mask_image.convert("L")) > 0
                        mask_valid = bool(values.any())
                        if not mask_valid:
                            empty_masks.append(sample_id)
                        components = int(ndimage.label(values)[1])
                        disconnected[str(components)] += 1
                    rows.append(
                        {
                            "image_id": sample_id,
                            "subset": item["subset"],
                            "labeled": bool(item["labeled"]),
                            "image_sha256": digest,
                            "perceptual_hash": phash,
                            "width": width,
                            "height": height,
                            "mask_valid": mask_valid,
                            "mask_components": components,
                        }
                    )
                except (OSError, KeyError, TypeError, UnidentifiedImageError) as exc:
                    corrupt.append({"sample_id": sample_id, "error": str(exc)})
    split_map = patient_level_split(sorted(exact))
    split_records = [
        {
            "image_id": str(row["image_id"]),
            "group_id": str(row["image_sha256"]),
            "split": split_map[str(row["image_sha256"])],
        }
        for row in rows
    ]
    split_path = Path("data/splits") / dataset_id / version / "split.json"
    split_hash = write_locked_split(split_records, split_path, 47)
    exact_groups = [group for group in exact.values() if len(group) > 1]
    near_groups = [group for group in perceptual.values() if len(group) > 1]
    report = {
        "dataset_id": dataset_id,
        "version": version,
        "total_images": len(rows) + len(corrupt),
        "readable_images": len(rows),
        "labeled_images": sum(bool(row["labeled"]) for row in rows),
        "unlabeled_images": sum(not bool(row["labeled"]) for row in rows),
        "corrupt_images": corrupt,
        "annotation_type": "binary semantic tooth mask; not tooth instances",
        "empty_masks": empty_masks,
        "misaligned_masks": misaligned_masks,
        "mask_connected_component_distribution": dict(disconnected),
        "dimensions": dict(dimensions),
        "exact_duplicate_groups": exact_groups,
        "perceptual_hash_candidate_groups": near_groups,
        "patient_independence": "PATIENT_INDEPENDENCE_UNVERIFIED",
        "grouping_rule": "exact image SHA-256; source patient/case identifiers unavailable",
        "split_manifest": str(split_path),
        "split_sha256": split_hash,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(
        f"# {dataset_id} data audit\n\n- Images: {report['total_images']}\n"
        f"- Readable: {len(rows)}\n- Semantic masks: {report['labeled_images']}\n"
        f"- Empty masks: {len(empty_masks)}\n- Misaligned masks: {len(misaligned_masks)}\n"
        f"- Exact duplicate groups: {len(exact_groups)}\n"
        f"- Perceptual-hash candidate groups: {len(near_groups)}\n"
        f"- Split SHA-256: `{split_hash}`\n\n"
        "Masks provide auxiliary semantic supervision only; they are not gold tooth instances.\n\n"
        "**PATIENT_INDEPENDENCE_UNVERIFIED**: hash grouping does not prove patient independence.\n",
        encoding="utf-8",
    )
    return report


def audit_dentex(root: Path, dataset_id: str, version: str, output: Path) -> dict:
    """Audit all three official DENTEX training supervision levels together."""
    subsets = {
        "quadrant": root / "quadrant/train_quadrant.json",
        "quadrant_enumeration": root / "quadrant_enumeration/train_quadrant_enumeration.json",
        "quadrant_enumeration_disease": root
        / "quadrant-enumeration-disease/train_quadrant_enumeration_disease.json",
    }
    rows: list[dict[str, object]] = []
    exact: defaultdict[str, list[str]] = defaultdict(list)
    perceptual: defaultdict[str, list[str]] = defaultdict(list)
    corrupt: list[dict[str, str]] = []
    invalid: list[str] = []
    duplicate_annotations: list[str] = []
    fdi: Counter[str] = Counter()
    diseases: Counter[str] = Counter()
    dimensions: Counter[str] = Counter()
    annotation_types: Counter[str] = Counter()
    for subset, annotation_path in subsets.items():
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
        images = {item["id"]: item for item in payload["images"]}
        quadrant_names = {item["id"]: str(item["name"]) for item in payload.get("categories_1", [])}
        tooth_names = {item["id"]: str(item["name"]) for item in payload.get("categories_2", [])}
        disease_names = {item["id"]: str(item["name"]) for item in payload.get("categories_3", [])}
        by_image: defaultdict[int, list[dict]] = defaultdict(list)
        seen_annotations: set[tuple] = set()
        for annotation in payload["annotations"]:
            by_image[int(annotation["image_id"])].append(annotation)
            bbox = tuple(round(float(value), 4) for value in annotation.get("bbox", []))
            key = (
                annotation["image_id"],
                bbox,
                annotation.get("category_id_1"),
                annotation.get("category_id_2"),
                annotation.get("category_id_3"),
            )
            if key in seen_annotations:
                duplicate_annotations.append(f"{subset}:{annotation['id']}")
            seen_annotations.add(key)
        image_dir = annotation_path.parent / "xrays"
        for image_id, image_record in images.items():
            image_path = image_dir / image_record["file_name"]
            namespaced_id = f"{subset}/{image_record['file_name']}"
            try:
                with Image.open(image_path) as image:
                    image.load()
                    width, height = image.size
                    dimensions[f"{width}x{height}"] += 1
                    phash = _perceptual_hash(image)
            except (OSError, UnidentifiedImageError) as exc:
                corrupt.append({"image_id": namespaced_id, "error": str(exc)})
                continue
            digest = sha256_file(image_path)
            exact[digest].append(namespaced_id)
            perceptual[phash].append(namespaced_id)
            valid_count = 0
            for annotation in by_image[int(image_id)]:
                bbox = annotation.get("bbox", [])
                polygons = annotation.get("segmentation", [])
                valid_bbox = (
                    len(bbox) == 4
                    and bbox[0] >= 0
                    and bbox[1] >= 0
                    and bbox[2] > 0
                    and bbox[3] > 0
                    and bbox[0] + bbox[2] <= width
                    and bbox[1] + bbox[3] <= height
                )
                valid_polygon = bool(polygons) and all(
                    len(polygon) >= 6
                    and len(polygon) % 2 == 0
                    and all(
                        0 <= coordinate < (width if index % 2 == 0 else height)
                        for index, coordinate in enumerate(polygon)
                    )
                    for polygon in polygons
                )
                if not valid_bbox or (subset != "quadrant" and not valid_polygon):
                    invalid.append(f"{subset}:{annotation['id']}")
                    continue
                valid_count += 1
                annotation_types["polygon" if valid_polygon else "bbox"] += 1
                if "category_id_2" in annotation:
                    label = (
                        quadrant_names[annotation["category_id_1"]]
                        + tooth_names[annotation["category_id_2"]]
                    )
                    fdi[label] += 1
                if "category_id_3" in annotation:
                    diseases[disease_names[annotation["category_id_3"]]] += 1
            rows.append(
                {
                    "image_id": namespaced_id,
                    "subset": subset,
                    "image_sha256": digest,
                    "perceptual_hash": phash,
                    "width": width,
                    "height": height,
                    "annotation_count": valid_count,
                }
            )
    split_map = patient_level_split(sorted(exact))
    split_records = [
        {
            "image_id": str(row["image_id"]),
            "group_id": str(row["image_sha256"]),
            "split": split_map[str(row["image_sha256"])],
        }
        for row in rows
    ]
    split_path = Path("data/splits") / dataset_id / version / "split.json"
    split_hash = write_locked_split(split_records, split_path, 47)
    exact_groups = [group for group in exact.values() if len(group) > 1]
    near_groups = [group for group in perceptual.values() if len(group) > 1]
    report = {
        "dataset_id": dataset_id,
        "version": version,
        "total_images": len(rows) + len(corrupt),
        "readable_images": len(rows),
        "corrupt_images": corrupt,
        "annotated_images": sum(cast(int, row["annotation_count"]) > 0 for row in rows),
        "annotation_count": sum(cast(int, row["annotation_count"]) for row in rows),
        "annotation_type_distribution": dict(annotation_types),
        "fdi_labelled_instances": sum(fdi.values()),
        "fdi_distribution": dict(fdi),
        "disease_distribution": dict(diseases),
        "invalid_annotations": invalid,
        "duplicate_annotations": duplicate_annotations,
        "dimensions": dict(dimensions),
        "exact_duplicate_groups": exact_groups,
        "perceptual_hash_candidate_groups": near_groups,
        "patient_independence": "PATIENT_INDEPENDENCE_UNVERIFIED",
        "grouping_rule": "exact image SHA-256 across all supervision levels",
        "split_manifest": str(split_path),
        "split_sha256": split_hash,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(
        f"# {dataset_id} data audit\n\n- Images: {report['total_images']}\n"
        f"- Readable: {len(rows)}\n- Valid annotations: {report['annotation_count']}\n"
        f"- FDI-labelled instances: {report['fdi_labelled_instances']}\n"
        f"- Invalid annotations: {len(invalid)}\n"
        f"- Exact duplicate groups: {len(exact_groups)}\n"
        f"- Equal perceptual-hash candidates: {len(near_groups)}\n"
        f"- Disease classes: {dict(diseases)}\n- Split SHA-256: `{split_hash}`\n\n"
        "**PATIENT_INDEPENDENCE_UNVERIFIED**: source patient identifiers are absent.\n",
        encoding="utf-8",
    )
    return report


def audit_classification_tree(root: Path, dataset_id: str, version: str, output: Path) -> dict:
    """Audit an immutable class-folder image tree without inferring localization labels."""
    suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    paths = sorted(path for path in root.rglob("*") if path.suffix.lower() in suffixes)
    rows: list[dict[str, object]] = []
    corrupt: list[dict[str, str]] = []
    exact: defaultdict[str, list[str]] = defaultdict(list)
    perceptual: defaultdict[str, list[str]] = defaultdict(list)
    dimensions: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    for path in paths:
        relative = str(path.relative_to(root))
        try:
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                phash = _perceptual_hash(image)
        except (OSError, UnidentifiedImageError) as exc:
            corrupt.append({"path": relative, "error": str(exc)})
            continue
        digest = sha256_file(path)
        label = path.relative_to(root).parts[0]
        exact[digest].append(relative)
        perceptual[phash].append(relative)
        dimensions[f"{width}x{height}"] += 1
        classes[label] += 1
        rows.append(
            {
                "image_id": relative,
                "group_id": digest,
                "image_sha256": digest,
                "perceptual_hash": phash,
                "source_class": label,
                "width": width,
                "height": height,
            }
        )
    split_map = patient_level_split(sorted(exact))
    split_records = [
        {
            "image_id": str(row["image_id"]),
            "group_id": str(row["group_id"]),
            "split": split_map[str(row["group_id"])],
        }
        for row in rows
    ]
    split_path = Path("data/splits") / dataset_id / version / "split.json"
    split_hash = write_locked_split(split_records, split_path, 47)
    exact_groups = [group for group in exact.values() if len(group) > 1]
    near_groups = [group for group in perceptual.values() if len(group) > 1]
    report = {
        "dataset_id": dataset_id,
        "version": version,
        "total_images": len(paths),
        "readable_images": len(rows),
        "corrupt_images": corrupt,
        "class_distribution": dict(classes),
        "dimensions": dict(dimensions),
        "annotation_type": "image-level class folder only",
        "exact_duplicate_groups": exact_groups,
        "perceptual_hash_candidate_groups": near_groups,
        "patient_independence": "PATIENT_INDEPENDENCE_UNVERIFIED",
        "split_manifest": str(split_path),
        "split_sha256": split_hash,
        "records": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(
        f"# {dataset_id} data audit\n\n- Images: {len(paths)}\n"
        f"- Readable: {len(rows)}\n- Corrupt: {len(corrupt)}\n"
        f"- Classes: {dict(classes)}\n- Exact duplicate groups: {len(exact_groups)}\n"
        f"- Perceptual-hash candidates: {len(near_groups)}\n"
        f"- Split SHA-256: `{split_hash}`\n\n"
        "Labels are image-level implant classes, not boxes or masks. "
        "**PATIENT_INDEPENDENCE_UNVERIFIED**.\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit_semantic_dataset(args.root, args.dataset_id, args.version, args.output)


if __name__ == "__main__":
    main()
