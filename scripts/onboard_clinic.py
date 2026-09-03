"""Provision a clinic after its control and tenant databases exist."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# When executed as ``python scripts/onboard_clinic.py`` inside the image,
# Python otherwise puts /app/scripts (not /app) on sys.path. Ensure the
# repository root is importable so ``app.*`` imports work consistently.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.security import hash_password
from app.database.control_models import ClinicRegistry
from app.database.models import Branch, Role, User, UserBranchScope


def migrate_tenant(database_url: str) -> None:
    previous_url = os.environ.get("DATABASE_URL")
    previous_plane = os.environ.get("MIGRATION_PLANE")
    try:
        os.environ["DATABASE_URL"] = database_url
        os.environ["MIGRATION_PLANE"] = "clinic"
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        if previous_plane is None:
            os.environ.pop("MIGRATION_PLANE", None)
        else:
            os.environ["MIGRATION_PLANE"] = previous_plane


def validate_email(value: str) -> str:
    try:
        return str(TypeAdapter(EmailStr).validate_python(value)).lower()
    except ValidationError as exc:
        raise SystemExit(f"Invalid --email value: {value}") from exc


async def main(a):
    tenant_url = os.environ["DATABASE_URL"]
    control_url = os.environ["CONTROL_DATABASE_URL"]
    tenant = create_async_engine(tenant_url)
    control = create_async_engine(control_url)
    async with async_sessionmaker(tenant, expire_on_commit=False)() as db, db.begin():
        branch = Branch(name=a.branch_name, code=a.branch_code)
        db.add(branch)
        await db.flush()
        user = User(
            username=a.username,
            email=a.email,
            password_hash=hash_password(a.password),
            role=Role.DIRECTOR,
            first_name=a.first_name,
            last_name=a.last_name,
        )
        db.add(user)
        await db.flush()
        db.add(UserBranchScope(user_id=user.id, branch_id=branch.id))
    encrypted = (
        Fernet(os.environ["TENANT_DSN_ENCRYPTION_KEY"].encode())
        .encrypt(tenant_url.encode())
        .decode()
    )
    async with async_sessionmaker(control, expire_on_commit=False)() as db, db.begin():
        db.add(
            ClinicRegistry(
                slug=a.slug.lower(),
                name=a.name,
                encrypted_database_url=encrypted,
                allowed_origins=a.origin,
            )
        )
    await tenant.dispose()
    await control.dispose()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for x in (
        "slug",
        "name",
        "branch-name",
        "branch-code",
        "username",
        "email",
        "password",
        "first-name",
        "last-name",
    ):
        p.add_argument(f"--{x}", required=True)
    p.add_argument("--origin", action="append", required=True)
    args = p.parse_args()
    args.email = validate_email(args.email)
    migrate_tenant(os.environ["DATABASE_URL"])
    asyncio.run(main(args))
