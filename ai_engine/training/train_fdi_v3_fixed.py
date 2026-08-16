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
    "checkpoints/fdi_v3_fixed"
)

OUT.mkdir(parents=True, exist_ok=True)

FDI_CLASSES = [
    str(q*10+n)
    for q in range(1,5)
    for n in range(1,9)
]

CLASS_TO_IDX = {
    c:i for i,c in enumerate(FDI_CLASSES)
}


class FDIV3Dataset(Dataset):
    def __init__(self, split, train=False):
        d = json.loads(
            (ROOT / f"{split}.json").read_text(
                encoding="utf-8"
            )
        )

        self.samples = []

        for r in d["records"]:
            image_path = r.get("image_path")

            if not image_path:
                continue

            for x in r.get("instances", []):
                if x.get("canonical_class") != "TOOTH":
                    continue

                fdi = str(
                    x.get("fdi_number", "")
                ).strip()

                if fdi not in CLASS_TO_IDX:
                    continue

                bbox = x.get("bbox_xyxy")

                if not bbox or len(bbox) != 4:
                    continue

                self.samples.append({
                    "image_path": image_path,
                    "bbox": bbox,
                    "fdi": fdi,
                    "label": CLASS_TO_IDX[fdi],
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
                    brightness=0.04,
                    contrast=0.06
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

        x1,y1,x2,y2 = map(
            float,
            s["bbox"]
        )

        box_w = x2-x1
        box_h = y2-y1

        pad_x = max(
            12,
            int(box_w*0.35)
        )

        pad_y = max(
            12,
            int(box_h*0.35)
        )

        xx1 = max(
            0,
            int(x1)-pad_x
        )

        yy1 = max(
            0,
            int(y1)-pad_y
        )

        xx2 = min(
            W,
            int(x2)+pad_x
        )

        yy2 = min(
            H,
            int(y2)+pad_y
        )

        crop = img.crop(
            (xx1,yy1,xx2,yy2)
        )

        # Exact V2-style spatial features.
        cx = ((x1+x2)/2.0)/max(W,1)
        cy = ((y1+y2)/2.0)/max(H,1)
        bw = box_w/max(W,1)
        bh = box_h/max(H,1)

        spatial = torch.tensor(
            [cx,cy,bw,bh],
            dtype=torch.float32
        )

        return (
            self.tf(crop),
            spatial,
            s["label"]
        )


class FDINetV2(nn.Module):
    def __init__(self):
        super().__init__()

        backbone = models.resnet18(
            weights=None
        )

        feature_dim = backbone.fc.in_features

        backbone.fc = nn.Identity()

        self.backbone = backbone

        self.spatial_net = nn.Sequential(
            nn.Linear(4,32),
            nn.ReLU(),
            nn.Linear(32,32),
            nn.ReLU()
        )

        self.classifier = nn.Sequential(
            nn.Linear(
                feature_dim+32,
                256
            ),
            nn.ReLU(),
            nn.Dropout(0.30),
            nn.Linear(
                256,
                len(FDI_CLASSES)
            )
        )

    def forward(self,image,spatial):
        visual = self.backbone(image)
        spatial = self.spatial_net(spatial)

        x = torch.cat(
            [visual,spatial],
            dim=1
        )

        return self.classifier(x)


def evaluate(model,loader,device):
    model.eval()

    correct = 0
    total = 0

    cc = Counter()
    ct = Counter()

    with torch.no_grad():
        for images,spatial,labels in loader:
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

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits = model(
                    images,
                    spatial
                )

            pred = logits.argmax(1)

            correct += (
                pred==labels
            ).sum().item()

            total += labels.size(0)

            for y,p in zip(labels,pred):
                yi = int(y)
                ct[yi] += 1
                cc[yi] += int(y==p)

    acc = correct/max(total,1)

    recalls = []

    for i in range(
        len(FDI_CLASSES)
    ):
        r = (
            cc[i]/ct[i]
            if ct[i]
            else 0
        )

        recalls.append(r)

    macro = (
        sum(recalls)
        / len(recalls)
    )

    return acc,macro,recalls


def main():
    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    train_ds = FDIV3Dataset(
        "train",
        train=True
    )

    val_ds = FDIV3Dataset(
        "validation",
        train=False
    )

    counts = Counter(
        s["fdi"]
        for s in train_ds.samples
    )

    print("="*72)
    print("FDI V3 FIXED — EXACT V2 ARCHITECTURE")
    print("="*72)

    print(
        "Train samples:",
        len(train_ds)
    )

    print(
        "Validation samples:",
        len(val_ds)
    )

    print(
        "Device:",
        device
    )

    if device.type=="cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    model = FDINetV2()

    ckpt = torch.load(
        OLD_CKPT,
        map_location="cpu",
        weights_only=False
    )

    model.load_state_dict(
        ckpt["model"],
        strict=True
    )

    print()
    print(
        "✓ FDI V2 checkpoint loaded STRICTLY"
    )
    print(
        "V2 epoch:",
        ckpt.get("epoch")
    )
    print(
        "V2 val_acc:",
        ckpt.get("val_acc")
    )

    model.to(device)

    val_loader = DataLoader(
        val_ds,
        batch_size=128,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    # ------------------------------------------------
    # BASELINE BEFORE TRAINING
    # ------------------------------------------------

    baseline_acc,baseline_macro,_ = evaluate(
        model,
        val_loader,
        device
    )

    print()
    print("="*72)
    print("FDI V2 BASELINE ON V3 VALIDATION")
    print("="*72)

    print(
        "Baseline val_acc:",
        round(baseline_acc,4)
    )

    print(
        "Baseline macro_recall:",
        round(baseline_macro,4)
    )

    # Fail-safe:
    # if preprocessing is still wrong,
    # do NOT destroy time with training.
    if baseline_acc < 0.65:
        raise RuntimeError(
            "Baseline too low. Stop: dataset/preprocessing "
            "is inconsistent with FDI V2."
        )

    sample_weights = []

    max_count = max(
        counts.values()
    )

    for s in train_ds.samples:
        n = counts[s["fdi"]]

        sample_weights.append(
            (
                max_count
                / max(n,1)
            )**0.25
        )

    sampler = WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_ds),
        replacement=True
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=96,
        sampler=sampler,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    loss_fn = nn.CrossEntropyLoss(
        label_smoothing=0.01
    )

    optimizer = torch.optim.AdamW(
        [
            {
                "params":
                    model.backbone.parameters(),
                "lr":1.5e-5
            },
            {
                "params":
                    model.spatial_net.parameters(),
                "lr":3e-5
            },
            {
                "params":
                    model.classifier.parameters(),
                "lr":3e-5
            },
        ],
        weight_decay=1e-4
    )

    scheduler = (
        torch.optim.lr_scheduler
        .CosineAnnealingLR(
            optimizer,
            T_max=5
        )
    )

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type=="cuda"
    )

    # Preserve original baseline as candidate.
    best_score = (
        0.70*baseline_acc
        + 0.30*baseline_macro
    )

    baseline_state = {
        "epoch":0,
        "model":model.state_dict(),
        "classes":FDI_CLASSES,
        "val_acc":baseline_acc,
        "macro_recall":baseline_macro,
        "score":best_score,
        "source":
            str(OLD_CKPT)
    }

    torch.save(
        baseline_state,
        OUT/"best.pt"
    )

    stale=0
    patience=2

    for epoch in range(5):
        model.train()

        correct=0
        total=0
        loss_sum=0

        for images,spatial,labels in train_loader:

            images=images.to(
                device,
                non_blocking=True
            )

            spatial=spatial.to(
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
                logits=model(
                    images,
                    spatial
                )

                loss=loss_fn(
                    logits,
                    labels
                )

            scaler.scale(
                loss
            ).backward()

            scaler.step(
                optimizer
            )

            scaler.update()

            pred=logits.argmax(1)

            correct += (
                pred==labels
            ).sum().item()

            total += labels.size(0)

            loss_sum += (
                loss.item()
                * labels.size(0)
            )

        scheduler.step()

        val_acc,macro,_ = evaluate(
            model,
            val_loader,
            device
        )

        score = (
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
            "source":
                str(OLD_CKPT)
        }

        torch.save(
            state,
            OUT/"latest.pt"
        )

        if score>best_score:
            best_score=score
            stale=0

            torch.save(
                state,
                OUT/"best.pt"
            )

            print(
                "*** NEW BEST:",
                round(best_score,4),
                "***"
            )

        else:
            stale+=1

        if stale>=patience:
            print(
                "EARLY STOPPING"
            )
            break

    best=torch.load(
        OUT/"best.pt",
        map_location="cpu",
        weights_only=False
    )

    print()
    print("="*72)
    print("FDI V3 FIXED COMPLETE")
    print("="*72)

    print(
        "BEST EPOCH:",
        best["epoch"]
    )

    print(
        "BEST VAL ACC:",
        best["val_acc"]
    )

    print(
        "BEST MACRO:",
        best["macro_recall"]
    )

    print(
        "MODEL:",
        OUT/"best.pt"
    )

    print("="*72)


if __name__=="__main__":
    main()
