import json
from pathlib import Path
from collections import Counter, defaultdict

import torch
from torch.utils.data import DataLoader

from ai_engine.inference.dentai_unified_v2 import (
    DEVICE,
    load_tooth,
    load_fdi,
    load_disease,
    infer_fdi,
    resolve_arch,
    infer_disease,
)
from ai_engine.training.train_restoration_detector_v1 import (
    RestorationDetectionDataset,
    collate_fn,
    evaluate_detector,
)
from ai_engine.inference.dentai_unified_v3 import (
    load_restoration_detector,
)

from PIL import Image
from torchvision.transforms.functional import to_tensor


TEST = Path("data/splits/tooth_v2/test.json")


def box_iou(a,b):
    ax1,ay1,ax2,ay2 = a
    bx1,by1,bx2,by2 = b

    ix1=max(ax1,bx1)
    iy1=max(ay1,by1)
    ix2=min(ax2,bx2)
    iy2=min(ay2,by2)

    iw=max(0,ix2-ix1)
    ih=max(0,iy2-iy1)

    inter=iw*ih

    aa=max(0,ax2-ax1)*max(0,ay2-ay1)
    bb=max(0,bx2-bx1)*max(0,by2-by1)

    union=aa+bb-inter

    return inter/union if union>0 else 0.0


def load_test():
    return json.loads(TEST.read_text())


def evaluate_tooth_fdi_disease():
    data = load_test()

    tooth_model = load_tooth()
    fdi_model = load_fdi()
    disease_a, disease_b = load_disease()

    gt_tooth_total = 0
    gt_tooth_matched = 0

    fdi_total = 0
    fdi_correct_raw = 0
    fdi_correct_resolved = 0

    disease_total = 0
    disease_correct = 0
    disease_cc = Counter()
    disease_ct = Counter()

    raw_duplicate_images = 0
    resolved_duplicate_images = 0
    low_conf_fdi = 0

    for idx, record in enumerate(data["records"], start=1):
        image = Image.open(record["image_path"]).convert("RGB")
        tensor = to_tensor(image).to(DEVICE)

        with torch.no_grad():
            pred = tooth_model([tensor])[0]

        boxes = pred["boxes"].detach().cpu()
        scores = pred["scores"].detach().cpu()

        keep = scores >= 0.50
        boxes = boxes[keep]

        pred_teeth = []

        for box in boxes:
            box_list = box.tolist()

            fdi, conf = infer_fdi(
                fdi_model,
                image,
                box_list,
            )

            pred_teeth.append({
                "bbox_xyxy": box_list,
                "fdi_number": fdi,
                "fdi_confidence": conf,
            })

            if conf < 0.70:
                low_conf_fdi += 1

        raw_counts = Counter(
            x["fdi_number"]
            for x in pred_teeth
        )

        if any(v > 1 for v in raw_counts.values()):
            raw_duplicate_images += 1

        pred_teeth = resolve_arch(pred_teeth)

        resolved_counts = Counter(
            x["resolved_fdi_number"]
            for x in pred_teeth
        )

        if any(v > 1 for v in resolved_counts.values()):
            resolved_duplicate_images += 1

        gt_instances = [
            x for x in record.get("instances", [])
            if x.get("canonical_class") == "TOOTH"
        ]

        gt_tooth_total += len(gt_instances)

        used_pred = set()

        for gt in gt_instances:
            gt_box = gt.get("bbox_xyxy")
            gt_fdi = str(gt.get("fdi_number", "")).strip()

            if not gt_box:
                continue

            best_iou = 0.0
            best_j = None

            for j, pt in enumerate(pred_teeth):
                if j in used_pred:
                    continue

                iou = box_iou(
                    gt_box,
                    pt["bbox_xyxy"],
                )

                if iou > best_iou:
                    best_iou = iou
                    best_j = j

            if best_j is None or best_iou < 0.50:
                continue

            used_pred.add(best_j)
            gt_tooth_matched += 1

            pt = pred_teeth[best_j]

            fdi_total += 1

            if pt["fdi_number"] == gt_fdi:
                fdi_correct_raw += 1

            if pt["resolved_fdi_number"] == gt_fdi:
                fdi_correct_resolved += 1

            disease_gt = gt.get("source_disease")

            if disease_gt in {
                "Caries",
                "Deep Caries",
                "Impacted",
                "Periapical Lesion",
            }:
                result = infer_disease(
                    disease_a,
                    disease_b,
                    image,
                    pt["bbox_xyxy"],
                    pt["resolved_fdi_number"],
                )

                pred_disease = result["candidate"]

                disease_total += 1
                disease_ct[disease_gt] += 1

                if pred_disease == disease_gt:
                    disease_correct += 1
                    disease_cc[disease_gt] += 1

        if idx % 20 == 0:
            print(
                f"[MASTER] processed {idx}/{len(data['records'])}"
            )

    return {
        "tooth_recall": (
            gt_tooth_matched / gt_tooth_total
            if gt_tooth_total else 0
        ),
        "gt_teeth": gt_tooth_total,
        "matched_teeth": gt_tooth_matched,

        "fdi_raw_acc": (
            fdi_correct_raw / fdi_total
            if fdi_total else 0
        ),
        "fdi_resolved_acc": (
            fdi_correct_resolved / fdi_total
            if fdi_total else 0
        ),
        "fdi_total": fdi_total,
        "low_conf_fdi": low_conf_fdi,
        "raw_duplicate_images": raw_duplicate_images,
        "resolved_duplicate_images": resolved_duplicate_images,

        "disease_acc": (
            disease_correct / disease_total
            if disease_total else 0
        ),
        "disease_total": disease_total,
        "disease_recall": {
            k: (
                disease_cc[k] / disease_ct[k]
                if disease_ct[k] else 0
            )
            for k in [
                "Caries",
                "Deep Caries",
                "Impacted",
                "Periapical Lesion",
            ]
        }
    }


