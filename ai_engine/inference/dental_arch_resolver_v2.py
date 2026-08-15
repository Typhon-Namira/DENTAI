import json
from pathlib import Path
from collections import Counter, defaultdict

INPUT = Path("artifacts/unified/dentai_unified_v1.json")
OUTPUT = Path("artifacts/unified/dentai_unified_v2_resolved.json")

QUADRANTS = {
    "1": ["11","12","13","14","15","16","17","18"],
    "2": ["21","22","23","24","25","26","27","28"],
    "3": ["31","32","33","34","35","36","37","38"],
    "4": ["41","42","43","44","45","46","47","48"],
}

LOCK_CONF = 0.85


def cx(tooth):
    x1, _, x2, _ = tooth["bbox_xyxy"]
    return (x1 + x2) / 2.0


def expected_x_direction(quadrant):
    # Based on the raw FDI orientation already learned by the model.
    # q1/q3: FDI position increases toward decreasing image-x.
    # q2/q4: FDI position increases toward increasing image-x.
    return -1 if quadrant in ("1", "3") else 1


def spatial_rank(teeth, quadrant):
    direction = expected_x_direction(quadrant)
    return sorted(
        teeth,
        key=lambda t: direction * cx(t)
    )


def resolve():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    teeth = [dict(t) for t in data["teeth"]]

    # Preserve every raw prediction.
    for t in teeth:
        t["raw_fdi_number"] = t["fdi_number"]
        t["raw_fdi_confidence"] = t.get("fdi_confidence", 0.0)
        t["resolved_fdi_number"] = t["fdi_number"]
        t["fdi_was_changed"] = False
        t["fdi_resolution_reason"] = "unchanged"

    groups = defaultdict(list)

    # IMPORTANT:
    # Never move a tooth to another quadrant based only on geometry.
    # Use model quadrant as the initial anatomical anchor.
    for t in teeth:
        raw = str(t["raw_fdi_number"])
        if len(raw) == 2 and raw[0] in QUADRANTS:
            groups[raw[0]].append(t)

    changed = []

    for q, group in groups.items():
        expected = QUADRANTS[q]

        counts = Counter(
            t["raw_fdi_number"] for t in group
        )

        duplicates = {
            fdi for fdi, n in counts.items()
            if n > 1
        }

        present = set(counts)
        missing = [
            fdi for fdi in expected
            if fdi not in present
        ]

        # Only duplicate members and very low-confidence predictions
        # are eligible for reassignment.
        movable = []

        for t in group:
            raw = t["raw_fdi_number"]
            conf = float(t["raw_fdi_confidence"])

            if raw in duplicates:
                movable.append(t)
            elif conf < 0.50:
                movable.append(t)

        if not movable:
            continue

        ordered = spatial_rank(group, q)

        # Estimate expected tooth position from spatial rank.
        # Do NOT require all 8 teeth to exist.
        rank = {
            id(t): i for i, t in enumerate(ordered)
        }

        # First handle duplicates.
        for duplicated_fdi in duplicates:
            members = [
                t for t in group
                if t["raw_fdi_number"] == duplicated_fdi
            ]

            # Keep the most confident duplicate unchanged.
            keeper = max(
                members,
                key=lambda t: float(t["raw_fdi_confidence"])
            )

            for t in members:
                if t is keeper:
                    t["fdi_resolution_reason"] = (
                        "duplicate_kept_highest_confidence"
                    )
                    continue

                if not missing:
                    t["fdi_resolution_reason"] = (
                        "duplicate_unresolved_no_safe_candidate"
                    )
                    continue

                current_rank = rank[id(t)]

                # Pick missing FDI whose numeric position is spatially closest.
                def score(candidate):
                    candidate_pos = int(candidate[1]) - 1

                    # normalize ranks when fewer than 8 teeth are present
                    if len(ordered) > 1:
                        approx_pos = (
                            current_rank
                            * 7.0
                            / (len(ordered) - 1)
                        )
                    else:
                        approx_pos = 0

                    return abs(candidate_pos - approx_pos)

                candidate = min(missing, key=score)

                # Safety rule: never jump across quadrant.
                if candidate[0] != q:
                    continue

                t["resolved_fdi_number"] = candidate
                t["fdi_was_changed"] = True
                t["fdi_resolution_reason"] = (
                    "duplicate_resolved_with_missing_same_quadrant"
                )

                missing.remove(candidate)
                changed.append(t)

        # Low-confidence non-duplicate labels are NOT automatically rewritten.
        # They are simply flagged for review.
        for t in group:
            conf = float(t["raw_fdi_confidence"])

            if (
                conf < 0.70
                and not t["fdi_was_changed"]
            ):
                t["fdi_resolution_reason"] = (
                    "low_confidence_review_required"
                )

    resolved_counts = Counter(
        t["resolved_fdi_number"] for t in teeth
    )

    remaining_duplicates = {
        k: v for k, v in resolved_counts.items()
        if v > 1
    }

    teeth.sort(
        key=lambda t: int(t["resolved_fdi_number"])
    )

    result = dict(data)

    result["schema_version"] = (
        "dentai-unified-v1-arch-resolver-v2"
    )

    result["arch_resolver"] = {
        "version": "2.0-conservative",
        "changed_count": len(changed),
        "remaining_duplicates": remaining_duplicates,
        "policy": (
            "Preserve confident model predictions. "
            "Never force complete dentition. "
            "Never move teeth across FDI quadrants. "
            "Only resolve duplicate assignments using missing labels "
            "inside the same quadrant."
        ),
    }

    result["teeth"] = teeth

    OUTPUT.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    print("=" * 64)
    print("DENTAL ARCH RESOLVER V2 COMPLETE")
    print("=" * 64)

    print("Input teeth:", len(teeth))
    print("Changed assignments:", len(changed))
    print("Remaining duplicates:", remaining_duplicates)
    print("Output:", OUTPUT)

    print("\n=== ACTUAL CHANGES ===")

    if not changed:
        print("No FDI assignments changed.")

    for t in changed:
        print(
            f'{t["raw_fdi_number"]} '
            f'({t["raw_fdi_confidence"]:.3f}) '
            f'-> {t["resolved_fdi_number"]} '
            f'| {t["fdi_resolution_reason"]}'
        )

    print("\n=== LOW-CONFIDENCE / REVIEW ===")

    for t in teeth:
        if float(t["raw_fdi_confidence"]) < 0.70:
            print(
                f'raw={t["raw_fdi_number"]} '
                f'conf={t["raw_fdi_confidence"]:.3f} '
                f'resolved={t["resolved_fdi_number"]} '
                f'| {t["fdi_resolution_reason"]}'
            )

    print("\n=== RESOLVED FDI ===")
    print(
        " ".join(
            t["resolved_fdi_number"]
            for t in teeth
        )
    )


if __name__ == "__main__":
    resolve()
