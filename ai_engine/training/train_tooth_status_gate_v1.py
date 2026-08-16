import json
import math
from pathlib import Path
from collections import Counter

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from PIL import Image

ROOT = Path("data/canonical/dual_labeled_status")

CLASSES = ["HEALTHY", "NON_HEALTHY"]
CLASS_TO_IDX = {c:i for i,c in enumerate(CLASSES)}

class StatusGateDataset(Dataset):
    def __init__(self, split, train=False):
        self.samples = []

        d = json.loads(
            (ROOT / f"{split}.json").read_text(encoding="utf-8")
        )

        for r in d["records"]:
            for t in r["teeth"]:
                status = t["status"]

                gate = (
                    "HEALTHY"
                    if status == "HEALTHY"
                    else "NON_HEALTHY"
                )

                self.samples.append({
                    "image_path": r["image_path"],
                    "bbox": t["bbox_xyxy"],
                    "label": CLASS_TO_IDX[gate],
                    "class_name": gate,
                    "status": status,
                    "fdi": t["fdi_number"],
                })

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((224,224)),
                transforms.RandomRotation(4),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.02,0.02),
                    scale=(0.96,1.04)
                ),
                transforms.ColorJitter(
                    brightness=0.05,
                    contrast=0.08
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485,0.456,0.406],
                    [0.229,0.224,0.225]
                )
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((224,224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485,0.456,0.406],
                    [0.229,0.224,0.225]
                )
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]

        img = Image.open(
            s["image_path"]
        ).convert("RGB")

        W,H = img.size

        x1,y1,x2,y2 = map(float,s["bbox"])

        bw = max(x2-x1,1)
        bh = max(y2-y1,1)

        px = max(16,int(bw*0.35))
        py = max(16,int(bh*0.35))

        crop = img.crop((
            max(0,int(x1)-px),
            max(0,int(y1)-py),
            min(W,int(x2)+px),
            min(H,int(y2)+py),
        ))

        return self.tf(crop), s["label"]


def evaluate(model,loader,device):
    model.eval()

    correct = 0
    total = 0

    cc = [0,0]
    ct = [0,0]

    with torch.no_grad():
        for image,label in loader:
            image = image.to(device,non_blocking=True)
            label = label.to(device,non_blocking=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits = model(image)

            pred = logits.argmax(1)

            correct += (pred==label).sum().item()
            total += label.size(0)

            for y,p in zip(label,pred):
                yi = int(y.item())
                ct[yi] += 1
                cc[yi] += int(y==p)

    acc = correct/max(total,1)

    per_class = {
        CLASSES[i]:
            cc[i]/ct[i] if ct[i] else 0
        for i in range(2)
    }

    macro = sum(per_class.values())/2

    return acc,macro,per_class


def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available()
        else "cpu"
    )

    train_ds = StatusGateDataset(
        "train",
        train=True
    )

    val_ds = StatusGateDataset(
        "validation",
        train=False
    )

    counts = Counter(
        x["class_name"]
        for x in train_ds.samples
    )

    print("="*60)
    print("TOOTH STATUS GATE V1")
    print("Train:",len(train_ds))
    print("Validation:",len(val_ds))
    print("Device:",device)

    if device.type=="cuda":
        print("GPU:",torch.cuda.get_device_name(0))

    print("Distribution:")
    for c in CLASSES:
        print(c,counts[c])

    sample_weights = []

    for s in train_ds.samples:
        n = counts[s["class_name"]]

        sample_weights.append(
            math.sqrt(
                len(train_ds)/max(n,1)
            )
        )

    sampler = WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_ds),
        replacement=True
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=64,
        sampler=sampler,
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
            2
        )
    )

    model = model.to(device)

    # Slightly stronger penalty for missing abnormal teeth.
    class_weights = torch.tensor(
        [1.0,1.6],
        dtype=torch.float32,
        device=device
    )

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
        T_max=10
    )

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type=="cuda"
    )

    out = Path(
        "checkpoints/tooth_status_gate_v1"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    best = -1
    stale = 0
    patience = 3

    for epoch in range(10):
        model.train()

        correct = 0
        total = 0
        loss_sum = 0

        for image,label in train_loader:
            image = image.to(
                device,
                non_blocking=True
            )

            label = label.to(
                device,
                non_blocking=True
            )

            optimizer.zero_grad(
                set_to_none=True
            )

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits = model(image)
                loss = loss_fn(logits,label)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            pred = logits.argmax(1)

            correct += (
                pred==label
            ).sum().item()

            total += label.size(0)

            loss_sum += (
                loss.item()*label.size(0)
            )

        train_acc = correct/max(total,1)

        val_acc,macro,per_class = evaluate(
            model,
            val_loader,
            device
        )

        scheduler.step()

        score = (
            0.40*val_acc
            + 0.60*macro
        )

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={loss_sum/max(total,1):.4f} "
            f"train_acc={train_acc:.4f} "
            f"val_acc={val_acc:.4f} "
            f"macro={macro:.4f} "
            f"score={score:.4f}"
        )

        for c in CLASSES:
            print(
                f"  {c}: "
                f"{per_class[c]:.4f}"
            )

        state = {
            "epoch":epoch+1,
            "model":model.state_dict(),
            "classes":CLASSES,
            "val_acc":val_acc,
            "macro_recall":macro,
            "per_class":per_class,
            "score":score
        }

        torch.save(
            state,
            out/"latest.pt"
        )

        if score>best:
            best=score
            stale=0

            torch.save(
                state,
                out/"best.pt"
            )

            print(
                "*** NEW BEST:",
                round(best,4),
                "***"
            )
        else:
            stale+=1

        if stale>=patience:
            print("EARLY STOPPING")
            break

    print()
    print("="*60)
    print("TOOTH STATUS GATE V1 COMPLETE")
    print("BEST SCORE:",best)
    print(
        "MODEL:",
        "checkpoints/tooth_status_gate_v1/best.pt"
    )
    print("="*60)


if __name__=="__main__":
    main()
