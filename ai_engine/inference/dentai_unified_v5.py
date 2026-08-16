"""DENTAI Unified Brain V5 production inference pipeline."""

import argparse
import gc
import json
import math
from collections import Counter
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
from torch import nn
from torchvision import models, transforms
from torchvision.models.detection import fasterrcnn_resnet50_fpn, maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from torchvision.transforms.functional import to_tensor

from ai_engine.evaluation.fdi_resolver_v3_eval import resolve_image as resolve_fdi_v3


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
FDI_CLASSES = [str(q * 10 + n) for q in range(1, 5) for n in range(1, 9)]
VALID_FDI = set(FDI_CLASSES)
STATUS_GATE_CLASSES = ["HEALTHY", "NON_HEALTHY"]
STATUS_CLASSES = [
    "HEALTHY", "FILLING", "CARIES", "RCT_CROWN", "CROWN",
    "ROOT_CANAL_TREATMENT", "RESIDUAL_ROOT",
]
PATHOLOGY_CLASSES = {
    1: "CARIES", 2: "APICAL_PERIODONTITIS", 3: "IMPACTED",
    4: "BONE_RESORPTION", 5: "ROOT_FRAGMENT", 6: "FURCATION_LESION",
}
PATHOLOGY_THRESHOLDS = {
    "CARIES": 0.70, "APICAL_PERIODONTITIS": 0.65, "IMPACTED": 0.65,
    "BONE_RESORPTION": 0.65, "ROOT_FRAGMENT": 0.30,
    "FURCATION_LESION": 0.55,
}
DEEP_CARIES_CLASSES = ["CARIES", "DEEP_CARIES"]
REST_CLASSES = {1: "FILLING", 2: "IMPLANT"}
EXPERIMENTAL = {"BONE_RESORPTION", "FURCATION_LESION"}

CHECKPOINTS = {
    "tooth": Path("checkpoints/tooth_v3/maskrcnn_fpn_v1/best.pt"),
    "fdi": Path("checkpoints/fdi_v3_fixed/best.pt"),
    "status_gate": Path("checkpoints/tooth_status_gate_v1/best.pt"),
    "status_v2": Path("checkpoints/tooth_status_v2/best.pt"),
    "pathology": Path("checkpoints/pathology_detector_v41/best.pt"),
    "deep_caries": Path("checkpoints/deep_caries_v2/best.pt"),
    "restoration_detector": Path("checkpoints/restoration_detector_v1/best.pt"),
    "restoration_classifier": Path("checkpoints/restoration_v1/best.pt"),
}

IMAGENET_NORMALIZE = transforms.Normalize(
    [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
)


class FDINetV2(nn.Module):
    """Exact network used by train_fdi_v3_fixed.py."""

    def __init__(self):
        super().__init__()
        backbone = models.resnet18(weights=None)
        feature_dim = backbone.fc.in_features
        backbone.fc = nn.Identity()
        self.backbone = backbone
        self.spatial_net = nn.Sequential(
            nn.Linear(4, 32), nn.ReLU(), nn.Linear(32, 32), nn.ReLU()
        )
        self.classifier = nn.Sequential(
            nn.Linear(feature_dim + 32, 256), nn.ReLU(), nn.Dropout(0.30),
            nn.Linear(256, len(FDI_CLASSES)),
        )

    def forward(self, image, spatial):
        return self.classifier(torch.cat((self.backbone(image), self.spatial_net(spatial)), dim=1))


def _checkpoint(path):
    if not path.is_file():
        raise FileNotFoundError(f"Required checkpoint not found: {path}")
    return torch.load(path, map_location="cpu", weights_only=False)


def _strict_load(model, path):
    ckpt = _checkpoint(path)
    state = ckpt.get("model", ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt)))
    model.load_state_dict(state, strict=True)
    model.to(DEVICE).eval()
    return model, ckpt


