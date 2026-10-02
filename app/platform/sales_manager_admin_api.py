import html
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.core.errors import AppError
from app.database.control_models import (
    AccessRequest,
    ClinicRegistry,
    PlatformAdminAudit,
    SalesCommission,
    SalesDailyReport,
    SalesEquityAward,
    SalesGrowthIdea,
    SalesManager,
    SalesManagerActivity,
    SalesManagerSession,
    SalesReferralAttribution,
    SalesReportClinic,
    SalesSubscriptionPayment,
    SalesWithdrawalRequest,
)
from app.database.sessions import control_session
from app.platform.api import require_platform_admin
from app.platform.sales_manager_service import (
    COMMISSION_RATE_BPS,
    EQUITY_AWARD_KEY,
    SCORE_GROWTH_POINTS,
    add_score_event,
    confirm_attribution,
    create_commission_for_payment,
    decrypt_bank_card,
    manager_balances,
    sales_score_summary,
)
from app.platform.service import (
    platform_settings,
    random_password,
    renew_clinic,
    send_logged_email,
)
from app.storage.providers import storage_provider

router = APIRouter(prefix="/platform/admin-control", tags=["platform-sales-admin"])
logger = logging.getLogger(__name__)

PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_PROFILE_PHOTO_BYTES = 5 * 1024 * 1024


class ManagerEdit(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    is_public: bool | None = None


class WithdrawalDecision(BaseModel):
    reference: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)


class AttributionConfirm(BaseModel):
    manager_id: uuid.UUID
    report_clinic_id: uuid.UUID | None = None


