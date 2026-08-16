import json
import hashlib
from pathlib import Path
from collections import Counter, defaultdict

import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from PIL import Image

from torchvision.transforms.functional import to_tensor
from torchvision.models.detection import (
    fasterrcnn_resnet50_fpn,
)
from torchvision.models.detection.faster_rcnn import (
    FastRCNNPredictor,
)

CANONICAL = Path(
    "data/canonical/dentai_v3_super"
)

CLASSES = {
    "CARIES": 1,
    "APICAL_PERIODONTITIS": 2,
    "IMPACTED": 3,
    "BONE_RESORPTION": 4,
    "ROOT_FRAGMENT": 5,
    "FURCATION_LESION": 6,
}

IDX_TO_CLASS = {
    v:k for k,v in CLASSES.items()
}

# Only sources with pathology object annotations.
ALLOWED_SOURCES = {
    "oralxrays9",
    "zenodo14",
}


def stable_bucket(text):
    h = hashlib.sha1(
        text.encode("utf-8")
    ).hexdigest()

    return int(h[:8], 16) % 100


def load_records():
    """
    Build a new pathology-specific split.

    - Zenodo keeps its official train/validation/test.
    - OralXrays currently has only train images available.
      We create deterministic 90/10 train/validation from
      its official training set.
    """

    output = {
        "train": [],
        "validation": [],
        "test": [],
    }

    for original_split in [
        "train",
        "validation",
        "test",
    ]:
        p = CANONICAL / f"{original_split}.json"

        data = json.loads(
            p.read_text(encoding="utf-8")
        )

        for r in data["records"]:
            source = r.get("source_dataset")

            if source not in ALLOWED_SOURCES:
                continue

            if source == "oralxrays9":
                # All available OralXrays images currently come
                # from train2017. Hold out 10% deterministically.
                key = (
                    source
                    + ":"
                    + str(r.get("source_image_id"))
                )

                bucket = stable_bucket(key)

                target_split = (
                    "validation"
                    if bucket < 10
                    else "train"
                )

            elif source == "zenodo14":
                target_split = original_split

            else:
                continue

            output[target_split].append(r)

    return output


ALL_RECORDS = load_records()


class PathologyDataset(Dataset):
    def __init__(self, split):
        self.records = []

        for r in ALL_RECORDS[split]:
            boxes = []
            labels = []

            for inst in r.get("instances", []):
                cls = inst.get("canonical_class")

                if cls not in CLASSES:
                    continue

                bbox = inst.get("bbox_xyxy")

                if not bbox:
                    continue

                x1,y1,x2,y2 = map(float,bbox)

                if x2 <= x1 or y2 <= y1:
                    continue

                boxes.append([
                    x1,y1,x2,y2
                ])

                labels.append(
                    CLASSES[cls]
                )

            # Keep zero-target images from these annotation-complete
            # sources so the detector learns true background.
            self.records.append({
                "image_path": r["image_path"],
                "source_dataset":
                    r.get("source_dataset"),
                "source_image_id":
                    r.get("source_image_id"),
                "boxes": boxes,
                "labels": labels,
            })

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        r = self.records[idx]

        image = Image.open(
            r["image_path"]
        ).convert("RGB")

        image = to_tensor(image)

        boxes = torch.tensor(
            r["boxes"],
            dtype=torch.float32
        )

        if boxes.numel() == 0:
            boxes = torch.zeros(
                (0,4),
                dtype=torch.float32
            )

        labels = torch.tensor(
            r["labels"],
            dtype=torch.int64
        )

        target = {
            "boxes": boxes,
            "labels": labels,
            "image_id":
                torch.tensor([idx]),
        }

        return image,target


def collate_fn(batch):
    return tuple(zip(*batch))


def iou(a,b):
    ax1,ay1,ax2,ay2 = a
    bx1,by1,bx2,by2 = b

    ix1=max(ax1,bx1)
    iy1=max(ay1,by1)
    ix2=min(ax2,bx2)
    iy2=min(ay2,by2)

    iw=max(0.0,ix2-ix1)
    ih=max(0.0,iy2-iy1)

    inter=iw*ih

    aa=max(0.0,ax2-ax1)*max(0.0,ay2-ay1)
    bb=max(0.0,bx2-bx1)*max(0.0,by2-by1)

    union=aa+bb-inter

    return inter/union if union>0 else 0.0


