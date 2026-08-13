from dataclasses import dataclass


@dataclass(frozen=True)
class ToothCandidate:
    x_center: float
    y_center: float
    confidence: float


def assign_fdi(candidates: list[ToothCandidate]) -> list[tuple[ToothCandidate, str]]:
    """Map complete adult arches; abnormal or incomplete arches require a trained mapper."""
    upper = sorted(
        (item for item in candidates if item.y_center < 0.5), key=lambda item: item.x_center
    )
    lower = sorted(
        (item for item in candidates if item.y_center >= 0.5), key=lambda item: item.x_center
    )
    result: list[tuple[ToothCandidate, str]] = []
    if len(upper) == 16:
        labels = [f"1{i}" for i in range(8, 0, -1)] + [f"2{i}" for i in range(1, 9)]
        result.extend(zip(upper, labels, strict=True))
    if len(lower) == 16:
        labels = [f"4{i}" for i in range(8, 0, -1)] + [f"3{i}" for i in range(1, 9)]
        result.extend(zip(lower, labels, strict=True))
    return result
