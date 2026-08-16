"""Mine Tooth V2 development hard cases with the frozen V1 teacher (CUDA only)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from PIL import Image, ImageDraw
from torchvision.ops import box_iou

from ai_engine.training.dataset import V2ManifestDataset
from ai_engine.training.hard_cases import HardCaseSignals, hard_case_score, sampling_weight
from ai_engine.training.maskrcnn import build_maskrcnn


def _score(output: dict, target: dict, threshold: float) -> tuple[HardCaseSignals, list[int]]:
    keep = output["scores"] >= threshold
    boxes, scores = output["boxes"][keep].cpu(), output["scores"][keep].cpu()
    expected = target["boxes"].cpu()
    ious = (
        box_iou(boxes, expected)
        if len(boxes) and len(expected)
        else torch.zeros((len(boxes), len(expected)))
    )
    claimed: set[int] = set()
    matched_ious: list[float] = []
    low_confidence = 0
    for prediction in scores.argsort(descending=True).tolist():
        candidates = ious[prediction].clone()
        if claimed:
            candidates[list(claimed)] = -1
        if len(candidates) and float(candidates.max()) >= 0.5:
            value, expected_index = candidates.max(dim=0)
            claimed.add(int(expected_index))
            matched_ious.append(float(value))
            low_confidence += int(float(scores[prediction]) < 0.7)
    false_negatives = len(expected) - len(claimed)
    false_positives = len(boxes) - len(claimed)
    categories = []
    if false_negatives:
        categories.append("false_negative")
    if false_positives:
        categories.append("false_positive")
    if low_confidence:
        categories.append("low_confidence_true_positive")
    signals = HardCaseSignals(
        false_negatives=false_negatives,
        false_positives=false_positives,
        low_confidence_true_positives=low_confidence,
        mean_matched_iou=sum(matched_ious) / len(matched_ious) if matched_ious else 0.0,
        categories=tuple(categories),
    )
    return signals, keep.nonzero().flatten().tolist()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=Path("checkpoints/tooth_v1/best.pt"))
    parser.add_argument("--manifest", type=Path, default=Path("data/splits/tooth_v2/train.json"))
    parser.add_argument("--output", type=Path, default=Path("data/splits/tooth_v2/hard_cases.json"))
    parser.add_argument("--overlays", type=Path, default=Path("artifacts/hard_cases/tooth_v2"))
    parser.add_argument("--score-threshold", type=float, default=0.35)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable: hard-case mining was not executed")
    dataset = V2ManifestDataset(args.manifest, (1024, 512), train=False)
    model = build_maskrcnn(pretrained=False).cuda().eval()
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model"])
    args.overlays.mkdir(parents=True, exist_ok=True)
    cases = []
    with torch.no_grad():
        for index in range(len(dataset)):
            image_tensor, target = dataset[index]
            output = model([image_tensor.cuda()])[0]
            signals, kept = _score(output, target, 0.35)
            score = hard_case_score(signals)
            if score < args.score_threshold:
                continue
            record = dataset.records[index]
            cases.append(
                {
                    "canonical_image_id": record["canonical_image_id"],
                    "hard_case_score": score,
                    "sampling_weight": sampling_weight(score),
                    "signals": signals.__dict__,
                }
            )
            if len(cases) <= 50:
                canvas = Image.open(record["image_path"]).convert("RGB").resize((1024, 512))
                draw = ImageDraw.Draw(canvas)
                for box in target["boxes"].tolist():
                    draw.rectangle(box, outline="lime", width=2)
                for prediction in kept:
                    draw.rectangle(
                        output["boxes"][prediction].cpu().tolist(), outline="red", width=2
                    )
                canvas.save(args.overlays / f"hard_{len(cases):03d}.jpg", quality=90)
    payload = {
        "status": "RESEARCH_ONLY",
        "teacher_checkpoint": str(args.checkpoint),
        "source_split": "train_only",
        "hard_case_count": len(cases),
        "cases": cases,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
