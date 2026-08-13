from pathlib import Path
from urllib.parse import urlparse

import httpx

from ai_engine.data.license_guard import require_production_allowed
from ai_engine.data.registry import DatasetManifest
from ai_engine.data.verify import verify_checksum


def download_dataset(manifest: DatasetManifest, destination: Path, production: bool) -> Path:
    if production:
        require_production_allowed(manifest)
    if not manifest.sha256:
        raise ValueError("downloads require a registry checksum")
    if urlparse(manifest.source_url).scheme != "https":
        raise ValueError("dataset downloads require HTTPS")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{manifest.dataset_id}-{manifest.version}.archive"
    temporary = target.with_suffix(".partial")
    with httpx.stream("GET", manifest.source_url, follow_redirects=True, timeout=120) as response:
        response.raise_for_status()
        with temporary.open("wb") as stream:
            for chunk in response.iter_bytes():
                stream.write(chunk)
    verify_checksum(temporary, manifest.sha256)
    temporary.replace(target)
    return target
