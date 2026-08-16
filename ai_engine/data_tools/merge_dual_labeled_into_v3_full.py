import json
import random
from pathlib import Path
from collections import Counter

SRC = Path("data/canonical/dual_labeled_fdi/all.json")
BASE = Path("data/canonical/dentai_v3_full")
OUT = Path("data/canonical/dentai_v3_super")
OUT.mkdir(parents=True, exist_ok=True)

SEED = 20260816

dual = json.loads(SRC.read_text(encoding="utf-8"))
dual_records = dual["records"]

random.Random(SEED).shuffle(dual_records)

n = len(dual_records)

n_train = int(n * 0.80)
n_val = int(n * 0.10)

dual_split = {
    "train": dual_records[:n_train],
    "validation": dual_records[n_train:n_train+n_val],
    "test": dual_records[n_train+n_val:],
}

def convert_dual_record(r, split):
    instances = []

    for x in r["instances"]:
        instances.append({
            "source_annotation_id": None,
            "instance_id": None,
            "annotation_type": "polygon",
            "source_class": x["fdi"],
            "canonical_class": "TOOTH",
            "fdi_number": x["fdi"],
            "bbox_xyxy": x["bbox_xyxy"],
            "polygon": x["polygon"],
            "source_dataset": "dual_labeled_fdi",
        })

    return {
        "source_dataset": "dual_labeled_fdi",
        "source_split": split,
        "source_image_id": Path(r["image_path"]).name,
        "canonical_image_id": r["id"],
        "image_path": r["image_path"],
        "width": r["metadata"].get("image_width"),
        "height": r["metadata"].get("image_height"),
        "instances": instances,
        "unknown_annotations": r.get("unknown_annotations", []),
    }

summary = {}

for split in ["train", "validation", "test"]:
    base = json.loads(
        (BASE / f"{split}.json").read_text(encoding="utf-8")
    )

    records = list(base["records"])

    for r in dual_split[split]:
        records.append(
            convert_dual_record(r, split)
        )

    payload = {
        "schema_version": "dentai-v3-super-1",
        "split": split,
        "records": records,
    }

    (OUT / f"{split}.json").write_text(
        json.dumps(
            payload,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    sources = Counter()
    classes = Counter()
    fdi = Counter()

    tooth_instances = 0
    pathology_instances = 0

    for rec in records:
        sources[
            rec.get("source_dataset", "UNKNOWN")
        ] += 1

        for inst in rec.get("instances", []):
            cls = inst.get("canonical_class")

            if cls:
                classes[cls] += 1

            if cls == "TOOTH":
                tooth_instances += 1

            f = inst.get("fdi_number")
            if f:
                fdi[str(f)] += 1

            pathology = inst.get("pathology_class")
            if pathology:
                classes[pathology] += 1
                pathology_instances += 1

    summary[split] = {
        "images": len(records),
        "tooth_instances": tooth_instances,
        "fdi_instances": sum(fdi.values()),
        "pathology_instances": pathology_instances,
        "sources": dict(sources),
        "fdi_counts": dict(
            sorted(fdi.items(), key=lambda x: int(x[0]))
        ),
        "classes": dict(classes),
    }

# Preserve external validation unchanged.
ext = BASE / "external_validation.json"

if ext.exists():
    (OUT / "external_validation.json").write_text(
        ext.read_text(encoding="utf-8"),
        encoding="utf-8"
    )

(OUT / "stats.json").write_text(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print("="*72)
print("DENTAI V3 SUPER DATASET READY")
print("="*72)

for split in ["train", "validation", "test"]:
    s = summary[split]

    print(f"\n[{split.upper()}]")
    print("Images:", s["images"])
    print("TOOTH instances:", s["tooth_instances"])
    print("FDI instances:", s["fdi_instances"])

    print("\nSOURCES:")
    for k,v in Counter(s["sources"]).most_common():
        print(f"{k:40} {v}")

print("\nOutput:", OUT)
