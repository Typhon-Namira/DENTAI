from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.auth.dependencies import AuthContext, roles
from app.common.serialization import model_dict
from app.database.models import AuditLog, Package, Role, Usage

router = APIRouter(tags=["administration"])


@router.get("/packages")
async def packages(ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR))]):
    rows = (await ctx.session.scalars(select(Package))).all()
    return [model_dict(row) for row in rows]


@router.get("/usage")
async def usage(ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR))]):
    rows = (await ctx.session.scalars(select(Usage).order_by(Usage.period_start.desc()))).all()
    return [model_dict(row) for row in rows]


@router.get("/audit")
async def audit_logs(
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR))],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    rows = (
        await ctx.session.scalars(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {"items": [model_dict(row) for row in rows], "page": page, "page_size": page_size}
