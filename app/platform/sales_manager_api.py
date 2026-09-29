import re
import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password, verify_password
from app.core.errors import AppError
from app.core.rate_limit import sensitive_limit
from app.database.control_models import (
    SalesCommission,
    SalesDailyReport,
    SalesManager,
    SalesReportClinic,
    SalesWithdrawalRequest,
)
from app.database.sessions import control_session
from app.platform.sales_manager_auth import (
    SALES_SESSION_HOURS,
    SalesManagerContext,
    authenticate_sales_manager,
    record_sales_activity,
    require_sales_manager,
)
from app.platform.sales_manager_service import (
    encrypt_bank_card,
    manager_balances,
    normalize_email,
    normalize_name,
    normalize_phone,
    normalize_website,
)
from app.storage.providers import LocalStorageProvider, storage_provider

router = APIRouter(prefix="/platform/sales-managers", tags=["platform-sales-managers"])


class ManagerLogin(BaseModel):
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=10, max_length=512)


class BankCardUpdate(BaseModel):
    card_number: str = Field(min_length=12, max_length=40)
    account_holder: str = Field(min_length=2, max_length=160)


class ReportClinicInput(BaseModel):
    clinic_name: str = Field(min_length=2, max_length=200)
    country: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=2, max_length=100)
    address: str | None = Field(default=None, max_length=300)
    website: str | None = Field(default=None, max_length=300)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_role: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    negotiation_result: str = Field(min_length=2, max_length=4000)
    outcome_status: Literal[
        "CONTACTED",
        "INTERESTED",
        "FOLLOW_UP",
        "PAYMENT_EXPECTED",
        "NOT_INTERESTED",
        "NO_RESPONSE",
    ] = "CONTACTED"
    next_step: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    contacted_at: datetime | None = None


class DailyReportUpsert(BaseModel):
    summary: str | None = Field(default=None, max_length=5000)
    clinics: list[ReportClinicInput] = Field(min_length=1, max_length=100)
    submit: bool = False


class WithdrawalCreate(BaseModel):
    amount: int = Field(gt=0, le=1_000_000_000)
    currency: str = Field(min_length=2, max_length=12)


def _manager_payload(manager: SalesManager) -> dict:
    return {
        "id": str(manager.id),
        "username": manager.username,
        "email": manager.email,
        "first_name": manager.first_name,
        "last_name": manager.last_name,
        "name": f"{manager.first_name} {manager.last_name}".strip(),
        "title": manager.title,
        "phone": manager.phone,
        "is_active": manager.is_active,
        "is_public": manager.is_public,
        "verified_at": manager.verified_at,
        "must_change_password": manager.must_change_password,
        "bank_card_last4": manager.bank_card_last4,
        "bank_account_holder": manager.bank_account_holder,
        "last_login_at": manager.last_login_at,
        "last_logout_at": manager.last_logout_at,
        "created_at": manager.created_at,
    }


def _report_entry_payload(entry: SalesReportClinic) -> dict:
    return {
        "id": str(entry.id),
        "clinic_name": entry.clinic_name,
        "country": entry.country,
        "city": entry.city,
        "address": entry.address,
        "website": entry.website,
        "contact_name": entry.contact_name,
        "contact_role": entry.contact_role,
        "email": entry.email,
        "phone": entry.phone,
        "negotiation_result": entry.negotiation_result,
        "outcome_status": entry.outcome_status,
        "next_step": entry.next_step,
        "notes": entry.notes,
        "contacted_at": entry.contacted_at,
        "created_at": entry.created_at,
    }


async def _report_payload(db: AsyncSession, report: SalesDailyReport) -> dict:
    entries = list(
        (
            await db.scalars(
                select(SalesReportClinic)
                .where(SalesReportClinic.report_id == report.id)
                .order_by(SalesReportClinic.contacted_at.asc())
            )
        ).all()
    )
    return {
        "id": str(report.id),
        "report_date": report.report_date,
        "status": report.status,
        "summary": report.summary,
        "submitted_at": report.submitted_at,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "clinics": [_report_entry_payload(entry) for entry in entries],
    }


