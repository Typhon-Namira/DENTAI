
import argparse
import json
from pathlib import Path

import torch
from torch import nn
from PIL import Image, ImageDraw
from torchvision import models
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms.functional import to_tensor

from ai_engine.inference.dentai_unified_v2 import (
    DEVICE,
    FDI_CLASSES,
    load_tooth,
    load_fdi,
    load_disease,
    infer_fdi,
    # resolve_arch removed; V4 uses global resolver V3,
    infer_disease,
)


from ai_engine.evaluation.fdi_resolver_v3_eval import (
    resolve_image as resolve_arch_v3,
    get_fdi_probs,
)
REST_CLASSES = {
    1: "FILLING",
    2: "IMPLANT",
}


def load_restoration_detector():
    p = Path("checkpoints/restoration_detector_v1/best.pt")
    ckpt = torch.load(p, map_location="cpu", weights_only=False)

    model = fasterrcnn_resnet50_fpn(
        weights=None,
        weights_backbone=None,
    )

    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(
        in_features,
        3,
    )

    model.load_state_dict(ckpt["model"], strict=True)
    model.to(DEVICE).eval()

    print(
        "✓ Restoration Detector V1 | macro_f1=",
        ckpt.get("macro_f1"),
    )

    return model


def load_restoration_classifier():
    p = Path("checkpoints/restoration_v1/best.pt")
    ckpt = torch.load(p, map_location="cpu", weights_only=False)

    model = models.resnet18(weights=None)

    model.fc = nn.Sequential(
        nn.Dropout(0.30),
        nn.Linear(model.fc.in_features, 2),
    )

    model.load_state_dict(ckpt["model"], strict=True)
    model.to(DEVICE).eval()

    print("✓ Restoration Classifier V1")
    return model


def crop_classifier_image(image, box):
    from torchvision import transforms

    tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            [0.485, 0.456, 0.406],
            [0.229, 0.224, 0.225],
        ),
    ])

    W, H = image.size
    x1, y1, x2, y2 = map(float, box)

    bw = max(x2 - x1, 1)
    bh = max(y2 - y1, 1)

    px = max(15, int(bw * 0.45))
    py = max(15, int(bh * 0.45))

    crop = image.crop((
        max(0, int(x1) - px),
        max(0, int(y1) - py),
        min(W, int(x2) + px),
        min(H, int(y2) + py),
    ))

    return tf(crop).unsqueeze(0).to(DEVICE)


def classify_restoration(classifier, image, box):
    tensor = crop_classifier_image(image, box)

    with torch.no_grad(), torch.amp.autocast(
        "cuda",
        enabled=DEVICE.type == "cuda",
        dtype=torch.bfloat16,
    ):
        logits = classifier(tensor)

    probs = torch.softmax(logits.float(), dim=1)
    conf, idx = probs.max(1)

    classes = ["FILLING", "IMPLANT"]

    return classes[idx.item()], float(conf.item())


def run_restoration_detector(
    detector,
    classifier,
    image,
    threshold=0.50,
):
    tensor = to_tensor(image).to(DEVICE)

    with torch.no_grad():
        out = detector([tensor])[0]

    boxes = out["boxes"].detach().cpu()
    labels = out["labels"].detach().cpu()
    scores = out["scores"].detach().cpu()

    results = []

    for box, label, score in zip(boxes, labels, scores):
        score = float(score)

        if score < threshold:
            continue

        label = int(label)

        if label not in REST_CLASSES:
            continue

        box_list = [float(x) for x in box.tolist()]
        detector_type = REST_CLASSES[label]

        classifier_type, classifier_conf = classify_restoration(
            classifier,
            image,
            box_list,
        )

        agreement = detector_type == classifier_type

        results.append({
            "bbox_xyxy": [round(x, 2) for x in box_list],
            "detector_type": detector_type,
            "detector_confidence": round(score, 4),
            "classifier_type": classifier_type,
            "classifier_confidence": round(classifier_conf, 4),
            "type_agreement": agreement,
            "final_type": detector_type,
            "review_required": not agreement,
        })

    return results


