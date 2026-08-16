import json
import math
from pathlib import Path
from collections import Counter, defaultdict

import torch
from PIL import Image
from torchvision.transforms.functional import to_tensor

from ai_engine.inference.dentai_unified_v2 import (
    DEVICE,
    load_tooth,
    load_fdi,
    FDI_TF,
    FDI_CLASSES,
    geometry,
)

TEST_FILE = Path("data/splits/tooth_v2/test.json")

QUADRANTS = {
    "1": ["11","12","13","14","15","16","17","18"],
    "2": ["21","22","23","24","25","26","27","28"],
    "3": ["31","32","33","34","35","36","37","38"],
    "4": ["41","42","43","44","45","46","47","48"],
}

CLASS_TO_IDX = {
    c:i for i,c in enumerate(FDI_CLASSES)
}


def box_iou(a,b):
    ax1,ay1,ax2,ay2 = a
    bx1,by1,bx2,by2 = b

    ix1=max(ax1,bx1)
    iy1=max(ay1,by1)
    ix2=min(ax2,bx2)
    iy2=min(ay2,by2)

    iw=max(0,ix2-ix1)
    ih=max(0,iy2-iy1)

    inter=iw*ih

    aa=max(0,ax2-ax1)*max(0,ay2-ay1)
    bb=max(0,bx2-bx1)*max(0,by2-by1)

    union=aa+bb-inter
    return inter/union if union>0 else 0.0


def center_x(box):
    return (box[0]+box[2])/2.0


def get_fdi_probs(model,image,box):
    W,H=image.size

    (
        x1,y1,x2,y2,
        bw,bh,cx,cy,nw,nh
    ) = geometry(box,W,H)

    spatial=torch.tensor(
        [[cx,cy,nw,nh]],
        dtype=torch.float32,
        device=DEVICE
    )

    pad_x=max(12,int(bw*0.35))
    pad_y=max(12,int(bh*0.35))

    crop=image.crop((
        max(0,int(x1)-pad_x),
        max(0,int(y1)-pad_y),
        min(W,int(x2)+pad_x),
        min(H,int(y2)+pad_y),
    ))

    tensor=FDI_TF(crop).unsqueeze(0).to(DEVICE)

    with torch.no_grad(), torch.amp.autocast(
        "cuda",
        enabled=DEVICE.type=="cuda",
        dtype=torch.bfloat16
    ):
        logits=model(tensor,spatial)

    return torch.softmax(
        logits.float(),
        dim=1
    )[0].detach().cpu()


def quadrant_from_probs(probs):
    q_scores={}

    for q,classes in QUADRANTS.items():
        q_scores[q]=sum(
            float(probs[CLASS_TO_IDX[c]])
            for c in classes
        )

    return max(
        q_scores,
        key=q_scores.get
    )


def sort_quadrant(teeth,q):
    # FDI orientation on panoramic radiographs:
    # Q1/Q3 tooth number rises toward decreasing x.
    reverse = q in ("1","3")

    return sorted(
        teeth,
        key=lambda t:center_x(t["bbox"]),
        reverse=reverse
    )


def sequence_resolve(teeth,q):
    """
    Global monotonic assignment inside one quadrant.

    Operations:
      assign detection -> FDI
      skip FDI = missing tooth
      skip detection = unresolved extra detection
    """

    teeth=sort_quadrant(teeth,q)
    labels=QUADRANTS[q]

    n=len(teeth)
    m=len(labels)

    INF=1e9

    # dp[i][j] = minimum cost after considering
    # first i detections and first j labels.
    dp=[
        [INF]*(m+1)
        for _ in range(n+1)
    ]

    parent=[
        [None]*(m+1)
        for _ in range(n+1)
    ]

    dp[0][0]=0.0

    missing_penalty=0.30
    extra_detection_penalty=1.60

    for i in range(n+1):
        for j in range(m+1):
            current=dp[i][j]

            if current>=INF:
                continue

            # Missing FDI label.
            if j<m:
                cost=current+missing_penalty

                if cost<dp[i][j+1]:
                    dp[i][j+1]=cost
                    parent[i][j+1]=(i,j,"skip_label")

            # Ignore an extra / uncertain detection.
            if i<n:
                cost=current+extra_detection_penalty

                if cost<dp[i+1][j]:
                    dp[i+1][j]=cost
                    parent[i+1][j]=(i,j,"skip_detection")

            # Assign.
            if i<n and j<m:
                label=labels[j]
                p=max(
                    float(
                        teeth[i]["probs"][
                            CLASS_TO_IDX[label]
                        ]
                    ),
                    1e-8
                )

                assign_cost=-math.log(p)

                raw=teeth[i]["raw"]

                # Slight preference for preserving original model output.
                if raw==label:
                    assign_cost-=0.25

                cost=current+assign_cost

                if cost<dp[i+1][j+1]:
                    dp[i+1][j+1]=cost
                    parent[i+1][j+1]=(i,j,"assign")

    # Allow ending at any j after all detections handled.
    end_j=min(
        range(m+1),
        key=lambda j:
            dp[n][j]
            + (m-j)*missing_penalty
    )

    i=n
    j=end_j

    assignments={}

    while i>0 or j>0:
        p=parent[i][j]

        if p is None:
            break

        pi,pj,action=p

        if action=="assign":
            assignments[pi]=labels[pj]

        elif action=="skip_detection":
            assignments[pi]=None

        i,j=pi,pj

    results=[]

    for idx,tooth in enumerate(teeth):
        resolved=assignments.get(idx)

        results.append({
            **tooth,
            "resolved": resolved or tooth["raw"],
            "was_changed": (
                resolved is not None
                and resolved != tooth["raw"]
            ),
            "unresolved_by_dp": resolved is None,
        })

    return results


