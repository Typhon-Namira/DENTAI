import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.models import CareConversation, CareConversationMessage, CarePlanItem
from app.clinic_resolution.service import resolver
from app.database.control_models import AccessRequest, ClinicRegistry, PlatformVisit
from app.database.models import AIAnalysis, FollowUp, Patient, XRay
from app.platform.market_api import market_code

PUBLIC_PAGE_PATHS = (
    "/",
    "/product",
    "/how-it-works",
    "/pricing",
    "/clinical-safety",
    "/about",
    "/register",
    "/request-access",
    "/login",
)


def aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def clinic_category(clinic: ClinicRegistry) -> str:
    """Separate gifted access from paid revenue and Free from Premium.

    The plan is authoritative for FREE/PREMIUM. The source only distinguishes
    gifted Premium from revenue-backed Premium and provides legacy provenance.
    This also correctly classifies older Free->Premium upgrades whose source was
    historically left as FREE.
    """
    source = (clinic.subscription_source or "").upper()
    plan = (clinic.subscription_plan or "").upper()
    if source == "GIFT":
        return "GIFT"
    if plan in {"PREMIUM", "TETA2_CARE"}:
        return "PAID"
    if plan == "FREE":
        return "FREE"
    return "LEGACY"


def clinic_operational_state(clinic: ClinicRegistry) -> str:
    now = datetime.now(UTC)
    expiry = aware(clinic.subscription_expires_at)
    if not clinic.is_active:
        return "ARCHIVED"
    if clinic.subscription_state == "PAYMENT_REVIEW":
        return "PAYMENT_REVIEW"
    if expiry is not None and expiry <= now:
        return "EXPIRED"
    return clinic.subscription_state or "ACTIVE"


async def count_rows(session: AsyncSession, model, *where) -> int:
    statement = select(func.count()).select_from(model)
    if where:
        statement = statement.where(*where)
    return int(await session.scalar(statement) or 0)


async def tenant_stats(control: AsyncSession, clinic: ClinicRegistry) -> dict:
    empty = {
        "patients": 0,
        "opgs": 0,
        "ai_analyses": 0,
        "followups_total": 0,
        "followups_completed": 0,
        "followups_pending": 0,
        "care_items_total": 0,
        "care_items_completed": 0,
        "care_items_pending": 0,
        "ai_conversations": 0,
        "conversation_messages": 0,
        "database_status": "UNAVAILABLE",
    }
    try:
        resolved = await resolver.by_id(control, clinic.id)
        factory = resolver.session_factory(resolved)
        async with factory() as tenant:
            patients = await count_rows(tenant, Patient)
            opgs = await count_rows(tenant, XRay)
            ai_analyses = await count_rows(tenant, AIAnalysis)
            followups_total = await count_rows(tenant, FollowUp)
            followups_completed = await count_rows(
                tenant,
                FollowUp,
                or_(
                    FollowUp.completed_at.is_not(None),
                    func.upper(FollowUp.status).in_(["COMPLETED", "DONE", "TREATED"]),
                ),
            )
            care_items_total = await count_rows(tenant, CarePlanItem)
            care_items_completed = await count_rows(
                tenant,
                CarePlanItem,
                or_(
                    CarePlanItem.outcome_at.is_not(None),
                    func.upper(CarePlanItem.status).in_(["COMPLETED", "DONE", "TREATED"]),
                ),
            )
            conversations = await count_rows(tenant, CareConversation)
            messages = await count_rows(tenant, CareConversationMessage)
        return {
            "patients": patients,
            "opgs": opgs,
            "ai_analyses": ai_analyses,
            "followups_total": followups_total,
            "followups_completed": followups_completed,
            "followups_pending": max(0, followups_total - followups_completed),
            "care_items_total": care_items_total,
            "care_items_completed": care_items_completed,
            "care_items_pending": max(0, care_items_total - care_items_completed),
            "ai_conversations": conversations,
            "conversation_messages": messages,
            "database_status": "ONLINE",
        }
    except Exception:
        # Analytics must degrade per tenant instead of making the entire internal
        # control center unavailable because one clinic database is offline.
        return empty


