import json
from pathlib import Path
import argparse

import torch
from torch import nn
from PIL import Image, ImageDraw
from torchvision import models, transforms
from torchvision.transforms.functional import to_tensor


FDI_CLASSES = [
    "11","12","13","14","15","16","17","18",
    "21","22","23","24","25","26","27","28",
    "31","32","33","34","35","36","37","38",
    "41","42","43","44","45","46","47","48"
]


class FDINetV2(nn.Module):
    def __init__(self):
        super().__init__()

        backbone = models.resnet18(weights=None)
        feature_dim = backbone.fc.in_features
        backbone.fc = nn.Identity()

        self.backbone = backbone

        self.spatial_net = nn.Sequential(
            nn.Linear(4, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU()
        )

        self.classifier = nn.Sequential(
            nn.Linear(feature_dim + 32, 256),
            nn.ReLU(),
            nn.Dropout(0.30),
            nn.Linear(256, len(FDI_CLASSES))
        )

    def forward(self, image, spatial):
        visual = self.backbone(image)
        spatial = self.spatial_net(spatial)
        return self.classifier(torch.cat([visual, spatial], dim=1))


def load_segmentation(device):
    from torchvision.models.detection import maskrcnn_resnet50_fpn

    path = Path("checkpoints/tooth_v2/maskrcnn_fpn_v1/best.pt")

    if not path.exists():
        raise FileNotFoundError(path)

    ckpt = torch.load(path, map_location="cpu")

    state = ckpt.get("model", ckpt)

    model = maskrcnn_resnet50_fpn(
        weights=None,
        weights_backbone=None,
        num_classes=2
    )

    model.load_state_dict(state, strict=True)
    model.to(device).eval()

    print("Loaded Tooth V2:", path)

    return model


def load_fdi(device):
    candidates = [
        Path("checkpoints/fdi_v2_final/fdi_v2_best_90_38.pt"),
        Path("checkpoints/fdi_v2/best.pt"),
    ]

    path = next((p for p in candidates if p.exists()), None)

    if path is None:
        raise FileNotFoundError("FDI V2 checkpoint not found")

    ckpt = torch.load(path, map_location="cpu")

    model = FDINetV2()
    model.load_state_dict(ckpt["model"], strict=True)
    model.to(device).eval()

    print(
        "Loaded FDI V2:",
        path,
        "val_acc=",
        ckpt.get("val_acc")
    )

    return model


FDI_TF = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])


def classify_fdi(model, image, box, device):
    W, H = image.size

    x1, y1, x2, y2 = [float(v) for v in box]

    cx = ((x1 + x2) / 2) / max(W, 1)
    cy = ((y1 + y2) / 2) / max(H, 1)
    bw = (x2 - x1) / max(W, 1)
    bh = (y2 - y1) / max(H, 1)

    spatial = torch.tensor(
        [[cx, cy, bw, bh]],
        dtype=torch.float32,
        device=device
    )

    pad_x = max(12, int((x2 - x1) * 0.35))
    pad_y = max(12, int((y2 - y1) * 0.35))

    xx1 = max(0, int(x1) - pad_x)
    yy1 = max(0, int(y1) - pad_y)
    xx2 = min(W, int(x2) + pad_x)
    yy2 = min(H, int(y2) + pad_y)

    crop = image.crop((xx1, yy1, xx2, yy2))
    tensor = FDI_TF(crop).unsqueeze(0).to(device)

    with torch.no_grad():
        with torch.amp.autocast(
            "cuda",
            enabled=device.type == "cuda",
            dtype=torch.bfloat16
        ):
            logits = model(tensor, spatial)

        probs = torch.softmax(logits.float(), dim=1)
        confidence, idx = probs.max(dim=1)

    return FDI_CLASSES[idx.item()], confidence.item()


def run(image_path, threshold=0.50):
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    if device.type == "cuda":
        print("GPU:", torch.cuda.get_device_name(0))

    seg_model = load_segmentation(device)
    fdi_model = load_fdi(device)

    image = Image.open(image_path).convert("RGB")
    image_tensor = to_tensor(image).to(device)

    print("Running Tooth V2 segmentation...")

    with torch.no_grad():
        prediction = seg_model([image_tensor])[0]

    boxes = prediction["boxes"].detach().cpu()
    scores = prediction["scores"].detach().cpu()

    keep = scores >= threshold

    boxes = boxes[keep]
    scores = scores[keep]

    print("Detected teeth:", len(boxes))

    results = []

    for i, (box, score) in enumerate(zip(boxes, scores), start=1):
        fdi, fdi_conf = classify_fdi(
            fdi_model,
            image,
            box.tolist(),
            device
        )

        results.append({
            "instance_id": i,
            "bbox_xyxy": [round(float(x), 2) for x in box],
            "segmentation_confidence": round(float(score), 4),
            "fdi_number": fdi,
            "fdi_confidence": round(float(fdi_conf), 4),
        })

    # Sort approximately by FDI number for readable output
    results.sort(key=lambda x: int(x["fdi_number"]))

    output = {
        "image": str(image_path),
        "device": str(device),
        "detected_teeth": len(results),
        "teeth": results,
    }

    out_dir = Path("artifacts/inference")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "tooth_fdi_result.json"

    json_path.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8"
    )

    # Annotated preview
    preview = image.copy()
    draw = ImageDraw.Draw(preview)

    for tooth in results:
        x1, y1, x2, y2 = tooth["bbox_xyxy"]
        label = (
            f'{tooth["fdi_number"]} '
            f'({tooth["fdi_confidence"]:.2f})'
        )

        draw.rectangle(
            [x1, y1, x2, y2],
            width=3
        )

        draw.text(
            (x1, max(0, y1 - 14)),
            label
        )

    preview_path = out_dir / "tooth_fdi_preview.jpg"
    preview.save(preview_path, quality=95)

    print()
    print("========================================")
    print("TOOTH + FDI PIPELINE COMPLETE")
    print("Detected teeth:", len(results))
    print("JSON:", json_path)
    print("Preview:", preview_path)
    print("========================================")

    print()
    for tooth in results:
        print(
            f'FDI {tooth["fdi_number"]} | '
            f'FDI conf={tooth["fdi_confidence"]:.3f} | '
            f'SEG conf={tooth["segmentation_confidence"]:.3f}'
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        required=True
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.50
    )

    args = parser.parse_args()

    run(args.image, args.threshold)
