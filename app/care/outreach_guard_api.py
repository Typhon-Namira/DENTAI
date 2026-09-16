import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.audit.service import audit
from app.auth.dependencies import AuthContext, authorized_patient, roles
from app.care.models import CarePlan
from app.care.sequential import approve_sequential_plan, generate_sequential_plan
from app.core.errors import AppError
from app.database.models import AIAnalysis, Role

router = APIRouter(prefix="/care", tags=["care-outreach-guard"])


def _branch_allowed(ctx: AuthContext, branch_id: uuid.UUID) -> bool:
    return ctx.user.role == Role.DIRECTOR or branch_id in ctx.branch_ids


@router.post("/plans/{plan_id}/approve")
async def guarded_legacy_plan_approval(
    plan_id: uuid.UUID,
    ctx: Annotated[
        AuthContext,
        Depends(roles(Role.DIRECTOR, Role.MANAGER, Role.DOCTOR)),
    ],
):
    """Make the legacy approval endpoint use the same dated sequential scheduler.

    The old endpoint sent every pending tooth immediately in a loop. Keeping this
    first-match route prevents older frontend/API clients from bypassing the
    one-tooth-per-date scheduling invariant.
    """
    plan = await ctx.session.get(CarePlan, plan_id)
    if not plan:
        raise AppError("CARE_PLAN_NOT_FOUND", "Care plan was not found.", 404)
    if not _branch_allowed(ctx, plan.branch_id):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Care plan is outside your scope.", 403)
    await authorized_patient(ctx, plan.patient_id)
    if plan.status != "PENDING_APPROVAL":
        raise AppError("INVALID_CARE_PLAN_STATE", "Care plan is not awaiting approval.", 409)

    analysis = await ctx.session.get(AIAnalysis, plan.analysis_id)
    if not analysis:
        raise AppError("ANALYSIS_NOT_FOUND", "Analysis was not found.", 404)

    repaired = await generate_sequential_plan(ctx.session, analysis)
    if not repaired:
        raise AppError("CARE_PLAN_NOT_AVAILABLE", "Care plan could not be scheduled.", 409)
    await approve_sequential_plan(ctx.session, plan=repaired)
    repaired.approved_by = ctx.user.id
    repaired.approved_at = datetime.now(UTC)
    await audit(
        ctx.session,
        ctx.user,
        "CARE_PLAN_APPROVED_SAFE_SEQUENCE",
        "CarePlan",
        repaired.id,
        repaired.branch_id,
    )
    await ctx.session.commit()
    return {
        "id": str(repaired.id),
        "status": repaired.status,
        "approved_at": repaired.approved_at,
    }
