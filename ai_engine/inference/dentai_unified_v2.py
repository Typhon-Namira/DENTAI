import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import torch
from torch import nn
from PIL import Image, ImageDraw
from torchvision import models, transforms
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision.transforms.functional import to_tensor

from ai_engine.training.train_fdi_v2 import FDINetV2, FDI_CLASSES
from ai_engine.training.train_disease_v3_hier import (
    HierNet,
    STAGE_A_CLASSES,
    STAGE_B_CLASSES,
)

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

FDI_TO_IDX = {x:i for i,x in enumerate(FDI_CLASSES)}

FDI_TF = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485,0.456,0.406],
        [0.229,0.224,0.225]
    ),
])

DISEASE_TF = transforms.Compose([
    transforms.Resize((256,256)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485,0.456,0.406],
        [0.229,0.224,0.225]
    ),
])

REST_TF = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize(
        [0.485,0.456,0.406],
        [0.229,0.224,0.225]
    ),
])


def load_tooth():
    p = Path(
        "checkpoints/tooth_v2/maskrcnn_fpn_v1/best.pt"
    )

    ckpt = torch.load(
        p,
        map_location="cpu",
        weights_only=False
    )

    model = maskrcnn_resnet50_fpn(
        weights=None,
        weights_backbone=None,
        num_classes=2
    )

    model.load_state_dict(
        ckpt["model"],
        strict=True
    )

    model.to(DEVICE).eval()

    print("✓ Tooth V2")
    return model


def load_fdi():
    p = Path(
        "checkpoints/fdi_v2_final/fdi_v2_best_90_38.pt"
    )

    if not p.exists():
        p = Path(
            "checkpoints/fdi_v2/best.pt"
        )

    ckpt = torch.load(
        p,
        map_location="cpu",
        weights_only=False
    )

    model = FDINetV2()

    model.load_state_dict(
        ckpt["model"],
        strict=True
    )

    model.to(DEVICE).eval()

    print(
        "✓ FDI V2 | val_acc=",
        ckpt.get("val_acc")
    )

    return model


def load_disease():
    pa = Path(
        "checkpoints/disease_v3/stage_a/best.pt"
    )

    pb = Path(
        "checkpoints/disease_v3/stage_b/best.pt"
    )

    ca = torch.load(
        pa,
        map_location="cpu",
        weights_only=False
    )

    cb = torch.load(
        pb,
        map_location="cpu",
        weights_only=False
    )

    a = HierNet(
        len(STAGE_A_CLASSES)
    )

    b = HierNet(
        len(STAGE_B_CLASSES)
    )

    a.load_state_dict(
        ca["model"],
        strict=True
    )

    b.load_state_dict(
        cb["model"],
        strict=True
    )

    a.to(DEVICE).eval()
    b.to(DEVICE).eval()

    print("✓ Disease V3")

    return a,b


def load_restoration_gate():
    p = Path(
        "checkpoints/restoration_gate_v1/best.pt"
    )

    ckpt = torch.load(
        p,
        map_location="cpu",
        weights_only=False
    )

    model = models.resnet18(
        weights=None
    )

    model.fc = nn.Sequential(
        nn.Dropout(0.30),
        nn.Linear(
            model.fc.in_features,
            2
        )
    )

    model.load_state_dict(
        ckpt["model"],
        strict=True
    )

    model.to(DEVICE).eval()

    print(
        "✓ Restoration Gate V1 | "
        "test_acc≈0.951"
    )

    return model


def geometry(box,W,H):
    x1,y1,x2,y2 = map(float,box)

    bw=max(x2-x1,1)
    bh=max(y2-y1,1)

    cx=((x1+x2)/2)/max(W,1)
    cy=((y1+y2)/2)/max(H,1)

    return (
        x1,y1,x2,y2,
        bw,bh,
        cx,cy,
        bw/max(W,1),
        bh/max(H,1)
    )


