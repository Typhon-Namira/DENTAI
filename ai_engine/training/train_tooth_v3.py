import json
from pathlib import Path
from collections import Counter

import torch
from torch.utils.data import Dataset, DataLoader
from torchvision.transforms.functional import to_tensor
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

from PIL import Image, ImageDraw


DATA_ROOT = Path("data/canonical/dentai_v3_super")

ALLOWED_SOURCES = {
    "dentex_hf_7b27ccc8",
    "akudental_git_92e2cc3",
    "dual_labeled_fdi",
}

OLD_CKPT = Path(
    "checkpoints/tooth_v2/maskrcnn_fpn_v1/best.pt"
)

OUT = Path(
    "checkpoints/tooth_v3/maskrcnn_fpn_v1"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)


def normalize_polygon(poly):
    """
    Accept common polygon representations and return
    [(x,y), ...] or None.
    """
    if not poly:
        return None

    # [[x,y], [x,y], ...]
    if (
        isinstance(poly, list)
        and len(poly) >= 3
        and isinstance(poly[0], (list, tuple))
        and len(poly[0]) >= 2
    ):
        try:
            return [
                (float(p[0]), float(p[1]))
                for p in poly
            ]
        except Exception:
            return None

    # Flat [x1,y1,x2,y2,...]
    if (
        isinstance(poly, list)
        and len(poly) >= 6
        and isinstance(poly[0], (int,float))
    ):
        try:
            return [
                (float(poly[i]), float(poly[i+1]))
                for i in range(0, len(poly)-1, 2)
            ]
        except Exception:
            return None

    return None


class ToothV3Dataset(Dataset):

    def __init__(self, split):
        p = DATA_ROOT / f"{split}.json"

        d = json.loads(
            p.read_text(encoding="utf-8")
        )

        self.records = []

        self.source_counts = Counter()
        self.instance_counts = Counter()

        skipped_no_polygon = 0

        for r in d["records"]:

            source = r.get("source_dataset")

            if source not in ALLOWED_SOURCES:
                continue

            instances = []

            for x in r.get("instances", []):

                if x.get("canonical_class") != "TOOTH":
                    continue

                bbox = x.get("bbox_xyxy")

                if not bbox or len(bbox) != 4:
                    continue

                poly = normalize_polygon(
                    x.get("polygon")
                )

                if poly is None:
                    skipped_no_polygon += 1
                    continue

                x1,y1,x2,y2 = map(float,bbox)

                if x2 <= x1 or y2 <= y1:
                    continue

                instances.append({
                    "bbox": [x1,y1,x2,y2],
                    "polygon": poly,
                    "fdi": x.get("fdi_number"),
                })

            if not instances:
                continue

            self.records.append({
                "image_path": r["image_path"],
                "source_dataset": source,
                "source_image_id":
                    r.get("source_image_id"),
                "instances": instances,
            })

            self.source_counts[source] += 1
            self.instance_counts[source] += len(instances)

        self.skipped_no_polygon = skipped_no_polygon


    def __len__(self):
        return len(self.records)


    def __getitem__(self, idx):

        r = self.records[idx]

        image = Image.open(
            r["image_path"]
        ).convert("RGB")

        W,H = image.size

        boxes = []
        masks = []

        for x in r["instances"]:

            x1,y1,x2,y2 = x["bbox"]

            x1 = max(0,min(float(W-1),x1))
            y1 = max(0,min(float(H-1),y1))
            x2 = max(0,min(float(W),x2))
            y2 = max(0,min(float(H),y2))

            if x2 <= x1 or y2 <= y1:
                continue

            poly = [
                (
                    max(0,min(W-1,float(px))),
                    max(0,min(H-1,float(py))),
                )
                for px,py in x["polygon"]
            ]

            if len(poly) < 3:
                continue

            mask_img = Image.new(
                "L",
                (W,H),
                0
            )

            draw = ImageDraw.Draw(mask_img)

            draw.polygon(
                poly,
                outline=1,
                fill=1
            )

            mask = torch.as_tensor(
                __import__("numpy").array(mask_img),
                dtype=torch.uint8
            )

            if mask.sum() == 0:
                continue

            boxes.append(
                [x1,y1,x2,y2]
            )

            masks.append(mask)

        if boxes:
            boxes = torch.tensor(
                boxes,
                dtype=torch.float32
            )

            masks = torch.stack(masks)

            labels = torch.ones(
                len(boxes),
                dtype=torch.int64
            )

        else:
            boxes = torch.zeros(
                (0,4),
                dtype=torch.float32
            )

            masks = torch.zeros(
                (0,H,W),
                dtype=torch.uint8
            )

            labels = torch.zeros(
                (0,),
                dtype=torch.int64
            )

        target = {
            "boxes": boxes,
            "labels": labels,
            "masks": masks,
            "image_id":
                torch.tensor([idx]),
        }

        return (
            to_tensor(image),
            target
        )


