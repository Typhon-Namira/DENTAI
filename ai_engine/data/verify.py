import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual.lower() != expected.lower():
        raise ValueError(f"checksum mismatch for {path.name}")