def crop_with_padding(
    image,
    box,
    px,
    py
):
    W,H=image.size

    x1,y1,x2,y2,bw,bh,*_=geometry(
        box,W,H
    )

    return image.crop((
        max(0,int(x1)-int(max(16,bw*px))),
        max(0,int(y1)-int(max(16,bh*py))),
        min(W,int(x2)+int(max(16,bw*px))),
        min(H,int(y2)+int(max(16,bh*py))),
    ))


def infer_fdi(model,image,box):
    W,H=image.size

    (
        x1,y1,x2,y2,
        bw,bh,cx,cy,nw,nh
    )=geometry(box,W,H)

    spatial=torch.tensor(
        [[cx,cy,nw,nh]],
        dtype=torch.float32,
        device=DEVICE
    )

    crop=image.crop((
        max(0,int(x1)-max(12,int(bw*.35))),
        max(0,int(y1)-max(12,int(bh*.35))),
        min(W,int(x2)+max(12,int(bw*.35))),
        min(H,int(y2)+max(12,int(bh*.35))),
    ))

    tensor=FDI_TF(crop).unsqueeze(0).to(DEVICE)

    with torch.no_grad(), torch.amp.autocast(
        "cuda",
        enabled=DEVICE.type=="cuda",
        dtype=torch.bfloat16
    ):
        logits=model(
            tensor,
            spatial
        )

    probs=torch.softmax(
        logits.float(),
        dim=1
    )

    conf,idx=probs.max(1)

    return (
        FDI_CLASSES[idx.item()],
        float(conf.item())
    )


# ------------------------------------------------
# CONSERVATIVE ARCH RESOLVER V2
# ------------------------------------------------

QUADRANTS={
    "1":["11","12","13","14","15","16","17","18"],
    "2":["21","22","23","24","25","26","27","28"],
    "3":["31","32","33","34","35","36","37","38"],
    "4":["41","42","43","44","45","46","47","48"],
}


def center_x(t):
    x1,_,x2,_=t["bbox_xyxy"]
    return (x1+x2)/2


def resolve_arch(teeth):
    for t in teeth:
        t["raw_fdi_number"]=t["fdi_number"]
        t["resolved_fdi_number"]=t["fdi_number"]
        t["fdi_was_changed"]=False

    groups=defaultdict(list)

    for t in teeth:
        raw=t["raw_fdi_number"]

        if (
            len(raw)==2
            and raw[0] in QUADRANTS
        ):
            groups[raw[0]].append(t)

    for q,group in groups.items():

        counts=Counter(
            x["raw_fdi_number"]
            for x in group
        )

        duplicates=[
            x for x,n in counts.items()
            if n>1
        ]

        expected=QUADRANTS[q]

        missing=[
            x for x in expected
            if x not in counts
        ]

        reverse=q in ("1","3")

        ordered=sorted(
            group,
            key=center_x,
            reverse=reverse
        )

        rank={
            id(t):i
            for i,t in enumerate(ordered)
        }

        for dup in duplicates:

            members=[
                t for t in group
                if t["raw_fdi_number"]==dup
            ]

            keeper=max(
                members,
                key=lambda t:
                    float(t["fdi_confidence"])
            )

            for t in members:

                if t is keeper:
                    continue

                if not missing:
                    continue

                r=rank[id(t)]

                approx=(
                    r*7/(len(ordered)-1)
                    if len(ordered)>1
                    else 0
                )

                candidate=min(
                    missing,
                    key=lambda c:
                        abs(
                            (int(c[1])-1)
                            - approx
                        )
                )

                t["resolved_fdi_number"]=candidate
                t["fdi_was_changed"]=True

                missing.remove(candidate)

    return teeth


