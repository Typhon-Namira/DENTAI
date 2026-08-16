from pathlib import Path
from collections import Counter
import json
import random

ROOT = Path("data/raw/dentai_v3_sources/dual_labeled/extracted")
IMAGES = ROOT / "images1"
LABELS = ROOT / "labels"

OUT = Path("data/canonical/dual_labeled_status")
OUT.mkdir(parents=True, exist_ok=True)

FDI = {
    str(q*10+n)
    for q in range(1,5)
    for n in range(1,9)
}

STATUS_MAP = {
    None: "HEALTHY",
    1: "FILLING",
    2: "ROOT_CANAL_TREATMENT",
    3: "CROWN",
    4: "CARIES",
    5: "RESIDUAL_ROOT",
    6: "RCT_CROWN",
}

image_map = {
    p.stem: p
    for p in IMAGES.iterdir()
    if p.is_file()
}

records = []
stats = Counter()

for p in sorted(LABELS.glob("*.json")):
    if p.stem not in image_map:
        continue

    d = json.loads(
        p.read_text(encoding="utf-8")
    )

    teeth = []

    for shape in d.get("shapes", []):
        fdi = str(
            shape.get("label", "")
        ).strip()

        if fdi not in FDI:
            continue

        gid = shape.get("group_id")

        if gid not in STATUS_MAP:
            continue

        points = shape.get("points") or []

        if not points:
            continue

        xs = [float(x[0]) for x in points]
        ys = [float(x[1]) for x in points]

        bbox = [
            min(xs),
            min(ys),
            max(xs),
            max(ys),
        ]

        status = STATUS_MAP[gid]

        teeth.append({
            "fdi_number": fdi,
            "status": status,
            "status_source_value": (
                0 if gid is None else gid
            ),
            "bbox_xyxy": bbox,
            "polygon": points,
        })

        stats[status] += 1

    records.append({
        "source_dataset":
            "dual_labeled_status",
        "source_image_id":
            image_map[p.stem].name,
        "image_path":
            str(image_map[p.stem]),
        "width":
            d.get("imageWidth"),
        "height":
            d.get("imageHeight"),
        "teeth":
            teeth,
    })

print("="*72)
print("DUAL-LABELED STATUS IMPORT")
print("="*72)

print("Images:", len(records))
print("Teeth:", sum(stats.values()))

for k,v in stats.most_common():
    print(f"{k:28} {v}")

# Reuse deterministic 80/10/10 split.
rng = random.Random(20260816)
rng.shuffle(records)

n = len(records)
n_train = int(n*0.80)
n_val = int(n*0.10)

splits = {
    "train": records[:n_train],
    "validation":
        records[n_train:n_train+n_val],
    "test":
        records[n_train+n_val:],
}

for split, recs in splits.items():
    payload = {
        "schema_version":
            "dual-labeled-status-v1",
        "split":
            split,
        "status_mapping": {
            "0": "HEALTHY",
            "1": "FILLING",
            "2": "ROOT_CANAL_TREATMENT",
            "3": "CROWN",
            "4": "CARIES",
            "5": "RESIDUAL_ROOT",
            "6": "RCT_CROWN",
        },
        "records":
            recs,
    }

    (OUT / f"{split}.json").write_text(
        json.dumps(
            payload,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    split_stats = Counter()

    for r in recs:
        for t in r["teeth"]:
            split_stats[t["status"]] += 1

    print("\n" + split.upper())

    for k,v in split_stats.most_common():
        print(f"{k:28} {v}")

print("\nOutput:", OUT)