def collate_fn(batch):
    return tuple(zip(*batch))


def box_iou(a,b):

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

    return (
        inter/union
        if union>0
        else 0.0
    )


def evaluate_recall(
    model,
    loader,
    device,
    score_threshold=0.50,
    iou_threshold=0.50,
):

    model.eval()

    matched_total=0
    gt_total=0

    precision_tp=0
    prediction_total=0

    with torch.no_grad():

        for images,targets in loader:

            images=[
                x.to(device)
                for x in images
            ]

            outputs=model(images)

            for out,target in zip(
                outputs,
                targets
            ):

                gt_boxes=(
                    target["boxes"]
                    .cpu()
                    .tolist()
                )

                pred_boxes=(
                    out["boxes"]
                    .detach()
                    .cpu()
                    .tolist()
                )

                pred_scores=(
                    out["scores"]
                    .detach()
                    .cpu()
                    .tolist()
                )

                preds=[
                    b
                    for b,s in zip(
                        pred_boxes,
                        pred_scores
                    )
                    if s>=score_threshold
                ]

                gt_total += len(gt_boxes)
                prediction_total += len(preds)

                used=set()

                for gb in gt_boxes:

                    best=0.0
                    best_j=None

                    for j,pb in enumerate(preds):

                        if j in used:
                            continue

                        v=box_iou(
                            gb,
                            pb
                        )

                        if v>best:
                            best=v
                            best_j=j

                    if (
                        best_j is not None
                        and best>=iou_threshold
                    ):
                        matched_total += 1
                        precision_tp += 1
                        used.add(best_j)

    recall=(
        matched_total/max(gt_total,1)
    )

    precision=(
        precision_tp
        / max(prediction_total,1)
    )

    f1=(
        2*precision*recall
        / max(
            precision+recall,
            1e-8
        )
    )

    return {
        "recall":recall,
        "precision":precision,
        "f1":f1,
        "matched":matched_total,
        "gt":gt_total,
        "predictions":prediction_total,
    }


def make_model():

    model=maskrcnn_resnet50_fpn(
        weights=None,
        weights_backbone=None,
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
            2
        )
    )

    in_features_mask=(
        model.roi_heads
        .mask_predictor
        .conv5_mask
        .in_channels
    )

    hidden_layer=256

    model.roi_heads.mask_predictor=(
        MaskRCNNPredictor(
            in_features_mask,
            hidden_layer,
            2
        )
    )

    return model


def extract_state_dict(ckpt):

    if not isinstance(ckpt,dict):
        return ckpt

    for key in [
        "model",
        "model_state_dict",
        "state_dict",
    ]:
        if (
            key in ckpt
            and isinstance(ckpt[key],dict)
        ):
            return ckpt[key]

    # raw state dict
    if all(
        isinstance(k,str)
        for k in ckpt.keys()
    ):
        return ckpt

    raise RuntimeError(
        "Could not locate model state_dict"
    )