def evaluate(
    model,
    loader,
    device,
    score_threshold=0.35,
    iou_threshold=0.50,
):
    model.eval()

    tp=Counter()
    fp=Counter()
    fn=Counter()

    with torch.no_grad():
        for images,targets in loader:
            images=[
                im.to(device)
                for im in images
            ]

            outputs=model(images)

            for out,target in zip(
                outputs,
                targets
            ):
                gt_boxes=target[
                    "boxes"
                ].tolist()

                gt_labels=target[
                    "labels"
                ].tolist()

                pred_boxes=out[
                    "boxes"
                ].detach().cpu().tolist()

                pred_labels=out[
                    "labels"
                ].detach().cpu().tolist()

                pred_scores=out[
                    "scores"
                ].detach().cpu().tolist()

                keep=[
                    i
                    for i,s in enumerate(pred_scores)
                    if s>=score_threshold
                ]

                matched=set()

                for i in keep:
                    pb=pred_boxes[i]
                    pl=pred_labels[i]

                    best_iou=0.0
                    best_j=None

                    for j,(gb,gl) in enumerate(
                        zip(gt_boxes,gt_labels)
                    ):
                        if j in matched:
                            continue

                        if gl != pl:
                            continue

                        v=iou(pb,gb)

                        if v>best_iou:
                            best_iou=v
                            best_j=j

                    name=IDX_TO_CLASS[
                        pl
                    ]

                    if (
                        best_j is not None
                        and best_iou>=iou_threshold
                    ):
                        tp[name]+=1
                        matched.add(best_j)

                    else:
                        fp[name]+=1

                for j,gl in enumerate(
                    gt_labels
                ):
                    if j not in matched:
                        fn[
                            IDX_TO_CLASS[gl]
                        ]+=1

    metrics={}

    for name in CLASSES:
        t=tp[name]
        p=fp[name]
        n=fn[name]

        precision=t/max(t+p,1)
        recall=t/max(t+n,1)

        f1=(
            2*precision*recall
            / max(
                precision+recall,
                1e-8
            )
        )

        metrics[name]={
            "precision":precision,
            "recall":recall,
            "f1":f1,
            "tp":t,
            "fp":p,
            "fn":n,
        }

    macro_f1=sum(
        m["f1"]
        for m in metrics.values()
    )/len(metrics)

    macro_recall=sum(
        m["recall"]
        for m in metrics.values()
    )/len(metrics)

    score=(
        0.55*macro_f1
        + 0.45*macro_recall
    )

    return score,macro_f1,macro_recall,metrics