class PaidRenewal(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    amount: int = Field(gt=0, le=1_000_000_000)
    currency: str = Field(min_length=2, max_length=12)
    reference: str = Field(min_length=2, max_length=200)


class GrowthIdeaDecision(BaseModel):
    note: str | None = Field(default=None, max_length=3000)


class GrowthContributionCreate(BaseModel):
    note: str = Field(min_length=3, max_length=3000)


class EquityAwardConfirm(BaseModel):
    note: str | None = Field(default=None, max_length=3000)


def _valid_photo_signature(content_type: str, data: bytes) -> bool:
    checks = {
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    return checks.get(content_type, False)


def _sales_manager_credentials_email_html(
    *,
    first_name: str,
    username: str,
    email: str,
    temporary_password: str,
    login_url: str,
) -> str:
    safe_first = html.escape(first_name)
    safe_username = html.escape(username)
    safe_email = html.escape(email)
    safe_password = html.escape(temporary_password)
    safe_login_url = html.escape(login_url, quote=True)
    return f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#eef1f4;font-family:Arial,Helvetica,sans-serif;color:#24313d;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef1f4;padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border:1px solid #d9e0e6;border-radius:18px;overflow:hidden;box-shadow:0 18px 50px rgba(39,52,65,.10);">
            <tr>
              <td style="padding:28px 34px;background:linear-gradient(135deg,#ffffff,#e8edf1);border-bottom:1px solid #dce2e7;">
                <div style="font-size:28px;font-weight:800;letter-spacing:-.8px;color:#1f2c38;">Teta2</div>
                <div style="margin-top:5px;font-size:11px;font-weight:700;letter-spacing:1.8px;color:#7c8894;">SALES OPERATIONS</div>
              </td>
            </tr>
            <tr>
              <td style="padding:34px;">
                <div style="display:inline-block;padding:6px 10px;border:1px solid #cfd7de;border-radius:999px;background:#f5f7f9;color:#5e6b77;font-size:11px;font-weight:700;letter-spacing:.8px;">VERIFIED SALES MANAGER ACCOUNT</div>
                <h1 style="margin:20px 0 8px;font-size:26px;line-height:1.25;color:#1f2c38;">Welcome to Teta2, {safe_first}</h1>
                <p style="margin:0 0 24px;color:#6f7d89;font-size:15px;line-height:1.7;">Your Sales Manager account has been created and verified by Teta2 Platform Administration. Use the secure credentials below for your first sign-in.</p>

                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #dce2e7;border-radius:14px;background:#f8fafb;">
                  <tr>
                    <td style="padding:18px 20px 8px;color:#7b8793;font-size:12px;font-weight:700;">USERNAME</td>
                  </tr>
                  <tr>
                    <td style="padding:0 20px 16px;color:#24313d;font-size:16px;font-weight:700;">{safe_username}</td>
                  </tr>
                  <tr>
                    <td style="padding:0 20px 8px;color:#7b8793;font-size:12px;font-weight:700;">EMAIL</td>
                  </tr>
                  <tr>
                    <td style="padding:0 20px 16px;color:#24313d;font-size:15px;">{safe_email}</td>
                  </tr>
                  <tr>
                    <td style="padding:0 20px 8px;color:#7b8793;font-size:12px;font-weight:700;">TEMPORARY PASSWORD</td>
                  </tr>
                  <tr>
                    <td style="padding:0 20px 20px;">
                      <span style="display:inline-block;padding:10px 12px;border-radius:8px;background:#202c38;color:#ffffff;font-family:Consolas,Monaco,monospace;font-size:15px;font-weight:700;letter-spacing:.4px;">{safe_password}</span>
                    </td>
                  </tr>
                </table>

                <div style="padding:22px 0 4px;text-align:center;">
                  <a href="{safe_login_url}" style="display:inline-block;padding:13px 24px;border-radius:10px;background:#3f4b56;color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;">Open Sales Manager Portal</a>
                </div>
                <p style="margin:10px 0 0;text-align:center;color:#8a96a1;font-size:12px;line-height:1.6;">{safe_login_url}</p>

                <div style="margin-top:26px;padding:16px 18px;border-left:4px solid #9ca8b3;background:#f4f6f8;border-radius:8px;">
                  <div style="font-size:13px;font-weight:700;color:#34424f;">Security requirement</div>
                  <p style="margin:5px 0 0;color:#6f7d89;font-size:13px;line-height:1.6;">You will be required to replace the temporary password immediately after your first sign-in. Do not forward or share these credentials.</p>
                </div>

                <p style="margin:24px 0 0;color:#6f7d89;font-size:13px;line-height:1.7;">Daily clinic reports, commissions, withdrawal requests, sign-in history and manager activity are recorded in the platform for operational and administrative purposes.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 34px;background:#f6f8fa;border-top:1px solid #e0e5ea;color:#87939e;font-size:12px;line-height:1.6;">
                This is an official Teta2 account message. If you did not expect this account, contact Teta2 Platform Administration.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _manager_payload(row: SalesManager) -> dict:
    return {
        "id": str(row.id),
        "username": row.username,
        "email": row.email,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "name": f"{row.first_name} {row.last_name}".strip(),
        "title": row.title,
        "phone": row.phone,
        "is_active": row.is_active,
        "is_public": row.is_public,
        "verified_at": row.verified_at,
        "must_change_password": row.must_change_password,
        "bank_card_last4": row.bank_card_last4,
        "bank_account_holder": row.bank_account_holder,
        "last_login_at": row.last_login_at,
        "last_logout_at": row.last_logout_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "photo_url": (
            f"/api/v1/platform/sales-managers/public/{row.id}/photo"
            if row.photo_storage_key
            else None
        ),
    }


async def _audit(
    db: AsyncSession,
    *,
    action: str,
    target_type: str,
    target_id: str | None,
    details: dict,
) -> None:
    db.add(
        PlatformAdminAudit(
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )


async def _unique_username(db: AsyncSession, requested: str | None, first: str, last: str) -> str:
    raw = (requested or f"{first}.{last}").strip().casefold()
    base = re.sub(r"[^a-z0-9._-]+", "", raw)[:60] or "sales.manager"
    candidate = base
    counter = 2
    while await db.scalar(select(SalesManager.id).where(SalesManager.username == candidate)):
        candidate = f"{base[:52]}.{counter}"
        counter += 1
    return candidate


async def _manager_stats(db: AsyncSession, manager_id: uuid.UUID) -> dict:
    reports = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesDailyReport)
            .where(
                SalesDailyReport.manager_id == manager_id,
                SalesDailyReport.status == "SUBMITTED",
            )
        )
        or 0
    )
    clinics = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesReportClinic)
            .where(SalesReportClinic.manager_id == manager_id)
        )
        or 0
    )
    logins = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesManagerActivity)
            .where(
                SalesManagerActivity.manager_id == manager_id,
                SalesManagerActivity.action == "LOGIN",
            )
        )
        or 0
    )
    commissions = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesCommission)
            .where(SalesCommission.manager_id == manager_id)
        )
        or 0
    )
    return {
        "submitted_reports": reports,
        "reported_clinics": clinics,
        "login_count": logins,
        "commission_events": commissions,
    }


@router.get("/sales-managers", dependencies=[Depends(require_platform_admin)])
async def list_sales_managers(db: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (await db.scalars(select(SalesManager).order_by(SalesManager.created_at.desc()))).all()
    )
    result = []
    for row in rows:
        payload = _manager_payload(row)
        payload["stats"] = await _manager_stats(db, row.id)
        payload["balances"] = await manager_balances(db, row.id)
        payload["score"] = await sales_score_summary(db, row.id)
        result.append(payload)
    await db.commit()
    return result


