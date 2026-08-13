from io import BytesIO

import numpy as np
from PIL import Image, UnidentifiedImageError

from ai_engine.schemas import ImageQuality, QualityLevel


class InvalidRadiographError(ValueError):
    pass


class OPGQualityEngine:
    """Conservative, non-diagnostic image quality gate."""

    def analyze(self, image_bytes: bytes) -> ImageQuality:
        try:
            image = Image.open(BytesIO(image_bytes)).convert("L")
        except (UnidentifiedImageError, OSError) as exc:
            raise InvalidRadiographError("unsupported or corrupt radiograph") from exc
        pixels = np.asarray(image, dtype=np.float32)
        height, width = pixels.shape
        if width < 512 or height < 256:
            return self._result(width, height, pixels, False, ["IMAGE_DIMENSIONS_TOO_SMALL"])
        aspect = width / height
        panoramic_shape = 1.5 <= aspect <= 3.5
        warnings: list[str] = []
        if not panoramic_shape:
            warnings.append("PANORAMIC_GEOMETRY_NOT_CONFIRMED")
        mean = float(pixels.mean())
        contrast = float(pixels.std())
        # Mean absolute adjacent difference is a deterministic sharpness proxy, not diagnosis.
        blur = float(
            (np.abs(np.diff(pixels, axis=0)).mean() + np.abs(np.diff(pixels, axis=1)).mean()) / 2
        )
        if mean < 25:
            warnings.append("POSSIBLE_UNDEREXPOSURE")
        if mean > 230:
            warnings.append("POSSIBLE_OVEREXPOSURE")
        if contrast < 18:
            warnings.append("LOW_CONTRAST")
        if blur < 2:
            warnings.append("POSSIBLE_BLUR")
        usable = panoramic_shape and not {"LOW_CONTRAST", "POSSIBLE_BLUR"}.intersection(warnings)
        return self._result(width, height, pixels, usable, warnings)

    def _result(
        self, width: int, height: int, pixels: np.ndarray, usable: bool, warnings: list[str]
    ) -> ImageQuality:
        quality = QualityLevel.ACCEPTABLE if usable and not warnings else QualityLevel.LIMITED
        if not usable:
            quality = QualityLevel.REQUIRES_RETAKE_OR_REVIEW
        return ImageQuality(
            image_type="PANORAMIC" if 1.5 <= width / max(height, 1) <= 3.5 else "UNCONFIRMED",
            orientation="LANDSCAPE" if width >= height else "PORTRAIT",
            width=width,
            height=height,
            blur_score=float(np.abs(np.diff(pixels, axis=1)).mean()) if width > 1 else 0,
            exposure_mean=float(pixels.mean()),
            contrast_score=float(pixels.std()),
            cropping_suspected=False,
            gross_artifact=False,
            quality=quality,
            usable_for_analysis=usable,
            warnings=warnings,
        )
