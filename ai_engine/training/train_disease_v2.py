import json
import math
from pathlib import Path
from collections import Counter

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from PIL import Image

CLASSES = [
    "Caries",
    "Deep Caries",
    "Impacted",
    "Periapical Lesion",
]

CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}

FDI_CLASSES = [
    "11","12","13","14","15","16","17","18",
    "21","22","23","24","25","26","27","28",
    "31","32","33","34","35","36","37","38",
    "41","42","43","44","45","46","47","48"
]

FDI_TO_IDX = {x:i for i,x in enumerate(FDI_CLASSES)}


class DiseaseDatasetV2(Dataset):
    def __init__(self, split_file, train=False):
        data = json.loads(Path(split_file).read_text())
        self.samples = []
        self.train = train

        for r in data["records"]:
            image_path = r["image_path"]

            for inst in r.get("instances", []):
                disease = inst.get("source_disease")
                bbox = inst.get("bbox_xyxy")
                fdi = str(inst.get("fdi_number", "")).strip()

                if disease in CLASS_TO_IDX and bbox:
                    self.samples.append({
                        "image_path": image_path,
                        "bbox": bbox,
                        "label": CLASS_TO_IDX[disease],
                        "disease": disease,
                        "fdi": fdi
                    })

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((256,256)),
                transforms.RandomRotation(4),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.025,0.025),
                    scale=(0.96,1.04)
                ),
                transforms.ColorJitter(
                    brightness=0.06,
                    contrast=0.08
                ),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485,0.456,0.406],
                    std=[0.229,0.224,0.225]
                )
            ])
        else:
            self.tf = transforms.Compose([
                transforms.Resize((256,256)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485,0.456,0.406],
                    std=[0.229,0.224,0.225]
                )
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]

        img = Image.open(s["image_path"]).convert("RGB")
        W,H = img.size

        x1,y1,x2,y2 = map(float, s["bbox"])
        bw = max(x2-x1, 1)
        bh = max(y2-y1, 1)

        # Large clinical context:
        # includes crown, roots and surrounding apical region
        pad_x = max(24, int(bw * 0.95))
        pad_top = max(22, int(bh * 0.55))
        pad_bottom = max(30, int(bh * 1.15))

        xx1 = max(0, int(x1)-pad_x)
        yy1 = max(0, int(y1)-pad_top)
        xx2 = min(W, int(x2)+pad_x)
        yy2 = min(H, int(y2)+pad_bottom)

        crop = img.crop((xx1,yy1,xx2,yy2))

        # spatial information
        cx = ((x1+x2)/2.0)/max(W,1)
        cy = ((y1+y2)/2.0)/max(H,1)
        nw = bw/max(W,1)
        nh = bh/max(H,1)

        # encode quadrant + tooth number when FDI exists
        fdi = s["fdi"]
        if fdi in FDI_TO_IDX:
            fdi_idx = FDI_TO_IDX[fdi] / 31.0
            quadrant = int(fdi[0]) / 4.0
            tooth_pos = int(fdi[1]) / 8.0
        else:
            fdi_idx = -1.0
            quadrant = 0.0
            tooth_pos = 0.0

        meta = torch.tensor(
            [cx,cy,nw,nh,fdi_idx,quadrant,tooth_pos],
            dtype=torch.float32
        )

        return self.tf(crop), meta, s["label"]


