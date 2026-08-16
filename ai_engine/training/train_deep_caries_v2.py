import json
import math
from pathlib import Path
from collections import Counter

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from PIL import Image

ROOT = Path("data/splits/tooth_v2")

CLASSES = ["CARIES", "DEEP_CARIES"]
CLASS_TO_IDX = {
    "Caries": 0,
    "Deep Caries": 1,
}


class DeepCariesDataset(Dataset):
    def __init__(self, split, train=False):
        self.samples = []

        p = ROOT / f"{split}.json"
        d = json.loads(p.read_text(encoding="utf-8"))

        for r in d["records"]:
            image_path = r.get("image_path")

            if not image_path:
                continue

            for x in r.get("instances", []):
                disease = x.get("source_disease")

                if disease not in CLASS_TO_IDX:
                    continue

                bbox = x.get("bbox_xyxy")

                if not bbox:
                    continue

                self.samples.append({
                    "image_path": image_path,
                    "bbox": bbox,
                    "label": CLASS_TO_IDX[disease],
                    "disease": disease,
                })

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((256, 256)),

                transforms.RandomRotation(7),

                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.03, 0.03),
                    scale=(0.90, 1.10),
                ),

                transforms.ColorJitter(
                    brightness=0.08,
                    contrast=0.12,
                ),

                transforms.RandomHorizontalFlip(
                    p=0.15
                ),

                transforms.ToTensor(),

                transforms.Normalize(
                    [0.485, 0.456, 0.406],
                    [0.229, 0.224, 0.225],
                ),
            ])

        else:
            self.tf = transforms.Compose([
                transforms.Resize((256, 256)),

                transforms.ToTensor(),

                transforms.Normalize(
                    [0.485, 0.456, 0.406],
                    [0.229, 0.224, 0.225],
                ),
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]

        image = Image.open(
            s["image_path"]
        ).convert("RGB")

        W, H = image.size

        x1, y1, x2, y2 = map(
            float,
            s["bbox"]
        )

        bw = max(x2-x1, 1)
        bh = max(y2-y1, 1)

        # Wider context is useful for deep caries.
        px = max(24, int(bw * 0.55))
        py = max(24, int(bh * 0.55))

        crop = image.crop((
            max(0, int(x1)-px),
            max(0, int(y1)-py),
            min(W, int(x2)+px),
            min(H, int(y2)+py),
        ))

        return (
            self.tf(crop),
            s["label"]
        )


class FocalLoss(nn.Module):
    def __init__(
        self,
        alpha=None,
        gamma=2.0,
    ):
        super().__init__()

        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits, target):
        ce = nn.functional.cross_entropy(
            logits,
            target,
            reduction="none",
            weight=self.alpha,
        )

        pt = torch.exp(-ce)

        loss = (
            (1-pt) ** self.gamma
        ) * ce

        return loss.mean()


