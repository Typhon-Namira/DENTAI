import argparse
import hashlib
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
