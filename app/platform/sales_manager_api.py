import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.core.errors import AppError
from app.core.rate_limit import sensitive_limit
from app.database.control_models import (
    PlatformAdminAudit,
    SalesClinicAttribution,
    SalesClinicContact,
    SalesCommission,
    SalesDailyReport,
    SalesManager,
    SalesManagerActivity,
    SalesManagerSession,
    SalesWithdrawal,
)
from app.database.sessions import control_session
from app.platform.api import require_platform_admin
from app.platform.sales_service import (
    MANAGER_SESSION_HOURS,
    available_balance,
    create_manager_session,
    decrypt_bank_card,
    encrypt_bank_card,
    generated_password,
    log_manager_activity,
    manager_admin_payload,
    manager_credentials_email,
    manager_dashboard,
    manager_from_token,
    manager_public_payload,
    normalize_phone,
    normalize_text,
    normalize_website,
    reports_payload,
    unique_manager_username,
)
from app.platform.service import send_logged_email
from app.storage.providers import storage_provider

router = APIRouter(prefix="/platform/sales", tags=["platform-sales"])


class ManagerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    title: str = Field(default="Sales Manager", min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=50)
    territory: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=3000)
    public_verified: bool = True
    commission_rate_bps: int = Field(default=3000, ge=0, le=10000)


class ManagerEdit(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    email: EmailStr | None = None
    title: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=50)
    territory: str | None = Field(default=None, max_length=160)
    bio: str | None = Field(default=None, max_length=3000)
    is_active: bool | None = None
    public_verified: bool | None = None
    commission_rate_bps: int | None = Field(default=None, ge=0, le=10000)


