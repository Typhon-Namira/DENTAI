import json
import math
from pathlib import Path
from collections import Counter

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from PIL import Image

CLASSES = ["FILLING", "IMPLANT"]
CLASS_TO_IDX = {c:i for i,c in enumerate(CLASSES)}

CANONICAL = Path(
    "data/canonical/akudental/git-92e2cc3/instances.json"
)

SPLIT_DIR = Path("data/splits/tooth_v2")


def build_image_to_split():
    m = {}

    for split in ["train", "validation", "test"]:
        d = json.loads(
            (SPLIT_DIR / f"{split}.json").read_text()
        )

        for r in d["records"]:
            if r.get("source_dataset", "").startswith("akudental"):
                m[str(r["source_image_id"])] = split

    return m


class RestorationDataset(Dataset):
    def __init__(self, split, train=False):
        self.samples = []
        self.train = train

        image_to_split = build_image_to_split()
        data = json.loads(CANONICAL.read_text())

        for r in data.get("images", []):
            image_id = str(r.get("source_image_id", ""))

            if image_to_split.get(image_id) != split:
                continue

            image_path = (
                Path("data/raw/akudental/current/source_repo/AKUDENTAL/images")
                / image_id
            )

            for inst in r.get("instances", []):
                cls = str(
                    inst.get("canonical_class", "")
                ).upper()

                bbox = inst.get("bbox_xyxy")

                if cls in CLASS_TO_IDX and bbox:
                    self.samples.append({
                        "image_path": str(image_path),
                        "bbox": bbox,
                        "label": CLASS_TO_IDX[cls],
                        "class_name": cls,
                    })

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((224,224)),
                transforms.RandomRotation(5),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.03,0.03),
                    scale=(0.95,1.05)
                ),
                transforms.ColorJitter(
                    brightness=0.06,
                    contrast=0.10
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485,0.456,0.406],
                    std=[0.229,0.224,0.225]
                ),
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((224,224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485,0.456,0.406],
                    std=[0.229,0.224,0.225]
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

        bw = max(x2-x1,1)
        bh = max(y2-y1,1)

        pad_x = max(15,int(bw*0.45))
        pad_y = max(15,int(bh*0.45))

        crop = img.crop((
            max(0,int(x1)-pad_x),
            max(0,int(y1)-pad_y),
            min(W,int(x2)+pad_x),
            min(H,int(y2)+pad_y),
        ))

        return self.tf(crop), s["label"]


def evaluate(model, loader, device):
    model.eval()

    correct=0
    total=0

    cc=[0]*len(CLASSES)
    ct=[0]*len(CLASSES)

    with torch.no_grad():
        for image,label in loader:
            image=image.to(
                device,
                non_blocking=True
            )

            label=label.to(
                device,
                non_blocking=True
            )

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits=model(image)

            pred=logits.argmax(1)

            correct += (
                pred==label
            ).sum().item()

            total += label.size(0)

            for y,p in zip(label,pred):
                yi=int(y.item())
                ct[yi]+=1
                cc[yi]+=int(y==p)

    acc=correct/max(total,1)

    per_class={
        CLASSES[i]:
            cc[i]/ct[i]
            if ct[i]
            else 0
        for i in range(len(CLASSES))
    }

    macro=sum(
        per_class.values()
    )/len(CLASSES)

    return acc,macro,per_class


def main():
    device=torch.device(
        "cuda" if torch.cuda.is_available()
        else "cpu"
    )

    train_ds=RestorationDataset(
        "train",
        train=True
    )

    val_ds=RestorationDataset(
        "validation",
        train=False
    )

    counts=Counter(
        s["class_name"]
        for s in train_ds.samples
    )

    print("====================================")
    print("RESTORATION V1")
    print("Train:",len(train_ds))
    print("Validation:",len(val_ds))
    print("Device:",device)

    if device.type=="cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    print("Distribution:")
    for c in CLASSES:
        print(c,counts[c])

    sample_weights=[]

    for s in train_ds.samples:
        n=counts[s["class_name"]]

        sample_weights.append(
            math.sqrt(
                len(train_ds)/max(n,1)
            )
        )

    sampler=WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_ds),
        replacement=True
    )

    train_loader=DataLoader(
        train_ds,
        batch_size=64,
        sampler=sampler,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    val_loader=DataLoader(
        val_ds,
        batch_size=96,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )

    model=models.resnet18(
        weights=models.ResNet18_Weights.IMAGENET1K_V1
    )

    model.fc=nn.Sequential(
        nn.Dropout(0.30),
        nn.Linear(
            model.fc.in_features,
            len(CLASSES)
        )
    )

    model=model.to(device)

    # Moderate extra emphasis on Implant.
    class_weights=torch.tensor(
        [1.0,2.5],
        dtype=torch.float32,
        device=device
    )

    loss_fn=nn.CrossEntropyLoss(
        weight=class_weights,
        label_smoothing=0.03
    )

    optimizer=torch.optim.AdamW(
        model.parameters(),
        lr=1e-4,
        weight_decay=1e-4
    )

    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=10
    )

    scaler=torch.amp.GradScaler(
        "cuda",
        enabled=device.type=="cuda"
    )

    out=Path(
        "checkpoints/restoration_v1"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    best_score=-1
    stale=0
    patience=3

    for epoch in range(10):

        model.train()

        correct=0
        total=0
        loss_sum=0

        for image,label in train_loader:
            image=image.to(
                device,
                non_blocking=True
            )

            label=label.to(
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
                logits=model(image)
                loss=loss_fn(
                    logits,label
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
                pred==label
            ).sum().item()

            total += label.size(0)

            loss_sum += (
                loss.item()*label.size(0)
            )

        train_acc=correct/max(total,1)

        val_acc,macro,per_class=evaluate(
            model,
            val_loader,
            device
        )

        scheduler.step()

        score=(
            0.45*val_acc
            + 0.55*macro
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

        state={
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

        if score>best_score:
            best_score=score
            stale=0

            torch.save(
                state,
                out/"best.pt"
            )

            print(
                "*** NEW BEST:",
                round(score,4),
                "***"
            )
        else:
            stale+=1

        if stale>=patience:
            print(
                "EARLY STOPPING"
            )
            break

    print()
    print("====================================")
    print("RESTORATION V1 COMPLETE")
    print("BEST SCORE:",best_score)
    print(
        "MODEL:",
        "checkpoints/restoration_v1/best.pt"
    )
    print("====================================")


if __name__=="__main__":
    main()
