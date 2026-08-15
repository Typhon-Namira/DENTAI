import json
import math
from pathlib import Path
from collections import Counter

import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import models, transforms
from PIL import Image


FINAL_CLASSES = [
    "Caries",
    "Deep Caries",
    "Impacted",
    "Periapical Lesion",
]

STAGE_A_CLASSES = [
    "Decay",
    "Impacted",
    "Periapical Lesion",
]

STAGE_B_CLASSES = [
    "Caries",
    "Deep Caries",
]

FDI_CLASSES = [
    "11","12","13","14","15","16","17","18",
    "21","22","23","24","25","26","27","28",
    "31","32","33","34","35","36","37","38",
    "41","42","43","44","45","46","47","48"
]

FDI_TO_IDX = {x:i for i,x in enumerate(FDI_CLASSES)}


def stage_a_label(disease):
    if disease in ("Caries", "Deep Caries"):
        return "Decay"
    if disease == "Impacted":
        return "Impacted"
    if disease == "Periapical Lesion":
        return "Periapical Lesion"
    return None


class HierDataset(Dataset):
    def __init__(self, split_file, stage, train=False):
        self.stage = stage
        self.train = train
        self.samples = []

        data = json.loads(
            Path(split_file).read_text(encoding="utf-8")
        )

        if stage == "A":
            classes = STAGE_A_CLASSES
        else:
            classes = STAGE_B_CLASSES

        class_to_idx = {
            c:i for i,c in enumerate(classes)
        }

        for r in data["records"]:
            image_path = r["image_path"]

            for inst in r.get("instances", []):
                disease = inst.get("source_disease")
                bbox = inst.get("bbox_xyxy")
                fdi = str(inst.get("fdi_number", "")).strip()

                if not bbox:
                    continue

                if stage == "A":
                    label_name = stage_a_label(disease)
                else:
                    label_name = (
                        disease
                        if disease in STAGE_B_CLASSES
                        else None
                    )

                if label_name is None:
                    continue

                self.samples.append({
                    "image_path": image_path,
                    "bbox": bbox,
                    "fdi": fdi,
                    "disease": disease,
                    "label_name": label_name,
                    "label": class_to_idx[label_name],
                })

        if train:
            self.tf = transforms.Compose([
                transforms.Resize((256,256)),
                transforms.RandomRotation(4),
                transforms.RandomAffine(
                    degrees=0,
                    translate=(0.025,0.025),
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

        # Large context to include crown + root + apex
        pad_x = max(24,int(bw*0.95))
        pad_top = max(22,int(bh*0.65))
        pad_bottom = max(32,int(bh*1.20))

        xx1=max(0,int(x1)-pad_x)
        yy1=max(0,int(y1)-pad_top)
        xx2=min(W,int(x2)+pad_x)
        yy2=min(H,int(y2)+pad_bottom)

        crop=img.crop(
            (xx1,yy1,xx2,yy2)
        )

        cx=((x1+x2)/2)/max(W,1)
        cy=((y1+y2)/2)/max(H,1)
        nw=bw/max(W,1)
        nh=bh/max(H,1)

        fdi=s["fdi"]

        if fdi in FDI_TO_IDX:
            fdi_idx=FDI_TO_IDX[fdi]/31.0
            quadrant=int(fdi[0])/4.0
            position=int(fdi[1])/8.0
        else:
            fdi_idx=-1.0
            quadrant=0.0
            position=0.0

        meta=torch.tensor(
            [
                cx,cy,nw,nh,
                fdi_idx,
                quadrant,
                position
            ],
            dtype=torch.float32
        )

        return (
            self.tf(crop),
            meta,
            s["label"]
        )


class HierNet(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        backbone=models.resnet18(
            weights=models.ResNet18_Weights.IMAGENET1K_V1
        )

        dim=backbone.fc.in_features
        backbone.fc=nn.Identity()

        self.backbone=backbone

        self.meta=nn.Sequential(
            nn.Linear(7,64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(64,64),
            nn.ReLU()
        )

        self.classifier=nn.Sequential(
            nn.Linear(dim+64,256),
            nn.ReLU(),
            nn.Dropout(0.35),
            nn.Linear(256,num_classes)
        )

    def forward(self,image,meta):
        v=self.backbone(image)
        m=self.meta(meta)

        return self.classifier(
            torch.cat([v,m],dim=1)
        )


def warmstart_from_v2(model):
    p=Path("checkpoints/disease_v2/best.pt")

    if not p.exists():
        print("Disease V2 warm-start not found.")
        return

    try:
        ckpt=torch.load(
            p,
            map_location="cpu"
        )

        state=ckpt["model"]

        current=model.state_dict()

        copied=0

        for k,v in state.items():
            if not k.startswith("backbone."):
                continue

            if k in current and current[k].shape == v.shape:
                current[k]=v
                copied+=1

        model.load_state_dict(
            current,
            strict=False
        )

        print(
            f"Warm-started backbone from Disease V2: "
            f"{copied} tensors"
        )

    except Exception as e:
        print(
            "V2 warm-start skipped:",
            e
        )


def make_loader(ds,batch_size,train):
    if train:
        counts=Counter(
            x["label_name"]
            for x in ds.samples
        )

        weights=[]

        for s in ds.samples:
            n=counts[s["label_name"]]

            # moderate class balancing
            weights.append(
                math.sqrt(
                    len(ds)/max(n,1)
                )
            )

        sampler=WeightedRandomSampler(
            weights,
            num_samples=len(ds),
            replacement=True
        )

        return DataLoader(
            ds,
            batch_size=batch_size,
            sampler=sampler,
            num_workers=4,
            pin_memory=True,
            persistent_workers=True
        )

    return DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        persistent_workers=True
    )


def evaluate(
    model,
    loader,
    classes,
    device
):
    model.eval()

    correct=0
    total=0

    cc=[0]*len(classes)
    ct=[0]*len(classes)

    confusion=torch.zeros(
        len(classes),
        len(classes),
        dtype=torch.int64
    )

    with torch.no_grad():
        for image,meta,label in loader:

            image=image.to(
                device,
                non_blocking=True
            )

            meta=meta.to(
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
                logits=model(
                    image,
                    meta
                )

            pred=logits.argmax(1)

            correct += (
                pred==label
            ).sum().item()

            total += label.size(0)

            for y,p in zip(
                label,
                pred
            ):
                yi=int(y.item())
                pi=int(p.item())

                ct[yi]+=1
                cc[yi]+=int(yi==pi)

                confusion[yi,pi]+=1

    acc=correct/max(total,1)

    recall={
        classes[i]:
            cc[i]/ct[i]
            if ct[i]
            else 0
        for i in range(len(classes))
    }

    macro=sum(
        recall.values()
    )/len(classes)

    return (
        acc,
        macro,
        recall,
        confusion
    )


def train_stage(
    stage,
    classes,
    epochs,
    device
):
    print()
    print("="*65)
    print(
        f"TRAINING STAGE {stage}"
    )
    print(
        "CLASSES:",
        classes
    )
    print("="*65)

    train_ds=HierDataset(
        "data/splits/tooth_v2/train.json",
        stage=stage,
        train=True
    )

    val_ds=HierDataset(
        "data/splits/tooth_v2/validation.json",
        stage=stage,
        train=False
    )

    counts=Counter(
        x["label_name"]
        for x in train_ds.samples
    )

    print(
        "Train samples:",
        len(train_ds)
    )

    print(
        "Validation samples:",
        len(val_ds)
    )

    print(
        "Distribution:"
    )

    for c in classes:
        print(
            f"  {c}: {counts[c]}"
        )

    train_loader=make_loader(
        train_ds,
        64,
        True
    )

    val_loader=make_loader(
        val_ds,
        96,
        False
    )

    model=HierNet(
        len(classes)
    )

    warmstart_from_v2(model)

    model=model.to(device)

    if stage=="A":
        # Periapical remains the rare class
        loss_weights=torch.tensor(
            [1.0,1.05,1.50],
            device=device
        )
    else:
        # Boost Deep Caries moderately
        loss_weights=torch.tensor(
            [1.0,1.40],
            device=device
        )

    loss_fn=nn.CrossEntropyLoss(
        weight=loss_weights,
        label_smoothing=0.04
    )

    optimizer=torch.optim.AdamW(
        [
            {
                "params":
                    model.backbone.parameters(),
                "lr":3e-5
            },
            {
                "params":
                    model.meta.parameters(),
                "lr":2e-4
            },
            {
                "params":
                    model.classifier.parameters(),
                "lr":2e-4
            }
        ],
        weight_decay=2e-4
    )

    scheduler=(
        torch.optim.lr_scheduler
        .CosineAnnealingLR(
            optimizer,
            T_max=epochs
        )
    )

    scaler=torch.amp.GradScaler(
        "cuda",
        enabled=device.type=="cuda"
    )

    out=Path(
        f"checkpoints/disease_v3/stage_{stage.lower()}"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    best_score=-1
    stale=0
    patience=4

    for epoch in range(epochs):

        model.train()

        loss_sum=0
        correct=0
        total=0

        for image,meta,label in train_loader:

            image=image.to(
                device,
                non_blocking=True
            )

            meta=meta.to(
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
                logits=model(
                    image,
                    meta
                )

                loss=loss_fn(
                    logits,
                    label
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
                loss.item()
                * label.size(0)
            )

        train_acc=(
            correct/max(total,1)
        )

        (
            val_acc,
            macro,
            recalls,
            confusion
        )=evaluate(
            model,
            val_loader,
            classes,
            device
        )

        scheduler.step()

        # Macro recall matters heavily here
        score=(
            0.45*val_acc
            + 0.55*macro
        )

        print()
        print(
            f"STAGE {stage} "
            f"epoch={epoch+1} "
            f"loss={loss_sum/max(total,1):.4f} "
            f"train_acc={train_acc:.4f} "
            f"val_acc={val_acc:.4f} "
            f"macro={macro:.4f} "
            f"score={score:.4f}"
        )

        for c in classes:
            print(
                f"  {c}: "
                f"{recalls[c]:.4f}"
            )

        print(
            "Confusion:",
            confusion.tolist()
        )

        state={
            "stage":stage,
            "epoch":epoch+1,
            "model":model.state_dict(),
            "classes":classes,
            "val_acc":val_acc,
            "macro_recall":macro,
            "score":score,
            "per_class":recalls
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
                "*** NEW BEST "
                f"STAGE {stage}: "
                f"{score:.4f} ***"
            )

        else:
            stale+=1

        if stale>=patience:
            print(
                f"EARLY STOP STAGE {stage}"
            )
            break

    best=torch.load(
        out/"best.pt",
        map_location="cpu"
    )

    model.load_state_dict(
        best["model"]
    )

    model=model.to(device)
    model.eval()

    print()
    print(
        f"STAGE {stage} BEST"
    )

    print(
        "val_acc:",
        best["val_acc"]
    )

    print(
        "macro:",
        best["macro_recall"]
    )

    return model


class FinalValidationDataset(Dataset):
    def __init__(self):
        self.base=HierDataset(
            "data/splits/tooth_v2/validation.json",
            stage="A",
            train=False
        )

    def __len__(self):
        return len(self.base)

    def __getitem__(self,idx):
        image,meta,_=self.base[idx]

        s=self.base.samples[idx]

        disease=s["disease"]

        final_idx=(
            FINAL_CLASSES.index(
                disease
            )
        )

        return (
            image,
            meta,
            final_idx
        )


def final_hierarchical_eval(
    stage_a,
    stage_b,
    device
):
    print()
    print("="*65)
    print(
        "FINAL 4-CLASS HIERARCHICAL VALIDATION"
    )
    print("="*65)

    ds=FinalValidationDataset()

    loader=DataLoader(
        ds,
        batch_size=96,
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )

    correct=0
    total=0

    cc=[0]*4
    ct=[0]*4

    confusion=torch.zeros(
        4,4,
        dtype=torch.int64
    )

    stage_a.eval()
    stage_b.eval()

    with torch.no_grad():

        for image,meta,label in loader:

            image=image.to(
                device,
                non_blocking=True
            )

            meta=meta.to(
                device,
                non_blocking=True
            )

            label=label.to(device)

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                logits_a=stage_a(
                    image,
                    meta
                )

            pred_a=logits_a.argmax(1)

            final_pred=[]

            decay_indices=[]

            for i,p in enumerate(
                pred_a.tolist()
            ):
                name=STAGE_A_CLASSES[p]

                if name=="Decay":
                    final_pred.append(None)
                    decay_indices.append(i)

                elif name=="Impacted":
                    final_pred.append(
                        FINAL_CLASSES.index(
                            "Impacted"
                        )
                    )

                else:
                    final_pred.append(
                        FINAL_CLASSES.index(
                            "Periapical Lesion"
                        )
                    )

            if decay_indices:

                idx=torch.tensor(
                    decay_indices,
                    device=device
                )

                with torch.amp.autocast(
                    "cuda",
                    enabled=device.type=="cuda",
                    dtype=torch.bfloat16
                ):
                    logits_b=stage_b(
                        image[idx],
                        meta[idx]
                    )

                pred_b=(
                    logits_b.argmax(1)
                    .tolist()
                )

                for original_i,b in zip(
                    decay_indices,
                    pred_b
                ):
                    disease=(
                        STAGE_B_CLASSES[b]
                    )

                    final_pred[original_i]=(
                        FINAL_CLASSES.index(
                            disease
                        )
                    )

            pred=torch.tensor(
                final_pred,
                device=device
            )

            correct += (
                pred==label
            ).sum().item()

            total += label.size(0)

            for y,p in zip(
                label,
                pred
            ):
                yi=int(y.item())
                pi=int(p.item())

                ct[yi]+=1

                if yi==pi:
                    cc[yi]+=1

                confusion[yi,pi]+=1

    accuracy=(
        correct/max(total,1)
    )

    recalls={}

    for i,c in enumerate(
        FINAL_CLASSES
    ):
        recalls[c]=(
            cc[i]/ct[i]
            if ct[i]
            else 0
        )

    macro=sum(
        recalls.values()
    )/4

    print(
        "FINAL VAL ACC:",
        round(accuracy,4)
    )

    print(
        "FINAL MACRO RECALL:",
        round(macro,4)
    )

    print()

    for c in FINAL_CLASSES:
        print(
            f"{c}: "
            f"{recalls[c]:.4f}"
        )

    print()
    print(
        "FINAL CONFUSION MATRIX:"
    )

    print(
        confusion.tolist()
    )

    print()
    print(
        "V2 reference accuracy: 0.7404"
    )

    if accuracy>0.7404:
        print(
            "✅ V3 BEATS DISEASE V2"
        )
    else:
        print(
            "⚠️ V3 DID NOT BEAT V2 "
            "ON OVERALL ACCURACY"
        )

    print("="*65)


def main():

    device=torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
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

    stage_a=train_stage(
        "A",
        STAGE_A_CLASSES,
        epochs=12,
        device=device
    )

    stage_b=train_stage(
        "B",
        STAGE_B_CLASSES,
        epochs=12,
        device=device
    )

    final_hierarchical_eval(
        stage_a,
        stage_b,
        device
    )

    print()
    print(
        "DISEASE V3 COMPLETE"
    )

    print(
        "Stage A:",
        "checkpoints/disease_v3/stage_a/best.pt"
    )

    print(
        "Stage B:",
        "checkpoints/disease_v3/stage_b/best.pt"
    )


if __name__=="__main__":
    main()
