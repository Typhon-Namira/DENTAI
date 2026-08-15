import json
from pathlib import Path
from collections import Counter

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image

CLASSES = [
    "Caries",
    "Deep Caries",
    "Impacted",
    "Periapical Lesion",
]

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


class DiseaseDataset(Dataset):
    def __init__(self, split_file, train=False):
        data = json.loads(Path(split_file).read_text())
        self.samples = []
        self.train = train

        for r in data["records"]:
            image_path = r["image_path"]

            for inst in r.get("instances", []):
                disease = inst.get("source_disease")
                bbox = inst.get("bbox_xyxy")

                if disease in CLASS_TO_IDX and bbox:
                    self.samples.append(
                        (
                            image_path,
                            bbox,
                            CLASS_TO_IDX[disease],
                            disease
                        )
                    )

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((256, 256)),
                transforms.RandomRotation(5),
                transforms.ColorJitter(
                    brightness=0.08,
                    contrast=0.10
                ),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.03, 0.03),
                    scale=(0.95, 1.05)
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((256, 256)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        image_path, bbox, label, _ = self.samples[idx]

        img = Image.open(image_path).convert("RGB")
        W, H = img.size

        x1, y1, x2, y2 = map(float, bbox)

        bw = x2 - x1
        bh = y2 - y1

        # Extra context is important for apical / root pathology.
        pad_x = max(20, int(bw * 0.70))
        pad_y = max(24, int(bh * 0.80))

        xx1 = max(0, int(x1) - pad_x)
        yy1 = max(0, int(y1) - pad_y)
        xx2 = min(W, int(x2) + pad_x)
        yy2 = min(H, int(y2) + pad_y)

        crop = img.crop((xx1, yy1, xx2, yy2))

        return self.tf(crop), label


def evaluate(model, loader, device):
    model.eval()

    correct = 0
    total = 0

    class_correct = [0] * len(CLASSES)
    class_total = [0] * len(CLASSES)

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type == "cuda",
                dtype=torch.bfloat16
            ):
                logits = model(images)

            pred = logits.argmax(1)

            correct += (pred == labels).sum().item()
            total += labels.size(0)

            for y, p in zip(labels, pred):
                yi = int(y.item())
                class_total[yi] += 1
                if y == p:
                    class_correct[yi] += 1

    acc = correct / max(total, 1)

    per_class = {}
    for i, name in enumerate(CLASSES):
        per_class[name] = (
            class_correct[i] / class_total[i]
            if class_total[i] else 0.0
        )

    return acc, per_class


def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    train_ds = DiseaseDataset(
        "data/splits/tooth_v2/train.json",
        train=True
    )

    val_ds = DiseaseDataset(
        "data/splits/tooth_v2/validation.json",
        train=False
    )

    print("====================================")
    print("DISEASE V1")
    print("Train samples:", len(train_ds))
    print("Validation samples:", len(val_ds))
    print("Device:", device)

    if device.type == "cuda":
        print("GPU:", torch.cuda.get_device_name(0))

    train_counts = Counter(
        disease
        for _, _, _, disease in train_ds.samples
    )

    print("Train distribution:")
    for c in CLASSES:
        print(c, train_counts[c])

    print("====================================")

    # Inverse-frequency weighting
    total = sum(train_counts.values())

    weights = []
    for c in CLASSES:
        n = max(train_counts[c], 1)
        weights.append(total / (len(CLASSES) * n))

    class_weights = torch.tensor(
        weights,
        dtype=torch.float32,
        device=device
    )

    print("Class weights:", class_weights.tolist())

    train_loader = DataLoader(
        train_ds,
        batch_size=64,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=96,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    model = models.resnet18(
        weights=models.ResNet18_Weights.IMAGENET1K_V1
    )

    model.fc = nn.Sequential(
        nn.Dropout(0.30),
        nn.Linear(
            model.fc.in_features,
            len(CLASSES)
        )
    )

    model = model.to(device)

    loss_fn = nn.CrossEntropyLoss(
        weight=class_weights,
        label_smoothing=0.03
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=1e-4,
        weight_decay=1e-4
    )

    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=12
    )

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda"
    )

    out = Path("checkpoints/disease_v1")
    out.mkdir(parents=True, exist_ok=True)

    best_acc = 0.0
    stale = 0
    patience = 4

    for epoch in range(12):
        model.train()

        correct = 0
        total_seen = 0
        loss_sum = 0.0

        for images, labels in train_loader:
            images = images.to(
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
                logits = model(images)
                loss = loss_fn(logits, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            loss_sum += loss.item() * labels.size(0)

            pred = logits.argmax(1)

            correct += (
                pred == labels
            ).sum().item()

            total_seen += labels.size(0)

        train_acc = correct / max(total_seen, 1)

        val_acc, per_class = evaluate(
            model,
            val_loader,
            device
        )

        scheduler.step()

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={loss_sum/len(train_ds):.4f} "
            f"train_acc={train_acc:.4f} "
            f"val_acc={val_acc:.4f}"
        )

        for name in CLASSES:
            print(
                f"  {name}: "
                f"{per_class[name]:.4f}"
            )

        torch.save(
            {
                "epoch": epoch + 1,
                "model": model.state_dict(),
                "classes": CLASSES,
                "val_acc": val_acc,
                "per_class": per_class
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
                    "classes": CLASSES,
                    "val_acc": val_acc,
                    "per_class": per_class
                },
                out / "best.pt"
            )

            print(
                "*** NEW BEST:",
                round(best_acc, 4),
                "***"
            )
        else:
            stale += 1

        if stale >= patience:
            print(
                "EARLY STOPPING | best_val_acc=",
                round(best_acc, 4)
            )
            break

    print()
    print("====================================")
    print("DISEASE V1 BEST VAL ACC:", best_acc)
    print("BEST MODEL: checkpoints/disease_v1/best.pt")
    print("====================================")


if __name__ == "__main__":
    main()
