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

CLASSES = [
    "HEALTHY",
    "FILLING",
    "CARIES",
    "RCT_CROWN",
    "CROWN",
    "ROOT_CANAL_TREATMENT",
    "RESIDUAL_ROOT",
]

CLASS_TO_IDX = {
    c:i for i,c in enumerate(CLASSES)
}


class StatusDataset(Dataset):
    def __init__(self, split, train=False):
        self.samples=[]

        data=json.loads(
            (ROOT/f"{split}.json").read_text(encoding="utf-8")
        )

        for r in data["records"]:
            for t in r["teeth"]:
                status=t["status"]

                if status not in CLASS_TO_IDX:
                    continue

                self.samples.append({
                    "image_path":r["image_path"],
                    "bbox":t["bbox_xyxy"],
                    "label":CLASS_TO_IDX[status],
                    "status":status,
                })

        if train:
            self.tf=transforms.Compose([
                transforms.Resize((256,256)),
                transforms.RandomRotation(5),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.025,0.025),
                    scale=(0.94,1.06)
                ),
                transforms.ColorJitter(
                    brightness=0.05,
                    contrast=0.10
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485,0.456,0.406],
                    [0.229,0.224,0.225]
                ),
            ])
        else:
            self.tf=transforms.Compose([
                transforms.Resize((256,256)),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485,0.456,0.406],
                    [0.229,0.224,0.225]
                ),
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self,idx):
        s=self.samples[idx]

        img=Image.open(
            s["image_path"]
        ).convert("RGB")

        W,H=img.size
        x1,y1,x2,y2=map(float,s["bbox"])

        bw=max(x2-x1,1)
        bh=max(y2-y1,1)

        px=max(18,int(bw*0.45))
        py=max(18,int(bh*0.45))

        crop=img.crop((
            max(0,int(x1)-px),
            max(0,int(y1)-py),
            min(W,int(x2)+px),
            min(H,int(y2)+py),
        ))

        return self.tf(crop),s["label"]


def evaluate(model,loader,device):
    model.eval()

    correct=0
    total=0

    cc=[0]*len(CLASSES)
    ct=[0]*len(CLASSES)

    confusion=[
        [0]*len(CLASSES)
        for _ in CLASSES
    ]

    with torch.no_grad():
        for images,labels in loader:
            images=images.to(device,non_blocking=True)
            labels=labels.to(device,non_blocking=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits=model(images)

            preds=logits.argmax(1)

            correct+=(preds==labels).sum().item()
            total+=labels.size(0)

            for y,p in zip(labels,preds):
                yi=int(y)
                pi=int(p)

                ct[yi]+=1
                cc[yi]+=int(yi==pi)
                confusion[yi][pi]+=1

    acc=correct/max(total,1)

    recall={
        CLASSES[i]:
            cc[i]/ct[i] if ct[i] else 0
        for i in range(len(CLASSES))
    }

    macro=sum(recall.values())/len(CLASSES)

    return acc,macro,recall,confusion


def main():
    device=torch.device(
        "cuda" if torch.cuda.is_available()
        else "cpu"
    )

    train_ds=StatusDataset("train",True)
    val_ds=StatusDataset("validation",False)

    counts=Counter(
        s["status"]
        for s in train_ds.samples
    )

    print("="*70)
    print("TOOTH STATUS V2 — 7 CLASS")
    print("Train:",len(train_ds))
    print("Validation:",len(val_ds))
    print("Device:",device)

    if device.type=="cuda":
        print("GPU:",torch.cuda.get_device_name(0))

    print("\nDistribution:")
    for c in CLASSES:
        print(c,counts[c])

    # stronger balancing for minority classes,
    # but not full inverse-frequency oversampling
    sample_weights=[]

    for s in train_ds.samples:
        n=counts[s["status"]]

        sample_weights.append(
            (len(train_ds)/max(n,1))**0.60
        )

    sampler=WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_ds),
        replacement=True
    )

    train_loader=DataLoader(
        train_ds,
        batch_size=48,
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

    model=models.resnet34(
        weights=models.ResNet34_Weights.IMAGENET1K_V1
    )

    model.fc=nn.Sequential(
        nn.Dropout(0.35),
        nn.Linear(
            model.fc.in_features,
            len(CLASSES)
        )
    )

    model=model.to(device)

    weights=[]

    max_count=max(counts.values())

    for c in CLASSES:
        weights.append(
            math.sqrt(
                max_count/max(counts[c],1)
            )
        )

    class_weights=torch.tensor(
        weights,
        dtype=torch.float32,
        device=device
    )

    loss_fn=nn.CrossEntropyLoss(
        weight=class_weights,
        label_smoothing=0.04
    )

    optimizer=torch.optim.AdamW(
        model.parameters(),
        lr=8e-5,
        weight_decay=2e-4
    )

    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=14
    )

    scaler=torch.amp.GradScaler(
        "cuda",
        enabled=device.type=="cuda"
    )

    out=Path("checkpoints/tooth_status_v2")
    out.mkdir(parents=True,exist_ok=True)

    best=-1
    stale=0
    patience=4

    for epoch in range(14):
        model.train()

        total=0
        correct=0
        loss_sum=0

        for images,labels in train_loader:
            images=images.to(device,non_blocking=True)
            labels=labels.to(device,non_blocking=True)

            optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits=model(images)
                loss=loss_fn(logits,labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            pred=logits.argmax(1)

            correct+=(pred==labels).sum().item()
            total+=labels.size(0)
            loss_sum+=loss.item()*labels.size(0)

        scheduler.step()

        train_acc=correct/max(total,1)

        val_acc,macro,recall,cm=evaluate(
            model,val_loader,device
        )

        # Favor minority-class recall more than overall accuracy.
        score=0.30*val_acc+0.70*macro

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
                f"  {c:25} "
                f"{recall[c]:.4f}"
            )

        state={
            "epoch":epoch+1,
            "model":model.state_dict(),
            "classes":CLASSES,
            "val_acc":val_acc,
            "macro_recall":macro,
            "per_class_recall":recall,
            "confusion":cm,
            "score":score,
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
    print("="*70)
    print("TOOTH STATUS V2 COMPLETE")
    print("BEST SCORE:",best)
    print(
        "MODEL:",
        "checkpoints/tooth_status_v2/best.pt"
    )
    print("="*70)


if __name__=="__main__":
    main()
