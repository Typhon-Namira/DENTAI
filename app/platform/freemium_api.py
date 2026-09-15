from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthContext, current_context
from app.core.rate_limit import sensitive_limit
from app.database.control_models import AccessRequest, ClinicRegistry
from app.database.sessions import control_session
from app.platform.api import (
    AccessRequestCreate,
    PaymentVerification,
    _serialize_access,
    _serialize_clinic,
    activate_access_request,
    require_platform_admin,
)
from app.platform.entitlements import entitlement_payload, seconds_remaining, subscription_state
from app.platform.freemium import (
    activate_existing_premium,
    free_credentials_email_body,
    provision_free_trial,
    request_premium_upgrade,
)
from app.platform.service import platform_settings, send_logged_email

router = APIRouter(prefix="/platform", tags=["platform-freemium"])


@router.post(
    "/access-requests",
    status_code=201,
    dependencies=[Depends(sensitive_limit("free-access-request", 5, 3600))],
)
async def create_free_access_request(
    body: AccessRequestCreate,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    now = datetime.now(UTC)
    row = AccessRequest(
        clinic_name=body.clinic_name.strip(),
        country=body.country.strip(),
        city=body.city.strip(),
        address=body.address.strip() if body.address else None,
        website=str(body.website) if body.website else None,
        contact_name=body.contact_name.strip(),
        contact_role=body.contact_role.strip(),
        email=str(body.email).casefold(),
        phone=body.phone.strip(),
        dentists_count=body.dentists_count,
        branches_count=body.branches_count,
        notes=body.notes.strip() if body.notes else None,
        status="PROVISIONING_FREE",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    await session.flush()
    settings = await platform_settings(session)
    clinic, username, password, expires_at = await provision_free_trial(
        session,
        request=row,
        settings=settings,
    )
    await send_logged_email(
        session,
        recipient=row.email,
        subject="Your Teta2 Free dashboard is ready",
        body=free_credentials_email_body(
            row,
            slug=clinic.slug,
            username=username,
            password=password,
            expires_at=expires_at,
        ),
        kind="FREE_ACTIVATION_CREDENTIALS",
        access_request_id=row.id,
        clinic_id=clinic.id,
    )
    await session.commit()
    return {
        "id": str(row.id),
        "status": "FREE_ACTIVE",
        "clinic_slug": clinic.slug,
        "free_expires_at": expires_at,
        "credentials_email_sent": True,
        "message": "Your one-time Free access is active. Login credentials were sent by email.",
    }


def _subscription_payload(clinic: ClinicRegistry) -> dict:
    from app.clinic_resolution.service import ResolvedClinic, resolver

    resolved = ResolvedClinic(
        id=clinic.id,
        slug=clinic.slug,
        name=clinic.name,
        database_url=resolver._decrypt(clinic.encrypted_database_url),
        allowed_origins=clinic.allowed_origins,
        subscription_plan=clinic.subscription_plan,
        subscription_state=clinic.subscription_state,
        subscription_starts_at=clinic.subscription_starts_at,
        subscription_expires_at=clinic.subscription_expires_at,
        free_trial_started_at=clinic.free_trial_started_at,
        upgrade_requested_at=clinic.upgrade_requested_at,
    )
    return {
        "plan": clinic.subscription_plan,
        "state": subscription_state(resolved),
        "starts_at": clinic.subscription_starts_at,
        "expires_at": clinic.subscription_expires_at,
        "seconds_remaining": seconds_remaining(resolved),
        "upgrade_requested_at": clinic.upgrade_requested_at,
        "entitlements": entitlement_payload(resolved),
    }


@router.get("/subscription/status")
async def subscription_status(
    ctx: Annotated[AuthContext, Depends(current_context)],
    control: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await control.get(ClinicRegistry, ctx.clinic.id)
    if not clinic:
        return {"plan": None, "state": "UNAVAILABLE"}
    return _subscription_payload(clinic)


@router.post(
    "/subscription/upgrade",
    dependencies=[Depends(sensitive_limit("premium-upgrade", 3, 3600))],
)
async def request_upgrade(
    ctx: Annotated[AuthContext, Depends(current_context)],
    control: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await control.get(ClinicRegistry, ctx.clinic.id)
    if not clinic:
        from app.core.errors import AppError

        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    settings = await platform_settings(control)
    request = await request_premium_upgrade(control, clinic=clinic, settings=settings)
    await control.commit()
    return {
        "status": "PAYMENT_REVIEW",
        "request": _serialize_access(request),
        "message": "Premium upgrade submitted. Payment approval may take 1–6 hours.",
    }


@router.post(
    "/admin/access-requests/{request_id}/activate",
    dependencies=[Depends(require_platform_admin)],
)
async def activate_free_upgrade_or_legacy(
    request_id,
    body: PaymentVerification,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    request = await session.get(AccessRequest, request_id)
    if not request:
        from app.core.errors import AppError

        raise AppError("ACCESS_REQUEST_NOT_FOUND", "Access request was not found.", 404)
    if request.activated_clinic_id:
        settings = await platform_settings(session)
        clinic, expires_at = await activate_existing_premium(
            session,
            request=request,
            settings=settings,
            reference=body.reference,
            proof_note=body.proof_note,
        )
        await session.commit()
        return {
            "request": _serialize_access(request),
            "clinic": _serialize_clinic(clinic),
            "subscription_expires_at": expires_at,
            "existing_workspace_preserved": True,
        }
    return await activate_access_request(request_id, body, session)


@router.get(
    "/admin/free-upgrades",
    dependencies=[Depends(require_platform_admin)],
)
async def admin_free_upgrades(
    session: Annotated[AsyncSession, Depends(control_session)],
):
    rows = (
        await session.scalars(
            select(AccessRequest)
            .where(AccessRequest.status == "PAYMENT_REVIEW")
            .order_by(AccessRequest.updated_at.desc())
        )
    ).all()
    return [_serialize_access(row) for row in rows]