class ManagerLogin(BaseModel):
    login: str = Field(min_length=2, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class BankCardUpdate(BaseModel):
    card_number: str = Field(min_length=12, max_length=40)
    holder_name: str | None = Field(default=None, max_length=180)


class ClinicContactInput(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=200)
    country: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    website: str | None = Field(default=None, max_length=300)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_role: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    negotiation_result: str = Field(min_length=2, max_length=4000)
    outcome: str = Field(min_length=2, max_length=60)
    next_step: str | None = Field(default=None, max_length=3000)
    follow_up_date: date | None = None


class DailyReportSubmit(BaseModel):
    report_date: date
    summary: str | None = Field(default=None, max_length=5000)
    contacts: list[ClinicContactInput] = Field(min_length=1, max_length=100)


class WithdrawalRequest(BaseModel):
    currency: str = Field(min_length=2, max_length=12)
    amount: int = Field(gt=0)


class WithdrawalDecision(BaseModel):
    payment_reference: str | None = Field(default=None, max_length=200)
    admin_note: str | None = Field(default=None, max_length=2000)


class AttributionDecision(BaseModel):
    manager_id: uuid.UUID
    clinic_contact_id: uuid.UUID | None = None


async def require_manager(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    manager, manager_session = await manager_from_token(session, supplied, request)
    await session.flush()
    return manager, manager_session


def _clean(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


@router.get("/public/managers")
async def public_managers(session: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (
            await session.scalars(
                select(SalesManager)
                .where(
                    SalesManager.is_active.is_(True),
                    SalesManager.public_verified.is_(True),
                    SalesManager.deleted_at.is_(None),
                )
                .order_by(SalesManager.full_name.asc())
            )
        ).all()
    )
    return [manager_public_payload(row) for row in rows]


@router.get("/public/managers/{manager_id}/photo")
async def public_manager_photo(
    manager_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await session.get(SalesManager, manager_id)
    if (
        not manager
        or not manager.is_active
        or not manager.public_verified
        or manager.deleted_at is not None
        or not manager.photo_storage_key
    ):
        raise AppError("MANAGER_PHOTO_NOT_FOUND", "Manager photo was not found.", 404)
    data = await storage_provider().read(manager.photo_storage_key)
    suffix = manager.photo_storage_key.rsplit(".", 1)[-1].lower()
    content_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(suffix, "application/octet-stream")
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=300"})


@router.post(
    "/login",
    dependencies=[Depends(sensitive_limit("sales-manager-login", 8, 300))],
)
async def manager_login(
    body: ManagerLogin,
    request: Request,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    login = body.login.strip().casefold()
    manager = await session.scalar(
        select(SalesManager).where(
            SalesManager.deleted_at.is_(None),
            (func.lower(SalesManager.username) == login) | (func.lower(SalesManager.email) == login),
        )
    )
    if not manager or not manager.is_active:
        raise AppError("MANAGER_LOGIN_INVALID", "Username or password is incorrect.", 401)
    from app.auth.security import verify_password

    if not verify_password(body.password, manager.password_hash):
        raise AppError("MANAGER_LOGIN_INVALID", "Username or password is incorrect.", 401)
    token = await create_manager_session(session, manager, request)
    await session.commit()
    return {
        "access_token": token,
        "expires_in": MANAGER_SESSION_HOURS * 3600,
        "manager": manager_admin_payload(manager),
    }


@router.post("/logout")
async def manager_logout(
    request: Request,
    ctx=Depends(require_manager),
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    manager, manager_session = ctx
    manager_session.logout_at = datetime.now(UTC)
    manager_session.logout_reason = "USER_LOGOUT"
    await log_manager_activity(
        session,
        manager,
        action="LOGOUT",
        manager_session=manager_session,
        request=request,
    )
    await session.commit()
    return {"signed_out": True}


@router.get("/me")
async def manager_me(
    ctx=Depends(require_manager),
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    manager, _ = ctx
    await session.commit()
    return manager_admin_payload(manager)


@router.get("/dashboard")
async def sales_dashboard(
    request: Request,
    ctx=Depends(require_manager),
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    manager, manager_session = ctx
    await log_manager_activity(
        session,
        manager,
        action="DASHBOARD_VIEWED",
        manager_session=manager_session,
        request=request,
    )
    payload = await manager_dashboard(session, manager)
    await session.commit()
    return payload


@router.get("/reports")
async def manager_reports(
    ctx=Depends(require_manager),
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    manager, _ = ctx
    payload = await reports_payload(session, manager.id)
    await session.commit()
    return payload


@router.put("/reports/daily")
async def submit_daily_report(
    body: DailyReportSubmit,
    request: Request,
    ctx=Depends(require_manager),
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    manager, manager_session = ctx
    report = await session.scalar(
        select(SalesDailyReport).where(
            SalesDailyReport.manager_id == manager.id,
            SalesDailyReport.report_date == body.report_date,
        )
    )
    now = datetime.now(UTC)
    if report is None:
        report = SalesDailyReport(
            manager_id=manager.id,
            report_date=body.report_date,
            summary=_clean(body.summary),
            submitted_at=now,
            updated_at=now,
        )
        session.add(report)
        await session.flush()
    else:
        report.summary = _clean(body.summary)
        report.updated_at = now
        existing = list(
            (
                await session.scalars(
                    select(SalesClinicContact).where(SalesClinicContact.report_id == report.id)
                )
            ).all()
        )
        for item in existing:
            await session.delete(item)
        await session.flush()

    for item in body.contacts:
        clinic_name = item.clinic_name.strip()
        session.add(
            SalesClinicContact(
                report_id=report.id,
                manager_id=manager.id,
                clinic_name=clinic_name,
                country=_clean(item.country),
                city=_clean(item.city),
                address=_clean(item.address),
                website=_clean(item.website),
                contact_name=_clean(item.contact_name),
                contact_role=_clean(item.contact_role),
                email=str(item.email).casefold() if item.email else None,
                phone=_clean(item.phone),
                negotiation_result=item.negotiation_result.strip(),
                outcome=item.outcome.strip().upper(),
                next_step=_clean(item.next_step),
                follow_up_date=item.follow_up_date,
                clinic_name_norm=normalize_text(clinic_name) or clinic_name.casefold(),
                email_norm=normalize_text(str(item.email)) if item.email else None,
                phone_norm=normalize_phone(item.phone),
                website_norm=normalize_website(item.website),
                city_norm=normalize_text(item.city),
                address_norm=normalize_text(item.address),
                created_at=now,
                updated_at=now,
            )
        )
    await log_manager_activity(
        session,
        manager,
        action="DAILY_REPORT_SUBMITTED",
        details={"report_date": body.report_date.isoformat(), "clinic_count": len(body.contacts)},
        manager_session=manager_session,
        request=request,
    )
    await session.commit()
    return {"saved": True, "report_date": body.report_date, "clinic_count": len(body.contacts)}


@router.put("/bank-card")
async def update_bank_card(
    body: BankCardUpdate,
    request: Request,
    ctx=Depends(require_manager),
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    manager, manager_session = ctx
    ciphertext, last4 = encrypt_bank_card(body.card_number)
    manager.bank_card_ciphertext = ciphertext
    manager.bank_card_last4 = last4
    manager.bank_card_holder = _clean(body.holder_name)
    manager.bank_card_updated_at = datetime.now(UTC)
    manager.updated_at = datetime.now(UTC)
    await log_manager_activity(
        session,
        manager,
        action="BANK_CARD_UPDATED",
        details={"last4": last4},
        manager_session=manager_session,
        request=request,
    )
    await session.commit()
    return {"saved": True, "last4": last4, "holder_name": manager.bank_card_holder}


@router.post("/withdrawals")
async def request_withdrawal(
    body: WithdrawalRequest,
    request: Request,
    ctx=Depends(require_manager),
    session: Annotated[AsyncSession, Depends(control_session)] = None,
):
    manager, manager_session = ctx
    if not manager.bank_card_ciphertext or not manager.bank_card_last4:
        raise AppError("BANK_CARD_REQUIRED", "Add a bank card before requesting a withdrawal.", 409)
    currency = body.currency.strip().upper()
    balances = await available_balance(session, manager.id)
    if body.amount > balances.get(currency, 0):
        raise AppError("WITHDRAWAL_BALANCE_INSUFFICIENT", "Withdrawal exceeds the available balance.", 409)
    withdrawal = SalesWithdrawal(
        manager_id=manager.id,
        currency=currency,
        amount=body.amount,
        status="REQUESTED",
        bank_card_ciphertext=manager.bank_card_ciphertext,
        bank_card_last4=manager.bank_card_last4,
        bank_card_holder=manager.bank_card_holder,
    )
    session.add(withdrawal)
    await session.flush()
    await log_manager_activity(
        session,
        manager,
        action="WITHDRAWAL_REQUESTED",
        details={"withdrawal_id": str(withdrawal.id), "amount": body.amount, "currency": currency},
        manager_session=manager_session,
        request=request,
    )
    await session.commit()
    return {"id": str(withdrawal.id), "status": withdrawal.status}


@router.get("/admin/managers", dependencies=[Depends(require_platform_admin)])
async def admin_managers(session: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (
            await session.scalars(
                select(SalesManager).where(SalesManager.deleted_at.is_(None)).order_by(SalesManager.created_at.desc())
            )
        ).all()
    )
    output = []
    for manager in rows:
        activity_count = int(
            await session.scalar(
                select(func.count()).select_from(SalesManagerActivity).where(SalesManagerActivity.manager_id == manager.id)
            )
            or 0
        )
        report_count = int(
            await session.scalar(
                select(func.count()).select_from(SalesDailyReport).where(SalesDailyReport.manager_id == manager.id)
            )
            or 0
        )
        balances = await available_balance(session, manager.id)
        output.append({**manager_admin_payload(manager), "activity_count": activity_count, "report_count": report_count, "available_balance": balances})
    return output


@router.post("/admin/managers", dependencies=[Depends(require_platform_admin)], status_code=201)
async def admin_create_manager(
    body: ManagerCreate,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    email = str(body.email).casefold()
    if await session.scalar(select(SalesManager.id).where(func.lower(SalesManager.email) == email)):
        raise AppError("MANAGER_EMAIL_EXISTS", "A sales manager with this email already exists.", 409)
    username = await unique_manager_username(session, body.full_name, email)
    password = generated_password()
    manager = SalesManager(
        username=username,
        email=email,
        password_hash=hash_password(password),
        full_name=body.full_name.strip(),
        title=body.title.strip(),
        phone=_clean(body.phone),
        territory=_clean(body.territory),
        bio=_clean(body.bio),
        is_active=True,
        public_verified=body.public_verified,
        commission_rate_bps=body.commission_rate_bps,
    )
    session.add(manager)
    await session.flush()
    subject, email_body = manager_credentials_email(manager, password)
    await send_logged_email(
        session,
        recipient=manager.email,
        subject=subject,
        body=email_body,
        kind="SALES_MANAGER_CREDENTIALS",
    )
    session.add(
        PlatformAdminAudit(
            action="SALES_MANAGER_CREATED",
            target_type="SALES_MANAGER",
            target_id=str(manager.id),
            details={"email": manager.email, "username": manager.username, "commission_rate_bps": manager.commission_rate_bps},
        )
    )
    await session.commit()
    return manager_admin_payload(manager)


@router.patch("/admin/managers/{manager_id}", dependencies=[Depends(require_platform_admin)])
async def admin_edit_manager(
    manager_id: uuid.UUID,
    body: ManagerEdit,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await session.get(SalesManager, manager_id)
    if not manager or manager.deleted_at is not None:
        raise AppError("MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    changes = body.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None:
        next_email = str(changes["email"]).casefold()
        duplicate = await session.scalar(
            select(SalesManager.id).where(func.lower(SalesManager.email) == next_email, SalesManager.id != manager.id)
        )
        if duplicate:
            raise AppError("MANAGER_EMAIL_EXISTS", "A sales manager with this email already exists.", 409)
        manager.email = next_email
    for field in ("full_name", "title", "phone", "territory", "bio"):
        if field in changes:
            setattr(manager, field, _clean(changes[field]))
    for field in ("is_active", "public_verified", "commission_rate_bps"):
        if field in changes:
            setattr(manager, field, changes[field])
    manager.updated_at = datetime.now(UTC)
    if "is_active" in changes and changes["is_active"] is False:
        sessions = list(
            (
                await session.scalars(
                    select(SalesManagerSession).where(
                        SalesManagerSession.manager_id == manager.id,
                        SalesManagerSession.logout_at.is_(None),
                    )
                )
            ).all()
        )
        for manager_session in sessions:
            manager_session.logout_at = datetime.now(UTC)
            manager_session.logout_reason = "ADMIN_DISABLED"
    session.add(
        PlatformAdminAudit(
            action="SALES_MANAGER_UPDATED",
            target_type="SALES_MANAGER",
            target_id=str(manager.id),
            details={"fields": list(changes)},
        )
    )
    await session.commit()
    return manager_admin_payload(manager)


@router.delete("/admin/managers/{manager_id}", dependencies=[Depends(require_platform_admin)])
async def admin_delete_manager(
    manager_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await session.get(SalesManager, manager_id)
    if not manager or manager.deleted_at is not None:
        raise AppError("MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    manager.is_active = False
    manager.public_verified = False
    manager.deleted_at = datetime.now(UTC)
    manager.updated_at = datetime.now(UTC)
    sessions = list(
        (
            await session.scalars(
                select(SalesManagerSession).where(
                    SalesManagerSession.manager_id == manager.id,
                    SalesManagerSession.logout_at.is_(None),
                )
            )
        ).all()
    )
    for manager_session in sessions:
        manager_session.logout_at = datetime.now(UTC)
        manager_session.logout_reason = "ADMIN_DELETED"
    session.add(
        PlatformAdminAudit(
            action="SALES_MANAGER_DELETED",
            target_type="SALES_MANAGER",
            target_id=str(manager.id),
            details={"email": manager.email},
        )
    )
    await session.commit()
    return {"deleted": True, "history_preserved": True}


@router.post("/admin/managers/{manager_id}/reset-password", dependencies=[Depends(require_platform_admin)])
async def admin_reset_manager_password(
    manager_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await session.get(SalesManager, manager_id)
    if not manager or manager.deleted_at is not None:
        raise AppError("MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    password = generated_password()
    manager.password_hash = hash_password(password)
    manager.updated_at = datetime.now(UTC)
    sessions = list(
        (
            await session.scalars(
                select(SalesManagerSession).where(
                    SalesManagerSession.manager_id == manager.id,
                    SalesManagerSession.logout_at.is_(None),
                )
            )
        ).all()
    )
    for manager_session in sessions:
        manager_session.logout_at = datetime.now(UTC)
        manager_session.logout_reason = "PASSWORD_RESET"
    subject, email_body = manager_credentials_email(manager, password)
    await send_logged_email(session, recipient=manager.email, subject=subject, body=email_body, kind="SALES_MANAGER_PASSWORD_RESET")
    session.add(
        PlatformAdminAudit(
            action="SALES_MANAGER_PASSWORD_RESET",
            target_type="SALES_MANAGER",
            target_id=str(manager.id),
            details={},
        )
    )
    await session.commit()
    return {"reset": True, "email_sent": True}


@router.post("/admin/managers/{manager_id}/photo", dependencies=[Depends(require_platform_admin)])
async def admin_upload_manager_photo(
    manager_id: uuid.UUID,
    file: UploadFile,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await session.get(SalesManager, manager_id)
    if not manager or manager.deleted_at is not None:
        raise AppError("MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    content_type = (file.content_type or "").lower()
    extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(content_type)
    if not extension:
        raise AppError("MANAGER_PHOTO_TYPE_INVALID", "Use JPEG, PNG, or WebP for manager photos.", 422)
    data = await file.read()
    if not data or len(data) > 5 * 1024 * 1024:
        raise AppError("MANAGER_PHOTO_SIZE_INVALID", "Manager photo must be between 1 byte and 5 MiB.", 422)
    key = f"platform/sales-managers/{manager.id}/{uuid.uuid4().hex}.{extension}"
    provider = storage_provider()
    await provider.upload(key, data, content_type)
    previous = manager.photo_storage_key
    manager.photo_storage_key = key
    manager.updated_at = datetime.now(UTC)
    session.add(
        PlatformAdminAudit(
            action="SALES_MANAGER_PHOTO_UPDATED",
            target_type="SALES_MANAGER",
            target_id=str(manager.id),
            details={},
        )
    )
    await session.commit()
    if previous:
        try:
            await provider.delete(previous)
        except Exception:
            pass
    return {"uploaded": True, "photo_available": True}


@router.get("/admin/managers/{manager_id}/detail", dependencies=[Depends(require_platform_admin)])
async def admin_manager_detail(
    manager_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await session.get(SalesManager, manager_id)
    if not manager:
        raise AppError("MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    activities = list(
        (
            await session.scalars(
                select(SalesManagerActivity)
                .where(SalesManagerActivity.manager_id == manager.id)
                .order_by(SalesManagerActivity.created_at.desc())
                .limit(300)
            )
        ).all()
    )
    sessions = list(
        (
            await session.scalars(
                select(SalesManagerSession)
                .where(SalesManagerSession.manager_id == manager.id)
                .order_by(SalesManagerSession.login_at.desc())
                .limit(100)
            )
        ).all()
    )
    return {
        "manager": manager_admin_payload(manager),
        "dashboard": await manager_dashboard(session, manager),
        "reports": await reports_payload(session, manager.id),
        "activities": [
            {
                "id": str(row.id),
                "action": row.action,
                "details": row.details,
                "ip_address": row.ip_address,
                "created_at": row.created_at,
            }
            for row in activities
        ],
        "sessions": [
            {
                "id": str(row.id),
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "login_at": row.login_at,
                "last_seen_at": row.last_seen_at,
                "expires_at": row.expires_at,
                "logout_at": row.logout_at,
                "logout_reason": row.logout_reason,
            }
            for row in sessions
        ],
    }


@router.get("/admin/withdrawals", dependencies=[Depends(require_platform_admin)])
async def admin_withdrawals(session: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (
            await session.scalars(
                select(SalesWithdrawal).order_by(SalesWithdrawal.requested_at.desc())
            )
        ).all()
    )
    managers = {manager.id: manager for manager in (await session.scalars(select(SalesManager))).all()}
    return [
        {
            "id": str(row.id),
            "manager_id": str(row.manager_id),
            "manager_name": managers[row.manager_id].full_name if row.manager_id in managers else "Unknown",
            "currency": row.currency,
            "amount": row.amount,
            "status": row.status,
            "bank_card_last4": row.bank_card_last4,
            "bank_card_holder": row.bank_card_holder,
            "requested_at": row.requested_at,
            "processed_at": row.processed_at,
            "payment_reference": row.payment_reference,
            "admin_note": row.admin_note,
        }
        for row in rows
    ]


@router.post("/admin/withdrawals/{withdrawal_id}/pay", dependencies=[Depends(require_platform_admin)])
async def admin_pay_withdrawal(
    withdrawal_id: uuid.UUID,
    body: WithdrawalDecision,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(SalesWithdrawal, withdrawal_id)
    if not row:
        raise AppError("WITHDRAWAL_NOT_FOUND", "Withdrawal request was not found.", 404)
    if row.status != "REQUESTED":
        raise AppError("WITHDRAWAL_STATE_INVALID", "Only requested withdrawals can be paid.", 409)
    if not body.payment_reference or not body.payment_reference.strip():
        raise AppError("PAYMENT_REFERENCE_REQUIRED", "Enter the manual payment reference.", 422)
    available = await session.scalars(
        select(SalesCommission)
        .where(
            SalesCommission.manager_id == row.manager_id,
            SalesCommission.currency == row.currency,
            SalesCommission.status == "AVAILABLE",
        )
        .order_by(SalesCommission.created_at.asc())
    )
    remaining = row.amount
    commissions = list(available.all())
    total = sum(item.commission_amount for item in commissions)
    other_pending = int(
        await session.scalar(
            select(func.coalesce(func.sum(SalesWithdrawal.amount), 0)).where(
                SalesWithdrawal.manager_id == row.manager_id,
                SalesWithdrawal.currency == row.currency,
                SalesWithdrawal.status == "REQUESTED",
                SalesWithdrawal.id != row.id,
            )
        )
        or 0
    )
    if total - other_pending < row.amount:
        raise AppError("WITHDRAWAL_BALANCE_CHANGED", "The available manager balance is no longer sufficient.", 409)
    for commission in commissions:
        if remaining <= 0:
            break
        if commission.commission_amount <= remaining:
            commission.status = "PAID"
            remaining -= commission.commission_amount
        else:
            # Keep exact accounting by splitting a partially consumed commission.
            paid_part = remaining
            commission.commission_amount -= paid_part
            session.add(
                SalesCommission(
                    manager_id=commission.manager_id,
                    clinic_id=commission.clinic_id,
                    payment_id=commission.payment_id,
                    attribution_id=commission.attribution_id,
                    rate_bps=commission.rate_bps,
                    gross_amount=commission.gross_amount,
                    commission_amount=paid_part,
                    currency=commission.currency,
                    status="PAID",
                )
            )
            remaining = 0
    row.status = "PAID"
    row.processed_at = datetime.now(UTC)
    row.payment_reference = body.payment_reference.strip()
    row.admin_note = _clean(body.admin_note)
    session.add(
        PlatformAdminAudit(
            action="SALES_WITHDRAWAL_PAID",
            target_type="SALES_WITHDRAWAL",
            target_id=str(row.id),
            details={"manager_id": str(row.manager_id), "amount": row.amount, "currency": row.currency, "payment_reference": row.payment_reference},
        )
    )
    await session.commit()
    return {"paid": True, "withdrawal_id": str(row.id)}


@router.post("/admin/withdrawals/{withdrawal_id}/reject", dependencies=[Depends(require_platform_admin)])
async def admin_reject_withdrawal(
    withdrawal_id: uuid.UUID,
    body: WithdrawalDecision,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(SalesWithdrawal, withdrawal_id)
    if not row:
        raise AppError("WITHDRAWAL_NOT_FOUND", "Withdrawal request was not found.", 404)
    if row.status != "REQUESTED":
        raise AppError("WITHDRAWAL_STATE_INVALID", "Only requested withdrawals can be rejected.", 409)
    row.status = "REJECTED"
    row.processed_at = datetime.now(UTC)
    row.admin_note = _clean(body.admin_note)
    session.add(
        PlatformAdminAudit(
            action="SALES_WITHDRAWAL_REJECTED",
            target_type="SALES_WITHDRAWAL",
            target_id=str(row.id),
            details={"manager_id": str(row.manager_id), "amount": row.amount, "currency": row.currency},
        )
    )
    await session.commit()
    return {"rejected": True}


@router.get("/admin/attributions", dependencies=[Depends(require_platform_admin)])
async def admin_attributions(session: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (
            await session.scalars(
                select(SalesClinicAttribution).order_by(SalesClinicAttribution.attributed_at.desc())
            )
        ).all()
    )
    managers = {manager.id: manager for manager in (await session.scalars(select(SalesManager))).all()}
    contacts = {contact.id: contact for contact in (await session.scalars(select(SalesClinicContact))).all()}
    return [
        {
            "id": str(row.id),
            "manager_id": str(row.manager_id),
            "manager_name": managers[row.manager_id].full_name if row.manager_id in managers else "Unknown",
            "clinic_id": str(row.clinic_id),
            "access_request_id": str(row.access_request_id) if row.access_request_id else None,
            "clinic_contact_id": str(row.clinic_contact_id) if row.clinic_contact_id else None,
            "reported_clinic_name": contacts[row.clinic_contact_id].clinic_name if row.clinic_contact_id in contacts else None,
            "match_score": row.match_score,
            "matched_signals": row.matched_signals,
            "status": row.status,
            "attributed_at": row.attributed_at,
        }
        for row in rows
    ]


@router.post("/admin/attributions/{attribution_id}/confirm", dependencies=[Depends(require_platform_admin)])
async def admin_confirm_attribution(
    attribution_id: uuid.UUID,
    body: AttributionDecision,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    row = await session.get(SalesClinicAttribution, attribution_id)
    if not row:
        raise AppError("ATTRIBUTION_NOT_FOUND", "Sales attribution was not found.", 404)
    manager = await session.get(SalesManager, body.manager_id)
    if not manager or manager.deleted_at is not None:
        raise AppError("MANAGER_NOT_FOUND", "Sales manager was not found.", 404)
    if body.clinic_contact_id:
        contact = await session.get(SalesClinicContact, body.clinic_contact_id)
        if not contact or contact.manager_id != manager.id:
            raise AppError("CLINIC_CONTACT_INVALID", "Selected clinic contact does not belong to this manager.", 409)
        row.clinic_contact_id = contact.id
    row.manager_id = manager.id
    row.status = "ADMIN_CONFIRMED"
    session.add(
        PlatformAdminAudit(
            action="SALES_ATTRIBUTION_CONFIRMED",
            target_type="SALES_ATTRIBUTION",
            target_id=str(row.id),
            details={"manager_id": str(manager.id), "clinic_id": str(row.clinic_id)},
        )
    )
    await session.commit()
    return {"confirmed": True}


@router.get("/admin/managers/{manager_id}/bank-destination", dependencies=[Depends(require_platform_admin)])
async def admin_bank_destination(
    manager_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await session.get(SalesManager, manager_id)
    if not manager or not manager.bank_card_ciphertext:
        raise AppError("BANK_CARD_NOT_FOUND", "Manager bank card is not configured.", 404)
    return {
        "manager_id": str(manager.id),
        "card_number": decrypt_bank_card(manager.bank_card_ciphertext),
        "holder_name": manager.bank_card_holder,
        "last4": manager.bank_card_last4,
    }