def resolve_image(pred_teeth):
    groups=defaultdict(list)

    for tooth in pred_teeth:
        q=quadrant_from_probs(
            tooth["probs"]
        )

        groups[q].append(tooth)

    output=[]

    for q in ("1","2","3","4"):
        if groups[q]:
            output.extend(
                sequence_resolve(
                    groups[q],
                    q
                )
            )

    return output


def main():
    print("="*70)
    print("FDI RESOLVER V3 GLOBAL TEST")
    print("Device:",DEVICE)
    print("="*70)

    tooth_model=load_tooth()
    fdi_model=load_fdi()

    data=json.loads(
        TEST_FILE.read_text()
    )

    total=0
    raw_correct=0
    v3_correct=0

    matched_teeth=0

    raw_duplicate_images=0
    v3_duplicate_images=0

    changed=0
    changed_correctly=0
    changed_incorrectly=0

    for image_index,record in enumerate(
        data["records"],
        start=1
    ):
        image=Image.open(
            record["image_path"]
        ).convert("RGB")

        image_tensor=to_tensor(
            image
        ).to(DEVICE)

        with torch.no_grad():
            pred=tooth_model(
                [image_tensor]
            )[0]

        boxes=pred["boxes"].detach().cpu()
        scores=pred["scores"].detach().cpu()

        keep=scores>=0.50
        boxes=boxes[keep]

        pred_teeth=[]

        for box in boxes:
            b=box.tolist()

            probs=get_fdi_probs(
                fdi_model,
                image,
                b
            )

            conf,idx=probs.max(0)

            raw=FDI_CLASSES[
                idx.item()
            ]

            pred_teeth.append({
                "bbox":b,
                "raw":raw,
                "raw_conf":float(conf),
                "probs":probs,
            })

        raw_counts=Counter(
            t["raw"]
            for t in pred_teeth
        )

        if any(
            n>1
            for n in raw_counts.values()
        ):
            raw_duplicate_images+=1

        resolved=resolve_image(
            pred_teeth
        )

        v3_counts=Counter(
            t["resolved"]
            for t in resolved
        )

        if any(
            n>1
            for n in v3_counts.values()
        ):
            v3_duplicate_images+=1

        gt_instances=[
            x for x in record.get(
                "instances",[]
            )
            if x.get(
                "canonical_class"
            )=="TOOTH"
        ]

        used=set()

        for gt in gt_instances:
            gt_box=gt.get(
                "bbox_xyxy"
            )

            gt_fdi=str(
                gt.get(
                    "fdi_number",""
                )
            )

            if not gt_box:
                continue

            best_iou=0
            best_j=None

            for j,p in enumerate(
                resolved
            ):
                if j in used:
                    continue

                v=box_iou(
                    gt_box,
                    p["bbox"]
                )

                if v>best_iou:
                    best_iou=v
                    best_j=j

            if (
                best_j is None
                or best_iou<0.50
            ):
                continue

            used.add(best_j)

            p=resolved[best_j]

            total+=1
            matched_teeth+=1

            raw_ok=(
                p["raw"]==gt_fdi
            )

            v3_ok=(
                p["resolved"]==gt_fdi
            )

            raw_correct+=int(raw_ok)
            v3_correct+=int(v3_ok)

            if p["was_changed"]:
                changed+=1

                if (
                    not raw_ok
                    and v3_ok
                ):
                    changed_correctly+=1

                elif (
                    raw_ok
                    and not v3_ok
                ):
                    changed_incorrectly+=1

        if image_index%20==0:
            print(
                f"processed "
                f"{image_index}/"
                f"{len(data['records'])}"
            )

    raw_acc=raw_correct/max(total,1)
    v3_acc=v3_correct/max(total,1)

    print()
    print("="*70)
    print("FDI RESOLVER V3 RESULTS")
    print("="*70)

    print(
        "Matched teeth:",
        matched_teeth
    )

    print(
        "Raw FDI accuracy:",
        round(raw_acc,4)
    )

    print(
        "Resolver V2 reference:",
        0.9001
    )

    print(
        "Resolver V3 accuracy:",
        round(v3_acc,4)
    )

    print(
        "Absolute improvement vs raw:",
        round(
            (v3_acc-raw_acc)*100,
            2
        ),
        "percentage points"
    )

    print(
        "Images with duplicate FDI before:",
        raw_duplicate_images
    )

    print(
        "Images with duplicate FDI after V3:",
        v3_duplicate_images
    )

    print(
        "Assignments changed:",
        changed
    )

    print(
        "Wrong -> correct changes:",
        changed_correctly
    )

    print(
        "Correct -> wrong changes:",
        changed_incorrectly
    )

    if v3_acc>0.9001:
        print()
        print(
            "✅ V3 BEATS RESOLVER V2"
        )
    else:
        print()
        print(
            "⚠️ V3 DOES NOT BEAT V2 — "
            "do not deploy it yet"
        )

    print("="*70)


if __name__=="__main__":
    main()