def center(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def attach_restorations(restorations, teeth):
    for tooth in teeth:
        tooth["restorations"] = []

    unmatched = []

    for rest in restorations:
        rcx, rcy = center(rest["bbox_xyxy"])

        best_tooth = None
        best_distance = None

        for tooth in teeth:
            tcx, tcy = center(tooth["bbox_xyxy"])

            d = (rcx - tcx) ** 2 + (rcy - tcy) ** 2

            if best_distance is None or d < best_distance:
                best_distance = d
                best_tooth = tooth

        if best_tooth is None:
            unmatched.append(rest)
            continue

        linked = dict(rest)
        linked["resolved_fdi_number"] = best_tooth[
            "resolved_fdi_number"
        ]

        best_tooth["restorations"].append(linked)

    return teeth, unmatched


def run(
    image_path,
    tooth_threshold=0.50,
    restoration_threshold=0.50,
):
    print("=" * 60)
    print("DENTAI UNIFIED BRAIN V4")
    print("Device:", DEVICE)

    if DEVICE.type == "cuda":
        print("GPU:", torch.cuda.get_device_name(0))

    print("=" * 60)

    tooth_model = load_tooth()
    fdi_model = load_fdi()
    disease_a, disease_b = load_disease()
    rest_detector = load_restoration_detector()
    rest_classifier = load_restoration_classifier()

    image = Image.open(image_path).convert("RGB")
    tensor = to_tensor(image).to(DEVICE)

    print("\nRunning Tooth V2...")

    with torch.no_grad():
        pred = tooth_model([tensor])[0]

    boxes = pred["boxes"].detach().cpu()
    scores = pred["scores"].detach().cpu()

    keep = scores >= tooth_threshold
    boxes = boxes[keep]
    scores = scores[keep]

    teeth = []

    for i, (box, score) in enumerate(zip(boxes, scores), start=1):
        box_list = [float(x) for x in box.tolist()]

        probs = get_fdi_probs(
            fdi_model,
            image,
            box_list,
        )

        conf, idx = probs.max(0)
        fdi = FDI_CLASSES[idx.item()]

        teeth.append({
            "instance_id": i,
            "bbox_xyxy": [round(x, 2) for x in box_list],
            "bbox": box_list,
            "segmentation_confidence": round(float(score), 4),
            "fdi_number": fdi,
            "raw": fdi,
            "raw_conf": float(conf),
            "fdi_confidence": round(float(conf), 4),
            "probs": probs,
        })

    resolved = resolve_arch_v3(teeth)

    teeth = []

    for t in resolved:
        t["raw_fdi_number"] = t["raw"]
        t["resolved_fdi_number"] = t["resolved"]
        t["fdi_was_changed"] = t["was_changed"]
        t["fdi_review_required"] = (
            float(t["raw_conf"]) < 0.70
            or bool(t["unresolved_by_dp"])
        )

        t.pop("probs", None)
        t.pop("raw", None)
        t.pop("raw_conf", None)
        t.pop("resolved", None)
        t.pop("was_changed", None)
        t.pop("unresolved_by_dp", None)
        t.pop("bbox", None)

        teeth.append(t)

    # Preserve Resolver V3 predictions.
    # Do not force duplicate correction; flag conflicts for review.
    from collections import Counter

    fdi_counts = Counter(
        t["resolved_fdi_number"]
        for t in teeth
    )

    for t in teeth:
        duplicate = (
            fdi_counts[t["resolved_fdi_number"]] > 1
        )

        t["duplicate_fdi_conflict"] = duplicate

        if duplicate:
            t["fdi_review_required"] = True

    for tooth in teeth:
        disease = infer_disease(
            disease_a,
            disease_b,
            image,
            tooth["bbox_xyxy"],
            tooth["resolved_fdi_number"],
        )

        tooth["disease"] = {
            "candidate": disease["candidate"],
            "confidence": round(disease["confidence"], 4),
            "review_required": True,
        }

    print("Running Restoration Detector...")

    restorations = run_restoration_detector(
        rest_detector,
        rest_classifier,
        image,
        restoration_threshold,
    )

    teeth, unmatched = attach_restorations(
        restorations,
        teeth,
    )

    teeth.sort(
        key=lambda t: int(t["resolved_fdi_number"])
    )

    result = {
        "schema_version": "dentai-unified-v4",
        "image": str(image_path),
        "detected_teeth": len(teeth),
        "detected_restorations": len(restorations),
        "unmatched_restorations": unmatched,
        "teeth": teeth,
    }

    out = Path("artifacts/unified")
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "dentai_unified_v4.json"
    json_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    preview = image.copy()
    draw = ImageDraw.Draw(preview)

    for tooth in teeth:
        x1, y1, x2, y2 = tooth["bbox_xyxy"]

        fdi = tooth["resolved_fdi_number"]
        disease = tooth["disease"]["candidate"]

        rest_types = [
            r["final_type"]
            for r in tooth["restorations"]
        ]

        label = f"{fdi} {disease}"

        if rest_types:
            label += " [" + ",".join(rest_types) + "]"

        draw.rectangle(
            [x1, y1, x2, y2],
            width=3,
        )

        draw.text(
            (x1, max(0, y1 - 15)),
            label,
        )

    for rest in restorations:
        x1, y1, x2, y2 = rest["bbox_xyxy"]

        draw.rectangle(
            [x1, y1, x2, y2],
            width=2,
        )

        draw.text(
            (x1, y1),
            rest["final_type"],
        )

    preview_path = (
        out / "dentai_unified_v4_preview.jpg"
    )

    preview.save(
        preview_path,
        quality=95,
    )

    print()
    print("=" * 60)
    print("DENTAI UNIFIED V4 COMPLETE")
    print("Teeth:", len(teeth))
    print("Restorations:", len(restorations))
    print("JSON:", json_path)
    print("Preview:", preview_path)
    print("=" * 60)

    print()

    for tooth in teeth:
        rest_text = "NONE"

        if tooth["restorations"]:
            rest_text = "; ".join(
                (
                    f'{r["final_type"]} '
                    f'det={r["detector_confidence"]:.3f} '
                    f'cls={r["classifier_confidence"]:.3f} '
                    f'agree={r["type_agreement"]}'
                )
                for r in tooth["restorations"]
            )

        print(
            f'FDI {tooth["resolved_fdi_number"]:>2} | '
            f'DISEASE={tooth["disease"]["candidate"]} '
            f'({tooth["disease"]["confidence"]:.3f}) | '
            f'REST={rest_text}'
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        required=True,
    )

    parser.add_argument(
        "--tooth-threshold",
        type=float,
        default=0.50,
    )

    parser.add_argument(
        "--restoration-threshold",
        type=float,
        default=0.50,
    )

    args = parser.parse_args()

    run(
        args.image,
        args.tooth_threshold,
        args.restoration_threshold,
    )
