import json
from pathlib import Path
from collections import Counter
from PIL import Image

ROOT = Path("data")

OUT = ROOT / "canonical/dentai_v3"
OUT.mkdir(parents=True, exist_ok=True)

ZEN = ROOT / "raw/dentai_v3_sources/zenodo14/extracted"
ORAL = ROOT / "raw/dentai_v3_sources/oralxrays9/OralXrays-9/extracted"

# Preserve semantics conservatively.
ZEN_CLASSES = {
    0: ("Implant", "IMPLANT"),
    1: ("Prosthetic Restoration", "PROSTHETIC_RESTORATION"),
    2: ("Obturation", "OBTURATION"),
    3: ("Endodontic Treatment", "ROOT_CANAL_TREATMENT"),
    4: ("Carious Lesion", "CARIES"),
    5: ("Bone Resorption", "BONE_RESORPTION"),
    6: ("Impacted Tooth", "IMPACTED"),
    7: ("Apical Periodontitis", "APICAL_PERIODONTITIS"),
    8: ("Root Fragment", "ROOT_FRAGMENT"),
    9: ("Furcation Lesion", "FURCATION_LESION"),
    10: ("Apical Surgery", "APICAL_SURGERY"),
    11: ("Root Resorption", "ROOT_RESORPTION"),
    12: ("Orthodontic Device", "ORTHODONTIC_DEVICE"),
    13: ("Surgical Device", "SURGICAL_DEVICE"),
}

ORAL_MAP = {
    "Apical Periodontitis": "APICAL_PERIODONTITIS",
    "Decay": "CARIES",
    "Wisdom Tooth": "WISDOM_TOOTH",
    "Missing Tooth": "MISSING_TOOTH",
    "Dental Filling": "FILLING",
    "Root Canal Filling": "ROOT_CANAL_TREATMENT",
    "Implant": "IMPLANT",
    "Porcelain Crown": "CROWN",
    "Ceramic Bridge": "BRIDGE",
}

records = {
    "train": [],
    "validation": [],
    "test": [],
    "external_validation": [],
}

stats = {
    k: Counter()
    for k in records
}


def add_record(split, record):
    records[split].append(record)

    for inst in record["instances"]:
        stats[split][inst["canonical_class"]] += 1


# ============================================================
# ZENODO YOLO
# ============================================================

zen_splits = {
    "train": ZEN / "train",
    "validation": ZEN / "valid",
    "test": ZEN / "test",
    "external_validation": (
        ZEN / "test_alte_cabinete/Ext-validation"
    ),
}

print("=== IMPORTING ZENODO14 ===")

for target_split, base in zen_splits.items():
    if not base.exists():
        continue

    img_dir = base / "images"
    lbl_dir = base / "labels"

    images = sorted([
        p for p in img_dir.iterdir()
        if p.is_file()
    ])

    imported = 0

    for image_path in images:
        label_path = lbl_dir / f"{image_path.stem}.txt"

        try:
            with Image.open(image_path) as im:
                W, H = im.size
        except Exception as e:
            print("BAD IMAGE:", image_path, e)
            continue

        instances = []

        if label_path.exists():
            for line_no, line in enumerate(
                label_path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                ).splitlines(),
                start=1
            ):
                parts = line.strip().split()

                if len(parts) < 5:
                    continue

                cid = int(float(parts[0]))

                if cid not in ZEN_CLASSES:
                    continue

                xc, yc, bw, bh = map(float, parts[1:5])

                x1 = max(0.0, (xc - bw/2.0) * W)
                y1 = max(0.0, (yc - bh/2.0) * H)
                x2 = min(float(W), (xc + bw/2.0) * W)
                y2 = min(float(H), (yc + bh/2.0) * H)

                source_name, canonical = ZEN_CLASSES[cid]

                instances.append({
                    "source_annotation_id":
                        f"{label_path.name}:{line_no}",
                    "annotation_type": "bbox",
                    "source_class_id": cid,
                    "source_class": source_name,
                    "canonical_class": canonical,
                    "bbox_xyxy": [
                        round(x1, 3),
                        round(y1, 3),
                        round(x2, 3),
                        round(y2, 3),
                    ],
                })

        add_record(
            target_split,
            {
                "source_dataset": "zenodo14",
                "source_split": target_split,
                "source_image_id": image_path.name,
                "image_path": str(image_path),
                "width": W,
                "height": H,
                "instances": instances,
            }
        )

        imported += 1

    print(
        target_split,
        "images=",
        imported
    )


