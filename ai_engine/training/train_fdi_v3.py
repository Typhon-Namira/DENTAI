import json
from pathlib import Path
from collections import Counter

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from PIL import Image

ROOT = Path("data/canonical/dentai_v3_super")

OLD_CKPT = Path(
    "checkpoints/fdi_v2_final/fdi_v2_best_90_38.pt"
)

OUT = Path(
    "checkpoints/fdi_v3"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)

FDI_CLASSES = [
    str(q*10+n)
    for q in range(1,5)
    for n in range(1,9)
]

CLASS_TO_IDX = {
    c:i for i,c in enumerate(FDI_CLASSES)
}


class FDIDataset(Dataset):
    def __init__(self, split, train=False):
        d = json.loads(
            (ROOT / f"{split}.json").read_text(
                encoding="utf-8"
            )
        )

        self.samples = []

        for r in d["records"]:
            for x in r.get("instances", []):
                if x.get("canonical_class") != "TOOTH":
                    continue

                fdi = str(
                    x.get("fdi_number", "")
                ).strip()

                if fdi not in CLASS_TO_IDX:
                    continue

                bbox = x.get("bbox_xyxy")

                if not bbox:
                    continue

                self.samples.append({
                    "image_path": r["image_path"],
                    "bbox": bbox,
                    "fdi": fdi,
                    "label": CLASS_TO_IDX[fdi],
                })

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((224,224)),
                transforms.RandomRotation(5),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.025,0.025),
                    scale=(0.95,1.05)
                ),
                transforms.ColorJitter(
                    brightness=0.04,
                    contrast=0.08
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485,0.456,0.406],
                    [0.229,0.224,0.225]
                ),
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((224,224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485,0.456,0.406],
                    [0.229,0.224,0.225]
                ),
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

        px = max(16,int(bw*0.28))
        py = max(16,int(bh*0.28))

        crop = img.crop((
            max(0,int(x1)-px),
            max(0,int(y1)-py),
            min(W,int(x2)+px),
            min(H,int(y2)+py),
        ))

        return self.tf(crop), s["label"]


def evaluate(model, loader, device):
    model.eval()

    correct = 0
    total = 0

    cc = Counter()
    ct = Counter()

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(
                device,
                non_blocking=True
            )

            labels = labels.to(
                device,
                non_blocking=True
            )

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits = model(images)

            pred = logits.argmax(1)

            correct += (
                pred == labels
            ).sum().item()

            total += labels.size(0)

            for y,p in zip(labels,pred):
                yi = int(y)
                ct[yi] += 1
                cc[yi] += int(y==p)

    acc = correct/max(total,1)

    recalls = []

    for i in range(len(FDI_CLASSES)):
        r = (
            cc[i]/ct[i]
            if ct[i] else 0
        )
        recalls.append(r)

    macro = sum(recalls)/len(recalls)

    return acc, macro, recalls


def extract_state(ckpt):
    if not isinstance(ckpt,dict):
        return ckpt

    for key in [
        "model",
        "model_state_dict",
        "state_dict"
    ]:
        if key in ckpt and isinstance(ckpt[key],dict):
            return ckpt[key]

    return ckpt


def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available()
        else "cpu"
    )

    train_ds = FDIDataset(
        "train",
        train=True
    )

    val_ds = FDIDataset(
        "validation",
        train=False
    )

    counts = Counter(
        s["fdi"]
        for s in train_ds.samples
    )

    print("="*72)
    print("FDI V3 — WARM START")
    print("="*72)

    print("Train samples:",len(train_ds))
    print("Validation samples:",len(val_ds))
    print("Device:",device)

    if device.type=="cuda":
        print("GPU:",torch.cuda.get_device_name(0))

    print("\nDistribution:")
    for c in FDI_CLASSES:
        print(c,counts[c])

    sample_weights=[]

    max_count=max(counts.values())

    for s in train_ds.samples:
        n=counts[s["fdi"]]

        sample_weights.append(
            (max_count/max(n,1))**0.35
        )

    sampler=WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_ds),
        replacement=True
    )

    train_loader=DataLoader(
        train_ds,
        batch_size=96,
        sampler=sampler,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    val_loader=DataLoader(
        val_ds,
        batch_size=128,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    model=models.resnet18(
        weights=None
    )

    model.fc=nn.Linear(
        model.fc.in_features,
        len(FDI_CLASSES)
    )

    old=torch.load(
        OLD_CKPT,
        map_location="cpu",
        weights_only=False
    )

    state=extract_state(old)

    result=model.load_state_dict(
        state,
        strict=False
    )

    print(
        "\n✓ Warm-started from FDI V2"
    )

    print(
        "Missing keys:",
        len(result.missing_keys)
    )

    print(
        "Unexpected keys:",
        len(result.unexpected_keys)
    )

    model.to(device)

    loss_fn=nn.CrossEntropyLoss(
        label_smoothing=0.02
    )

    optimizer=torch.optim.AdamW(
        model.parameters(),
        lr=4e-5,
        weight_decay=1e-4
    )

    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=6
    )

    scaler=torch.amp.GradScaler(
        "cuda",
        enabled=device.type=="cuda"
    )

    best=-1
    stale=0
    patience=2

    for epoch in range(6):

        model.train()

        total=0
        correct=0
        loss_sum=0

        for images,labels in train_loader:
            images=images.to(
                device,
                non_blocking=True
            )

            labels=labels.to(
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
                logits=model(images)
                loss=loss_fn(
                    logits,
                    labels
                )

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            pred=logits.argmax(1)

            correct += (
                pred==labels
            ).sum().item()

            total += labels.size(0)
            loss_sum += loss.item()*labels.size(0)

        scheduler.step()

        val_acc,macro,recalls=evaluate(
            model,
            val_loader,
            device
        )

        score=(
            0.70*val_acc
            + 0.30*macro
        )

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={loss_sum/max(total,1):.4f} "
            f"train_acc={correct/max(total,1):.4f} "
            f"val_acc={val_acc:.4f} "
            f"macro_recall={macro:.4f} "
            f"score={score:.4f}"
        )

        state={
            "epoch":epoch+1,
            "model":model.state_dict(),
            "classes":FDI_CLASSES,
            "val_acc":val_acc,
            "macro_recall":macro,
            "score":score,
        }

        torch.save(
            state,
            OUT/"latest.pt"
        )

        if score>best:
            best=score
            stale=0

            torch.save(
                state,
                OUT/"best.pt"
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
    print("="*72)
    print("FDI V3 COMPLETE")
    print("BEST SCORE:",best)
    print(
        "MODEL:",
        OUT/"best.pt"
    )
    print("="*72)


if __name__=="__main__":
    main()
