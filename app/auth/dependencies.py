import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_token
from app.clinic_resolution.service import ResolvedClinic, resolver
from app.core.errors import AppError
from app.database.models import Patient, PatientDoctorAssignment, Role, User, UserBranchScope
from app.database.sessions import control_session
from app.platform.entitlements import (
    enforce_free_opg_limit,
    enforce_free_patient_limit,
    require_product_access,
)

bearer = HTTPBearer(auto_error=False)

_SUBSCRIPTION_SHELL_PATHS = {
    "/api/v1/auth/me",
    "/api/v1/auth/logout",
    "/api/v1/platform/subscription/status",
    "/api/v1/platform/subscription/upgrade",
}


@dataclass
class AuthContext:
    clinic: ResolvedClinic
    user: User
    branch_ids: set[uuid.UUID]
    session: AsyncSession


async def current_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    control: Annotated[AsyncSession, Depends(control_session)],
):
    if not credentials:
        raise AppError("AUTH_REQUIRED", "Authentication is required.", 401)
    payload = decode_token(credentials.credentials, "access")
    clinic = await resolver.by_id(control, uuid.UUID(payload["clinic"]))
    if request.url.path not in _SUBSCRIPTION_SHELL_PATHS:
        require_product_access(clinic)
    factory = resolver.session_factory(clinic)
    async with factory() as db:
        user = await db.get(User, uuid.UUID(payload["sub"]))
        if not user or not user.is_active or user.token_version != payload.get("ver"):
            raise AppError("INVALID_SESSION", "Session is no longer valid.", 401)
        branches = set(
            (
                await db.scalars(
                    select(UserBranchScope.branch_id).where(UserBranchScope.user_id == user.id)
                )
            ).all()
        )

        if request.method == "POST" and request.url.path == "/api/v1/patients":
            await enforce_free_patient_limit(db, clinic)
        xray_prefix = "/api/v1/xrays/patients/"
        if request.method == "POST" and request.url.path.startswith(xray_prefix):
            raw_patient_id = request.url.path.removeprefix(xray_prefix).split("/", 1)[0]
            try:
                patient_id = uuid.UUID(raw_patient_id)
            except ValueError as exc:
                raise AppError("PATIENT_ID_INVALID", "Patient ID is invalid.", 422) from exc
            await enforce_free_opg_limit(db, clinic, patient_id)

        yield AuthContext(clinic, user, branches, db)


def roles(*allowed: Role):
    async def check(ctx: Annotated[AuthContext, Depends(current_context)]):
        if ctx.user.role not in allowed:
            raise AppError("FORBIDDEN", "You do not have permission for this action.", 403)
        return ctx

    return check


async def authorized_patient(ctx: AuthContext, patient_id: uuid.UUID) -> Patient:
    patient = await ctx.session.get(Patient, patient_id)
    if not patient:
        raise AppError("PATIENT_NOT_FOUND", "Patient was not found.", 404)
    if ctx.user.role == Role.DIRECTOR:
        return patient
    if patient.branch_id not in ctx.branch_ids:
        raise AppError("PATIENT_NOT_AUTHORIZED", "You do not have access to this patient.", 403)
    if ctx.user.role == Role.DOCTOR:
        assignment = await ctx.session.scalar(
            select(PatientDoctorAssignment.id).where(
                PatientDoctorAssignment.patient_id == patient.id,
                PatientDoctorAssignment.doctor_id == ctx.user.id,
                PatientDoctorAssignment.active.is_(True),
            )
        )
        if not assignment:
            raise AppError("PATIENT_NOT_AUTHORIZED", "You do not have access to this patient.", 403)
    return patient