# ============================================================
# ORALXRAYS-9 COCO
# ============================================================

print("\n=== IMPORTING ORALXRAYS-9 TRAIN ===")

ann_path = (
    ORAL / "annotations/instances_train2017.json"
)

img_dir = ORAL / "train2017"

oral = json.loads(
    ann_path.read_text(encoding="utf-8")
)

categories = {
    int(c["id"]): c["name"]
    for c in oral["categories"]
}

anns_by_image = {}

for ann in oral["annotations"]:
    anns_by_image.setdefault(
        int(ann["image_id"]),
        []
    ).append(ann)

imported = 0
missing_images = 0

for img in oral["images"]:
    image_id = int(img["id"])
    filename = img["file_name"]

    image_path = img_dir / filename

    if not image_path.exists():
        missing_images += 1
        continue

    W = int(img.get("width") or 0)
    H = int(img.get("height") or 0)

    if not W or not H:
        with Image.open(image_path) as im:
            W, H = im.size

    instances = []

    for ann in anns_by_image.get(image_id, []):
        cid = int(ann["category_id"])

        if cid not in categories:
            continue

        source_name = categories[cid]

        canonical = ORAL_MAP.get(source_name)

        if canonical is None:
            continue

        x, y, w, h = map(float, ann["bbox"])

        instances.append({
            "source_annotation_id":
                str(ann.get("id")),
            "annotation_type": "bbox",
            "source_class_id": cid,
            "source_class": source_name,
            "canonical_class": canonical,
            "bbox_xyxy": [
                round(x, 3),
                round(y, 3),
                round(x+w, 3),
                round(y+h, 3),
            ],
        })

    add_record(
        "train",
        {
            "source_dataset": "oralxrays9",
            "source_split": "train2017",
            "source_image_id": filename,
            "image_path": str(image_path),
            "width": W,
            "height": H,
            "instances": instances,
        }
    )

    imported += 1

print("OralXrays train images:", imported)
print("Missing OralXrays train images:", missing_images)


# ============================================================
# WRITE OUTPUT
# ============================================================

print("\n=== WRITING CANONICAL V3 ===")

for split, split_records in records.items():
    payload = {
        "schema_version": "dentai-v3-canonical-1",
        "split": split,
        "records": split_records,
    }

    path = OUT / f"{split}.json"

    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(
        split,
        "records=",
        len(split_records),
        "->",
        path
    )


summary = {
    "schema_version": "dentai-v3-canonical-1",
    "sources": [
        "zenodo14",
        "oralxrays9",
    ],
    "important_notes": [
        "OralXrays-9 validation images are not yet imported.",
        "WISDOM_TOOTH is NOT treated as IMPACTED.",
        "OBTURATION is preserved separately from FILLING.",
        "No HEALTHY class has been fabricated from unlabeled samples.",
        "DEEP_CARIES remains separate and currently comes only from existing DENTAI data.",
    ],
    "splits": {},
}

for split in records:
    summary["splits"][split] = {
        "images": len(records[split]),
        "instances": sum(stats[split].values()),
        "class_counts": dict(
            stats[split].most_common()
        ),
    }

(OUT / "stats.json").write_text(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print("\n" + "="*72)
print("DENTAI V3 CANONICAL BUILD COMPLETE")
print("="*72)

for split in records:
    print(
        f"\n[{split.upper()}]"
    )

    print(
        "images:",
        len(records[split])
    )

    print(
        "instances:",
        sum(stats[split].values())
    )

    for cls, n in stats[split].most_common():
        print(
            f"{cls:30} {n}"
        )

print(
    "\nStats:",
    OUT / "stats.json"
)