def load_models():
    tooth = maskrcnn_resnet50_fpn(
        weights=None, weights_backbone=None, min_size=640, max_size=1600
    )
    f = tooth.roi_heads.box_predictor.cls_score.in_features
    tooth.roi_heads.box_predictor = FastRCNNPredictor(f, 2)
    f = tooth.roi_heads.mask_predictor.conv5_mask.in_channels
    tooth.roi_heads.mask_predictor = MaskRCNNPredictor(f, 256, 2)
    tooth, tooth_ckpt = _strict_load(tooth, CHECKPOINTS["tooth"])

    fdi, fdi_ckpt = _strict_load(FDINetV2(), CHECKPOINTS["fdi"])

    gate = models.resnet18(weights=None)
    gate.fc = nn.Sequential(nn.Dropout(0.30), nn.Linear(gate.fc.in_features, 2))
    gate, gate_ckpt = _strict_load(gate, CHECKPOINTS["status_gate"])

    status = models.resnet34(weights=None)
    status.fc = nn.Sequential(nn.Dropout(0.35), nn.Linear(status.fc.in_features, 7))
    status, status_ckpt = _strict_load(status, CHECKPOINTS["status_v2"])

    pathology = fasterrcnn_resnet50_fpn(
        weights=None, weights_backbone=None, min_size=640, max_size=1600
    )
    f = pathology.roi_heads.box_predictor.cls_score.in_features
    pathology.roi_heads.box_predictor = FastRCNNPredictor(f, 7)
    pathology, pathology_ckpt = _strict_load(pathology, CHECKPOINTS["pathology"])

    deep = models.resnet34(weights=None)
    deep.fc = nn.Sequential(nn.Dropout(0.40), nn.Linear(deep.fc.in_features, 2))
    deep, deep_ckpt = _strict_load(deep, CHECKPOINTS["deep_caries"])

    rest_det = fasterrcnn_resnet50_fpn(weights=None, weights_backbone=None)
    f = rest_det.roi_heads.box_predictor.cls_score.in_features
    rest_det.roi_heads.box_predictor = FastRCNNPredictor(f, 3)
    rest_det, rest_det_ckpt = _strict_load(rest_det, CHECKPOINTS["restoration_detector"])

    rest_cls = models.resnet18(weights=None)
    rest_cls.fc = nn.Sequential(nn.Dropout(0.30), nn.Linear(rest_cls.fc.in_features, 2))
    rest_cls, rest_cls_ckpt = _strict_load(rest_cls, CHECKPOINTS["restoration_classifier"])
    return {
        "tooth": tooth, "fdi": fdi, "status_gate": gate, "status_v2": status,
        "pathology": pathology, "deep_caries": deep,
        "restoration_detector": rest_det, "restoration_classifier": rest_cls,
    }, {
        "tooth": tooth_ckpt, "fdi": fdi_ckpt, "status_gate": gate_ckpt,
        "status_v2": status_ckpt, "pathology": pathology_ckpt,
        "deep_caries": deep_ckpt, "restoration_detector": rest_det_ckpt,
        "restoration_classifier": rest_cls_ckpt,
    }


def crop_tensor(image, box, padding, minimum, size):
    width, height = image.size
    x1, y1, x2, y2 = map(float, box)
    px = max(minimum, int(max(x2 - x1, 1) * padding))
    py = max(minimum, int(max(y2 - y1, 1) * padding))
    crop = image.crop((max(0, int(x1) - px), max(0, int(y1) - py),
                       min(width, int(x2) + px), min(height, int(y2) + py)))
    tf = transforms.Compose([transforms.Resize((size, size)), transforms.ToTensor(), IMAGENET_NORMALIZE])
    return tf(crop).unsqueeze(0).to(DEVICE)


def classify(model, tensor, classes):
    logits = model(tensor)
    probs = torch.softmax(logits.float(), dim=1)[0]
    conf, idx = probs.max(0)
    return classes[int(idx)], float(conf), {c: round(float(p), 6) for c, p in zip(classes, probs.cpu())}


