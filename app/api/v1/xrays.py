import logging
import uuid
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy import delete, select, update

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, current_context
from app.care.models import (
    CareAppointment,
    CareConversation,
    CareConversationMessage,
    CarePlan,
    CarePlanItem,
)
from app.care.outreach_invariants import supersede_patient_schedule_for_new_xray
from app.common.serialization import model_dict
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import sensitive_limit
from app.database.models import (
    AIAnalysis,
    DentalFinding,
    FutureRiskProfile,
    WhatsAppOutreach,
    XRay,
)
from app.storage.providers import LocalStorageProvider, make_storage_key, storage_provider

router = APIRouter(prefix="/xrays", tags=["xrays"])
allowed = {"image/jpeg", "image/png", "image/webp", "application/dicom"}
logger = logging.getLogger(__name__)


def valid_signature(content_type: str, data: bytes) -> bool:
    signatures = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        "application/dicom": len(data) >= 132 and data[128:132] == b"DICM",
    }
    return signatures.get(content_type, False)


def safe_display_filename(filename: str | None) -> str:
    name = PurePath((filename or "xray").replace("\\", "/")).name
    printable = "".join(character for character in name if character.isprintable())
    return (printable or "xray")[:255]


@router.post(
    "/patients/{patient_id}",
    status_code=201,
    dependencies=[Depends(sensitive_limit("xray-upload", 30, 60))],
)
async def upload(
    patient_id: uuid.UUID,
    ctx: Annotated[AuthContext, Depends(current_context)],
    file: Annotated[UploadFile, File()],
):
    patient = await authorized_patient(ctx, patient_id)
    if file.content_type not in allowed:
        raise AppError("XRAY_MIME_INVALID", "Unsupported X-ray file type.", 415)
    data = await file.read(get_settings().max_xray_bytes + 1)
    if len(data) > get_settings().max_xray_bytes:
        raise AppError("XRAY_TOO_LARGE", "X-ray exceeds the upload limit.", 413)
    if not valid_signature(file.content_type, data):
        raise AppError("XRAY_CONTENT_INVALID", "File content does not match its type.", 415)
    key = make_storage_key(ctx.clinic.id, patient.id)
    provider = storage_provider()
    await provider.upload(key, data, file.content_type)
    xray = XRay(
        patient_id=patient.id,
        uploaded_by=ctx.user.id,
        branch_id=patient.branch_id,
        storage_key=key,
        original_filename=safe_display_filename(file.filename),
        mime_type=file.content_type,
        size_bytes=len(data),
    )
    ctx.session.add(xray)
    try:
        await ctx.session.flush()
        superseded = await supersede_patient_schedule_for_new_xray(
            ctx.session,
            patient_id=patient.id,
            new_xray_id=xray.id,
        )
        await audit(
            ctx.session,
            ctx.user,
            "XRAY_UPLOADED",
            "XRay",
            xray.id,
            patient.branch_id,
            {"superseded_care_schedule": superseded},
        )
        await ctx.session.commit()
    except Exception:
        await provider.delete(key)
        raise
    return model_dict(xray)