@router.post(
    "/login",
    dependencies=[Depends(sensitive_limit("sales-manager-login", 8, 300))],
)
async def manager_login(
    body: ManagerLogin,
    request: Request,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    manager, _, token = await authenticate_sales_manager(
        db,
        request,
        identifier=body.identifier,
        password=body.password,
    )
    await db.commit()
    return {
        "access_token": token,
        "expires_in": SALES_SESSION_HOURS * 60 * 60,
        "manager": _manager_payload(manager),
    }


@router.post("/logout")
async def manager_logout(ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)]):
    now = datetime.now(UTC)
    ctx.session_row.ended_at = now
    ctx.session_row.last_seen_at = now
    ctx.manager.last_logout_at = now
    ctx.manager.updated_at = now
    await record_sales_activity(
        ctx,
        action="LOGOUT",
        entity_type="SESSION",
        entity_id=str(ctx.session_row.id),
    )
    await ctx.db.commit()
    return {"ok": True}


@router.get("/me")
async def manager_me(ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)]):
    await record_sales_activity(ctx, action="PROFILE_VIEWED")
    await ctx.db.commit()
    return _manager_payload(ctx.manager)


@router.post("/password")
async def manager_change_password(
    body: PasswordChange,
    ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)],
):
    if not verify_password(body.current_password, ctx.manager.password_hash):
        raise AppError("PASSWORD_INVALID", "Current password is incorrect.", 400)
    if body.current_password == body.new_password:
        raise AppError("PASSWORD_UNCHANGED", "New password must be different.", 400)
    ctx.manager.password_hash = hash_password(body.new_password)
    ctx.manager.must_change_password = False
    ctx.manager.token_version += 1
    ctx.manager.updated_at = datetime.now(UTC)
    await record_sales_activity(ctx, action="PASSWORD_CHANGED")
    await ctx.db.commit()
    return {"changed": True, "sign_in_again": True}


@router.put("/bank-card")
async def manager_update_bank_card(
    body: BankCardUpdate,
    ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)],
):
    digits = re.sub(r"\D+", "", body.card_number)
    if not 12 <= len(digits) <= 19:
        raise AppError(
            "BANK_CARD_INVALID",
            "Card number must contain between 12 and 19 digits.",
            422,
        )
    ctx.manager.encrypted_bank_card = encrypt_bank_card(digits)
    ctx.manager.bank_card_last4 = digits[-4:]
    ctx.manager.bank_account_holder = body.account_holder.strip()
    ctx.manager.updated_at = datetime.now(UTC)
    await record_sales_activity(
        ctx,
        action="BANK_CARD_UPDATED",
        details={"last4": digits[-4:]},
    )
    await ctx.db.commit()
    return {
        "bank_card_last4": ctx.manager.bank_card_last4,
        "bank_account_holder": ctx.manager.bank_account_holder,
    }


@router.get("/dashboard")
async def manager_dashboard(ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)]):
    db = ctx.db
    report_count = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesDailyReport)
            .where(
                SalesDailyReport.manager_id == ctx.manager.id,
                SalesDailyReport.status == "SUBMITTED",
            )
        )
        or 0
    )
    clinic_count = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesReportClinic)
            .where(SalesReportClinic.manager_id == ctx.manager.id)
        )
        or 0
    )
    commission_count = int(
        await db.scalar(
            select(func.count())
            .select_from(SalesCommission)
            .where(SalesCommission.manager_id == ctx.manager.id)
        )
        or 0
    )
    recent_commissions = list(
        (
            await db.scalars(
                select(SalesCommission)
                .where(SalesCommission.manager_id == ctx.manager.id)
                .order_by(SalesCommission.created_at.desc())
                .limit(20)
            )
        ).all()
    )
    withdrawals = list(
        (
            await db.scalars(
                select(SalesWithdrawalRequest)
                .where(SalesWithdrawalRequest.manager_id == ctx.manager.id)
                .order_by(SalesWithdrawalRequest.requested_at.desc())
                .limit(20)
            )
        ).all()
    )
    today_report = await db.scalar(
        select(SalesDailyReport).where(
            SalesDailyReport.manager_id == ctx.manager.id,
            SalesDailyReport.report_date == date.today(),
        )
    )
    await record_sales_activity(ctx, action="DASHBOARD_VIEWED")
    await db.commit()
    return {
        "manager": _manager_payload(ctx.manager),
        "summary": {
            "submitted_reports": report_count,
            "reported_clinics": clinic_count,
            "commission_events": commission_count,
            "today_report_status": today_report.status if today_report else "NOT_STARTED",
        },
        "balances": await manager_balances(db, ctx.manager.id),
        "recent_commissions": [
            {
                "id": str(row.id),
                "clinic_id": str(row.clinic_id),
                "gross_amount": row.gross_amount,
                "commission_rate_percent": row.commission_rate_bps / 100,
                "commission_amount": row.commission_amount,
                "currency": row.currency,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in recent_commissions
        ],
        "withdrawals": [
            {
                "id": str(row.id),
                "amount": row.amount,
                "currency": row.currency,
                "status": row.status,
                "bank_card_last4": row.bank_card_last4,
                "requested_at": row.requested_at,
                "reviewed_at": row.reviewed_at,
                "paid_at": row.paid_at,
                "paid_reference": row.paid_reference,
                "admin_note": row.admin_note,
            }
            for row in withdrawals
        ],
    }


@router.get("/reports")
async def manager_reports(ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)]):
    rows = list(
        (
            await ctx.db.scalars(
                select(SalesDailyReport)
                .where(SalesDailyReport.manager_id == ctx.manager.id)
                .order_by(SalesDailyReport.report_date.desc())
                .limit(365)
            )
        ).all()
    )
    await record_sales_activity(ctx, action="REPORT_HISTORY_VIEWED")
    await ctx.db.commit()
    return [await _report_payload(ctx.db, row) for row in rows]


