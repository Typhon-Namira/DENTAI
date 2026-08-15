import json
from pathlib import Path
from collections import Counter

INPUT = Path("artifacts/unified/dentai_unified_v1.json")
OUTPUT = Path("artifacts/unified/dentai_unified_v1_resolved.json")

# Expected permanent-dentition order per quadrant.
QUADRANTS = {
    1: ["11","12","13","14","15","16","17","18"],
    2: ["21","22","23","24","25","26","27","28"],
    3: ["31","32","33","34","35","36","37","38"],
    4: ["41","42","43","44","45","46","47","48"],
}

ALL_FDI = [x for q in QUADRANTS.values() for x in q]


def center(box):
    x1, y1, x2, y2 = box
    return ((x1+x2)/2.0, (y1+y2)/2.0)


def expected_quadrant(tooth, image_mid_x, image_mid_y):
    cx, cy = center(tooth["bbox_xyxy"])

    # FDI patient laterality in panoramic display:
    # image-left usually corresponds to patient's right.
    upper = cy < image_mid_y
    image_left = cx < image_mid_x

    if upper and image_left:
        return 1
    if upper and not image_left:
        return 2
    if not upper and not image_left:
        return 3
    return 4


def sort_for_quadrant(teeth, quadrant):
    # Within each quadrant, order from midline -> posterior.
    #
    # q1: image x tends to decrease from 11 -> 18
    # q2: image x tends to increase from 21 -> 28
    # q3: image x tends to decrease from 31 -> 38
    # q4: image x tends to increase from 41 -> 48
    reverse = quadrant in (1, 3)

    return sorted(
        teeth,
        key=lambda t: center(t["bbox_xyxy"])[0],
        reverse=reverse
    )


def candidate_score(tooth, candidate, expected_index):
    raw = tooth["fdi_number"]
    conf = float(tooth.get("fdi_confidence", 0.0))

    score = 0.0

    # Strong reward for keeping a confident original FDI.
    if raw == candidate:
        score += 2.5 * conf

    # Small reward for retaining quadrant.
    try:
        if raw and raw[0] == candidate[0]:
            score += 0.30
    except Exception:
        pass

    # Spatial order penalty.
    cand_idx = int(candidate[1]) - 1
    score -= abs(cand_idx - expected_index) * 0.22

    return score


def resolve_quadrant(teeth, quadrant):
    ordered = sort_for_quadrant(teeth, quadrant)
    expected = QUADRANTS[quadrant]

    # Greedy monotonic assignment with uniqueness.
    available = expected.copy()
    resolved = []

    for idx, tooth in enumerate(ordered):
        raw = tooth["fdi_number"]
        conf = float(tooth.get("fdi_confidence", 0.0))

        # If original is valid, unused, same quadrant and confidence is good,
        # preserve it unless it badly breaks ordering.
        if (
            raw in available
            and raw.startswith(str(quadrant))
            and conf >= 0.85
        ):
            raw_pos = expected.index(raw)

            if abs(raw_pos - idx) <= 1:
                chosen = raw
                available.remove(chosen)

                resolved.append((tooth, chosen, "kept_high_confidence"))
                continue

        # Otherwise choose best remaining candidate.
        best = max(
            available,
            key=lambda c: candidate_score(tooth, c, idx)
        )

        available.remove(best)

        reason = (
            "resolved_low_confidence"
            if conf < 0.70
            else "resolved_sequence_conflict"
        )

        resolved.append((tooth, best, reason))

    return resolved


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    teeth = data["teeth"]

    # Estimate image coordinate midlines from detections.
    centers = [center(t["bbox_xyxy"]) for t in teeth]

    xs = [x for x, _ in centers]
    ys = [y for _, y in centers]

    image_mid_x = (min(xs) + max(xs)) / 2.0
    image_mid_y = (min(ys) + max(ys)) / 2.0

    groups = {1: [], 2: [], 3: [], 4: []}

    for tooth in teeth:
        q = expected_quadrant(
            tooth,
            image_mid_x,
            image_mid_y
        )
        groups[q].append(tooth)

    output_teeth = []

    for q in (1,2,3,4):
        resolved = resolve_quadrant(groups[q], q)

        for tooth, resolved_fdi, reason in resolved:
            new = dict(tooth)

            new["raw_fdi_number"] = tooth["fdi_number"]
            new["resolved_fdi_number"] = resolved_fdi

            new["fdi_was_changed"] = (
                tooth["fdi_number"] != resolved_fdi
            )

            new["fdi_resolution_reason"] = reason

            # Preserve original confidence.
            new["raw_fdi_confidence"] = tooth.get(
                "fdi_confidence"
            )

            output_teeth.append(new)

    output_teeth.sort(
        key=lambda x: int(x["resolved_fdi_number"])
    )

    resolved_counts = Counter(
        t["resolved_fdi_number"]
        for t in output_teeth
    )

    duplicate_resolved = {
        k:v for k,v in resolved_counts.items()
        if v > 1
    }

    changed = [
        t for t in output_teeth
        if t["fdi_was_changed"]
    ]

    result = dict(data)

    result["schema_version"] = (
        "dentai-unified-v1-arch-resolved"
    )

    result["arch_resolver"] = {
        "version": "1.0",
        "changed_count": len(changed),
        "remaining_duplicate_fdi": duplicate_resolved,
        "note": (
            "Rule-based anatomical resolver. "
            "Resolved FDI must remain reviewable; "
            "raw model output is preserved."
        )
    }

    result["teeth"] = output_teeth

    OUTPUT.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8"
    )

    print("="*60)
    print("DENTAL ARCH RESOLVER V1 COMPLETE")
    print("="*60)

    print("Input teeth:", len(teeth))
    print("Changed FDI assignments:", len(changed))
    print("Remaining duplicates:", duplicate_resolved)
    print("Output:", OUTPUT)

    print("\n=== CHANGED FDI ===")

    for t in changed:
        print(
            f'raw={t["raw_fdi_number"]} '
            f'({t["raw_fdi_confidence"]:.3f}) '
            f'-> resolved={t["resolved_fdi_number"]} '
            f'| {t["fdi_resolution_reason"]}'
        )

    print("\n=== FINAL FDI SEQUENCE ===")

    print(
        " ".join(
            t["resolved_fdi_number"]
            for t in output_teeth
        )
    )


if __name__ == "__main__":
    main()
