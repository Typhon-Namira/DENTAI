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

CLASS_TO_IDX = {c:i for i,c in enumerate(FDI_CLASSES)}

class FDIDataset(Dataset):
    def __init__(self, split_file):
        data = json.loads(Path(split_file).read_text())
        self.samples = []

        for r in data["records"]:
            image_path = r["image_path"]

            for inst in r.get("instances", []):
                fdi = str(inst.get("fdi_number", "")).strip()
                bbox = inst.get("bbox_xyxy")

                if fdi in CLASS_TO_IDX and bbox:
                    self.samples.append(
                        (image_path, bbox, CLASS_TO_IDX[fdi])
                    )

        self.tf = transforms.Compose([
            transforms.Resize((224,224)),
            transforms.RandomRotation(5),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485,0.456,0.406],
                std=[0.229,0.224,0.225]
            ),
        ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        image_path, bbox, label = self.samples[idx]

        img = Image.open(image_path).convert("RGB")

        x1,y1,x2,y2 = map(int, bbox)

        pad = 12
        x1 = max(0, x1-pad)
        y1 = max(0, y1-pad)
        x2 = min(img.width, x2+pad)
        y2 = min(img.height, y2+pad)

        crop = img.crop((x1,y1,x2,y2))

        return self.tf(crop), label

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_ds = FDIDataset("data/splits/tooth_v2/train.json")
    val_ds = FDIDataset("data/splits/tooth_v2/validation.json")

    print("Train samples:", len(train_ds))
    print("Validation samples:", len(val_ds))
    print("Device:", device)

    train_loader = DataLoader(
        train_ds,
        batch_size=64,
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=64,
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )

    model = models.resnet18(
        weights=models.ResNet18_Weights.IMAGENET1K_V1
    )

    model.fc = nn.Linear(model.fc.in_features, len(FDI_CLASSES))
    model = model.to(device)

    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=1e-4,
        weight_decay=1e-4
    )

    scaler = torch.amp.GradScaler("cuda", enabled=device.type=="cuda")

    out = Path("checkpoints/fdi_v1")
    out.mkdir(parents=True, exist_ok=True)

    best_acc = 0.0

    for epoch in range(12):

        model.train()
        correct = 0
        total = 0
        running_loss = 0.0

        for images, labels in train_loader:

            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits = model(images)
                loss = loss_fn(logits, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * images.size(0)

            pred = logits.argmax(1)
            correct += (pred == labels).sum().item()
            total += labels.size(0)

        train_acc = correct / total

        model.eval()
        correct = 0
        total = 0

        with torch.no_grad():
            for images, labels in val_loader:

                images = images.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)

                logits = model(images)
                pred = logits.argmax(1)

                correct += (pred == labels).sum().item()
                total += labels.size(0)

        val_acc = correct / total

        print(
            f"epoch={epoch+1} "
            f"loss={running_loss/len(train_ds):.4f} "
            f"train_acc={train_acc:.4f} "
            f"val_acc={val_acc:.4f}"
        )

        torch.save(
            {
                "epoch": epoch+1,
                "model": model.state_dict(),
                "classes": FDI_CLASSES,
                "val_acc": val_acc
            },
            out / "latest.pt"
        )

        if val_acc > best_acc:
            best_acc = val_acc

            torch.save(
                {
                    "epoch": epoch+1,
                    "model": model.state_dict(),
                    "classes": FDI_CLASSES,
                    "val_acc": val_acc
                },
                out / "best.pt"
            )

    print("BEST VAL ACC:", best_acc)

if __name__ == "__main__":
    main()