@router.delete("/{xray_id}", status_code=204)
async def remove(xray_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]) -> Response:
    xray = await ctx.session.get(XRay, xray_id)
    if not xray:
        raise AppError("XRAY_NOT_FOUND", "X-ray was not found.", 404)
    await authorized_patient(ctx, xray.patient_id)

    storage_key = xray.storage_key
    analysis_ids = list(
        (
            await ctx.session.scalars(
                select(AIAnalysis.id).where(AIAnalysis.xray_id == xray.id)
            )
        ).all()
    )

    if analysis_ids:
        plan_ids = list(
            (
                await ctx.session.scalars(
                    select(CarePlan.id).where(CarePlan.analysis_id.in_(analysis_ids))
                )
            ).all()
        )
        if plan_ids:
            item_ids = list(
                (
                    await ctx.session.scalars(
                        select(CarePlanItem.id).where(CarePlanItem.care_plan_id.in_(plan_ids))
                    )
                ).all()
            )
            if item_ids:
                await ctx.session.execute(
                    update(CareConversationMessage)
                    .where(CareConversationMessage.care_plan_item_id.in_(item_ids))
                    .values(care_plan_item_id=None)
                )
                await ctx.session.execute(
                    update(CareAppointment)
                    .where(CareAppointment.care_plan_item_id.in_(item_ids))
                    .values(care_plan_item_id=None)
                )
                await ctx.session.execute(delete(CarePlanItem).where(CarePlanItem.id.in_(item_ids)))

            await ctx.session.execute(
                update(CareConversation)
                .where(CareConversation.care_plan_id.in_(plan_ids))
                .values(
                    care_plan_id=None,
                    status="CLOSED",
                    summary="Source OPG was deleted. This conversation is retained as historical communication only.",
                )
            )
            await ctx.session.execute(delete(CarePlan).where(CarePlan.id.in_(plan_ids)))

        await ctx.session.execute(
            delete(WhatsAppOutreach).where(WhatsAppOutreach.analysis_id.in_(analysis_ids))
        )
        await ctx.session.execute(
            delete(FutureRiskProfile).where(
                FutureRiskProfile.generated_from_analysis_id.in_(analysis_ids)
            )
        )
        await ctx.session.execute(
            delete(DentalFinding).where(DentalFinding.analysis_id.in_(analysis_ids))
        )
        await ctx.session.execute(delete(AIAnalysis).where(AIAnalysis.id.in_(analysis_ids)))

    await audit(
        ctx.session,
        ctx.user,
        "XRAY_DELETED",
        "XRay",
        xray.id,
        xray.branch_id,
        {
            "patient_id": str(xray.patient_id),
            "filename": xray.original_filename,
            "derived_analyses_removed": len(analysis_ids),
        },
    )
    await ctx.session.delete(xray)
    await ctx.session.commit()

    try:
        await storage_provider().delete(storage_key)
    except Exception:
        logger.exception("Failed to remove unreferenced X-ray object %s", storage_key)

    return Response(status_code=204)


@router.get("/{xray_id}/download")
async def download(xray_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]):
    xray = await ctx.session.get(XRay, xray_id)
    if not xray:
        raise AppError("XRAY_NOT_FOUND", "X-ray was not found.", 404)
    await authorized_patient(ctx, xray.patient_id)
    provider = storage_provider()
    url = (
        f"/api/v1/xrays/{xray.id}/content"
        if isinstance(provider, LocalStorageProvider)
        else await provider.create_download_url(xray.storage_key, 300)
    )
    await audit(ctx.session, ctx.user, "XRAY_VIEWED", "XRay", xray.id, xray.branch_id)
    await ctx.session.commit()
    return {"url": url, "expires_in": 300}


@router.get("/{xray_id}/content", response_class=Response)
async def content(
    xray_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]
) -> Response:
    xray = await ctx.session.get(XRay, xray_id)
    if not xray:
        raise AppError("XRAY_NOT_FOUND", "X-ray was not found.", 404)
    await authorized_patient(ctx, xray.patient_id)
    provider = storage_provider()
    if not isinstance(provider, LocalStorageProvider):
        raise AppError("DIRECT_DOWNLOAD_UNAVAILABLE", "Use the temporary download URL.", 409)
    try:
        data = await provider.read(xray.storage_key)
    except FileNotFoundError as exc:
        raise AppError("XRAY_CONTENT_MISSING", "X-ray content is unavailable.", 404) from exc
    await audit(ctx.session, ctx.user, "XRAY_ACCESSED", "XRay", xray.id, xray.branch_id)
    await ctx.session.commit()
    return Response(
        data,
        media_type=xray.mime_type,
        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline"},
    )