def disease_meta(
    image,
    box,
    fdi
):
    W,H=image.size

    (
        x1,y1,x2,y2,
        bw,bh,cx,cy,nw,nh
    )=geometry(box,W,H)

    if fdi in FDI_TO_IDX:
        fdi_idx=FDI_TO_IDX[fdi]/31
        quadrant=int(fdi[0])/4
        position=int(fdi[1])/8
    else:
        fdi_idx=-1
        quadrant=0
        position=0

    meta=torch.tensor(
        [[
            cx,cy,nw,nh,
            fdi_idx,
            quadrant,
            position
        ]],
        dtype=torch.float32,
        device=DEVICE
    )

    pad_x=max(24,int(bw*.95))
    pad_top=max(22,int(bh*.65))
    pad_bottom=max(32,int(bh*1.20))

    crop=image.crop((
        max(0,int(x1)-pad_x),
        max(0,int(y1)-pad_top),
        min(W,int(x2)+pad_x),
        min(H,int(y2)+pad_bottom),
    ))

    return (
        DISEASE_TF(crop)
        .unsqueeze(0)
        .to(DEVICE),
        meta
    )


def infer_disease(
    a,
    b,
    image,
    box,
    fdi
):
    tensor,meta=disease_meta(
        image,
        box,
        fdi
    )

    with torch.no_grad(), torch.amp.autocast(
        "cuda",
        enabled=DEVICE.type=="cuda",
        dtype=torch.bfloat16
    ):
        la=a(tensor,meta)

    pa=torch.softmax(
        la.float(),
        dim=1
    )

    ca,ia=pa.max(1)

    stage_a=STAGE_A_CLASSES[
        ia.item()
    ]

    if stage_a=="Decay":

        with torch.no_grad(), torch.amp.autocast(
            "cuda",
            enabled=DEVICE.type=="cuda",
            dtype=torch.bfloat16
        ):
            lb=b(tensor,meta)

        pb=torch.softmax(
            lb.float(),
            dim=1
        )

        cb,ib=pb.max(1)

        return {
            "candidate":
                STAGE_B_CLASSES[
                    ib.item()
                ],

            "confidence":
                float(
                    ca.item()
                    * cb.item()
                )
        }

    return {
        "candidate":stage_a,
        "confidence":
            float(ca.item())
    }


def infer_restoration_gate(
    model,
    image,
    box
):
    crop=crop_with_padding(
        image,
        box,
        .35,
        .35
    )

    tensor=REST_TF(
        crop
    ).unsqueeze(0).to(
        DEVICE
    )

    with torch.no_grad(), torch.amp.autocast(
        "cuda",
        enabled=DEVICE.type=="cuda",
        dtype=torch.bfloat16
    ):
        logits=model(tensor)

    probs=torch.softmax(
        logits.float(),
        dim=1
    )

    present_prob=float(
        probs[0,1].item()
    )

    absent_prob=float(
        probs[0,0].item()
    )

    present=(
        present_prob
        >= absent_prob
    )

    return {
        "present":present,
        "present_probability":
            round(present_prob,4),

        "absent_probability":
            round(absent_prob,4),

        # IMPORTANT:
        # type classifier requires localized
        # restoration bbox, so do not invent
        # Filling/Implant here.
        "type":
            "UNRESOLVED"
            if present
            else None
    }


