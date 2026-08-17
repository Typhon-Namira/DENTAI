from collections import Counter
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

import ai_engine.inference.dentai_unified_v5_onnx as unified_v5
from ai_engine.inference.dentai_unified_v5_onnx import (
    CENTER_DEAD_ZONE_FRACTION,
    FDI,
    FDI_IDX,
    Engine,
    allowed_quadrants_for_bbox,
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
    alternatives: dict[str, float] | None = None,
    bbox: list[float] | None = None,
) -> dict:
    probabilities = np.full(len(FDI), 1e-9, dtype=np.float32)
    probabilities[FDI_IDX[fdi]] = raw_conf
    for candidate, probability in (alternatives or {}).items():
        probabilities[FDI_IDX[candidate]] = probability
    return {
        "id": int(fdi),
        "bbox": bbox or [center_x - 20, 200, center_x + 20, 400],
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
    quadrant_rows = [
        row
        for row in resolved
        if row["resolved"] is not None and row["resolved"].startswith(quadrant)
    ]
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
        ("11", 520, "LEFT"),
        ("18", 200, "LEFT"),
        ("21", 680, "RIGHT"),
        ("28", 1000, "RIGHT"),
        ("31", 680, "RIGHT"),
        ("38", 1000, "RIGHT"),
        ("41", 520, "LEFT"),
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


def test_viewer_left_raw_q3_is_constrained_before_resolution() -> None:
    box = [240.56, 381.01, 336.86, 504.73]
    row = resolver_row("37", 288, alternatives={"47": 0.80}, bbox=box)

    resolved = resolve([row], IMAGE_WIDTH)[0]

    assert resolved["raw"] == "37"
    assert resolved["quadrant_candidates"] == ["1", "4"]
    assert resolved["side_constraint_applied"] is True
    assert resolved["side_constraint_overrode_raw_quadrant"] is True
    assert resolved["resolved"] is None or resolved["resolved"].startswith(("1", "4"))
    assert resolved["resolved"] != "37"


def test_viewer_right_raw_q4_is_constrained_before_resolution() -> None:
    row = resolver_row("47", 900, alternatives={"37": 0.80})

    resolved = resolve([row], IMAGE_WIDTH)[0]

    assert resolved["raw"] == "47"
    assert resolved["quadrant_candidates"] == ["2", "3"]
    assert resolved["side_constraint_overrode_raw_quadrant"] is True
    assert resolved["resolved"] is None or resolved["resolved"].startswith(("2", "3"))
    assert resolved["resolved"] != "47"


@pytest.mark.parametrize(
    ("raw_fdi", "center_x"),
    [("11", 580), ("21", 620), ("31", 580), ("41", 620)],
)
def test_center_dead_zone_does_not_hard_gate_incisors(
    raw_fdi: str,
    center_x: float,
) -> None:
    row = resolver_row(raw_fdi, center_x)

    resolved = resolve([row], IMAGE_WIDTH)[0]

    assert CENTER_DEAD_ZONE_FRACTION == 0.08
    assert allowed_quadrants_for_bbox(row["bbox"], IMAGE_WIDTH) == ("1", "2", "3", "4")
    assert resolved["quadrant_candidates"] == ["1", "2", "3", "4"]
    assert resolved["side_constraint_applied"] is False
    assert resolved["resolved"] == raw_fdi


def test_dp_unresolved_does_not_promote_raw_fdi() -> None:
    row = resolver_row("37", 900)
    row["probs"] = np.zeros(len(FDI), dtype=np.float32)

    resolved = resolve([row], IMAGE_WIDTH)[0]

    assert resolved["raw"] == "37"
    assert resolved["resolved"] is None
    assert resolved["unresolved"] is True


def test_over_capacity_rows_keep_raw_trace_and_null_ambiguous_final_fdi() -> None:
    labels = ["31", "32", "33", "34", "34", "35", "35", "36", "37", "38"]
    rows = [
        resolver_row(label, 680 + index * 40, raw_conf=0.99 - index * 0.001)
        for index, label in enumerate(labels)
    ]

    resolved = resolve(rows, IMAGE_WIDTH)
    non_null = [row["resolved"] for row in resolved if row["resolved"] is not None]
    unresolved = [row for row in resolved if row["resolved"] is None]

    assert len(resolved) == 10
    assert len(non_null) == len(set(non_null))
    assert unresolved
    assert all(row["unresolved"] for row in unresolved)
    assert Counter(row["raw"] for row in resolved)["34"] == 2
    assert Counter(row["raw"] for row in resolved)["35"] == 2


def test_production_inspired_30_detection_fixture_has_safe_final_fdi() -> None:
    rows = []
    rows.extend(
        resolver_row(f"1{index}", 600 - index * 45)
        for index in range(1, 9)
    )
    rows.extend(
        resolver_row(
            "37" if index == 7 else f"4{index}",
            600 - index * 45,
            alternatives={"47": 0.95} if index == 7 else None,
        )
        for index in range(1, 8)
    )
    rows.extend(
        resolver_row(f"2{index}", 600 + index * 45)
        for index in range(1, 8)
    )
    rows.extend(
        resolver_row(
            "47" if index == 7 else f"3{index}",
            600 + index * 45,
            alternatives={"37": 0.95} if index == 7 else None,
        )
        for index in range(1, 9)
    )

    resolved = resolve(list(reversed(rows)), IMAGE_WIDTH)
    non_null = [row["resolved"] for row in resolved if row["resolved"] is not None]

    assert len(resolved) == 30
    assert len(non_null) == len(set(non_null))
    assert all(
        fdi_side_consistent(row["resolved"], row["bbox"], IMAGE_WIDTH)
        for row in resolved
        if row["resolved"] is not None
    )
    assert all(
        not (
            bbox_center_x(row["bbox"]) < IMAGE_WIDTH / 2
            and row["resolved"] is not None
            and row["resolved"].startswith(("2", "3"))
        )
        for row in resolved
    )
    assert all(
        not (
            bbox_center_x(row["bbox"]) > IMAGE_WIDTH / 2
            and row["resolved"] is not None
            and row["resolved"].startswith(("1", "4"))
        )
        for row in resolved
    )


def test_analyze_bytes_passes_opened_image_width_to_resolver(monkeypatch) -> None:
    captured: list[tuple[int, int | None]] = []

    def fake_detect(*_args):
        return (
            np.empty((0, 4), dtype=np.float32),
            np.empty(0, dtype=np.float32),
            np.empty(0, dtype=np.int64),
        )

    def fake_resolve(rows, image_width=None):
        captured.append((len(rows), image_width))
        return []

    monkeypatch.setattr(unified_v5, "detect", fake_detect)
    monkeypatch.setattr(unified_v5, "resolve", fake_resolve)

    engine = Engine.__new__(Engine)
    engine.s = {
        name: object()
        for name in ("tooth", "pre", "fdi", "gate", "status", "path", "deep", "rd", "rc")
    }
    image_bytes = BytesIO()
    Image.new("RGB", (1200, 684), color="black").save(image_bytes, format="PNG")

    result = engine.analyze_bytes(image_bytes.getvalue())

    assert captured == [(0, 1200)]
    assert result["summary"]["teeth"] == 0
