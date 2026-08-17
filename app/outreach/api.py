import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.dependencies import AuthContext, authorized_patient, current_context
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import Role, WhatsAppOutreach, WhatsAppOutreachStatus, XRay
from app.outreach.images import finding_crop
from app.outreach.service import build_outreach, latest_eligible_finding
from app.outreach.whatsapp_client import WhatsAppServiceClient, WhatsAppServiceError, normalize_phone

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class WhatsAppPhoneUpdate(BaseModel):
    whatsapp_phone: str | None


class TestSendRequest(BaseModel):
    include_image: bool = False


def client() -> WhatsAppServiceClient:
    return WhatsAppServiceClient()


@router.get("/status")
async def status(ctx: Annotated[AuthContext, Depends(current_context)]):
    try:
        return await client().status(ctx.clinic.id)
    except WhatsAppServiceError as exc:
        raise AppError(exc.code, "WhatsApp service is unavailable.", exc.status_code) from exc


@router.get("/qr")
async def qr(ctx: Annotated[AuthContext, Depends(current_context)]):
    try:
        return await client().qr(ctx.clinic.id)
    except WhatsAppServiceError as exc:
        raise AppError(exc.code, "Unable to create WhatsApp QR code.", exc.status_code) from exc


@router.post("/logout")
async def logout(ctx: Annotated[AuthContext, Depends(current_context)]):
    try:
        return await client().logout(ctx.clinic.id)
    except WhatsAppServiceError as exc:
        raise AppError(exc.code, "Unable to disconnect WhatsApp.", exc.status_code) from exc


@router.patch("/patients/{patient_id}")
async def update_patient_phone(
    patient_id: uuid.UUID, body: WhatsAppPhoneUpdate,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    patient = await authorized_patient(ctx, patient_id)
    if ctx.user.role not in {Role.DIRECTOR, Role.MANAGER, Role.DOCTOR}:
        raise AppError("FORBIDDEN", "You do not have permission for this action.", 403)
    try:
        patient.whatsapp_phone = normalize_phone(body.whatsapp_phone) if body.whatsapp_phone else None
    except ValueError as exc:
        raise AppError("INVALID_WHATSAPP_PHONE", str(exc), 422) from exc
    await ctx.session.commit()
    return model_dict(patient)


@router.get("/patients/{patient_id}/outreach")
async def patient_outreach(
    patient_id: uuid.UUID, ctx: Annotated[AuthContext, Depends(current_context)]
):
    await authorized_patient(ctx, patient_id)
    rows = (
        await ctx.session.scalars(
            select(WhatsAppOutreach).where(WhatsAppOutreach.patient_id == patient_id)
            .order_by(WhatsAppOutreach.created_at.desc()).limit(50)
        )
    ).all()
    return {"items": [model_dict(row) for row in rows]}


@router.post("/patients/{patient_id}/test", status_code=202)
async def send_test(
    patient_id: uuid.UUID, body: TestSendRequest,
    ctx: Annotated[AuthContext, Depends(current_context)],
):
    patient = await authorized_patient(ctx, patient_id)
    if not patient.whatsapp_phone:
        raise AppError("WHATSAPP_PHONE_REQUIRED", "Save the patient's WhatsApp number first.", 409)
    analysis, finding = await latest_eligible_finding(ctx.session, patient.id)
    if analysis is None or finding is None:
        raise AppError("NO_ELIGIBLE_FINDING", "No resolved product-visible DENTAI finding is available.", 409)
    service = client()
    row = None
    try:
        connection = await service.status(ctx.clinic.id)
        if not connection.get("connected"):
            raise AppError("WHATSAPP_CONNECTION_REQUIRED", "Connect the clinic WhatsApp account first.", 409)
        validation = await service.validate_phone(ctx.clinic.id, patient.whatsapp_phone)
        if not validation.get("registered"):
            raise AppError("PHONE_NOT_ON_WHATSAPP", "The saved number is not registered on WhatsApp.", 422)
        row = await build_outreach(
            ctx.session, patient=patient, analysis=analysis, finding=finding,
            immediate=True, include_image=body.include_image,
        )
        row.status = WhatsAppOutreachStatus.SENDING
        row.attempt_count += 1
        await ctx.session.commit()
        if body.include_image:
            xray = await ctx.session.get(XRay, analysis.xray_id)
            image = await finding_crop(xray, finding) if xray else None
            result = (
                await service.send_image_message(
                    ctx.clinic.id, patient.whatsapp_phone, row.message, image
                ) if image else
                await service.send_message(ctx.clinic.id, patient.whatsapp_phone, row.message)
            )
        else:
            result = await service.send_message(ctx.clinic.id, patient.whatsapp_phone, row.message)
        row.status = WhatsAppOutreachStatus.SENT
        row.provider_message_id = result.get("message_id")
        row.sent_at = datetime.now(UTC)
        await ctx.session.commit()
        return model_dict(row)
    except AppError:
        raise
    except WhatsAppServiceError as exc:
        if row is not None:
            row.status = WhatsAppOutreachStatus.FAILED
            row.safe_error = exc.code
            row.failed_at = datetime.now(UTC)
            await ctx.session.commit()
        raise AppError(exc.code, "WhatsApp message could not be sent.", exc.status_code) from exc