def serialize_clinic(clinic: ClinicRegistry, stats: dict) -> dict:
    expiry = aware(clinic.subscription_expires_at)
    now = datetime.now(UTC)
    days_remaining = max(0, (expiry - now).days) if expiry is not None else None
    return {
        "id": str(clinic.id),
        "slug": clinic.slug,
        "name": clinic.name,
        "registry_active": clinic.is_active,
        "subscription_plan": clinic.subscription_plan or "LEGACY",
        "subscription_state": clinic.subscription_state or "ACTIVE",
        "subscription_source": clinic.subscription_source or "LEGACY",
        "category": clinic_category(clinic),
        "operational_state": clinic_operational_state(clinic),
        "subscription_starts_at": clinic.subscription_starts_at,
        "subscription_expires_at": expiry,
        "days_remaining": days_remaining,
        "free_trial_started_at": clinic.free_trial_started_at,
        "upgrade_requested_at": clinic.upgrade_requested_at,
        "gift_granted_at": clinic.gift_granted_at,
        "gift_note": clinic.gift_note,
        "created_at": clinic.created_at,
        "updated_at": clinic.updated_at,
        "stats": stats,
    }


async def traffic_payload(session: AsyncSession) -> dict:
    now = datetime.now(UTC)
    day = now - timedelta(hours=24)
    month = now - timedelta(days=30)

    async def grouped_count(since: datetime | None = None) -> dict[str, int]:
        statement = (
            select(PlatformVisit.path, func.count())
            .where(PlatformVisit.path.in_(PUBLIC_PAGE_PATHS))
            .group_by(PlatformVisit.path)
        )
        if since is not None:
            statement = statement.where(PlatformVisit.created_at >= since)
        return {str(path): int(value) for path, value in (await session.execute(statement)).all()}

    totals = await grouped_count()
    last_24h = await grouped_count(day)
    last_30d = await grouped_count(month)
    unique_30d = {
        str(path): int(value)
        for path, value in (
            await session.execute(
                select(
                    PlatformVisit.path,
                    func.count(func.distinct(PlatformVisit.visitor_hash)),
                )
                .where(
                    PlatformVisit.path.in_(PUBLIC_PAGE_PATHS),
                    PlatformVisit.created_at >= month,
                )
                .group_by(PlatformVisit.path)
            )
        ).all()
    }
    pages = [
        {
            "path": path,
            "visits_total": totals.get(path, 0),
            "visits_24h": last_24h.get(path, 0),
            "visits_30d": last_30d.get(path, 0),
            "unique_30d": unique_30d.get(path, 0),
        }
        for path in PUBLIC_PAGE_PATHS
    ]
    return {
        "pages": pages,
        "totals": {
            "visits_total": sum(item["visits_total"] for item in pages),
            "visits_24h": sum(item["visits_24h"] for item in pages),
            "visits_30d": sum(item["visits_30d"] for item in pages),
        },
    }


async def payment_payload(
    session: AsyncSession, clinics_by_id: dict[uuid.UUID, ClinicRegistry]
) -> dict:
    rows = list(
        (
            await session.scalars(
                select(AccessRequest)
                .where(AccessRequest.payment_verified_at.is_not(None))
                .order_by(AccessRequest.payment_verified_at.desc())
            )
        ).all()
    )
    payments = []
    revenue: dict[str, int] = defaultdict(int)
    accounted = 0
    for row in rows:
        clinic = clinics_by_id.get(row.activated_clinic_id) if row.activated_clinic_id else None
        if clinic is not None and clinic_category(clinic) == "GIFT":
            continue
        amount = row.payment_amount
        currency = row.payment_currency
        is_accounted = amount is not None and bool(currency)
        if is_accounted:
            revenue[str(currency)] += int(amount or 0)
            accounted += 1
        payments.append(
            {
                "id": str(row.id),
                "clinic_id": str(row.activated_clinic_id) if row.activated_clinic_id else None,
                "clinic_name": clinic.name if clinic else row.clinic_name,
                "market": market_code(row.country, row.city, row.address),
                "amount": amount,
                "currency": currency,
                "accounted": is_accounted,
                "reference": row.payment_reference,
                "proof_note": row.payment_proof_note,
                "verified_at": row.payment_verified_at,
                "created_at": row.created_at,
            }
        )
    return {
        "items": payments,
        "verified_count": len(payments),
        "accounted_count": accounted,
        "unpriced_legacy_count": len(payments) - accounted,
        "revenue_by_currency": dict(revenue),
    }


def aggregate_clinic_stats(clinic_rows: list[dict]) -> tuple[Counter, Counter, dict[str, int]]:
    categories = Counter(row["category"] for row in clinic_rows)
    states = Counter(row["operational_state"] for row in clinic_rows)
    totals: dict[str, int] = defaultdict(int)
    for row in clinic_rows:
        for key, value in row["stats"].items():
            if isinstance(value, int):
                totals[key] += value
    return categories, states, dict(totals)
