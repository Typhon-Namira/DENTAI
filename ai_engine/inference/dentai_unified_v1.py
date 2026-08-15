import argparse
import json
from collections import Counter
from pathlib import Path

import torch
from PIL import Image, ImageDraw
from torchvision import models, transforms
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.transforms.functional import to_tensor

from ai_engine.training.train_fdi_v2 import FDINetV2, FDI_CLASSES
from ai_engine.training.train_disease_v3_hier import (
    HierNet,
    STAGE_A_CLASSES,
    STAGE_B_CLASSES,
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

FDI_TF = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

DISEASE_TF = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])

FDI_TO_IDX = {x: i for i, x in enumerate(FDI_CLASSES)}


def load_tooth_model():
    p = Path("checkpoints/tooth_v2/maskrcnn_fpn_v1/best.pt")
    ckpt = torch.load(p, map_location="cpu", weights_only=False)

    model = maskrcnn_resnet50_fpn(
        weights=None,
        weights_backbone=None,
        num_classes=2,
    )

    model.load_state_dict(ckpt["model"], strict=True)
    model.to(DEVICE).eval()

    print("✓ Tooth V2:", p)
    return model


def load_fdi_model():
    candidates = [
        Path("checkpoints/fdi_v2_final/fdi_v2_best_90_38.pt"),
        Path("checkpoints/fdi_v2/best.pt"),
    ]

    p = next((x for x in candidates if x.exists()), None)
    if p is None:
        raise FileNotFoundError("FDI V2 best checkpoint not found")

    ckpt = torch.load(p, map_location="cpu", weights_only=False)

    model = FDINetV2()
    model.load_state_dict(ckpt["model"], strict=True)
    model.to(DEVICE).eval()

    print("✓ FDI V2:", p, "val_acc=", ckpt.get("val_acc"))
    return model


def load_disease_models():
    pa = Path("checkpoints/disease_v3/stage_a/best.pt")
    pb = Path("checkpoints/disease_v3/stage_b/best.pt")

    ca = torch.load(pa, map_location="cpu", weights_only=False)
    cb = torch.load(pb, map_location="cpu", weights_only=False)

    a = HierNet(len(STAGE_A_CLASSES))
    b = HierNet(len(STAGE_B_CLASSES))

    a.load_state_dict(ca["model"], strict=True)
    b.load_state_dict(cb["model"], strict=True)

    a.to(DEVICE).eval()
    b.to(DEVICE).eval()

    print("✓ Disease V3 Stage A:", pa)
    print("✓ Disease V3 Stage B:", pb)

    return a, b


def bbox_geometry(box, W, H):
    x1, y1, x2, y2 = map(float, box)

    bw = max(x2 - x1, 1.0)
    bh = max(y2 - y1, 1.0)

    cx = ((x1 + x2) / 2.0) / max(W, 1)
    cy = ((y1 + y2) / 2.0) / max(H, 1)
    nw = bw / max(W, 1)
    nh = bh / max(H, 1)

    return x1, y1, x2, y2, bw, bh, cx, cy, nw, nh


def classify_fdi(model, image, box):
    W, H = image.size

    x1, y1, x2, y2, bw, bh, cx, cy, nw, nh = bbox_geometry(
        box, W, H
    )

    spatial = torch.tensor(
        [[cx, cy, nw, nh]],
        dtype=torch.float32,
        device=DEVICE,
    )

    pad_x = max(12, int(bw * 0.35))
    pad_y = max(12, int(bh * 0.35))

    crop = image.crop((
        max(0, int(x1) - pad_x),
        max(0, int(y1) - pad_y),
        min(W, int(x2) + pad_x),
        min(H, int(y2) + pad_y),
    ))

    tensor = FDI_TF(crop).unsqueeze(0).to(DEVICE)

    with torch.no_grad(), torch.amp.autocast(
        "cuda",
        enabled=DEVICE.type == "cuda",
        dtype=torch.bfloat16,
    ):
        logits = model(tensor, spatial)

    probs = torch.softmax(logits.float(), dim=1)
    conf, idx = probs.max(dim=1)

    return FDI_CLASSES[idx.item()], float(conf.item())


def disease_input(image, box, fdi):
    W, H = image.size

    x1, y1, x2, y2, bw, bh, cx, cy, nw, nh = bbox_geometry(
        box, W, H
    )

    pad_x = max(24, int(bw * 0.95))
    pad_top = max(22, int(bh * 0.65))
    pad_bottom = max(32, int(bh * 1.20))

    crop = image.crop((
        max(0, int(x1) - pad_x),
        max(0, int(y1) - pad_top),
        min(W, int(x2) + pad_x),
        min(H, int(y2) + pad_bottom),
    ))

    if fdi in FDI_TO_IDX:
        fdi_idx = FDI_TO_IDX[fdi] / 31.0
        quadrant = int(fdi[0]) / 4.0
        position = int(fdi[1]) / 8.0
    else:
        fdi_idx = -1.0
        quadrant = 0.0
        position = 0.0

    meta = torch.tensor(
        [[cx, cy, nw, nh, fdi_idx, quadrant, position]],
        dtype=torch.float32,
        device=DEVICE,
    )

    tensor = DISEASE_TF(crop).unsqueeze(0).to(DEVICE)

    return tensor, meta