def main():

    device=torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    train_ds=ToothV3Dataset(
        "train"
    )

    val_ds=ToothV3Dataset(
        "validation"
    )

    print("="*72)
    print("TOOTH V3 — WARM START")
    print("="*72)

    print(
        "Train images:",
        len(train_ds)
    )

    print(
        "Validation images:",
        len(val_ds)
    )

    print(
        "Train tooth instances:",
        sum(
            train_ds.instance_counts.values()
        )
    )

    print(
        "Validation tooth instances:",
        sum(
            val_ds.instance_counts.values()
        )
    )

    print(
        "Skipped train instances without polygon:",
        train_ds.skipped_no_polygon
    )

    print("\nTRAIN SOURCES")

    for k,v in train_ds.source_counts.items():
        print(
            f"{k:40}",
            v,
            "images |",
            train_ds.instance_counts[k],
            "teeth"
        )

    print("\nDevice:",device)

    if device.type=="cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    if len(train_ds)==0:
        raise RuntimeError(
            "No usable training records."
        )

    model=make_model()

    if not OLD_CKPT.exists():
        raise FileNotFoundError(
            f"Missing Tooth V2 checkpoint: {OLD_CKPT}"
        )

    old=torch.load(
        OLD_CKPT,
        map_location="cpu",
        weights_only=False
    )

    state=extract_state_dict(old)

    result=model.load_state_dict(
        state,
        strict=False
    )

    print()
    print("✓ Warm-started from Tooth V2")
    print(
        "Missing keys:",
        len(result.missing_keys)
    )
    print(
        "Unexpected keys:",
        len(result.unexpected_keys)
    )

    model.to(device)

    train_loader=DataLoader(
        train_ds,
        batch_size=2,
        shuffle=True,
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

    optimizer=torch.optim.AdamW(
        model.parameters(),
        lr=3e-5,
        weight_decay=1e-4
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

    best=-1.0

    for epoch in range(4):

        model.train()

        loss_total=0.0
        steps=0

        for images,targets in train_loader:

            images=[
                x.to(
                    device,
                    non_blocking=True
                )
                for x in images
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

                loss_dict=model(
                    images,
                    targets
                )

                loss=sum(
                    loss_dict.values()
                )

            scaler.scale(
                loss
            ).backward()

            scaler.step(
                optimizer
            )

            scaler.update()

            loss_total += float(
                loss.item()
            )

            steps += 1

        scheduler.step()

        metrics=evaluate_recall(
            model,
            val_loader,
            device,
            score_threshold=0.50,
            iou_threshold=0.50
        )

        # Detection recall remains primary,
        # but precision prevents prediction explosion.
        score=(
            0.70*metrics["recall"]
            + 0.30*metrics["f1"]
        )

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={loss_total/max(steps,1):.4f} "
            f"val_recall={metrics['recall']:.4f} "
            f"precision={metrics['precision']:.4f} "
            f"f1={metrics['f1']:.4f} "
            f"score={score:.4f}"
        )

        print(
            f"  matched="
            f"{metrics['matched']}/"
            f"{metrics['gt']} "
            f"predictions="
            f"{metrics['predictions']}"
        )

        state={
            "epoch":epoch+1,
            "model":model.state_dict(),
            "metrics":metrics,
            "score":score,
            "source_checkpoint":
                str(OLD_CKPT),
            "dataset":
                "dentai_v3_super",
        }

        torch.save(
            state,
            OUT/"latest.pt"
        )

        if score>best:

            best=score

            torch.save(
                state,
                OUT/"best.pt"
            )

            print(
                "*** NEW BEST:",
                round(best,4),
                "***"
            )

    print()
    print("="*72)
    print("TOOTH V3 COMPLETE")
    print("BEST SCORE:",best)
    print(
        "MODEL:",
        OUT/"best.pt"
    )
    print("="*72)


if __name__=="__main__":
    main()
