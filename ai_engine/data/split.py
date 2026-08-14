import hashlib
import json
from collections.abc import Iterable
from pathlib import Path


def patient_level_split(group_ids: Iterable[str], seed: int = 47) -> dict[str, str]:
    """Stable group split; every derivative sharing a group ID stays in one partition."""
    result = {}
    for group_id in set(group_ids):
        value = int(hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()[:8], 16) % 100
        result[group_id] = "train" if value < 70 else "validation" if value < 85 else "test"
    return result


def assert_no_group_leakage(records: Iterable[dict[str, str]]) -> None:
    seen: dict[str, str] = {}
    for record in records:
        group, partition = record["group_id"], record["split"]
        if group in seen and seen[group] != partition:
            raise ValueError(f"group leakage: {group} appears in {seen[group]} and {partition}")
        seen[group] = partition


def write_locked_split(records: list[dict[str, str]], destination: Path, seed: int) -> str:
    assert_no_group_leakage(records)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1",
        "seed": seed,
        "records": sorted(records, key=lambda x: x["image_id"]),
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    destination.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    destination.with_suffix(".sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="utf-8"
    )
    return digest
