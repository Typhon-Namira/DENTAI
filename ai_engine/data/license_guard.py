from ai_engine.data.registry import DatasetManifest, DatasetTier


class DatasetLicenseError(PermissionError):
    pass


def require_production_allowed(manifest: DatasetManifest) -> None:
    if manifest.tier != DatasetTier.PRODUCTION_ALLOWED:
        raise DatasetLicenseError(f"{manifest.dataset_id} tier is {manifest.tier}")
    if not manifest.commercial_use_allowed or not manifest.modification_allowed:
        raise DatasetLicenseError(f"{manifest.dataset_id} is not approved for production training")
    if not manifest.sha256:
        raise DatasetLicenseError(f"{manifest.dataset_id} requires a verified artifact checksum")