@router.get("/sales-growth-ideas", dependencies=[Depends(require_platform_admin)])
async def list_sales_growth_ideas(db: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (
            await db.scalars(
                select(SalesGrowthIdea).order_by(SalesGrowthIdea.submitted_at.desc()).limit(1000)
            )
        ).all()
    )
    manager_ids = {row.manager_id for row in rows}
    managers = (
        {
            row.id: row
            for row in (
                await db.scalars(select(SalesManager).where(SalesManager.id.in_(manager_ids)))
            ).all()
        }
        if manager_ids
        else {}
    )
    return [
        {
            "id": str(row.id),
            "manager_id": str(row.manager_id),
            "manager_name": (
                f"{managers[row.manager_id].first_name} {managers[row.manager_id].last_name}".strip()
                if row.manager_id in managers
                else "Unknown manager"
            ),
            "manager_email": managers[row.manager_id].email if row.manager_id in managers else None,
            "title": row.title,
            "description": row.description,
            "expected_impact": row.expected_impact,
            "status": row.status,
            "admin_note": row.admin_note,
            "submitted_at": row.submitted_at,
            "reviewed_at": row.reviewed_at,
        }
        for row in rows
    ]


@router.post(
    "/sales-growth-ideas/{idea_id}/approve",
    dependencies=[Depends(require_platform_admin)],
)
async def approve_sales_growth_idea(
    idea_id: uuid.UUID,
    body: GrowthIdeaDecision,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesGrowthIdea, idea_id)
    if not row:
        raise AppError("SALES_GROWTH_IDEA_NOT_FOUND", "Growth idea was not found.", 404)
    if row.status != "PENDING":
        raise AppError("SALES_GROWTH_IDEA_FINAL", "This idea has already been reviewed.", 409)
    now = datetime.now(UTC)
    row.status = "APPROVED"
    row.admin_note = body.note.strip() if body.note else None
    row.reviewed_at = now
    row.updated_at = now
    await add_score_event(
        db,
        manager_id=row.manager_id,
        category="GROWTH",
        points=SCORE_GROWTH_POINTS,
        source_type="APPROVED_IDEA",
        source_id=str(row.id),
        description=f"Approved product growth idea: {row.title}",
    )
    score = await sales_score_summary(db, row.manager_id)
    await _audit(
        db,
        action="SALES_GROWTH_IDEA_APPROVED",
        target_type="SALES_GROWTH_IDEA",
        target_id=str(row.id),
        details={"manager_id": str(row.manager_id), "points": SCORE_GROWTH_POINTS},
    )
    await db.commit()
    return {"approved": True, "score": score}


@router.post(
    "/sales-growth-ideas/{idea_id}/reject",
    dependencies=[Depends(require_platform_admin)],
)
async def reject_sales_growth_idea(
    idea_id: uuid.UUID,
    body: GrowthIdeaDecision,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesGrowthIdea, idea_id)
    if not row:
        raise AppError("SALES_GROWTH_IDEA_NOT_FOUND", "Growth idea was not found.", 404)
    if row.status != "PENDING":
        raise AppError("SALES_GROWTH_IDEA_FINAL", "This idea has already been reviewed.", 409)
    now = datetime.now(UTC)
    row.status = "REJECTED"
    row.admin_note = body.note.strip() if body.note else None
    row.reviewed_at = now
    row.updated_at = now
    await _audit(
        db,
        action="SALES_GROWTH_IDEA_REJECTED",
        target_type="SALES_GROWTH_IDEA",
        target_id=str(row.id),
        details={"manager_id": str(row.manager_id)},
    )
    await db.commit()
    return {"rejected": True}