def evaluate(
    model,
    loader,
    device,
    threshold=0.50,
):
    model.eval()

    tp = tn = fp = fn = 0

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
                enabled=device.type == "cuda",
                dtype=torch.bfloat16
            ):
                logits = model(images)

            probs = torch.softmax(
                logits.float(),
                dim=1
            )[:, 1]

            preds = (
                probs >= threshold
            ).long()

            tp += int(
                (
                    (preds == 1)
                    & (labels == 1)
                ).sum()
            )

            tn += int(
                (
                    (preds == 0)
                    & (labels == 0)
                ).sum()
            )

            fp += int(
                (
                    (preds == 1)
                    & (labels == 0)
                ).sum()
            )

            fn += int(
                (
                    (preds == 0)
                    & (labels == 1)
                ).sum()
            )

    deep_recall = tp / max(tp+fn, 1)
    caries_recall = tn / max(tn+fp, 1)

    deep_precision = tp / max(tp+fp, 1)

    deep_f1 = (
        2 * deep_precision * deep_recall
        / max(
            deep_precision + deep_recall,
            1e-8
        )
    )

    balanced_acc = (
        deep_recall + caries_recall
    ) / 2

    accuracy = (
        tp + tn
    ) / max(
        tp + tn + fp + fn,
        1
    )

    return {
        "accuracy": accuracy,
        "balanced_acc": balanced_acc,
        "deep_recall": deep_recall,
        "deep_precision": deep_precision,
        "deep_f1": deep_f1,
        "caries_recall": caries_recall,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def main():

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    train_ds = DeepCariesDataset(
        "train",
        train=True
    )

    val_ds = DeepCariesDataset(
        "validation",
        train=False
    )

    counts = Counter(
        s["disease"]
        for s in train_ds.samples
    )

    print("="*70)
    print("DEEP CARIES SPECIALIST V2")
    print("="*70)

    print("Train:", len(train_ds))
    print("Validation:", len(val_ds))
    print("Device:", device)

    if device.type == "cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    print("\nDistribution:")
    for k,v in counts.items():
        print(k, v)

    # Aggressive oversampling of Deep Caries.
    sample_weights = []

    for s in train_ds.samples:
        if s["disease"] == "Deep Caries":
            sample_weights.append(3.5)
        else:
            sample_weights.append(1.0)

    sampler = WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_ds),
        replacement=True
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=48,
        sampler=sampler,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True,
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=96,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True,
    )

    model = models.resnet34(
        weights=models.ResNet34_Weights.IMAGENET1K_V1
    )

    model.fc = nn.Sequential(
        nn.Dropout(0.40),
        nn.Linear(
            model.fc.in_features,
            2
        )
    )

    model.to(device)

    # Additional loss weighting.
    alpha = torch.tensor(
        [1.0, 1.8],
        dtype=torch.float32,
        device=device
    )

    loss_fn = FocalLoss(
        alpha=alpha,
        gamma=1.5,
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=7e-5,
        weight_decay=2e-4
    )

    scheduler = (
        torch.optim.lr_scheduler
        .CosineAnnealingLR(
            optimizer,
            T_max=12
        )
    )

    scaler = torch.amp.GradScaler(
        "cuda",
        enabled=device.type == "cuda"
    )

    out = Path(
        "checkpoints/deep_caries_v2"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    best = -1
    stale = 0
    patience = 4

    for epoch in range(12):

        model.train()

        running = 0
        total = 0
        correct = 0

        for images, labels in train_loader:

            images = images.to(
                device,
                non_blocking=True
            )

            labels = labels.to(
                device,
                non_blocking=True
            )

            optimizer.zero_grad(
                set_to_none=True
            )

            with torch.amp.autocast(
                "cuda",
                enabled=device.type == "cuda",
                dtype=torch.bfloat16
            ):
                logits = model(images)
                loss = loss_fn(
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

            pred = logits.argmax(1)

            correct += (
                pred == labels
            ).sum().item()

            total += labels.size(0)

            running += (
                loss.item()
                * labels.size(0)
            )

        scheduler.step()

        metrics = evaluate(
            model,
            val_loader,
            device,
            threshold=0.50
        )

        # Prioritize Deep Caries sensitivity,
        # while still penalizing collapse of Caries specificity.
        score = (
            0.45 * metrics["deep_f1"]
            + 0.35 * metrics["deep_recall"]
            + 0.20 * metrics["caries_recall"]
        )

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={running/max(total,1):.4f} "
            f"train_acc={correct/max(total,1):.4f} "
            f"val_acc={metrics['accuracy']:.4f} "
            f"balanced={metrics['balanced_acc']:.4f} "
            f"score={score:.4f}"
        )

        print(
            f"  CARIES recall: "
            f"{metrics['caries_recall']:.4f}"
        )

        print(
            f"  DEEP recall: "
            f"{metrics['deep_recall']:.4f}"
        )

        print(
            f"  DEEP precision: "
            f"{metrics['deep_precision']:.4f}"
        )

        print(
            f"  DEEP F1: "
            f"{metrics['deep_f1']:.4f}"
        )

        print(
            f"  TP={metrics['tp']} "
            f"FP={metrics['fp']} "
            f"FN={metrics['fn']} "
            f"TN={metrics['tn']}"
        )

        state = {
            "epoch": epoch+1,
            "model": model.state_dict(),
            "classes": CLASSES,
            "metrics": metrics,
            "score": score,
        }

        torch.save(
            state,
            out/"latest.pt"
        )

        if score > best:
            best = score
            stale = 0

            torch.save(
                state,
                out/"best.pt"
            )

            print(
                "*** NEW BEST:",
                round(best, 4),
                "***"
            )

        else:
            stale += 1

        if stale >= patience:
            print("EARLY STOPPING")
            break

    print()
    print("="*70)
    print("DEEP CARIES V2 COMPLETE")
    print("BEST SCORE:", best)
    print(
        "MODEL:",
        "checkpoints/deep_caries_v2/best.pt"
    )
    print("="*70)


if __name__ == "__main__":
    main()