def fdi_probs(model, image, box):
    width, height = image.size
    x1, y1, x2, y2 = map(float, box)
    bw, bh = x2 - x1, y2 - y1
    spatial = torch.tensor([[(x1 + x2) / 2 / width, (y1 + y2) / 2 / height,
                             bw / width, bh / height]], device=DEVICE)
    tensor = crop_tensor(image, box, 0.35, 12, 224)
    logits = model(tensor, spatial)
    return torch.softmax(logits.float(), dim=1)[0].cpu()


def minimal_duplicate_cleanup(teeth):
    """Apply only V3.1's duplicate repair, and only to duplicate assignments."""
    changes = []
    for quadrant in "1234":
        expected = [f"{quadrant}{n}" for n in range(1, 9)]
        group = [t for t in teeth if str(t["resolved"]).startswith(quadrant)]
        counts = Counter(t["resolved"] for t in group)
        missing = [fdi for fdi in expected if fdi not in counts]
        for duplicate in [fdi for fdi, count in counts.items() if count > 1]:
            members = [t for t in group if t["resolved"] == duplicate]
            keeper = max(members, key=lambda t: float(t["raw_conf"]))
            ordered = sorted(group, key=lambda t: (t["bbox"][0] + t["bbox"][2]) / 2,
                             reverse=quadrant in ("1", "3"))
            for tooth in members:
                if tooth is keeper or not missing:
                    continue
                rank = ordered.index(tooth)
                approximate = rank * 7 / (len(ordered) - 1) if len(ordered) > 1 else 0
                candidate = min(missing, key=lambda fdi: abs((int(fdi[1]) - 1) - approximate))
                old = tooth["resolved"]
                tooth["resolved"] = candidate
                tooth["was_changed"] = candidate != tooth["raw"]
                tooth["duplicate_cleanup"] = True
                changes.append({"from": old, "to": candidate, "instance_id": tooth["instance_id"]})
                missing.remove(candidate)
    return changes


def intersection_metrics(a, b):
    ax1, ay1, ax2, ay2 = a; bx1, by1, bx2, by2 = b
    iw, ih = max(0.0, min(ax2, bx2) - max(ax1, bx1)), max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = iw * ih
    aa, ba = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1), max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / (aa + ba - inter) if aa + ba > inter else 0.0, inter / ba if ba else 0.0


