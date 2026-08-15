import json
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image

FDI_CLASSES = [
    "11","12","13","14","15","16","17","18",
    "21","22","23","24","25","26","27","28",
    "31","32","33","34","35","36","37","38",
    "41","42","43","44","45","46","47","48"
]

CLASS_TO_IDX = {c: i for i, c in enumerate(FDI_CLASSES)}


class FDIDatasetV2(Dataset):
    def __init__(self, split_file, train=False):
        data = json.loads(Path(split_file).read_text())
        self.samples = []
        self.train = train

        for r in data["records"]:
            image_path = r["image_path"]

            for inst in r.get("instances", []):
                fdi = str(inst.get("fdi_number", "")).strip()
                bbox = inst.get("bbox_xyxy")

                if fdi in CLASS_TO_IDX and bbox:
                    self.samples.append(
                        (image_path, bbox, CLASS_TO_IDX[fdi])
                    )

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.RandomRotation(4),
                transforms.ColorJitter(
                    brightness=0.08,
                    contrast=0.08
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        image_path, bbox, label = self.samples[idx]

        img = Image.open(image_path).convert("RGB")
        W, H = img.size

        x1, y1, x2, y2 = map(float, bbox)

        # Normalized spatial information
        cx = ((x1 + x2) / 2.0) / max(W, 1)
        cy = ((y1 + y2) / 2.0) / max(H, 1)
        bw = (x2 - x1) / max(W, 1)
        bh = (y2 - y1) / max(H, 1)

        spatial = torch.tensor(
            [cx, cy, bw, bh],
            dtype=torch.float32
        )

        # Larger contextual crop than V1
        box_w = x2 - x1
        box_h = y2 - y1

        pad_x = max(12, int(box_w * 0.35))
        pad_y = max(12, int(box_h * 0.35))

        xx1 = max(0, int(x1) - pad_x)
        yy1 = max(0, int(y1) - pad_y)
        xx2 = min(W, int(x2) + pad_x)
        yy2 = min(H, int(y2) + pad_y)

        crop = img.crop((xx1, yy1, xx2, yy2))

        return self.tf(crop), spatial, label


class FDINetV2(nn.Module):
    def __init__(self):
        super().__init__()

        backbone = models.resnet18(weights=None)

        # Warm-start from best FDI V1
        v1_path = Path("checkpoints/fdi_v1/best.pt")

        if v1_path.exists():
            ckpt = torch.load(v1_path, map_location="cpu")
            backbone.fc = nn.Linear(
                backbone.fc.in_features,
                len(FDI_CLASSES)
            )
            backbone.load_state_dict(ckpt["model"])
            print(
                "Loaded FDI V1 best checkpoint:",
                v1_path,
                "val_acc=",
                ckpt.get("val_acc")
            )
        else:
            print("WARNING: FDI V1 best.pt not found")
            backbone = models.resnet18(
                weights=models.ResNet18_Weights.IMAGENET1K_V1
            )

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

        x = torch.cat([visual, spatial], dim=1)

        return self.classifier(x)


def evaluate(model, loader, device):
    model.eval()

    correct = 0
    total = 0

    with torch.no_grad():
        for images, spatial, labels in loader:

            images = images.to(device, non_blocking=True)
            spatial = spatial.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type == "cuda",
                dtype=torch.bfloat16
            ):
                logits = model(images, spatial)

            pred = logits.argmax(1)

            correct += (pred == labels).sum().item()
            total += labels.size(0)

    return correct / max(total, 1)


def main():

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    train_ds = FDIDatasetV2(
        "data/splits/tooth_v2/train.json",
        train=True
    )

    val_ds = FDIDatasetV2(
        "data/splits/tooth_v2/validation.json",
        train=False
    )

    print("====================================")
    print("FDI V2")
    print("Train samples:", len(train_ds))
    print("Validation samples:", len(val_ds))
    print("Device:", device)

    if device.type == "cuda":
        print("GPU:", torch.cuda.get_device_name(0))

    print("====================================")

    train_loader = DataLoader(
        train_ds,
        batch_size=96,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=128,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    model = FDINetV2().to(device)

    loss_fn = nn.CrossEntropyLoss(
        label_smoothing=0.05
    )

    optimizer = torch.optim.AdamW(
        [
            {
                "params": model.backbone.parameters(),
                "lr": 5e-5
            },
            {
                "params": model.spatial_net.parameters(),
                "lr": 3e-4
            },
            {
                "params": model.classifier.parameters(),
                "lr": 3e-4
            },
        ],
        weight_decay=1e-4
    )

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=10
    )

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda"
    )

    out = Path("checkpoints/fdi_v2")
    out.mkdir(parents=True, exist_ok=True)

    best_acc = 0.0
    stale = 0
    patience = 3

    for epoch in range(10):

        model.train()

        correct = 0
        total = 0
        loss_sum = 0.0

        for images, spatial, labels in train_loader:

            images = images.to(
                device,
                non_blocking=True
            )

            spatial = spatial.to(
                device,
                non_blocking=True
            )

            labels = labels.to(
                device,
                non_blocking=True
            )

            optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type == "cuda",
                dtype=torch.bfloat16
            ):
                logits = model(images, spatial)
                loss = loss_fn(logits, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            loss_sum += loss.item() * labels.size(0)

            pred = logits.argmax(1)

            correct += (
                pred == labels
            ).sum().item()

            total += labels.size(0)

        train_acc = correct / total
        val_acc = evaluate(
            model,
            val_loader,
            device
        )

        scheduler.step()

        avg_loss = loss_sum / len(train_ds)

        print(
            f"epoch={epoch+1} "
            f"loss={avg_loss:.4f} "
            f"train_acc={train_acc:.4f} "
            f"val_acc={val_acc:.4f}"
        )

        torch.save(
            {
                "epoch": epoch + 1,
                "model": model.state_dict(),
                "classes": FDI_CLASSES,
                "val_acc": val_acc
            },
            out / "latest.pt"
        )

        if val_acc > best_acc:

            best_acc = val_acc
            stale = 0

            torch.save(
                {
                    "epoch": epoch + 1,
                    "model": model.state_dict(),
                    "classes": FDI_CLASSES,
                    "val_acc": val_acc
                },
                out / "best.pt"
            )

            print(
                f"*** NEW BEST: {best_acc:.4f} ***"
            )

        else:
            stale += 1

        if stale >= patience:
            print(
                "EARLY STOPPING - "
                f"best_val_acc={best_acc:.4f}"
            )
            break

    print("====================================")
    print("FDI V2 BEST VAL ACC:", best_acc)
    print("BEST MODEL: checkpoints/fdi_v2/best.pt")
    print("====================================")


if __name__ == "__main__":
    main()
