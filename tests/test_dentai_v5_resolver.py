from collections import Counter

import numpy as np
import pytest

from ai_engine.inference.dentai_unified_v5_onnx import (
    FDI,
    FDI_IDX,
    bbox_center_x,
    expected_viewer_side,
    fdi_side_consistent,
    resolve,
)


IMAGE_WIDTH = 1200


def resolver_row(
    fdi: str,
    center_x: float,
    *,
    raw_conf: float = 0.99,
) -> dict:
    probabilities = np.full(len(FDI), 1e-9, dtype=np.float32)
    probabilities[FDI_IDX[fdi]] = raw_conf
    return {
        "id": int(fdi),
        "bbox": [center_x - 20, 200, center_x + 20, 400],
        "probs": probabilities,
        "raw": fdi,
        "raw_conf": raw_conf,
        "score": 0.99,
    }


@pytest.mark.parametrize(
    ("quadrant", "centers", "expected"),
    [
        ("1", [550, 500, 450, 400, 350, 300, 250, 200], [f"1{i}" for i in range(1, 9)]),
        ("2", [650, 700, 750, 800, 850, 900, 950, 1000], [f"2{i}" for i in range(1, 9)]),
        ("3", [650, 700, 750, 800, 850, 900, 950, 1000], [f"3{i}" for i in range(1, 9)]),
        ("4", [550, 500, 450, 400, 350, 300, 250, 200], [f"4{i}" for i in range(1, 9)]),
    ],
)
def test_resolver_orders_center_to_posterior_for_every_quadrant(
    quadrant: str,
    centers: list[int],
    expected: list[str],
) -> None:
    rows = [resolver_row(fdi, center) for fdi, center in zip(expected, centers, strict=True)]

    resolved = resolve(list(reversed(rows)), IMAGE_WIDTH)
    quadrant_rows = [row for row in resolved if row["resolved"].startswith(quadrant)]
    ordered = sorted(
        quadrant_rows,
        key=lambda row: bbox_center_x(row["bbox"]),
        reverse=quadrant in "14",
    )

    assert [row["resolved"] for row in ordered] == expected
    assert all(not row["unresolved"] for row in ordered)


@pytest.mark.parametrize(
    ("fdi", "center_x", "expected_side"),
    [
        ("11", 550, "LEFT"),
        ("18", 200, "LEFT"),
        ("21", 650, "RIGHT"),
        ("28", 1000, "RIGHT"),
        ("31", 650, "RIGHT"),
        ("38", 1000, "RIGHT"),
        ("41", 550, "LEFT"),
        ("48", 200, "LEFT"),
    ],
)
def test_standard_panoramic_side_consistency(
    fdi: str,
    center_x: float,
    expected_side: str,
) -> None:
    box = [center_x - 20, 200, center_x + 20, 400]

    assert expected_viewer_side(fdi) == expected_side
    assert fdi_side_consistent(fdi, box, IMAGE_WIDTH)


def test_production_regression_fdi_38_on_viewer_left_requires_review() -> None:
    row = resolver_row("38", 288)

    resolved = resolve([row], IMAGE_WIDTH)

    assert resolved[0]["resolved"] == "38"
    assert resolved[0]["unresolved"] is True
    assert not fdi_side_consistent("38", [240.56, 381.01, 336.86, 504.73], IMAGE_WIDTH)


def test_over_capacity_duplicate_fdi_detections_are_preserved_but_unresolved() -> None:
    labels = ["31", "32", "33", "34", "34", "35", "35", "36", "37", "38"]
    rows = [
        resolver_row(label, 650 + index * 45, raw_conf=0.99 - index * 0.001)
        for index, label in enumerate(labels)
    ]

    resolved = resolve(rows, IMAGE_WIDTH)
    counts = Counter(row["resolved"] for row in resolved)
    duplicated = {fdi for fdi, count in counts.items() if count > 1}

    assert len(resolved) == 10
    assert duplicated
    assert all(row["unresolved"] for row in resolved if row["resolved"] in duplicated)
    assert not any(not row["unresolved"] for row in resolved if row["resolved"] in duplicated)


def test_duplicate_cleanup_only_uses_an_unambiguous_ordered_missing_slot() -> None:
    labels = ["31", "32", "34", "34", "35", "36", "37", "38"]
    rows = [
        resolver_row(label, 650 + index * 45, raw_conf=0.98 if index == 3 else 0.97)
        for index, label in enumerate(labels)
    ]

    resolved = resolve(rows, IMAGE_WIDTH)
    ordered = sorted(resolved, key=lambda row: bbox_center_x(row["bbox"]))

    assert [row["resolved"] for row in ordered] == [f"3{i}" for i in range(1, 9)]
    assert sum(bool(row.get("cleanup")) for row in ordered) == 1
    assert len({row["resolved"] for row in ordered}) == 8