def main():
    device=torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    train_ds=PathologyDataset(
        "train"
    )

    val_ds=PathologyDataset(
        "validation"
    )

    print("="*72)
    print("PATHOLOGY DETECTOR V4.2 DOMAIN BALANCED")
    print("="*72)

    print("Train images:",len(train_ds))
    print("Validation images:",len(val_ds))
    print("Device:",device)

    if device.type=="cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    train_counts=Counter()
    val_counts=Counter()
    sources_train=Counter()
    sources_val=Counter()

    for r in train_ds.records:
        sources_train[
            r["source_dataset"]
        ]+=1

        for l in r["labels"]:
            train_counts[
                IDX_TO_CLASS[l]
            ]+=1

    for r in val_ds.records:
        sources_val[
            r["source_dataset"]
        ]+=1

        for l in r["labels"]:
            val_counts[
                IDX_TO_CLASS[l]
            ]+=1

    print("\nTRAIN SOURCES:")
    for k,v in sources_train.items():
        print(k,v)

    print("\nVALIDATION SOURCES:")
    for k,v in sources_val.items():
        print(k,v)

    print("\nTRAIN OBJECTS:")
    for c in CLASSES:
        print(
            f"{c:25}",
            train_counts[c]
        )

    print("\nVALIDATION OBJECTS:")
    for c in CLASSES:
        print(
            f"{c:25}",
            val_counts[c]
        )

    # V4.2 DOMAIN + PATHOLOGY BALANCED SAMPLING
    #
    # OralXrays is much larger than Zenodo.
    # We compensate so both domains contribute
    # approximately equally during training.

    domain_counts = Counter(
        r["source_dataset"]
        for r in train_ds.records
    )

    CLASS_BONUS = {
        "CARIES": 1.0,
        "APICAL_PERIODONTITIS": 1.25,
        "IMPACTED": 1.50,
        "BONE_RESORPTION": 1.40,
        "ROOT_FRAGMENT": 1.40,
        "FURCATION_LESION": 2.50,
    }

    sample_weights = []

    total_domains = len(domain_counts)

    for r in train_ds.records:
        domain = r["source_dataset"]

        # inverse domain frequency
        domain_weight = (
            len(train_ds)
            / (
                total_domains
                * max(domain_counts[domain], 1)
            )
        )

        present = {
            IDX_TO_CLASS[l]
            for l in r["labels"]
        }

        if present:
            class_bonus = max(
                CLASS_BONUS.get(c, 1.0)
                for c in present
            )
        else:
            class_bonus = 0.40

        sample_weights.append(
            domain_weight * class_bonus
        )

    sampler = WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_ds),
        replacement=True,
    )

    train_loader=DataLoader(
        train_ds,
        batch_size=2,
        sampler=sampler,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=collate_fn,
    )

    val_loader=DataLoader(
        val_ds,
        batch_size=2,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=collate_fn,
    )

    model=fasterrcnn_resnet50_fpn(
        weights="DEFAULT",
        min_size=640,
        max_size=1600,
    )

    in_features=(
        model.roi_heads
        .box_predictor
        .cls_score
        .in_features
    )

    model.roi_heads.box_predictor=(
        FastRCNNPredictor(
            in_features,
            len(CLASSES)+1
        )
    )

    model.to(device)

    warm = Path("checkpoints/pathology_detector_v41/best.pt")

    if warm.exists():
        ckpt = torch.load(
            warm,
            map_location="cpu",
            weights_only=False
        )

        model.load_state_dict(
            ckpt["model"],
            strict=True
        )

        print(
            "✓ Warm-started V4.1 from epoch",
            ckpt.get("epoch")
        )

    optimizer=torch.optim.AdamW(
        model.parameters(),
        lr=4e-5,
        weight_decay=1e-4,
    )

    scheduler=(
        torch.optim.lr_scheduler
        .CosineAnnealingLR(
            optimizer,
            T_max=4
        )
    )

    scaler=torch.amp.GradScaler(
        "cuda",
        enabled=device.type=="cuda"
    )

    out=Path(
        "checkpoints/pathology_detector_v42"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    best=-1
    stale=0
    patience=2

    # 6 epochs max to avoid wasting time/GPU.
    for epoch in range(4):
        model.train()

        running=0.0
        steps=0

        for images,targets in train_loader:
            images=[
                im.to(
                    device,
                    non_blocking=True
                )
                for im in images
            ]

            targets=[
                {
                    k:v.to(
                        device,
                        non_blocking=True
                    )
                    for k,v in t.items()
                }
                for t in targets
            ]

            optimizer.zero_grad(
                set_to_none=True
            )

            with torch.amp.autocast(
                "cuda",
                enabled=device.type=="cuda",
                dtype=torch.bfloat16
            ):
                losses=model(
                    images,
                    targets
                )

                loss=sum(
                    losses.values()
                )

            scaler.scale(
                loss
            ).backward()

            scaler.step(
                optimizer
            )

            scaler.update()

            running+=float(
                loss.item()
            )

            steps+=1

        scheduler.step()

        (
            score,
            macro_f1,
            macro_recall,
            metrics,
        )=evaluate(
            model,
            val_loader,
            device,
            score_threshold=0.35,
            iou_threshold=0.50,
        )

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={running/max(steps,1):.4f} "
            f"macro_f1={macro_f1:.4f} "
            f"macro_recall={macro_recall:.4f} "
            f"score={score:.4f}"
        )

        for name in CLASSES:
            m=metrics[name]

            print(
                f"  {name:24} "
                f"P={m['precision']:.3f} "
                f"R={m['recall']:.3f} "
                f"F1={m['f1']:.3f} "
                f"TP={m['tp']} "
                f"FP={m['fp']} "
                f"FN={m['fn']}"
            )

        state={
            "epoch":epoch+1,
            "model":model.state_dict(),
            "classes":CLASSES,
            "score":score,
            "macro_f1":macro_f1,
            "macro_recall":macro_recall,
            "metrics":metrics,
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
            print(
                "EARLY STOPPING"
            )
            break

    print()
    print("="*72)
    print("PATHOLOGY DETECTOR V4.2 DOMAIN BALANCED COMPLETE")
    print("BEST SCORE:",best)
    print(
        "MODEL:",
        "checkpoints/pathology_detector_v4/best.pt"
    )
    print("="*72)


if __name__=="__main__":
    main()
