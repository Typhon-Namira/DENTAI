import hashlib
from collections.abc import Iterable


def patient_level_split(group_ids: Iterable[str], seed: int = 47) -> dict[str, str]:
    """Stable group split; every derivative sharing a group ID stays in one partition."""
    result = {}
    for group_id in set(group_ids):
        value = int(hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()[:8], 16) % 100
        result[group_id] = "train" if value < 70 else "validation" if value < 85 else "test"
    return result