def attach_detections(detections, teeth, field):
    for tooth in teeth:
        tooth[field] = []
    unmatched = []
    for detection in detections:
        box = detection["bbox_xyxy"]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        candidates = []
        for tooth in teeth:
            tb = tooth["tooth_detection"]["bbox_xyxy"]
            iou, coverage = intersection_metrics(tb, box)
            tcx, tcy = (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2
            scale = max(math.hypot(tb[2] - tb[0], tb[3] - tb[1]), 1)
            distance = math.hypot(cx - tcx, cy - tcy) / scale
            contains = tb[0] <= cx <= tb[2] and tb[1] <= cy <= tb[3]
            score = coverage * 3 + iou * 2 + (1 if contains else 0) - 0.25 * distance
            candidates.append((score, distance, tooth))
        best = max(candidates, key=lambda x: x[0]) if candidates else None
        if best is None or (best[0] <= 0 and best[1] > 1.25):
            unmatched.append(detection)
        else:
            linked = dict(detection)
            linked["associated_fdi"] = best[2]["fdi"]
            linked["association_score"] = round(best[0], 4)
            best[2][field].append(linked)
    return unmatched


def run_detector(model, image, class_map, thresholds):
    output = model([to_tensor(image).to(DEVICE)])[0]
    results = []
    for box, label, score in zip(output["boxes"].cpu(), output["labels"].cpu(), output["scores"].cpu()):
        name = class_map.get(int(label)); confidence = float(score)
        if name and confidence >= thresholds[name]:
            results.append({"type": name, "confidence": round(confidence, 6),
                            "threshold": thresholds[name],
                            "bbox_xyxy": [round(float(v), 2) for v in box]})
    return results


def run_restorations(detector, classifier, image, threshold):
    raw = detector([to_tensor(image).to(DEVICE)])[0]
    results = []
    for box, label, score in zip(raw["boxes"].cpu(), raw["labels"].cpu(), raw["scores"].cpu()):
        det_type, conf = REST_CLASSES.get(int(label)), float(score)
        if not det_type or conf < threshold:
            continue
        bbox = [float(v) for v in box]
        cls_type, cls_conf, cls_probs = classify(
            classifier, crop_tensor(image, bbox, 0.45, 15, 224), ["FILLING", "IMPLANT"]
        )
        results.append({"type": det_type, "bbox_xyxy": [round(v, 2) for v in bbox],
                        "detector_type": det_type, "detector_confidence": round(conf, 6),
                        "detector_threshold": threshold, "classifier_type": cls_type,
                        "classifier_confidence": round(cls_conf, 6),
                        "classifier_probabilities": cls_probs, "type_agreement": det_type == cls_type})
    return results


def fuse_tooth(tooth, image, deep_model):
    status = tooth["status_v2"]["prediction"]
    findings = [] if status == "HEALTHY" else (["CROWN", "ROOT_CANAL_TREATMENT"] if status == "RCT_CROWN" else [status])
    findings += [p["type"] for p in tooth["pathology_evidence"]]
    findings += [r["detector_type"] for r in tooth["restorations"]]
    findings = list(dict.fromkeys(findings))
    reasons = []
    if status == "HEALTHY" and tooth["pathology_evidence"]:
        reasons.append("STATUS_HEALTHY_CONFLICTS_WITH_PATHOLOGY")
    if status == "HEALTHY" and tooth["restorations"]:
        reasons.append("STATUS_HEALTHY_CONFLICTS_WITH_RESTORATION")
    for rest in tooth["restorations"]:
        if not rest["type_agreement"]:
            reasons.append("RESTORATION_DETECTOR_CLASSIFIER_DISAGREEMENT")
        if status == "FILLING" and rest["classifier_type"] == "IMPLANT" and rest["classifier_confidence"] >= 0.70:
            reasons.append("STATUS_FILLING_CONFLICTS_WITH_IMPLANT")
    has_caries = "CARIES" in findings
    if has_caries:
        label, confidence, probabilities = classify(
            deep_model, crop_tensor(image, tooth["tooth_detection"]["bbox_xyxy"], 0.55, 24, 256), DEEP_CARIES_CLASSES
        )
        deep_probability = probabilities["DEEP_CARIES"]
        tooth["deep_caries"] = {"ran": True, "prediction": label, "confidence": round(confidence, 6),
                                "probability": deep_probability, "threshold": 0.65,
                                "upgraded": deep_probability >= 0.65}
        if deep_probability >= 0.65:
            findings = ["DEEP_CARIES" if f == "CARIES" else f for f in findings]
    else:
        tooth["deep_caries"] = {"ran": False, "probability": None, "threshold": 0.65, "upgraded": False,
                                "reason": "NO_CARIES_EVIDENCE"}
    if any(f in EXPERIMENTAL for f in findings):
        reasons.append("EXPERIMENTAL_PATHOLOGY_FINDING")
    if tooth.get("fdi_review_required"):
        reasons.append("FDI_LOW_CONFIDENCE_OR_UNRESOLVED")
    tooth["final_findings"] = list(dict.fromkeys(findings)) or ["HEALTHY"]
    tooth["review_reasons"] = list(dict.fromkeys(reasons))
    tooth["review_required"] = bool(tooth["review_reasons"])


def checkpoint_metadata(ckpts):
    names = {
        "tooth": "Tooth V3", "fdi": "FDI V3 FIXED", "status_gate": "Tooth Status Gate V1",
        "status_v2": "Tooth Status V2", "pathology": "Pathology Detector V4.1",
        "deep_caries": "Deep Caries Specialist V2", "restoration_detector": "Restoration Detector V1",
        "restoration_classifier": "Restoration Classifier V1",
    }
    return {key: {"name": names[key], "checkpoint": str(CHECKPOINTS[key]),
                  "epoch": ckpts[key].get("epoch"), "strict_load": True}
            for key in names}


def save_preview(image, teeth, path):
    preview = image.copy(); draw = ImageDraw.Draw(preview); font = ImageFont.load_default()
    for tooth in teeth:
        x1, y1, x2, y2 = tooth["tooth_detection"]["bbox_xyxy"]
        review = " !REVIEW" if tooth["review_required"] else ""
        findings = ",".join(tooth["final_findings"])
        draw.rectangle((x1, y1, x2, y2), outline=(255, 210, 0) if review else (0, 255, 100), width=2)
        lines = [f"FDI {tooth['fdi']}{review}", findings]
        ty = max(0, y1 - 23)
        for line in lines:
            box = draw.textbbox((x1, ty), line, font=font)
            draw.rectangle(box, fill=(0, 0, 0))
            draw.text((x1, ty), line, fill=(255, 230, 80) if review else (255, 255, 255), font=font)
            ty += 11
    preview.save(path, quality=95)


@torch.inference_mode()
def run(image_path, tooth_threshold=0.50, restoration_threshold=0.50):
    image_path = Path(image_path)
    image = Image.open(image_path).convert("RGB")
    models_by_name, ckpts = load_models()
    print("Running Tooth V3...")
    output = models_by_name["tooth"]([to_tensor(image).to(DEVICE)])[0]
    teeth_for_resolver = []
    for index, (box, score) in enumerate(zip(output["boxes"].cpu(), output["scores"].cpu()), 1):
        if float(score) < tooth_threshold:
            continue
        bbox = [float(v) for v in box]
        probs = fdi_probs(models_by_name["fdi"], image, bbox)
        conf, idx = probs.max(0)
        teeth_for_resolver.append({"instance_id": index, "bbox": bbox, "probs": probs,
                                   "raw": FDI_CLASSES[int(idx)], "raw_conf": float(conf),
                                   "segmentation_confidence": float(score)})
    resolved = resolve_fdi_v3(teeth_for_resolver)
    cleanup = minimal_duplicate_cleanup(resolved)
    teeth = []
    for item in resolved:
        bbox = item["bbox"]
        gate_pred, gate_conf, gate_probs = classify(models_by_name["status_gate"], crop_tensor(image, bbox, .35, 16, 224), STATUS_GATE_CLASSES)
        nonhealthy = gate_probs["NON_HEALTHY"]
        gate_effective = "NON_HEALTHY" if nonhealthy >= .30 else "HEALTHY"
        status_pred, status_conf, status_probs = classify(models_by_name["status_v2"], crop_tensor(image, bbox, .45, 18, 256), STATUS_CLASSES)
        teeth.append({
            "tooth_detection": {"instance_id": item["instance_id"], "bbox_xyxy": [round(v, 2) for v in bbox],
                                "confidence": round(item["segmentation_confidence"], 6)},
            "fdi": item["resolved"], "fdi_confidence": round(item["raw_conf"], 6), "raw_fdi": item["raw"],
            "fdi_was_changed": bool(item["was_changed"]), "duplicate_cleanup_applied": bool(item.get("duplicate_cleanup", False)),
            "fdi_review_required": bool(item["unresolved_by_dp"] or item["raw_conf"] < .70),
            "status_gate": {"prediction": gate_pred, "effective_prediction": gate_effective,
                            "confidence": round(gate_conf, 6), "probabilities": gate_probs,
                            "non_healthy_probability": nonhealthy, "abnormal_threshold": .30},
            "status_v2": {"prediction": status_pred, "confidence": round(status_conf, 6), "probabilities": status_probs},
        })
    del output, teeth_for_resolver, resolved
    pathology = run_detector(models_by_name["pathology"], image, PATHOLOGY_CLASSES, PATHOLOGY_THRESHOLDS)
    unmatched_pathologies = attach_detections(pathology, teeth, "pathology_evidence")
    restorations = run_restorations(models_by_name["restoration_detector"], models_by_name["restoration_classifier"], image, restoration_threshold)
    unmatched_restorations = attach_detections(restorations, teeth, "restorations")
    for tooth in teeth:
        fuse_tooth(tooth, image, models_by_name["deep_caries"])
    teeth.sort(key=lambda tooth: int(tooth["fdi"]))
    duplicate_fdis = sorted(fdi for fdi, count in Counter(t["fdi"] for t in teeth).items() if count > 1)
    result = {
        "version": "dentai-unified-v5", "image": str(image_path), "device": str(DEVICE),
        "models": checkpoint_metadata(ckpts), "thresholds": {"tooth": tooth_threshold,
            "status_gate_non_healthy": .30, "pathology": PATHOLOGY_THRESHOLDS,
            "deep_caries": .65, "restoration": restoration_threshold},
        "summary": {"teeth": len(teeth), "unique_fdi": len(set(t["fdi"] for t in teeth)),
                    "duplicate_fdi": duplicate_fdis, "pathology_detections": len(pathology),
                    "restorations": len(restorations), "review_required": sum(t["review_required"] for t in teeth),
                    "resolver_duplicate_cleanup_changes": cleanup},
        "teeth": teeth, "unmatched_pathologies": unmatched_pathologies,
        "unmatched_restorations": unmatched_restorations,
    }
    out = Path("artifacts/unified"); out.mkdir(parents=True, exist_ok=True)
    json_path = out / "dentai_unified_v5.json"; preview_path = out / "dentai_unified_v5_preview.jpg"
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    save_preview(image, teeth, preview_path)
    del models_by_name; gc.collect()
    if DEVICE.type == "cuda": torch.cuda.empty_cache()
    labels = checkpoint_metadata(ckpts)
    print("=" * 60); print("DENTAI UNIFIED BRAIN V5"); print("=" * 60)
    for key, title in [("tooth", "Tooth model"), ("fdi", "FDI model")]: print(f"{title}: {labels[key]['name']}")
    print("Resolver: Conservative FDI Resolver V3 + duplicate-only V3.1 cleanup")
    for key, title in [("status_gate", "Status Gate"), ("status_v2", "Status V2"), ("pathology", "Pathology"),
                       ("deep_caries", "Deep Caries"), ("restoration_detector", "Restoration Detector"),
                       ("restoration_classifier", "Restoration Classifier")]: print(f"{title}: {labels[key]['name']}")
    print(); print("Teeth:", len(teeth)); print("Unique FDI:", len(set(t["fdi"] for t in teeth)))
    print("Pathology detections:", len(pathology)); print("Restorations:", len(restorations))
    print("Review required:", sum(t["review_required"] for t in teeth)); print("JSON:", json_path); print("Preview:", preview_path); print("=" * 60)
    for tooth in teeth:
        print(f"FDI {tooth['fdi']} | STATUS={tooth['status_v2']['prediction']} | FINDINGS={','.join(tooth['final_findings'])} | REVIEW={tooth['review_required']}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DENTAI Unified Brain V5")
    parser.add_argument("--image", required=True)
    parser.add_argument("--tooth-threshold", type=float, default=.50)
    parser.add_argument("--restoration-threshold", type=float, default=.50)
    args = parser.parse_args()
    run(args.image, args.tooth_threshold, args.restoration_threshold)
