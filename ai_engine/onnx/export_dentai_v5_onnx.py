"""Export frozen DENTAI V5 production models to FP32 ONNX."""

import hashlib
import gc
import json
import sys
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from PIL import Image
from torch import nn
from torchvision import models
from torchvision.models.detection import fasterrcnn_resnet50_fpn, maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

from ai_engine.inference import dentai_unified_v5 as v5


ONNX_DIR = Path("models/onnx/dentai_v5")
MANIFEST_PATH = Path("artifacts/production/dentai_v5_model_manifest.json")
OPSET = 18


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist() if value.numel() <= 100 else {"tensor_shape": list(value.shape)}
    if isinstance(value, Path): return str(value)
    if isinstance(value, dict): return {str(k): json_safe(v) for k, v in value.items() if k != "model"}
    if isinstance(value, (list, tuple)): return [json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    return str(value)


def load_strict(model, path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    state = checkpoint.get("model", checkpoint.get("model_state_dict", checkpoint.get("state_dict", checkpoint)))
    model.load_state_dict(state, strict=True)
    return model.eval(), checkpoint


def classifier_models():
    fdi = v5.FDINetV2()
    gate = models.resnet18(weights=None); gate.fc = nn.Sequential(nn.Dropout(.30), nn.Linear(gate.fc.in_features, 2))
    status = models.resnet34(weights=None); status.fc = nn.Sequential(nn.Dropout(.35), nn.Linear(status.fc.in_features, 7))
    deep = models.resnet34(weights=None); deep.fc = nn.Sequential(nn.Dropout(.40), nn.Linear(deep.fc.in_features, 2))
    restoration = models.resnet18(weights=None); restoration.fc = nn.Sequential(nn.Dropout(.30), nn.Linear(restoration.fc.in_features, 2))
    specs = {
        "fdi": (fdi, v5.CHECKPOINTS["fdi"], "fdi_v3.onnx", ["image", "spatial"], ["logits"]),
        "status_gate": (gate, v5.CHECKPOINTS["status_gate"], "status_gate_v1.onnx", ["image"], ["logits"]),
        "status_v2": (status, v5.CHECKPOINTS["status_v2"], "status_v2.onnx", ["image"], ["logits"]),
        "deep_caries": (deep, v5.CHECKPOINTS["deep_caries"], "deep_caries_v2.onnx", ["image"], ["logits"]),
        "restoration_classifier": (restoration, v5.CHECKPOINTS["restoration_classifier"], "restoration_classifier_v1.onnx", ["image"], ["logits"]),
    }
    return {key: (load_strict(model, path)[0], path, filename, inputs, outputs)
            for key, (model, path, filename, inputs, outputs) in specs.items()}


def real_inputs():
    status_record = json.loads(Path("data/canonical/dual_labeled_status/test.json").read_text())["records"][0]
    status_image = Image.open(status_record["image_path"]).convert("RGB")
    status_box = status_record["teeth"][0]["bbox_xyxy"]
    deep_data = json.loads(Path("data/canonical/dentai_v3_super/test.json").read_text())
    deep_record = next((r, x) for r in deep_data["records"] for x in r.get("instances", [])
                       if x.get("source_disease") in ("Caries", "Deep Caries") and x.get("bbox_xyxy"))
    deep_image = Image.open(deep_record[0]["image_path"]).convert("RGB")
    rest_data = json.loads(Path("data/canonical/akudental/git-92e2cc3/instances.json").read_text())
    rest_record = next((r, x) for r in rest_data["images"] for x in r.get("instances", [])
                       if str(x.get("canonical_class", "")).upper() in ("FILLING", "IMPLANT") and x.get("bbox_xyxy"))
    rest_image = Image.open(Path("data/raw/akudental/current/source_repo/AKUDENTAL/images") / str(rest_record[0]["source_image_id"])).convert("RGB")
    fdi_tensor = v5.crop_tensor(status_image, status_box, .35, 12, 224).cpu()
    width, height = status_image.size; x1,y1,x2,y2 = map(float,status_box)
    spatial = torch.tensor([[(x1+x2)/2/width,(y1+y2)/2/height,(x2-x1)/width,(y2-y1)/height]], dtype=torch.float32)
    return {
        "fdi": (fdi_tensor, spatial),
        "status_gate": (v5.crop_tensor(status_image,status_box,.35,16,224).cpu(),),
        "status_v2": (v5.crop_tensor(status_image,status_box,.45,18,256).cpu(),),
        "deep_caries": (v5.crop_tensor(deep_image,deep_record[1]["bbox_xyxy"],.55,24,256).cpu(),),
        "restoration_classifier": (v5.crop_tensor(rest_image,rest_record[1]["bbox_xyxy"],.45,15,224).cpu(),),
    }


def export_classifiers():
    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    inputs_by_model = real_inputs(); results = {}
    for key, (model, _, filename, input_names, output_names) in classifier_models().items():
        target = ONNX_DIR / filename; example = inputs_by_model[key]
        dynamic_axes = {name: {0: "batch"} for name in input_names}; dynamic_axes["logits"] = {0: "batch"}
        torch.onnx.export(model, example, target, export_params=True, opset_version=OPSET,
                          do_constant_folding=True, input_names=input_names, output_names=output_names,
                          dynamic_axes=dynamic_axes, dynamo=False)
        graph = onnx.load(target); onnx.checker.check_model(graph)
        session = ort.InferenceSession(str(target), providers=["CPUExecutionProvider"])
        feed = {name: tensor.numpy() for name, tensor in zip(input_names, example)}
        with torch.inference_mode(): torch_logits = model(*example).detach().numpy()
        ort_logits = session.run(None, feed)[0]
        abs_diff = np.abs(torch_logits - ort_logits)
        agreement = bool(np.array_equal(torch_logits.argmax(1), ort_logits.argmax(1)))
        if not agreement or float(abs_diff.max()) > 1e-3:
            raise RuntimeError(f"{key} parity failed: agreement={agreement}, max_abs={abs_diff.max()}")
        results[key] = {"onnx_path": str(target), "onnx_sha256": sha256(target),
                        "max_abs_logit_difference": float(abs_diff.max()),
                        "mean_abs_logit_difference": float(abs_diff.mean()), "prediction_agreement": agreement,
                        "providers": session.get_providers(), "opset": OPSET}
        print(f"PASS {key}: max_abs={abs_diff.max():.8g} mean_abs={abs_diff.mean():.8g}")
    return results


class DetectionOutputWrapper(nn.Module):
    """Stable production outputs; tooth masks are deliberately not exposed."""
    def __init__(self, model):
        super().__init__(); self.model = model

    def forward(self, image):
        output = self.model([image[0]])[0]
        return output["boxes"], output["scores"], output["labels"]


def detector_models():
    tooth = maskrcnn_resnet50_fpn(weights=None, weights_backbone=None, min_size=640, max_size=1600)
    features = tooth.roi_heads.box_predictor.cls_score.in_features
    tooth.roi_heads.box_predictor = FastRCNNPredictor(features, 2)
    mask_features = tooth.roi_heads.mask_predictor.conv5_mask.in_channels
    tooth.roi_heads.mask_predictor = MaskRCNNPredictor(mask_features, 256, 2)
    pathology = fasterrcnn_resnet50_fpn(weights=None, weights_backbone=None, min_size=640, max_size=1600)
    features = pathology.roi_heads.box_predictor.cls_score.in_features
    pathology.roi_heads.box_predictor = FastRCNNPredictor(features, 7)
    restoration = fasterrcnn_resnet50_fpn(weights=None, weights_backbone=None)
    features = restoration.roi_heads.box_predictor.cls_score.in_features
    restoration.roi_heads.box_predictor = FastRCNNPredictor(features, 3)
    return {
        "tooth": (load_strict(tooth, v5.CHECKPOINTS["tooth"])[0], "tooth_v3.onnx", (640, 1312)),
        "pathology": (load_strict(pathology, v5.CHECKPOINTS["pathology"])[0], "pathology_v41.onnx", (640, 1312)),
        "restoration_detector": (load_strict(restoration, v5.CHECKPOINTS["restoration_detector"])[0], "restoration_detector_v1.onnx", (650, 1333)),
    }


def export_detectors():
    """Export fixed-shape detector graphs. Runtime must use aspect-preserving letterbox."""
    results = {}
    for key, (model, filename, shape) in detector_models().items():
        wrapper = DetectionOutputWrapper(model).eval(); target = ONNX_DIR / filename
        example = torch.zeros((1, 3, shape[0], shape[1]), dtype=torch.float32)
        print(f"Exporting {key} at fixed input {tuple(example.shape)} ...")
        torch.onnx.export(wrapper, (example,), target, export_params=True, opset_version=OPSET,
                          do_constant_folding=True, input_names=["image"],
                          output_names=["boxes", "scores", "labels"], dynamo=False)
        graph = onnx.load(target); onnx.checker.check_model(graph)
        session = ort.InferenceSession(str(target), providers=["CPUExecutionProvider"])
        outputs = session.run(None, {"image": example.numpy()})
        if len(outputs) != 3 or outputs[0].ndim != 2 or outputs[0].shape[1] != 4:
            raise RuntimeError(f"{key} invalid runtime outputs: {[x.shape for x in outputs]}")
        results[key] = {"onnx_path": str(target), "onnx_sha256": sha256(target),
                        "fixed_input_shape": list(example.shape), "outputs": ["boxes", "scores", "labels"],
                        "preprocessing_contract": "aspect-preserving resize then zero letterbox; coordinates mapped back by subtracting padding and dividing scale",
                        "providers": session.get_providers(), "opset": OPSET}
        print(f"PASS {key}: ORT shapes {[x.shape for x in outputs]}")
        del session, wrapper, model; gc.collect()
    return results


def create_manifest(exports=None):
    architectures = {
        "tooth": ("Mask R-CNN ResNet-50 FPN; 2 classes; min_size=640 max_size=1600", "variable RGB panorama", "boxes, labels, scores (masks unused downstream)", ["BACKGROUND", "TOOTH"]),
        "fdi": ("FDINetV2: ResNet-18 visual backbone + 4D spatial MLP", "N x 3 x 224 x 224 plus N x 4", "32-class FDI logits", v5.FDI_CLASSES),
        "status_gate": ("ResNet-18; Dropout(0.30)+Linear(2)", "N x 3 x 224 x 224", "HEALTHY/NON_HEALTHY logits", v5.STATUS_GATE_CLASSES),
        "status_v2": ("ResNet-34; Dropout(0.35)+Linear(7)", "N x 3 x 256 x 256", "7-class status logits", v5.STATUS_CLASSES),
        "pathology": ("Faster R-CNN ResNet-50 FPN; 7 classes; min_size=640 max_size=1600", "variable RGB panorama", "boxes, labels, scores", ["BACKGROUND", *v5.PATHOLOGY_THRESHOLDS]),
        "deep_caries": ("ResNet-34; Dropout(0.40)+Linear(2)", "N x 3 x 256 x 256", "CARIES/DEEP_CARIES logits", v5.DEEP_CARIES_CLASSES),
        "restoration_detector": ("Faster R-CNN ResNet-50 FPN; 3 classes", "variable RGB panorama", "boxes, labels, scores", ["BACKGROUND", "FILLING", "IMPLANT"]),
        "restoration_classifier": ("ResNet-18; Dropout(0.30)+Linear(2)", "N x 3 x 224 x 224", "FILLING/IMPLANT logits", ["FILLING", "IMPLANT"]),
    }
    preprocessing = {
        "tooth": "PIL RGB -> float32 CHW [0,1]; torchvision detector transform resizes min=640 max=1600 and normalizes ImageNet",
        "fdi": "bbox padding max(12,35% width/height), Resize 224x224, ToTensor, ImageNet normalize; spatial=(cx/W,cy/H,bw/W,bh/H)",
        "status_gate": "bbox padding max(16,35%), Resize 224x224, ToTensor, ImageNet normalize",
        "status_v2": "bbox padding max(18,45%), Resize 256x256, ToTensor, ImageNet normalize",
        "pathology": "PIL RGB -> float32 CHW [0,1]; torchvision detector transform resizes min=640 max=1600 and normalizes ImageNet",
        "deep_caries": "bbox padding max(24,55%), Resize 256x256, ToTensor, ImageNet normalize",
        "restoration_detector": "PIL RGB -> float32 CHW [0,1]; torchvision detector transform and ImageNet normalization",
        "restoration_classifier": "bbox padding max(15,45%), Resize 224x224, ToTensor, ImageNet normalize",
    }
    models_manifest = {}
    for key, path in v5.CHECKPOINTS.items():
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        architecture, shape, output, classes = architectures[key]
        models_manifest[key] = {"checkpoint": str(path), "checkpoint_sha256": sha256(path),
            "architecture": architecture, "input_shape": shape, "preprocessing": preprocessing[key],
            "output_meaning": output, "class_mapping": classes, "checkpoint_epoch": ckpt.get("epoch"),
            "checkpoint_metric_metadata": json_safe(ckpt), "onnx_export": (exports or {}).get(key)}
    manifest = {"model_version": "dentai-unified-v5", "freeze_status": "PRODUCTION_FROZEN",
        "reference_engine": "ai_engine/inference/dentai_unified_v5.py", "opset": OPSET,
        "thresholds": {"tooth": .5, "status_gate_non_healthy": .30, "pathology": v5.PATHOLOGY_THRESHOLDS,
                       "deep_caries": .65, "restoration": .5}, "models": models_manifest}
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    print("Manifest:", MANIFEST_PATH)
    return manifest


def main():
    if "--detectors" in sys.argv:
        exports = export_detectors()
        existing = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else None
        if existing:
            for key, value in exports.items(): existing["models"][key]["onnx_export"] = value
            MANIFEST_PATH.write_text(json.dumps(existing, indent=2, allow_nan=False), encoding="utf-8")
            print("Manifest updated:", MANIFEST_PATH)
        return
    exports = export_classifiers()
    create_manifest(exports)


if __name__ == "__main__": main()
