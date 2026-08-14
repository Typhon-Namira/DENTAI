"""V1 teacher hard-case scoring and bounded weighted sampling."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

import torch
from torch.utils.data import WeightedRandomSampler


@dataclass(frozen=True)
class HardCaseSignals:
    false_negatives: int = 0
    false_positives: int = 0
    low_confidence_true_positives: int = 0
    merged_teeth: int = 0
    split_teeth: int = 0
    mean_matched_iou: float = 1.0
    categories: tuple[str, ...] = ()


def hard_case_score(signals: HardCaseSignals) -> float:
    """Return a stable 0..1 difficulty score from label-aware teacher errors."""
    raw = (
        0.16 * min(signals.false_negatives, 4)
        + 0.10 * min(signals.false_positives, 4)
        + 0.06 * min(signals.low_confidence_true_positives, 4)
        + 0.18 * min(signals.merged_teeth, 2)
        + 0.14 * min(signals.split_teeth, 2)
        + 0.30 * max(0.0, 1.0 - signals.mean_matched_iou)
        + 0.03 * min(len(set(signals.categories)), 4)
    )
    return min(1.0, round(raw, 6))


def sampling_weight(score: float, *, moderate: float = 1.5, severe: float = 2.25) -> float:
    if not 0 <= score <= 1:
        raise ValueError("hard-case score must be between zero and one")
    return 1.0 if score < 0.35 else moderate if score < 0.7 else severe


def bounded_weights(scores: Iterable[float], *, max_fraction: float = 0.25) -> list[float]:
    """Cap each severity bucket's total probability to avoid tiny-group collapse."""
    weights = [sampling_weight(score) for score in scores]
    buckets = [
        "normal" if weight == 1 else "moderate" if weight < 2 else "severe" for weight in weights
    ]
    counts = Counter(buckets)
    total = sum(weights)
    for bucket in ("moderate", "severe"):
        bucket_total = sum(
            weight for weight, name in zip(weights, buckets, strict=True) if name == bucket
        )
        cap = max_fraction * total
        if bucket_total > cap and counts[bucket]:
            scale = cap / bucket_total
            weights = [
                weight * scale if name == bucket else weight
                for weight, name in zip(weights, buckets, strict=True)
            ]
    return weights


def make_weighted_sampler(scores: Iterable[float], *, seed: int = 47) -> WeightedRandomSampler:
    weights = bounded_weights(scores)
    generator = torch.Generator().manual_seed(seed)
    return WeightedRandomSampler(
        weights, num_samples=len(weights), replacement=True, generator=generator
    )
