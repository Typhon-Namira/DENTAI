import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.audit.service import audit
from app.auth.dependencies import AuthContext, roles
from app.auth.security import hash_password
from app.common.serialization import model_dict
from app.core.errors import AppError
from app.database.models import (
    Branch,
    DoctorProfile,
    ManagerProfile,
    Role,
    User,
    UserBranchScope,
)

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    branch_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    specialty: str | None = Field(default=None, max_length=160)
    professional_title: str | None = Field(default=None, max_length=160)


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


async def create_role_user(body: UserCreate, role: Role, ctx: AuthContext) -> dict:
    branch_ids = set(body.branch_ids)
    if ctx.user.role == Role.MANAGER and not branch_ids.issubset(ctx.branch_ids):
        raise AppError("BRANCH_NOT_AUTHORIZED", "Branch is outside your scope.", 403)
    existing_branches = set(
        (await ctx.session.scalars(select(Branch.id).where(Branch.id.in_(branch_ids)))).all()
    )
    if existing_branches != branch_ids:
        raise AppError("BRANCH_NOT_FOUND", "One or more branches were not found.", 422)
    existing = await ctx.session.scalar(
        select(User.id).where((User.username == body.username) | (User.email == body.email.lower()))
    )
    if existing:
        raise AppError("USER_ALREADY_EXISTS", "Username or email is already registered.", 409)
    user = User(
        username=body.username,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        role=role,
        first_name=body.first_name,
        last_name=body.last_name,
    )
    ctx.session.add(user)
    await ctx.session.flush()
    ctx.session.add_all(
        [UserBranchScope(user_id=user.id, branch_id=branch_id) for branch_id in branch_ids]
    )
    if role == Role.MANAGER:
        ctx.session.add(ManagerProfile(user_id=user.id))
    else:
        ctx.session.add(
            DoctorProfile(
                user_id=user.id,
                specialty=body.specialty or "General Dentistry",
                professional_title=body.professional_title or "Dentist",
            )
        )
    await audit(ctx.session, ctx.user, "USER_CREATED", "User", user.id)
    await ctx.session.commit()
    return model_dict(user)


@router.post("/managers", status_code=201)
async def create_manager(
    body: UserCreate, ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR))]
):
    return await create_role_user(body, Role.MANAGER, ctx)


@router.post("/doctors", status_code=201)
async def create_doctor(
    body: UserCreate,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    return await create_role_user(body, Role.DOCTOR, ctx)


@router.patch("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    ctx: Annotated[AuthContext, Depends(roles(Role.DIRECTOR, Role.MANAGER))],
):
    target = await ctx.session.get(User, user_id)
    if not target or target.role == Role.DIRECTOR:
        raise AppError("USER_NOT_FOUND", "User was not found.", 404)
    if ctx.user.role == Role.MANAGER:
        if target.role != Role.DOCTOR:
            raise AppError("FORBIDDEN", "Managers may update Doctors only.", 403)
        scopes = set(
            (
                await ctx.session.scalars(
                    select(UserBranchScope.branch_id).where(UserBranchScope.user_id == target.id)
                )
            ).all()
        )
        if not scopes or not scopes.issubset(ctx.branch_ids):
            raise AppError("BRANCH_NOT_AUTHORIZED", "Doctor is outside your scope.", 403)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    if body.is_active is False:
        target.token_version += 1
    await audit(ctx.session, ctx.user, "USER_UPDATED", "User", target.id)
    await ctx.session.commit()
    return model_dict(target)
