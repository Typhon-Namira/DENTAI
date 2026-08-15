import json
from pathlib import Path
from collections import Counter

import torch
from torch.utils.data import Dataset, DataLoader
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.transforms.functional import to_tensor
from PIL import Image

CANONICAL = Path(
    "data/canonical/akudental/git-92e2cc3/instances.json"
)

SPLIT_DIR = Path("data/splits/tooth_v2")

CLASSES = {
    "FILLING": 1,
    "IMPLANT": 2,
}

IDX_TO_CLASS = {
    1: "FILLING",
    2: "IMPLANT",
}


def build_image_to_split():
    result = {}

    for split in ["train", "validation", "test"]:
        d = json.loads(
            (SPLIT_DIR / f"{split}.json").read_text()
        )

        for r in d["records"]:
            if r.get("source_dataset", "").startswith("akudental"):
                result[str(r["source_image_id"])] = split

    return result


class RestorationDetectionDataset(Dataset):
    def __init__(self, split):
        image_to_split = build_image_to_split()
        data = json.loads(CANONICAL.read_text())

        self.records = []

        base = Path(
            "data/raw/akudental/current/source_repo/AKUDENTAL/images"
        )

        for r in data.get("images", []):
            image_id = str(r.get("source_image_id", ""))

            if image_to_split.get(image_id) != split:
                continue

            boxes = []
            labels = []

            for inst in r.get("instances", []):
                cls = str(
                    inst.get("canonical_class", "")
                ).upper()

                bbox = inst.get("bbox_xyxy")

                if cls in CLASSES and bbox:
                    x1,y1,x2,y2 = map(float,bbox)

                    if x2 > x1 and y2 > y1:
                        boxes.append(
                            [x1,y1,x2,y2]
                        )
                        labels.append(
                            CLASSES[cls]
                        )

            # IMPORTANT:
            # keep images with zero restoration objects too,
            # so detector learns background.
            self.records.append({
                "image_path": str(base / image_id),
                "boxes": boxes,
                "labels": labels,
                "image_id": image_id,
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
            "image_id": torch.tensor([idx]),
        }

        return image, target


def collate_fn(batch):
    return tuple(zip(*batch))


def evaluate_detector(
    model,
    loader,
    device,
    score_threshold=0.50,
    iou_threshold=0.50
):
    model.eval()

    tp = Counter()
    fp = Counter()
    fn = Counter()

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

        return inter/union if union>0 else 0.0

    with torch.no_grad():
        for images, targets in loader:
            images = [
                x.to(device)
                for x in images
            ]

            outputs = model(images)

            for out,target in zip(outputs,targets):
                gt_boxes = target["boxes"].tolist()
                gt_labels = target["labels"].tolist()

                pred_boxes = out["boxes"].detach().cpu().tolist()
                pred_labels = out["labels"].detach().cpu().tolist()
                pred_scores = out["scores"].detach().cpu().tolist()

                keep = [
                    i for i,s in enumerate(pred_scores)
                    if s >= score_threshold
                ]

                pred_boxes = [pred_boxes[i] for i in keep]
                pred_labels = [pred_labels[i] for i in keep]

                matched_gt = set()

                for pb,pl in zip(pred_boxes,pred_labels):
                    best_iou = 0.0
                    best_j = None

                    for j,(gb,gl) in enumerate(zip(gt_boxes,gt_labels)):
                        if j in matched_gt:
                            continue

                        if gl != pl:
                            continue

                        v = box_iou(pb,gb)

                        if v > best_iou:
                            best_iou = v
                            best_j = j

                    name = IDX_TO_CLASS.get(pl,str(pl))

                    if best_j is not None and best_iou >= iou_threshold:
                        tp[name] += 1
                        matched_gt.add(best_j)
                    else:
                        fp[name] += 1

                for j,gl in enumerate(gt_labels):
                    if j not in matched_gt:
                        name = IDX_TO_CLASS.get(gl,str(gl))
                        fn[name] += 1

    results = {}

    for name in ["FILLING","IMPLANT"]:
        t = tp[name]
        f_p = fp[name]
        f_n = fn[name]

        precision = t / max(t + f_p, 1)
        recall = t / max(t + f_n, 1)
        f1 = (
            2*precision*recall
            / max(precision+recall,1e-8)
        )

        results[name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "tp": t,
            "fp": f_p,
            "fn": f_n,
        }

    macro_f1 = sum(
        x["f1"]
        for x in results.values()
    ) / len(results)

    return macro_f1, results


def main():
    device = torch.device(
        "cuda" if torch.cuda.is_available()
        else "cpu"
    )

    train_ds = RestorationDetectionDataset("train")
    val_ds = RestorationDetectionDataset("validation")

    print("============================================")
    print("RESTORATION DETECTOR V1")
    print("Train images:", len(train_ds))
    print("Validation images:", len(val_ds))
    print("Device:", device)

    if device.type=="cuda":
        print("GPU:",torch.cuda.get_device_name(0))

    train_obj = Counter()
    val_obj = Counter()

    for r in train_ds.records:
        for l in r["labels"]:
            train_obj[IDX_TO_CLASS[l]] += 1

    for r in val_ds.records:
        for l in r["labels"]:
            val_obj[IDX_TO_CLASS[l]] += 1

    print("Train objects:", dict(train_obj))
    print("Validation objects:", dict(val_obj))
    print("============================================")

    train_loader = DataLoader(
        train_ds,
        batch_size=2,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
        collate_fn=collate_fn
    )

    val_loader = DataLoader(
        val_ds,
        batch_size=2,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        collate_fn=collate_fn
    )

    model = fasterrcnn_resnet50_fpn(
        weights="DEFAULT"
    )

    in_features = (
        model.roi_heads.box_predictor.cls_score.in_features
    )

    model.roi_heads.box_predictor = FastRCNNPredictor(
        in_features,
        3
    )

    model.to(device)

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
        "checkpoints/restoration_detector_v1"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    best_f1 = -1.0
    stale = 0
    patience = 3

    for epoch in range(10):
        model.train()

        running_loss = 0.0
        steps = 0

        for images,targets in train_loader:
            images = [
                x.to(device)
                for x in images
            ]

            targets = [
                {
                    k:v.to(device)
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
                losses = model(
                    images,
                    targets
                )

                loss = sum(
                    losses.values()
                )

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += float(loss.item())
            steps += 1

        scheduler.step()

        macro_f1, metrics = evaluate_detector(
            model,
            val_loader,
            device
        )

        print()
        print(
            f"epoch={epoch+1} "
            f"loss={running_loss/max(steps,1):.4f} "
            f"macro_f1={macro_f1:.4f}"
        )

        for name in ["FILLING","IMPLANT"]:
            m = metrics[name]

            print(
                f"  {name}: "
                f"P={m['precision']:.4f} "
                f"R={m['recall']:.4f} "
                f"F1={m['f1']:.4f} "
                f"TP={m['tp']} "
                f"FP={m['fp']} "
                f"FN={m['fn']}"
            )

        state = {
            "epoch": epoch+1,
            "model": model.state_dict(),
            "macro_f1": macro_f1,
            "metrics": metrics,
            "classes": {
                1:"FILLING",
                2:"IMPLANT"
            }
        }

        torch.save(
            state,
            out/"latest.pt"
        )

        if macro_f1 > best_f1:
            best_f1 = macro_f1
            stale = 0

            torch.save(
                state,
                out/"best.pt"
            )

            print(
                "*** NEW BEST macro_f1=",
                round(best_f1,4),
                "***"
            )
        else:
            stale += 1

        if stale >= patience:
            print("EARLY STOPPING")
            break

    print()
    print("============================================")
    print("RESTORATION DETECTOR V1 COMPLETE")
    print("BEST MACRO F1:",best_f1)
    print(
        "MODEL:",
        "checkpoints/restoration_detector_v1/best.pt"
    )
    print("============================================")


if __name__=="__main__":
    main()
