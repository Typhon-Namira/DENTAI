import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.database.control_models import AccessRequest, ClinicRegistry, PlatformAdminAudit
from app.database.sessions import control_session
from app.platform.api import PaymentVerification, require_platform_admin
from app.platform.freemium_api import activate_free_upgrade_or_legacy
from app.platform.market_api import MarketPaymentDecision, send_market_payment_instructions
from app.platform.service import platform_settings

router = APIRouter(prefix="/platform/admin-control", tags=["platform-admin-payments"])


@router.post(
    "/access-requests/{request_id}/send-payment",
    dependencies=[Depends(require_platform_admin)],
)
async def send_payment_and_record_amount(
    request_id: uuid.UUID,
    body: MarketPaymentDecision,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    result = await send_market_payment_instructions(request_id, body, session)
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    row.payment_amount = int(result["price_amount"])
    row.payment_currency = str(result["price_currency"])
    session.add(
        PlatformAdminAudit(
            action="PAYMENT_INSTRUCTIONS_SENT",
            target_type="ACCESS_REQUEST",
            target_id=str(row.id),
            details={
                "market": result.get("market"),
                "pricing_tier": result.get("pricing_tier"),
                "amount": row.payment_amount,
                "currency": row.payment_currency,
            },
        )
    )
    await session.commit()
    return result


@router.post(
    "/access-requests/{request_id}/activate",
    dependencies=[Depends(require_platform_admin)],
)
async def verify_payment_and_activate(
    request_id: uuid.UUID,
    body: PaymentVerification,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(AccessRequest, request_id)
    if not row:
        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)

    if row.payment_amount is None and row.activated_clinic_id:
        settings = await platform_settings(session)
        row.payment_amount = settings.price_amount
        row.payment_currency = settings.price_currency
        await session.flush()

    result = await activate_free_upgrade_or_legacy(request_id, body, session)
    clinic_data = result.get("clinic") if isinstance(result, dict) else None
    clinic_id = clinic_data.get("id") if isinstance(clinic_data, dict) else None
    clinic = await session.get(ClinicRegistry, uuid.UUID(clinic_id)) if clinic_id else None
    if clinic and (clinic.subscription_source or "").upper() != "GIFT":
        clinic.subscription_source = "PAID"
        clinic.gift_granted_at = None
        clinic.gift_note = None

    session.add(
        PlatformAdminAudit(
            action="PAYMENT_VERIFIED_AND_ACTIVATED",
            target_type="ACCESS_REQUEST",
            target_id=str(row.id),
            details={
                "clinic_id": clinic_id,
                "amount": row.payment_amount,
                "currency": row.payment_currency,
                "reference": body.reference,
            },
        )
    )
    await session.commit()
    return result