def run(
    image_path,
    threshold=.50
):
    print("="*60)
    print("DENTAI UNIFIED BRAIN V2")
    print("Device:",DEVICE)

    if DEVICE.type=="cuda":
        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

    print("="*60)

    tooth_model=load_tooth()
    fdi_model=load_fdi()
    disease_a,disease_b=load_disease()
    rest_gate=load_restoration_gate()

    image=Image.open(
        image_path
    ).convert("RGB")

    tensor=to_tensor(
        image
    ).to(DEVICE)

    print("\nRunning Tooth V2...")

    with torch.no_grad():
        pred=tooth_model(
            [tensor]
        )[0]

    boxes=pred["boxes"].cpu()
    scores=pred["scores"].cpu()

    keep=scores>=threshold

    boxes=boxes[keep]
    scores=scores[keep]

    teeth=[]

    for i,(box,score) in enumerate(
        zip(boxes,scores),
        start=1
    ):

        box=box.tolist()

        fdi,fdi_conf=infer_fdi(
            fdi_model,
            image,
            box
        )

        teeth.append({
            "instance_id":i,
            "bbox_xyxy":[
                round(float(x),2)
                for x in box
            ],
            "segmentation_confidence":
                round(
                    float(score),
                    4
                ),

            "fdi_number":fdi,
            "fdi_confidence":
                round(fdi_conf,4)
        })

    # Resolve FDI BEFORE disease inference
    teeth=resolve_arch(teeth)

    for t in teeth:

        resolved=t[
            "resolved_fdi_number"
        ]

        disease=infer_disease(
            disease_a,
            disease_b,
            image,
            t["bbox_xyxy"],
            resolved
        )

        restoration=(
            infer_restoration_gate(
                rest_gate,
                image,
                t["bbox_xyxy"]
            )
        )

        t["disease"]={
            "candidate":
                disease["candidate"],

            "confidence":
                round(
                    disease[
                        "confidence"
                    ],
                    4
                ),

            "review_required":True,

            "limitation":
                "No HEALTHY disease class yet."
        }

        t["restoration"]=restoration

        t["fdi_review_required"]=(
            t["fdi_confidence"]<.70
        )

    teeth.sort(
        key=lambda t:
            int(
                t[
                    "resolved_fdi_number"
                ]
            )
    )

    result={
        "schema_version":
            "dentai-unified-v2",

        "image":str(image_path),

        "detected_teeth":
            len(teeth),

        "models":{
            "tooth":
                "Tooth V2",

            "fdi":
                "FDI V2 + Arch Resolver V2",

            "disease":
                "Disease V3 Hierarchical",

            "restoration_gate":
                "Restoration Gate V1"
        },

        "limitations":[
            "Disease model has no explicit Healthy class.",
            "Disease predictions are candidate findings.",
            "Restoration type is not classified until a restoration bbox detector is available."
        ],

        "teeth":teeth
    }

    out=Path(
        "artifacts/unified"
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

    jp=out/"dentai_unified_v2.json"

    jp.write_text(
        json.dumps(
            result,
            indent=2
        ),
        encoding="utf-8"
    )

    preview=image.copy()
    draw=ImageDraw.Draw(
        preview
    )

    for t in teeth:

        x1,y1,x2,y2=t[
            "bbox_xyxy"
        ]

        fdi=t[
            "resolved_fdi_number"
        ]

        disease=t[
            "disease"
        ]["candidate"]

        rest=(
            "REST"
            if t[
                "restoration"
            ]["present"]
            else ""
        )

        text=(
            f"{fdi} "
            f"{disease} "
            f"{rest}"
        )

        draw.rectangle(
            [x1,y1,x2,y2],
            width=3
        )

        draw.text(
            (
                x1,
                max(0,y1-15)
            ),
            text
        )

    pp=out/"dentai_unified_v2_preview.jpg"

    preview.save(
        pp,
        quality=95
    )

    print()
    print("="*60)
    print(
        "DENTAI UNIFIED V2 COMPLETE"
    )
    print(
        "Detected teeth:",
        len(teeth)
    )
    print(
        "JSON:",
        jp
    )
    print(
        "Preview:",
        pp
    )
    print("="*60)

    print()

    for t in teeth:

        r=t["restoration"]

        print(
            f'FDI '
            f'{t["resolved_fdi_number"]:>2} | '
            f'FDI={t["fdi_confidence"]:.3f} | '
            f'DISEASE={t["disease"]["candidate"]} '
            f'({t["disease"]["confidence"]:.3f}) | '
            f'REST={"PRESENT" if r["present"] else "ABSENT"} '
            f'({r["present_probability"]:.3f})'
        )


if __name__=="__main__":

    parser=argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        required=True
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=.50
    )

    args=parser.parse_args()

    run(
        args.image,
        args.threshold
    )