@router.post(
    "/sales-managers/{manager_id}/growth-contribution",
    dependencies=[Depends(require_platform_admin)],
)
async def add_sales_growth_contribution(
    manager_id: uuid.UUID,
    body: GrowthContributionCreate,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await db.get(SalesManager, manager_id)
    if not manager or not manager.is_active:
        raise AppError("SALES_MANAGER_NOT_FOUND", "Active sales manager was not found.", 404)
    source_id = str(uuid.uuid4())
    await add_score_event(
        db,
        manager_id=manager.id,
        category="GROWTH",
        points=SCORE_GROWTH_POINTS,
        source_type="ADMIN_GROWTH_CONTRIBUTION",
        source_id=source_id,
        description=body.note.strip(),
    )
    score = await sales_score_summary(db, manager.id)
    await _audit(
        db,
        action="SALES_GROWTH_CONTRIBUTION_AWARDED",
        target_type="SALES_MANAGER",
        target_id=str(manager.id),
        details={
            "points": SCORE_GROWTH_POINTS,
            "note": body.note.strip(),
            "source_id": source_id,
        },
    )
    await db.commit()
    return {"awarded": True, "points": SCORE_GROWTH_POINTS, "score": score}


@router.get("/sales-equity-award", dependencies=[Depends(require_platform_admin)])
async def sales_equity_award(db: Annotated[AsyncSession, Depends(control_session)]):
    award = await db.scalar(
        select(SalesEquityAward).where(SalesEquityAward.award_key == EQUITY_AWARD_KEY)
    )
    if not award:
        return {"award": None}
    manager = await db.get(SalesManager, award.manager_id)
    score = await sales_score_summary(db, award.manager_id)
    await db.commit()
    return {
        "award": {
            "id": str(award.id),
            "manager_id": str(award.manager_id),
            "manager_name": (
                f"{manager.first_name} {manager.last_name}".strip()
                if manager
                else "Unknown manager"
            ),
            "manager_email": manager.email if manager else None,
            "status": award.status,
            "points_at_award": award.points_at_award,
            "equity_percent": award.equity_percent_bps / 100,
            "reached_at": award.reached_at,
            "reviewed_at": award.reviewed_at,
            "admin_note": award.admin_note,
            "score": score,
        }
    }


@router.post(
    "/sales-equity-award/{award_id}/confirm",
    dependencies=[Depends(require_platform_admin)],
)
async def confirm_sales_equity_award(
    award_id: uuid.UUID,
    body: EquityAwardConfirm,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesEquityAward, award_id)
    if not row:
        raise AppError("SALES_EQUITY_AWARD_NOT_FOUND", "Equity award was not found.", 404)
    row.status = "CONFIRMED"
    row.reviewed_at = datetime.now(UTC)
    row.admin_note = body.note.strip() if body.note else None
    row.updated_at = datetime.now(UTC)
    manager = await db.get(SalesManager, row.manager_id)
    if manager:
        manager.title = "Senior Business Manager"
        manager.updated_at = datetime.now(UTC)
    await _audit(
        db,
        action="SALES_EQUITY_AWARD_CONFIRMED",
        target_type="SALES_EQUITY_AWARD",
        target_id=str(row.id),
        details={
            "manager_id": str(row.manager_id),
            "equity_percent": row.equity_percent_bps / 100,
        },
    )
    await db.commit()
    return {"confirmed": True}


@router.post("/sales-managers", dependencies=[Depends(require_platform_admin)], status_code=201)
async def create_sales_manager(
    db: Annotated[AsyncSession, Depends(control_session)],
    first_name: Annotated[str, Form(min_length=1, max_length=100)],
    last_name: Annotated[str, Form(min_length=1, max_length=100)],
    email: Annotated[EmailStr, Form()],
    title: Annotated[str, Form(min_length=2, max_length=120)] = "Sales Manager",
    phone: Annotated[str | None, Form(max_length=50)] = None,
    username: Annotated[str | None, Form(max_length=80)] = None,
    is_public: Annotated[bool, Form()] = True,
    photo: Annotated[UploadFile | None, File()] = None,
):
    normalized_email = str(email).strip().casefold()
    duplicate = await db.scalar(
        select(SalesManager.id).where(SalesManager.email == normalized_email)
    )
    if duplicate:
        raise AppError(
            "SALES_MANAGER_EMAIL_EXISTS", "A manager with this email already exists.", 409
        )
    if not photo or photo.content_type not in PHOTO_TYPES:
        raise AppError(
            "SALES_MANAGER_PHOTO_REQUIRED",
            "A JPEG, PNG or WebP profile photo is required.",
            422,
        )
    data = await photo.read(MAX_PROFILE_PHOTO_BYTES + 1)
    if len(data) > MAX_PROFILE_PHOTO_BYTES:
        raise AppError("SALES_MANAGER_PHOTO_TOO_LARGE", "Profile photo exceeds 5 MB.", 413)
    if not _valid_photo_signature(photo.content_type, data):
        raise AppError("SALES_MANAGER_PHOTO_INVALID", "Profile photo content is invalid.", 415)

    manager_id = uuid.uuid4()
    resolved_username = await _unique_username(db, username, first_name, last_name)
    temporary_password = random_password(18)
    now = datetime.now(UTC)
    extension = PHOTO_TYPES[photo.content_type]
    storage_key = f"platform/sales-managers/{manager_id}/{uuid.uuid4().hex}{extension}"
    provider = storage_provider()
    await provider.upload(storage_key, data, photo.content_type)

    manager = SalesManager(
        id=manager_id,
        username=resolved_username,
        email=normalized_email,
        password_hash=hash_password(temporary_password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        title=title.strip(),
        phone=phone.strip() if phone else None,
        photo_storage_key=storage_key,
        photo_mime=photo.content_type,
        is_active=True,
        is_public=is_public,
        verified_at=now,
        must_change_password=True,
        token_version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(manager)
    try:
        await db.flush()
        public_url = (
            __import__("app.core.config", fromlist=["get_settings"])
            .get_settings()
            .platform_public_url.rstrip("/")
        )
        login_url = f"{public_url}/platform-managers"
        body = (
            f"Hello {manager.first_name},\n\n"
            "Your Teta2 Sales Manager account has been created and verified.\n\n"
            f"Login URL: {login_url}\n"
            f"Username: {manager.username}\n"
            f"Email: {manager.email}\n"
            f"Temporary password: {temporary_password}\n\n"
            "You will be required to change this password immediately after your first sign-in. "
            "Do not forward or share these credentials.\n\n"
            "Daily clinic reports, commissions, withdrawal requests, sign-in history and manager activity "
            "are recorded in the platform for operational and administrative purposes.\n\n"
            "Teta2 Platform Administration"
        )
        html_body = _sales_manager_credentials_email_html(
            first_name=manager.first_name,
            username=manager.username,
            email=manager.email,
            temporary_password=temporary_password,
            login_url=login_url,
        )
        await send_logged_email(
            db,
            recipient=manager.email,
            subject="Your verified Teta2 Sales Manager account",
            body=body,
            html_body=html_body,
            kind="SALES_MANAGER_CREDENTIALS",
        )
        await _audit(
            db,
            action="SALES_MANAGER_CREATED",
            target_type="SALES_MANAGER",
            target_id=str(manager.id),
            details={
                "email": manager.email,
                "username": manager.username,
                "is_public": manager.is_public,
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()
        await provider.delete(storage_key)
        raise
    return _manager_payload(manager)


@router.patch("/sales-managers/{manager_id}", dependencies=[Depends(require_platform_admin)])
async def edit_sales_manager(
    manager_id: uuid.UUID,
    body: ManagerEdit,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesManager, manager_id)
    if not row:
        raise AppError("SALES_MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    changes = body.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None:
        email = str(changes["email"]).casefold()
        duplicate = await db.scalar(
            select(SalesManager.id).where(
                SalesManager.email == email,
                SalesManager.id != row.id,
            )
        )
        if duplicate:
            raise AppError(
                "SALES_MANAGER_EMAIL_EXISTS",
                "A manager with this email already exists.",
                409,
            )
        row.email = email
    for field in ("first_name", "last_name", "title", "phone", "is_public"):
        if field in changes:
            value = changes[field]
            setattr(row, field, value.strip() if isinstance(value, str) else value)
    if "is_active" in changes and changes["is_active"] is not None:
        next_active = bool(changes["is_active"])
        if row.is_active and not next_active:
            row.token_version += 1
            await db.execute(
                update(SalesManagerSession)
                .where(
                    SalesManagerSession.manager_id == row.id,
                    SalesManagerSession.ended_at.is_(None),
                )
                .values(ended_at=datetime.now(UTC))
            )
        row.is_active = next_active
        if not next_active:
            row.is_public = False
    row.updated_at = datetime.now(UTC)
    await _audit(
        db,
        action="SALES_MANAGER_EDITED",
        target_type="SALES_MANAGER",
        target_id=str(row.id),
        details={"fields": sorted(changes)},
    )
    await db.commit()
    return _manager_payload(row)


@router.post("/sales-managers/{manager_id}/photo", dependencies=[Depends(require_platform_admin)])
async def replace_sales_manager_photo(
    manager_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(control_session)],
    photo: Annotated[UploadFile, File()],
):
    row = await db.get(SalesManager, manager_id)
    if not row:
        raise AppError("SALES_MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    if photo.content_type not in PHOTO_TYPES:
        raise AppError("SALES_MANAGER_PHOTO_INVALID", "Use JPEG, PNG or WebP.", 415)
    data = await photo.read(MAX_PROFILE_PHOTO_BYTES + 1)
    if len(data) > MAX_PROFILE_PHOTO_BYTES or not _valid_photo_signature(photo.content_type, data):
        raise AppError("SALES_MANAGER_PHOTO_INVALID", "Profile photo is invalid.", 415)
    extension = PHOTO_TYPES[photo.content_type]
    new_key = f"platform/sales-managers/{row.id}/{uuid.uuid4().hex}{extension}"
    provider = storage_provider()
    await provider.upload(new_key, data, photo.content_type)
    old_key = row.photo_storage_key
    row.photo_storage_key = new_key
    row.photo_mime = photo.content_type
    row.updated_at = datetime.now(UTC)
    await _audit(
        db,
        action="SALES_MANAGER_PHOTO_UPDATED",
        target_type="SALES_MANAGER",
        target_id=str(row.id),
        details={},
    )
    await db.commit()
    if old_key:
        try:
            await provider.delete(old_key)
        except Exception:
            logger.exception("Failed to delete superseded sales manager profile photo")
    return _manager_payload(row)


@router.post(
    "/sales-managers/{manager_id}/reset-password", dependencies=[Depends(require_platform_admin)]
)
async def reset_sales_manager_password(
    manager_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesManager, manager_id)
    if not row:
        raise AppError("SALES_MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    password = random_password(18)
    row.password_hash = hash_password(password)
    row.must_change_password = True
    row.token_version += 1
    row.updated_at = datetime.now(UTC)
    await db.execute(
        update(SalesManagerSession)
        .where(
            SalesManagerSession.manager_id == row.id,
            SalesManagerSession.ended_at.is_(None),
        )
        .values(ended_at=datetime.now(UTC))
    )
    public_url = (
        __import__("app.core.config", fromlist=["get_settings"])
        .get_settings()
        .platform_public_url.rstrip("/")
    )
    await send_logged_email(
        db,
        recipient=row.email,
        subject="Teta2 Sales Manager password reset",
        body=(
            f"Hello {row.first_name},\n\n"
            f"Login URL: {public_url}/platform-managers\n"
            f"Username: {row.username}\n"
            f"Temporary password: {password}\n\n"
            "Please sign in and change this password immediately.\n\nTeta2"
        ),
        kind="SALES_MANAGER_PASSWORD_RESET",
    )
    await _audit(
        db,
        action="SALES_MANAGER_PASSWORD_RESET",
        target_type="SALES_MANAGER",
        target_id=str(row.id),
        details={},
    )
    await db.commit()
    return {"reset": True, "credentials_email_sent": True}


@router.delete("/sales-managers/{manager_id}", dependencies=[Depends(require_platform_admin)])
async def remove_sales_manager(
    manager_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesManager, manager_id)
    if not row:
        raise AppError("SALES_MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    row.is_active = False
    row.is_public = False
    row.token_version += 1
    row.updated_at = datetime.now(UTC)
    await db.execute(
        update(SalesManagerSession)
        .where(
            SalesManagerSession.manager_id == row.id,
            SalesManagerSession.ended_at.is_(None),
        )
        .values(ended_at=datetime.now(UTC))
    )
    await _audit(
        db,
        action="SALES_MANAGER_REMOVED",
        target_type="SALES_MANAGER",
        target_id=str(row.id),
        details={"history_preserved": True},
    )
    await db.commit()
    return {"removed": True, "history_preserved": True}


@router.get("/sales-managers/{manager_id}/activity", dependencies=[Depends(require_platform_admin)])
async def sales_manager_activity(
    manager_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await db.get(SalesManager, manager_id)
    if not manager:
        raise AppError("SALES_MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    activities = list(
        (
            await db.scalars(
                select(SalesManagerActivity)
                .where(SalesManagerActivity.manager_id == manager_id)
                .order_by(SalesManagerActivity.created_at.desc())
                .limit(1000)
            )
        ).all()
    )
    sessions = list(
        (
            await db.scalars(
                select(SalesManagerSession)
                .where(SalesManagerSession.manager_id == manager_id)
                .order_by(SalesManagerSession.started_at.desc())
                .limit(250)
            )
        ).all()
    )
    reports = list(
        (
            await db.scalars(
                select(SalesDailyReport)
                .where(SalesDailyReport.manager_id == manager_id)
                .order_by(SalesDailyReport.report_date.desc())
                .limit(365)
            )
        ).all()
    )
    report_rows = []
    for report in reports:
        clinics = list(
            (
                await db.scalars(
                    select(SalesReportClinic)
                    .where(SalesReportClinic.report_id == report.id)
                    .order_by(SalesReportClinic.contacted_at.asc())
                )
            ).all()
        )
        report_rows.append(
            {
                "id": str(report.id),
                "report_date": report.report_date,
                "status": report.status,
                "summary": report.summary,
                "submitted_at": report.submitted_at,
                "clinics": [
                    {
                        "id": str(item.id),
                        "clinic_name": item.clinic_name,
                        "country": item.country,
                        "city": item.city,
                        "contact_name": item.contact_name,
                        "email": item.email,
                        "phone": item.phone,
                        "website": item.website,
                        "negotiation_result": item.negotiation_result,
                        "outcome_status": item.outcome_status,
                        "next_step": item.next_step,
                        "notes": item.notes,
                        "contacted_at": item.contacted_at,
                    }
                    for item in clinics
                ],
            }
        )
    return {
        "manager": _manager_payload(manager),
        "stats": await _manager_stats(db, manager.id),
        "balances": await manager_balances(db, manager.id),
        "sessions": [
            {
                "id": str(row.id),
                "started_at": row.started_at,
                "last_seen_at": row.last_seen_at,
                "ended_at": row.ended_at,
                "ip_hash": row.ip_hash,
                "user_agent": row.user_agent,
            }
            for row in sessions
        ],
        "activities": [
            {
                "id": str(row.id),
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "details": row.details,
                "created_at": row.created_at,
                "ip_hash": row.ip_hash,
                "user_agent": row.user_agent,
            }
            for row in activities
        ],
        "reports": report_rows,
    }


@router.get("/sales-withdrawals", dependencies=[Depends(require_platform_admin)])
async def list_sales_withdrawals(
    db: Annotated[AsyncSession, Depends(control_session)],
    status: Literal["PENDING", "PAID", "REJECTED", "ALL"] = "ALL",
):
    query = select(SalesWithdrawalRequest).order_by(SalesWithdrawalRequest.requested_at.desc())
    if status != "ALL":
        query = query.where(SalesWithdrawalRequest.status == status)
    rows = list((await db.scalars(query)).all())
    managers = {
        row.id: row
        for row in (
            await db.scalars(
                select(SalesManager).where(
                    SalesManager.id.in_({item.manager_id for item in rows} or {uuid.uuid4()})
                )
            )
        ).all()
    }
    result = []
    for row in rows:
        manager = managers.get(row.manager_id)
        result.append(
            {
                "id": str(row.id),
                "manager_id": str(row.manager_id),
                "manager_name": (
                    f"{manager.first_name} {manager.last_name}".strip() if manager else "Unknown"
                ),
                "manager_email": manager.email if manager else None,
                "amount": row.amount,
                "currency": row.currency,
                "status": row.status,
                "card_number": decrypt_bank_card(row.encrypted_bank_card_snapshot),
                "bank_card_last4": row.bank_card_last4,
                "bank_account_holder": row.bank_account_holder,
                "requested_at": row.requested_at,
                "reviewed_at": row.reviewed_at,
                "paid_at": row.paid_at,
                "paid_reference": row.paid_reference,
                "admin_note": row.admin_note,
            }
        )
    return result


@router.post(
    "/sales-withdrawals/{withdrawal_id}/confirm", dependencies=[Depends(require_platform_admin)]
)
async def confirm_sales_withdrawal(
    withdrawal_id: uuid.UUID,
    body: WithdrawalDecision,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesWithdrawalRequest, withdrawal_id)
    if not row:
        raise AppError("SALES_WITHDRAWAL_NOT_FOUND", "Withdrawal request was not found.", 404)
    if row.status != "PENDING":
        raise AppError(
            "SALES_WITHDRAWAL_STATE_INVALID",
            "Only pending withdrawals can be paid.",
            409,
        )
    reference = (body.reference or "").strip()
    if not reference:
        raise AppError("SALES_WITHDRAWAL_REFERENCE_REQUIRED", "Payment reference is required.", 422)
    now = datetime.now(UTC)
    row.status = "PAID"
    row.reviewed_at = now
    row.paid_at = now
    row.paid_reference = reference
    row.admin_note = body.note.strip() if body.note else None
    await _audit(
        db,
        action="SALES_WITHDRAWAL_PAID",
        target_type="SALES_WITHDRAWAL",
        target_id=str(row.id),
        details={
            "manager_id": str(row.manager_id),
            "amount": row.amount,
            "currency": row.currency,
            "reference": reference,
        },
    )
    await db.commit()
    return {"paid": True, "id": str(row.id)}


@router.post(
    "/sales-withdrawals/{withdrawal_id}/reject", dependencies=[Depends(require_platform_admin)]
)
async def reject_sales_withdrawal(
    withdrawal_id: uuid.UUID,
    body: WithdrawalDecision,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    row = await db.get(SalesWithdrawalRequest, withdrawal_id)
    if not row:
        raise AppError("SALES_WITHDRAWAL_NOT_FOUND", "Withdrawal request was not found.", 404)
    if row.status != "PENDING":
        raise AppError(
            "SALES_WITHDRAWAL_STATE_INVALID",
            "Only pending withdrawals can be rejected.",
            409,
        )
    row.status = "REJECTED"
    row.reviewed_at = datetime.now(UTC)
    row.admin_note = body.note.strip() if body.note else None
    await _audit(
        db,
        action="SALES_WITHDRAWAL_REJECTED",
        target_type="SALES_WITHDRAWAL",
        target_id=str(row.id),
        details={"manager_id": str(row.manager_id), "amount": row.amount, "currency": row.currency},
    )
    await db.commit()
    return {"rejected": True, "id": str(row.id)}


@router.get("/sales-attributions", dependencies=[Depends(require_platform_admin)])
async def list_sales_attributions(db: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (
            await db.scalars(
                select(SalesReferralAttribution)
                .order_by(SalesReferralAttribution.created_at.desc())
                .limit(1000)
            )
        ).all()
    )
    manager_ids = {row.manager_id for row in rows if row.manager_id}
    managers = (
        {
            row.id: row
            for row in (
                await db.scalars(select(SalesManager).where(SalesManager.id.in_(manager_ids)))
            ).all()
        }
        if manager_ids
        else {}
    )
    request_map = (
        {
            row.id: row
            for row in (
                await db.scalars(
                    select(AccessRequest).where(
                        AccessRequest.id.in_({item.access_request_id for item in rows})
                    )
                )
            ).all()
        }
        if rows
        else {}
    )
    result = []
    for row in rows:
        access_request = request_map.get(row.access_request_id)
        manager = managers.get(row.manager_id) if row.manager_id else None
        result.append(
            {
                "id": str(row.id),
                "access_request_id": str(row.access_request_id),
                "clinic_id": str(row.clinic_id) if row.clinic_id else None,
                "clinic_name": access_request.clinic_name if access_request else None,
                "manager_id": str(row.manager_id) if row.manager_id else None,
                "manager_name": (
                    f"{manager.first_name} {manager.last_name}".strip() if manager else None
                ),
                "report_clinic_id": (str(row.report_clinic_id) if row.report_clinic_id else None),
                "status": row.status,
                "match_method": row.match_method,
                "match_score": row.match_score,
                "match_details": row.match_details,
                "matched_at": row.matched_at,
                "confirmed_at": row.confirmed_at,
                "created_at": row.created_at,
            }
        )
    return result


@router.post(
    "/sales-attributions/{attribution_id}/confirm", dependencies=[Depends(require_platform_admin)]
)
async def admin_confirm_sales_attribution(
    attribution_id: uuid.UUID,
    body: AttributionConfirm,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    attribution = await db.get(SalesReferralAttribution, attribution_id)
    if not attribution:
        raise AppError("SALES_ATTRIBUTION_NOT_FOUND", "Sales attribution was not found.", 404)
    manager = await db.get(SalesManager, body.manager_id)
    if not manager or not manager.is_active:
        raise AppError("SALES_MANAGER_NOT_FOUND", "Active sales manager was not found.", 404)
    if body.report_clinic_id:
        report_entry = await db.get(SalesReportClinic, body.report_clinic_id)
        if not report_entry or report_entry.manager_id != manager.id:
            raise AppError(
                "SALES_REPORT_CLINIC_INVALID",
                "Reported clinic does not belong to this manager.",
                409,
            )
    commission = await confirm_attribution(
        db,
        attribution,
        manager_id=manager.id,
        report_clinic_id=body.report_clinic_id,
    )
    await _audit(
        db,
        action="SALES_ATTRIBUTION_CONFIRMED",
        target_type="SALES_ATTRIBUTION",
        target_id=str(attribution.id),
        details={
            "manager_id": str(manager.id),
            "commission_id": str(commission.id) if commission else None,
        },
    )
    await db.commit()
    return {
        "confirmed": True,
        "manager_id": str(manager.id),
        "commission_id": str(commission.id) if commission else None,
    }


@router.post("/clinics/{clinic_id}/paid-renewal", dependencies=[Depends(require_platform_admin)])
async def paid_clinic_renewal(
    clinic_id: uuid.UUID,
    body: PaidRenewal,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    clinic = await db.get(ClinicRegistry, clinic_id)
    if not clinic:
        raise AppError("CLINIC_NOT_FOUND", "Clinic was not found.", 404)
    currency = body.currency.strip().upper()
    duplicate = await db.scalar(
        select(SalesSubscriptionPayment.id).where(
            SalesSubscriptionPayment.clinic_id == clinic.id,
            SalesSubscriptionPayment.kind == "RENEWAL",
            SalesSubscriptionPayment.reference == body.reference.strip(),
            SalesSubscriptionPayment.amount == body.amount,
            SalesSubscriptionPayment.currency == currency,
        )
    )
    if duplicate:
        raise AppError(
            "SUBSCRIPTION_PAYMENT_DUPLICATE",
            "This paid renewal was already recorded.",
            409,
        )
    settings = await platform_settings(db)
    expires_at = await renew_clinic(clinic, settings, days=body.days)
    clinic.subscription_state = "ACTIVE"
    payment = SalesSubscriptionPayment(
        clinic_id=clinic.id,
        access_request_id=None,
        kind="RENEWAL",
        amount=body.amount,
        currency=currency,
        reference=body.reference.strip(),
        subscription_days=body.days,
        verified_at=datetime.now(UTC),
    )
    db.add(payment)
    await db.flush()
    attribution = await db.scalar(
        select(SalesReferralAttribution)
        .where(
            SalesReferralAttribution.clinic_id == clinic.id,
            SalesReferralAttribution.manager_id.is_not(None),
            SalesReferralAttribution.status.in_(["AUTO_MATCHED", "ADMIN_CONFIRMED"]),
        )
        .order_by(SalesReferralAttribution.created_at.asc())
        .limit(1)
    )
    commission = await create_commission_for_payment(db, payment, attribution)
    await _audit(
        db,
        action="PAID_SUBSCRIPTION_RENEWAL",
        target_type="CLINIC",
        target_id=str(clinic.id),
        details={
            "days": body.days,
            "amount": body.amount,
            "currency": currency,
            "reference": body.reference,
            "expires_at": expires_at.isoformat(),
            "commission_id": str(commission.id) if commission else None,
        },
    )
    await db.commit()
    return {
        "renewed": True,
        "subscription_expires_at": expires_at,
        "payment_id": str(payment.id),
        "commission_id": str(commission.id) if commission else None,
        "commission_rate_percent": COMMISSION_RATE_BPS / 100,
    }