@router.get("/reports/{report_date}")
async def manager_report(
    report_date: date,
    ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)],
):
    row = await ctx.db.scalar(
        select(SalesDailyReport).where(
            SalesDailyReport.manager_id == ctx.manager.id,
            SalesDailyReport.report_date == report_date,
        )
    )
    if not row:
        raise AppError("SALES_REPORT_NOT_FOUND", "Daily report was not found.", 404)
    await record_sales_activity(
        ctx,
        action="REPORT_VIEWED",
        entity_type="DAILY_REPORT",
        entity_id=str(row.id),
    )
    await ctx.db.commit()
    return await _report_payload(ctx.db, row)


@router.put("/reports/{report_date}")
async def manager_upsert_report(
    report_date: date,
    body: DailyReportUpsert,
    ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)],
):
    if report_date > date.today():
        raise AppError("SALES_REPORT_DATE_INVALID", "Future daily reports are not allowed.", 422)
    db = ctx.db
    row = await db.scalar(
        select(SalesDailyReport).where(
            SalesDailyReport.manager_id == ctx.manager.id,
            SalesDailyReport.report_date == report_date,
        )
    )
    now = datetime.now(UTC)
    if row and row.status == "SUBMITTED":
        raise AppError(
            "SALES_REPORT_LOCKED",
            "Submitted daily reports are immutable. Contact an administrator if a correction is required.",
            409,
        )
    if not row:
        row = SalesDailyReport(
            manager_id=ctx.manager.id,
            report_date=report_date,
            status="DRAFT",
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
    row.summary = body.summary.strip() if body.summary else None
    row.updated_at = now

    await db.execute(delete(SalesReportClinic).where(SalesReportClinic.report_id == row.id))
    for item in body.clinics:
        db.add(
            SalesReportClinic(
                report_id=row.id,
                manager_id=ctx.manager.id,
                clinic_name=item.clinic_name.strip(),
                country=item.country.strip(),
                city=item.city.strip(),
                address=item.address.strip() if item.address else None,
                website=item.website.strip() if item.website else None,
                contact_name=item.contact_name.strip() if item.contact_name else None,
                contact_role=item.contact_role.strip() if item.contact_role else None,
                email=str(item.email).casefold() if item.email else None,
                phone=item.phone.strip() if item.phone else None,
                negotiation_result=item.negotiation_result.strip(),
                outcome_status=item.outcome_status,
                next_step=item.next_step.strip() if item.next_step else None,
                notes=item.notes.strip() if item.notes else None,
                contacted_at=item.contacted_at or now,
                normalized_name=normalize_name(item.clinic_name),
                normalized_email=normalize_email(str(item.email)) if item.email else None,
                normalized_phone=normalize_phone(item.phone),
                normalized_website=normalize_website(item.website),
            )
        )
    if body.submit:
        row.status = "SUBMITTED"
        row.submitted_at = now
    await record_sales_activity(
        ctx,
        action="REPORT_SUBMITTED" if body.submit else "REPORT_SAVED",
        entity_type="DAILY_REPORT",
        entity_id=str(row.id),
        details={"report_date": report_date.isoformat(), "clinic_count": len(body.clinics)},
    )
    await db.commit()
    await db.refresh(row)
    return await _report_payload(db, row)


@router.get("/withdrawals")
async def manager_withdrawals(ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)]):
    rows = list(
        (
            await ctx.db.scalars(
                select(SalesWithdrawalRequest)
                .where(SalesWithdrawalRequest.manager_id == ctx.manager.id)
                .order_by(SalesWithdrawalRequest.requested_at.desc())
            )
        ).all()
    )
    await record_sales_activity(ctx, action="WITHDRAWAL_HISTORY_VIEWED")
    await ctx.db.commit()
    return [
        {
            "id": str(row.id),
            "amount": row.amount,
            "currency": row.currency,
            "status": row.status,
            "bank_card_last4": row.bank_card_last4,
            "requested_at": row.requested_at,
            "reviewed_at": row.reviewed_at,
            "paid_at": row.paid_at,
            "paid_reference": row.paid_reference,
            "admin_note": row.admin_note,
        }
        for row in rows
    ]