class DiseaseNetV2(nn.Module):
    def __init__(self):
        super().__init__()

        backbone = models.resnet18(
            weights=models.ResNet18_Weights.IMAGENET1K_V1
        )

        dim = backbone.fc.in_features
        backbone.fc = nn.Identity()

        self.backbone = backbone

        self.meta = nn.Sequential(
            nn.Linear(7,64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(64,64),
            nn.ReLU()
        )

        self.classifier = nn.Sequential(
            nn.Linear(dim+64,256),
            nn.ReLU(),
            nn.Dropout(0.40),
            nn.Linear(256,len(CLASSES))
        )

    def forward(self, image, meta):
        visual = self.backbone(image)
        meta = self.meta(meta)
        return self.classifier(
            torch.cat([visual,meta],dim=1)
        )


def evaluate(model, loader, device):
    model.eval()

    correct = 0
    total = 0

    cc = [0]*len(CLASSES)
    ct = [0]*len(CLASSES)

    confusion = torch.zeros(
        len(CLASSES),
        len(CLASSES),
        dtype=torch.int64
    )

    with torch.no_grad():
        for image,meta,label in loader:
            image = image.to(device,non_blocking=True)
            meta = meta.to(device,non_blocking=True)
            label = label.to(device,non_blocking=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits = model(image,meta)

            pred = logits.argmax(1)

            correct += (pred==label).sum().item()
            total += label.size(0)

            for y,p in zip(label,pred):
                yi=int(y.item())
                pi=int(p.item())
                ct[yi]+=1
                cc[yi]+=int(yi==pi)
                confusion[yi,pi]+=1

    overall = correct/max(total,1)

    per_class = {
        CLASSES[i]: cc[i]/ct[i] if ct[i] else 0.0
        for i in range(len(CLASSES))
    }

    # macro recall prevents majority class dominating model selection
    macro = sum(per_class.values()) / len(CLASSES)

    return overall, macro, per_class, confusion


def main():
    device=torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    train_ds=DiseaseDatasetV2(
        "data/splits/tooth_v2/train.json",
        train=True
    )

    val_ds=DiseaseDatasetV2(
        "data/splits/tooth_v2/validation.json",
        train=False
    )

    counts=Counter(
        x["disease"] for x in train_ds.samples
    )

    print("====================================")
    print("DISEASE V2")
    print("Train:",len(train_ds))
    print("Validation:",len(val_ds))
    print("Device:",device)

    if device.type=="cuda":
        print("GPU:",torch.cuda.get_device_name(0))

    print("Distribution:")
    for c in CLASSES:
        print(c,counts[c])

    # Moderate oversampling rather than extreme duplication.
    # sqrt inverse frequency is intentionally less aggressive.
    sample_weights = []

    for s in train_ds.samples:
        n = counts[s["disease"]]
        sample_weights.append(
            math.sqrt(len(train_ds)/max(n,1))
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

    model=DiseaseNetV2().to(device)

    # Smaller loss weighting because sampler already balances classes
    weights=torch.tensor(
        [
            1.0,
            1.35,
            1.10,
            1.65
        ],
        dtype=torch.float32,
        device=device
    )

    loss_fn=nn.CrossEntropyLoss(
        weight=weights,
        label_smoothing=0.06
    )

    optimizer=torch.optim.AdamW(
        [
            {
                "params":model.backbone.parameters(),
                "lr":4e-5
            },
            {
                "params":model.meta.parameters(),
                "lr":2e-4
            },
            {
                "params":model.classifier.parameters(),
                "lr":2e-4
            }
        ],
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

    out=Path("checkpoints/disease_v2")
    out.mkdir(parents=True,exist_ok=True)

    best_score=-1
    best_acc=0
    stale=0
    patience=4

    for epoch in range(14):
        model.train()

        loss_sum=0
        correct=0
        seen=0

        for image,meta,label in train_loader:
            image=image.to(device,non_blocking=True)
            meta=meta.to(device,non_blocking=True)
            label=label.to(device,non_blocking=True)

            optimizer.zero_grad(set_to_none=True)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits=model(image,meta)
                loss=loss_fn(logits,label)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            loss_sum += loss.item()*label.size(0)
            pred=logits.argmax(1)

            correct += (pred==label).sum().item()
            seen += label.size(0)

        train_acc=correct/max(seen,1)

        val_acc,macro,per_class,conf=evaluate(
            model,val_loader,device
        )

        scheduler.step()

        # Combined selection criterion
        # favors both total accuracy and minority classes
        score=0.55*val_acc + 0.45*macro

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={loss_sum/max(seen,1):.4f} "
            f"train_acc={train_acc:.4f} "
            f"val_acc={val_acc:.4f} "
            f"macro_recall={macro:.4f} "
            f"score={score:.4f}"
        )

        for name in CLASSES:
            print(
                f"  {name}: {per_class[name]:.4f}"
            )

        print("Confusion:")
        print(conf.tolist())

        state={
            "epoch":epoch+1,
            "model":model.state_dict(),
            "classes":CLASSES,
            "val_acc":val_acc,
            "macro_recall":macro,
            "per_class":per_class,
            "score":score
        }

        torch.save(state,out/"latest.pt")

        if score > best_score:
            best_score=score
            best_acc=val_acc
            stale=0

            torch.save(state,out/"best.pt")

            print(
                "*** NEW BEST "
                f"score={score:.4f} "
                f"val={val_acc:.4f} "
                f"macro={macro:.4f} ***"
            )
        else:
            stale+=1

        if stale>=patience:
            print(
                "EARLY STOPPING | "
                f"best_score={best_score:.4f}"
            )
            break

    print()
    print("====================================")
    print("DISEASE V2 FINISHED")
    print("BEST VAL ACC:",best_acc)
    print("BEST SCORE:",best_score)
    print("MODEL: checkpoints/disease_v2/best.pt")
    print("====================================")


if __name__=="__main__":
    main()
