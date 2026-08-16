import json
from pathlib import Path
from collections import Counter

NEW = Path("data/canonical/dentai_v3")
OLD = Path("data/splits/tooth_v2")
OUT = Path("data/canonical/dentai_v3_full")
OUT.mkdir(parents=True, exist_ok=True)

OLD_SPLITS = {
    "train": "train.json",
    "validation": "validation.json",
    "test": "test.json",
}

DISEASE_MAP = {
    "Caries": "CARIES",
    "Deep Caries": "DEEP_CARIES",
    "Impacted": "IMPACTED",
    "Periapical Lesion": "APICAL_PERIODONTITIS",
}

for split in ["train", "validation", "test"]:
    new_data = json.loads(
        (NEW / f"{split}.json").read_text()
    )

    old_data = json.loads(
        (OLD / OLD_SPLITS[split]).read_text()
    )

    records = list(new_data["records"])

    # Add existing DENTAI Tooth/FDI records.
    for r in old_data["records"]:
        instances = []

        for x in r.get("instances", []):
            item = {
                "source_annotation_id":
                    x.get("source_annotation_id"),
                "instance_id":
                    x.get("instance_id"),
                "annotation_type":
                    x.get("annotation_type"),
                "source_class":
                    x.get("source_class"),
                "canonical_class":
                    x.get("canonical_class"),
                "fdi_number":
                    x.get("fdi_number"),
                "bbox_xyxy":
                    x.get("bbox_xyxy"),
                "polygon":
                    x.get("polygon"),
            }

            disease = x.get("source_disease")

            if disease in DISEASE_MAP:
                item["pathology_class"] = (
                    DISEASE_MAP[disease]
                )
                item["source_disease"] = disease

            instances.append(item)

        records.append({
            "source_dataset":
                r.get("source_dataset"),
            "source_split":
                split,
            "source_image_id":
                r.get("source_image_id"),
            "canonical_image_id":
                r.get("canonical_image_id"),
            "image_path":
                r.get("image_path"),
            "width":
                r.get("width"),
            "height":
                r.get("height"),
            "instances":
                instances,
        })

    payload = {
        "schema_version":
            "dentai-v3-full-1",
        "split":
            split,
        "records":
            records,
    }

    (OUT / f"{split}.json").write_text(
        json.dumps(
            payload,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

# Keep external validation from Zenodo unchanged.
ext = NEW / "external_validation.json"

if ext.exists():
    (OUT / "external_validation.json").write_text(
        ext.read_text(),
        encoding="utf-8"
    )


# =========================================================
# FULL AUDIT
# =========================================================

summary = {}

for split in [
    "train",
    "validation",
    "test",
    "external_validation",
]:
    p = OUT / f"{split}.json"

    if not p.exists():
        continue

    d = json.loads(p.read_text())

    classes = Counter()
    sources = Counter()

    tooth_instances = 0
    fdi_instances = 0
    pathology_instances = 0

    for r in d["records"]:
        sources[
            r.get("source_dataset", "UNKNOWN")
        ] += 1

        for x in r.get("instances", []):
            cls = x.get("canonical_class")

            if cls:
                classes[cls] += 1

            pathology = x.get("pathology_class")

            if pathology:
                classes[pathology] += 1
                pathology_instances += 1

            if cls == "TOOTH":
                tooth_instances += 1

            if x.get("fdi_number"):
                fdi_instances += 1

    summary[split] = {
        "images": len(d["records"]),
        "tooth_instances": tooth_instances,
        "fdi_instances": fdi_instances,
        "pathology_instances":
            pathology_instances,
        "sources": dict(sources),
        "classes": dict(classes),
    }

    print("\n" + "="*72)
    print(split.upper())
    print("="*72)

    print("Images:", len(d["records"]))
    print("TOOTH instances:", tooth_instances)
    print("FDI instances:", fdi_instances)
    print(
        "Existing DENTAI disease labels:",
        pathology_instances
    )

    print("\nSOURCES:")
    for k,v in sources.most_common():
        print(f"{k:40} {v}")

    print("\nTOP CLASSES:")
    for k,v in classes.most_common(40):
        print(f"{k:30} {v}")

(OUT / "stats.json").write_text(
    json.dumps(
        summary,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print("\n" + "="*72)
print("DENTAI V3 FULL READY")
print("="*72)
print("Output:", OUT)
