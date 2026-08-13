from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.auth.dependencies import AuthContext, current_context
from app.core.errors import AppError
from app.database.models import (
    AIAnalysis,
    Branch,
    FollowUp,
    Patient,
    PatientDoctorAssignment,
    Role,
    User,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


async def count(db, model, *where):
    return await db.scalar(select(func.count()).select_from(model).where(*where))


@router.get("/{kind}")
async def dashboard(kind: str, ctx: Annotated[AuthContext, Depends(current_context)]):
    if kind.lower() != ctx.user.role.value.lower():
        raise AppError("FORBIDDEN", "Dashboard does not match your role.", 403)
    if ctx.user.role == Role.DIRECTOR:
        return {
            "patient_count": await count(ctx.session, Patient),
            "doctor_count": await count(ctx.session, User, User.role == Role.DOCTOR),
            "manager_count": await count(ctx.session, User, User.role == Role.MANAGER),
            "branch_count": await count(ctx.session, Branch),
            "ai_analysis_count": await count(ctx.session, AIAnalysis),
            "followup_count": await count(ctx.session, FollowUp),
        }
    if ctx.user.role == Role.MANAGER:
        return {
            "authorized_patient_count": await count(
                ctx.session, Patient, Patient.branch_id.in_(ctx.branch_ids)
            ),
            "authorized_doctor_count": await count(ctx.session, User, User.role == Role.DOCTOR),
            "followups_due": await count(
                ctx.session,
                FollowUp,
                FollowUp.branch_id.in_(ctx.branch_ids),
                FollowUp.status == "DUE",
            ),
        }
    return {
        "assigned_patient_count": await count(
            ctx.session,
            PatientDoctorAssignment,
            PatientDoctorAssignment.doctor_id == ctx.user.id,
            PatientDoctorAssignment.active.is_(True),
        ),
        "recent_xrays": [],
        "recent_ai_analyses": [],
        "followups_due": await count(
            ctx.session, FollowUp, FollowUp.doctor_id == ctx.user.id, FollowUp.status == "DUE"
        ),
    }