@router.post("/withdrawals", status_code=201)
async def manager_request_withdrawal(
    body: WithdrawalCreate,
    ctx: Annotated[SalesManagerContext, Depends(require_sales_manager)],
):
    if not ctx.manager.encrypted_bank_card or not ctx.manager.bank_card_last4:
        raise AppError(
            "BANK_CARD_REQUIRED",
            "Add a payout card before requesting a withdrawal.",
            409,
        )
    currency = body.currency.strip().upper()
    balances = {row["currency"]: row for row in await manager_balances(ctx.db, ctx.manager.id)}
    available = int(balances.get(currency, {}).get("available", 0))
    if body.amount > available:
        raise AppError(
            "WITHDRAWAL_BALANCE_INSUFFICIENT",
            "Requested amount exceeds the available balance.",
            409,
        )
    row = SalesWithdrawalRequest(
        manager_id=ctx.manager.id,
        amount=body.amount,
        currency=currency,
        status="PENDING",
        bank_card_last4=ctx.manager.bank_card_last4,
        encrypted_bank_card_snapshot=ctx.manager.encrypted_bank_card,
        bank_account_holder=ctx.manager.bank_account_holder,
    )
    ctx.db.add(row)
    await ctx.db.flush()
    await record_sales_activity(
        ctx,
        action="WITHDRAWAL_REQUESTED",
        entity_type="WITHDRAWAL",
        entity_id=str(row.id),
        details={"amount": row.amount, "currency": row.currency},
    )
    await ctx.db.commit()
    return {
        "id": str(row.id),
        "amount": row.amount,
        "currency": row.currency,
        "status": row.status,
        "bank_card_last4": row.bank_card_last4,
        "requested_at": row.requested_at,
    }


@router.get("/public")
async def public_sales_managers(db: Annotated[AsyncSession, Depends(control_session)]):
    rows = list(
        (
            await db.scalars(
                select(SalesManager)
                .where(
                    SalesManager.is_active.is_(True),
                    SalesManager.is_public.is_(True),
                    SalesManager.verified_at.is_not(None),
                    SalesManager.photo_storage_key.is_not(None),
                )
                .order_by(SalesManager.first_name.asc(), SalesManager.last_name.asc())
            )
        ).all()
    )
    return [
        {
            "id": str(row.id),
            "name": f"{row.first_name} {row.last_name}".strip(),
            "title": row.title,
            "email": row.email,
            "photo_url": f"/api/v1/platform/sales-managers/public/{row.id}/photo",
            "verified": True,
        }
        for row in rows
    ]


@router.get("/public/{manager_id}/photo")
async def public_manager_photo(
    manager_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(control_session)],
):
    manager = await db.get(SalesManager, manager_id)
    if (
        not manager
        or not manager.is_active
        or not manager.is_public
        or not manager.verified_at
        or not manager.photo_storage_key
        or not manager.photo_mime
    ):
        raise AppError(
            "SALES_MANAGER_PHOTO_NOT_FOUND", "Manager photo was not found.", 404
        )
    provider = storage_provider()
    if isinstance(provider, LocalStorageProvider):
        try:
            data = await provider.read(manager.photo_storage_key)
        except FileNotFoundError as exc:
            raise AppError(
                "SALES_MANAGER_PHOTO_NOT_FOUND", "Manager photo was not found.", 404
            ) from exc
        return Response(
            data,
            media_type=manager.photo_mime,
            headers={"Cache-Control": "public, max-age=300"},
        )
    url = await provider.create_download_url(manager.photo_storage_key, 900)
    return RedirectResponse(url=url, status_code=307)
