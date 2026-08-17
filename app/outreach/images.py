from io import BytesIO

from PIL import Image

from app.database.models import DentalFinding, XRay
from app.storage.providers import storage_provider


async def finding_crop(xray: XRay, finding: DentalFinding) -> bytes | None:
    box = (finding.provenance or {}).get("bounding_box")
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    try:
        left, top, right, bottom = [float(value) for value in box]
    except (TypeError, ValueError):
        return None
    data = await storage_provider().read(xray.storage_key)
    image = Image.open(BytesIO(data)).convert("RGB")
    pad_x, pad_y = (right - left) * 0.15, (bottom - top) * 0.15
    crop_box = (
        max(0, int(left - pad_x)),
        max(0, int(top - pad_y)),
        min(image.width, int(right + pad_x)),
        min(image.height, int(bottom + pad_y)),
    )
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        return None
    output = BytesIO()
    image.crop(crop_box).save(output, format="JPEG", quality=88, optimize=True)
    return output.getvalue()