def evaluate_restoration():
    detector = load_restoration_detector()

    ds = RestorationDetectionDataset("test")

    loader = DataLoader(
        ds,
        batch_size=2,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=collate_fn,
    )

    macro_f1, metrics = evaluate_detector(
        detector,
        loader,
        DEVICE,
        score_threshold=0.50,
        iou_threshold=0.50,
    )

    return {
        "macro_f1": macro_f1,
        "metrics": metrics,
        "test_images": len(ds),
    }


def main():
    print("="*70)
    print("DENTAI MASTER EVALUATION V1")
    print("Device:", DEVICE)
    print("="*70)

    core = evaluate_tooth_fdi_disease()
    rest = evaluate_restoration()

    print()
    print("="*70)
    print("MASTER RESULTS")
    print("="*70)

    print("\n[TOOTH]")
    print(
        "Detection recall @ IoU0.50:",
        round(core["tooth_recall"],4),
        f'({core["matched_teeth"]}/{core["gt_teeth"]})'
    )

    print("\n[FDI]")
    print(
        "Raw accuracy:",
        round(core["fdi_raw_acc"],4)
    )
    print(
        "Resolved accuracy:",
        round(core["fdi_resolved_acc"],4)
    )
    print(
        "Low-confidence predictions:",
        core["low_conf_fdi"]
    )
    print(
        "Images with duplicate FDI before resolver:",
        core["raw_duplicate_images"]
    )
    print(
        "Images with duplicate FDI after resolver:",
        core["resolved_duplicate_images"]
    )

    print("\n[DISEASE — labeled teeth only]")
    print(
        "Accuracy:",
        round(core["disease_acc"],4),
        f'| n={core["disease_total"]}'
    )

    for k,v in core["disease_recall"].items():
        print(
            f"{k:22}",
            round(v,4)
        )

    print("\n[RESTORATION DETECTOR]")
    print(
        "Macro F1:",
        round(rest["macro_f1"],4)
    )

    for k,m in rest["metrics"].items():
        print(
            f"{k:10} "
            f'P={m["precision"]:.4f} '
            f'R={m["recall"]:.4f} '
            f'F1={m["f1"]:.4f}'
        )

    summary = {
        "tooth": core,
        "restoration": rest,
    }

    out = Path(
        "artifacts/evaluation"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    path = out / "master_eval_v1.json"

    path.write_text(
        json.dumps(
            summary,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(
        "Report:",
        path
    )

    print("="*70)


if __name__ == "__main__":
    main()
