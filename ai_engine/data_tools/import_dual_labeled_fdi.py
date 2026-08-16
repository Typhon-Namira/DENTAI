from pathlib import Path
from collections import Counter
import json
import hashlib

SRC = Path("data/raw/dentai_v3_sources/dual_labeled/extracted")
IMAGES = SRC / "images1"
LABELS = SRC / "labels"

OUT = Path("data/canonical/dual_labeled_fdi")
OUT.mkdir(parents=True, exist_ok=True)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}

VALID_FDI = {
    str(q * 10 + n)
    for q in range(1, 5)
    for n in range(1, 9)
}

image_map = {
    p.stem: p
    for p in IMAGES.rglob("*")
    if p.is_file() and p.suffix.lower() in IMAGE_EXTS
}

stats = Counter()
fdi_stats = Counter()
records = []

def bbox_from_points(points):
    if not points:
        return None

    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]

    x1, y1 = min(xs), min(ys)
    x2, y2 = max(xs), max(ys)

    return [x1, y1, x2, y2]

for label_path in sorted(LABELS.glob("*.json")):

    stem = label_path.stem

    # Critical: only annotations with an actual available image.
    if stem not in image_map:
        stats["json_without_image"] += 1
        continue

    image_path = image_map[stem]

    try:
        data = json.loads(
            label_path.read_text(encoding="utf-8")
        )
    except Exception:
        stats["bad_json"] += 1
        continue

    instances = []
    unknown = []

    for shape in data.get("shapes", []):

        label = str(shape.get("label", "")).strip()
        points = shape.get("points") or []

        if label not in VALID_FDI:
            unknown.append({
                "source_label": label,
                "shape_type": shape.get("shape_type"),
                "points": points,
                "group_id": shape.get("group_id"),
            })
            stats[f"unknown_label_{label}"] += 1
            continue

        bbox = bbox_from_points(points)

        if bbox is None:
            stats["empty_polygon"] += 1
            continue

        instance = {
            "class": "TOOTH",
            "fdi": label,
            "bbox_xyxy": bbox,
            "polygon": points,
            "shape_type": shape.get("shape_type", "polygon"),
            "group_id": shape.get("group_id"),
            "source": "dual_labeled_fdi",
            "source_label": label,
        }

        instances.append(instance)

        fdi_stats[label] += 1
        stats["tooth_instances"] += 1

    record_id = hashlib.sha1(
        str(image_path).encode("utf-8")
    ).hexdigest()[:16]

    record = {
        "id": f"dual_labeled_{record_id}",
        "image_path": str(image_path),
        "source": "dual_labeled_fdi",
        "annotation_path": str(label_path),

        "instances": instances,

        # Do NOT interpret these as disease labels.
        "unknown_annotations": unknown,

        "metadata": {
            "image_width": data.get("imageWidth"),
            "image_height": data.get("imageHeight"),
            "image_path_original": data.get("imagePath"),
            "labelme_version": data.get("version"),
        }
    }

    records.append(record)
    stats["images"] += 1


output = {
    "dataset": "dual_labeled_fdi",
    "task": [
        "tooth_instance_segmentation",
        "fdi_identification"
    ],

    # Explicitly prevent accidental use as healthy/disease GT.
    "disease_ground_truth": False,
    "healthy_ground_truth": False,

    "records": records
}

(OUT / "all.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

stats_output = {
    "images": stats["images"],
    "tooth_instances": stats["tooth_instances"],
    "json_without_image": stats["json_without_image"],
    "bad_json": stats["bad_json"],
    "empty_polygon": stats["empty_polygon"],

    "unknown_labels": {
        k.replace("unknown_label_", ""): v
        for k, v in stats.items()
        if k.startswith("unknown_label_")
    },

    "fdi_counts": dict(
        sorted(fdi_stats.items(), key=lambda x: int(x[0]))
    )
}

(OUT / "stats.json").write_text(
    json.dumps(stats_output, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=" * 72)
print("DUAL-LABELED FDI IMPORT COMPLETE")
print("=" * 72)

print("Images:", stats["images"])
print("TOOTH instances:", stats["tooth_instances"])
print("JSON without available image:", stats["json_without_image"])
print("Bad JSON:", stats["bad_json"])
print("Empty polygons:", stats["empty_polygon"])

print("\nFDI COUNTS")
for fdi, count in sorted(fdi_stats.items(), key=lambda x: int(x[0])):
    print(f"{fdi:5} {count}")

print("\nUNKNOWN LABELS")
for k, v in stats.items():
    if k.startswith("unknown_label_"):
        print(k.replace("unknown_label_", ""), v)

print("\nOutput:", OUT / "all.json")
print("=" * 72)
