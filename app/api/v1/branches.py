from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth.dependencies import AuthContext, current_context
from app.database.models import Branch, Role

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("")
async def branches(ctx: Annotated[AuthContext, Depends(current_context)]):
    q = select(Branch)
    if ctx.user.role != Role.DIRECTOR:
        q = q.where(Branch.id.in_(ctx.branch_ids))
    return [
        {c.name: getattr(x, c.name) for c in x.__table__.columns}
        for x in (await ctx.session.scalars(q)).all()
    ]
