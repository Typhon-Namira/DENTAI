"""Canonical Tooth V2 corpus construction and leakage controls.

The builder never edits source images or annotations.  A duplicate group is the
atomic split unit, so alternate supervision copies cannot cross split boundaries.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

SCHEMA_VERSION = "dentai-tooth-v2-corpus-1.0"
INDEPENDENCE_UNVERIFIED = "PATIENT_INDEPENDENCE_UNVERIFIED"


def stable_json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def normalized_image_hash(path: Path, size: tuple[int, int] = (256, 128)) -> str:
    """Hash decoded grayscale pixels at a fixed size to catch encoding copies."""
    with Image.open(path) as image:
        pixels = image.convert("L").resize(size, Image.Resampling.BILINEAR).tobytes()
    return hashlib.sha256(pixels).hexdigest()


def perceptual_dhash(path: Path, width: int = 16) -> int:
    with Image.open(path) as image:
        pixels = list(
            image.convert("L").resize((width + 1, width), Image.Resampling.BILINEAR).getdata()
        )
    value = 0
    for row in range(width):
        start = row * (width + 1)
        for column in range(width):
            value = (value << 1) | int(pixels[start + column] > pixels[start + column + 1])
    return value


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


@dataclass(frozen=True)
class Source:
    dataset_id: str
    canonical_file: Path
    image_root: Path
    license: str
    source_version: str


class _Groups:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[max(left_root, right_root)] = min(left_root, right_root)


def _image_path(source: Source, record: dict[str, Any]) -> Path:
    relative = record.get("image_path") or record["source_image_id"]
    return source.image_root / relative


def load_sources(sources: Iterable[Source], *, compute_pixels: bool = True) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in sources:
        payload = json.loads(source.canonical_file.read_text(encoding="utf-8"))
        for original in payload["images"]:
            image_path = _image_path(source, original)
            if not image_path.is_file() or not original.get("instances"):
                continue
            source_image_id = str(original.get("source_image_id") or original["image_path"])
            canonical_id = f"{source.dataset_id}:{source_image_id}"
            teeth = [
                instance
                for instance in original["instances"]
                if instance.get("canonical_class") == "TOOTH"
                and instance.get("polygon")
                and instance.get("bbox_xyxy")
            ]
            if not teeth:
                continue
            exact_hash = (
                original.get("image_sha256") or hashlib.sha256(image_path.read_bytes()).hexdigest()
            )
            record = {
                "canonical_image_id": canonical_id,
                "source_dataset": source.dataset_id,
                "source_version": source.source_version,
                "source_image_id": source_image_id,
                "image_path": str(image_path),
                "image_sha256": exact_hash,
                "normalized_image_sha256": normalized_image_hash(image_path)
                if compute_pixels
                else None,
                "perceptual_dhash": f"{perceptual_dhash(image_path):064x}"
                if compute_pixels
                else None,
                "width": int(original["width"]),
                "height": int(original["height"]),
                "case_id": original.get("source_case_id"),
                "patient_id": original.get("patient_id"),
                "patient_independence": original.get(
                    "patient_independence", INDEPENDENCE_UNVERIFIED
                ),
                "license": source.license,
                "annotation_source": str(source.canonical_file),
                "converter_version": payload.get("converter_version"),
                "transformation_provenance": {
                    "operation": "reference_only",
                    "image_modified": False,
                },
                "instances": teeth,
            }
            records.append(record)
    return sorted(records, key=lambda item: item["canonical_image_id"])


def duplicate_groups(records: list[dict[str, Any]]) -> list[list[str]]:
    groups = _Groups()
    indexes: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record in records:
        item = record["canonical_image_id"]
        groups.find(item)
        for field in ("image_sha256", "normalized_image_sha256"):
            value = record.get(field)
            if value:
                indexes[(field, value)].append(item)
        if record.get("patient_id"):
            indexes[("patient", f"{record['source_dataset']}:{record['patient_id']}")].append(item)
        elif record.get("case_id"):
            indexes[("case", f"{record['source_dataset']}:{record['case_id']}")].append(item)
    for members in indexes.values():
        for member in members[1:]:
            groups.union(members[0], member)
    output: dict[str, list[str]] = defaultdict(list)
    for record in records:
        output[groups.find(record["canonical_image_id"])].append(record["canonical_image_id"])
    return sorted((sorted(items) for items in output.values()), key=lambda items: items[0])


def deterministic_split(
    records: list[dict[str, Any]],
    *,
    seed: int = 47,
    fractions: tuple[float, float, float] = (0.8, 0.1, 0.1),
) -> dict[str, str]:
    if len(fractions) != 3 or abs(sum(fractions) - 1) > 1e-9:
        raise ValueError("train/validation/test fractions must sum to one")
    by_id = {record["canonical_image_id"]: record for record in records}
    groups = duplicate_groups(records)
    # Security is irrelevant here: a fixed pseudo-random order is required for reproducibility.
    random.Random(seed).shuffle(groups)  # nosec B311
    targets = [len(records) * value for value in fractions]
    counts = [0, 0, 0]
    assignment: dict[str, str] = {}
    names = ("train", "validation", "test")
    # Largest normalized deficit preserves whole duplicate/case groups.
    for group in groups:
        candidates = [targets[index] - counts[index] for index in range(3)]
        split_index = max(range(3), key=lambda index: (candidates[index], -index))
        for item in group:
            assignment[item] = names[split_index]
            counts[split_index] += 1
            by_id[item]["duplicate_group_id"] = stable_json_hash(group)[:16]
    return assignment


def validate_no_leakage(records: list[dict[str, Any]], assignment: dict[str, str]) -> None:
    for group in duplicate_groups(records):
        splits = {assignment[item] for item in group}
        if len(splits) != 1:
            raise ValueError(f"duplicate/case group crosses splits: {group}")


def write_corpus(
    records: list[dict[str, Any]], output_dir: Path, *, seed: int = 47
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    original_count = len(records)
    original_groups = duplicate_groups(records)
    by_id = {record["canonical_image_id"]: record for record in records}
    deduplicated: list[dict[str, Any]] = []
    removed: list[dict[str, str]] = []
    for group in original_groups:
        # Prefer the supervision copy with most tooth instances, then stable ID.
        retained_id = min(group, key=lambda item: (-len(by_id[item]["instances"]), item))
        retained = by_id[retained_id]
        retained["alternate_supervision_copies"] = [item for item in group if item != retained_id]
        deduplicated.append(retained)
        removed.extend(
            {"removed": item, "retained": retained_id} for item in group if item != retained_id
        )
    records = sorted(deduplicated, key=lambda item: item["canonical_image_id"])
    assignment = deterministic_split(records, seed=seed)
    validate_no_leakage(records, assignment)
    manifests: dict[str, list[dict[str, Any]]] = {
        name: [] for name in ("train", "validation", "test")
    }
    for record in records:
        split = assignment[record["canonical_image_id"]]
        manifests[split].append(record)
    for split, items in manifests.items():
        (output_dir / f"{split}.json").write_text(
            json.dumps(
                {"schema_version": SCHEMA_VERSION, "split": split, "records": items}, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
    duplicate_sets = [group for group in original_groups if len(group) > 1]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "RESEARCH_ONLY",
        "seed": seed,
        "counts": {name: len(items) for name, items in manifests.items()},
        "total_images": len(records),
        "total_supervision_records_before_deduplication": original_count,
        "total_tooth_instances": sum(len(record["instances"]) for record in records),
        "fdi_labelled_instances": sum(
            bool(instance.get("fdi_number"))
            for record in records
            for instance in record["instances"]
        ),
        "duplicate_groups": duplicate_sets,
        "exact_duplicate_supervision_copies_removed": len(removed),
        "duplicate_removals": removed,
        "near_duplicate_count": None,
        "near_duplicate_status": "NOT_MEASURED; perceptual hashes recorded for review",
        "patient_independence": INDEPENDENCE_UNVERIFIED,
        "locked_test_policy": "final_evaluation_only",
    }
    summary["dataset_hash"] = stable_json_hash(
        [(record["canonical_image_id"], record["image_sha256"]) for record in records]
    )
    (output_dir / "dataset_manifest.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    split_hash = stable_json_hash(
        {key: [item["canonical_image_id"] for item in value] for key, value in manifests.items()}
    )
    (output_dir / "split.sha256").write_text(split_hash + "\n", encoding="utf-8")
    return summary