def classify_disease(stage_a, stage_b, image, box, fdi):
    tensor, meta = disease_input(image, box, fdi)

    with torch.no_grad(), torch.amp.autocast(
        "cuda",
        enabled=DEVICE.type == "cuda",
        dtype=torch.bfloat16,
    ):
        logits_a = stage_a(tensor, meta)

    probs_a = torch.softmax(logits_a.float(), dim=1)
    conf_a, idx_a = probs_a.max(dim=1)

    stage_a_name = STAGE_A_CLASSES[idx_a.item()]
    stage_a_conf = float(conf_a.item())

    if stage_a_name == "Decay":
        with torch.no_grad(), torch.amp.autocast(
            "cuda",
            enabled=DEVICE.type == "cuda",
            dtype=torch.bfloat16,
        ):
            logits_b = stage_b(tensor, meta)

        probs_b = torch.softmax(logits_b.float(), dim=1)
        conf_b, idx_b = probs_b.max(dim=1)

        disease = STAGE_B_CLASSES[idx_b.item()]
        stage_b_conf = float(conf_b.item())

        # Combined confidence is deliberately conservative.
        combined = stage_a_conf * stage_b_conf

        return {
            "disease_candidate": disease,
            "disease_confidence": round(combined, 4),
            "stage_a": stage_a_name,
            "stage_a_confidence": round(stage_a_conf, 4),
            "stage_b_confidence": round(stage_b_conf, 4),
            "review_required": True,
        }

    return {
        "disease_candidate": stage_a_name,
        "disease_confidence": round(stage_a_conf, 4),
        "stage_a": stage_a_name,
        "stage_a_confidence": round(stage_a_conf, 4),
        "stage_b_confidence": None,
        "review_required": True,
    }


def run(image_path, segmentation_threshold=0.50):
    print("==============================================")
    print("DENTAI UNIFIED BRAIN V1")
    print("Device:", DEVICE)

    if DEVICE.type == "cuda":
        print("GPU:", torch.cuda.get_device_name(0))

    print("==============================================")

    tooth_model = load_tooth_model()
    fdi_model = load_fdi_model()
    disease_a, disease_b = load_disease_models()

    image = Image.open(image_path).convert("RGB")
    tensor = to_tensor(image).to(DEVICE)

    print("\nRunning Tooth V2...")

    with torch.no_grad():
        pred = tooth_model([tensor])[0]

    boxes = pred["boxes"].detach().cpu()
    scores = pred["scores"].detach().cpu()

    keep = scores >= segmentation_threshold
    boxes = boxes[keep]
    scores = scores[keep]

    print("Detected tooth instances:", len(boxes))

    teeth = []

    for instance_id, (box, seg_score) in enumerate(
        zip(boxes, scores), start=1
    ):
        box_list = box.tolist()

        fdi, fdi_conf = classify_fdi(
            fdi_model,
            image,
            box_list,
        )

        disease = classify_disease(
            disease_a,
            disease_b,
            image,
            box_list,
            fdi,
        )

        tooth = {
            "instance_id": instance_id,
            "bbox_xyxy": [round(float(x), 2) for x in box_list],
            "segmentation_confidence": round(float(seg_score), 4),
            "fdi_number": fdi,
            "fdi_confidence": round(fdi_conf, 4),
            **disease,
        }

        # FDI itself also requires review when uncertain.
        tooth["fdi_review_required"] = bool(fdi_conf < 0.70)

        teeth.append(tooth)

    # Flag duplicate FDI assignments instead of silently resolving them.
    counts = Counter(t["fdi_number"] for t in teeth)

    for tooth in teeth:
        tooth["duplicate_fdi_conflict"] = (
            counts[tooth["fdi_number"]] > 1
        )

    teeth.sort(key=lambda x: int(x["fdi_number"]))

    result = {
        "schema_version": "dentai-unified-v1",
        "image": str(image_path),
        "device": str(DEVICE),
        "detected_teeth": len(teeth),
        "important_limitation": (
            "Disease V3 has no HEALTHY class. Disease outputs are "
            "candidate findings only and must not be interpreted as "
            "confirmation that every tooth is diseased."
        ),
        "teeth": teeth,
    }

    out = Path("artifacts/unified")
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "dentai_unified_v1.json"
    json_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    preview = image.copy()
    draw = ImageDraw.Draw(preview)

    for tooth in teeth:
        x1, y1, x2, y2 = tooth["bbox_xyxy"]

        text = (
            f'{tooth["fdi_number"]} | '
            f'{tooth["disease_candidate"]}'
        )

        draw.rectangle(
            [x1, y1, x2, y2],
            width=3,
        )

        draw.text(
            (x1, max(0, y1 - 15)),
            text,
        )

    preview_path = out / "dentai_unified_v1_preview.jpg"
    preview.save(preview_path, quality=95)

    print("\n==============================================")
    print("UNIFIED INFERENCE COMPLETE")
    print("Detected teeth:", len(teeth))
    print("JSON:", json_path)
    print("Preview:", preview_path)
    print("==============================================\n")

    for t in teeth:
        conflict = " DUPLICATE-FDI" if t["duplicate_fdi_conflict"] else ""
        print(
            f'FDI {t["fdi_number"]:>2} | '
            f'FDI={t["fdi_confidence"]:.3f} | '
            f'SEG={t["segmentation_confidence"]:.3f} | '
            f'CANDIDATE={t["disease_candidate"]} | '
            f'DISEASE={t["disease_confidence"]:.3f}'
            f'{conflict}'
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        required=True,
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.50,
    )

    args = parser.parse_args()

    run(
        args.image,
        segmentation_threshold=args.threshold,
    )
