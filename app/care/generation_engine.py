from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.care.language import language_for_phone
from app.care.models import CarePlan, CarePlanItem
from app.care.service import settings_for_branch
from app.database.models import AIAnalysis, DentalFinding, FindingReview, Patient
from app.outreach.service import timing_for_finding

# This ontology intentionally matches frontend-test/src/utils/findingVisuals.ts.
# Confidence is NOT an eligibility gate for a clinician-controlled plan. It is
# an advisory signal used for review prompts and priority ranking only.
RESTORATIVE_FINDINGS = {
    "FILLING",
    "CROWN",
    "RESTORATION",
    "RESTORED",
    "IMPLANT",
    "BRIDGE",
    "ROOT_CANAL_TREATMENT",
    "ROOT_CANAL_FILLING",
    "ENDODONTIC_TREATMENT",
}
REVIEW_RECOMMENDED_BELOW = 0.60

_PRIORITY_BASE: dict[str, tuple[str, float]] = {
    "BONE_RESORPTION": ("URGENT", 100.0),
    "FURCATION_LESION": ("URGENT", 98.0),
    "DEEP_CARIES": ("HIGH", 92.0),
    "APICAL_PERIODONTITIS": ("HIGH", 90.0),
    "ROOT_FRAGMENT": ("HIGH", 88.0),
    "RESIDUAL_ROOT": ("HIGH", 86.0),
    "CARIES": ("HIGH", 82.0),
    "IMPACTED": ("MEDIUM", 62.0),
}


@dataclass(frozen=True)
class ToothCandidate:
    tooth_fdi: str
    primary: DentalFinding
    findings: tuple[DentalFinding, ...]
    priority_level: str
    priority_score: float


def valid_permanent_fdi(tooth_code: str | None) -> bool:
    return bool(
        tooth_code
        and len(tooth_code) == 2
        and tooth_code[0] in "1234"
        and tooth_code[1] in "12345678"
    )


def is_pathological_finding(finding: DentalFinding) -> bool:
    """Return whether an AI finding can enter a clinician-controlled tooth plan.

    This deliberately does not reject a finding because its confidence is below
    0.60. The OPG viewer already renders those findings as pathological (red),
    and the dentist must be able to generate a draft plan before reviewing it.
    Rejected findings, restorative-only observations, and unresolved tooth IDs
    remain excluded.
    """

    return bool(
        valid_permanent_fdi(finding.tooth_code)
        and finding.finding_type.strip().upper() not in RESTORATIVE_FINDINGS
        and finding.review_status != FindingReview.REJECTED
    )


def review_recommended(finding: DentalFinding) -> bool:
    confidence = finding.confidence
    return bool(
        finding.review_status != FindingReview.CONFIRMED
        or confidence is None
        or confidence < REVIEW_RECOMMENDED_BELOW
    )


def _priority(finding: DentalFinding) -> tuple[str, float]:
    level, base = _PRIORITY_BASE.get(finding.finding_type.upper(), ("ROUTINE", 45.0))
    confidence = max(0.0, min(1.0, float(finding.confidence or 0.0)))
    review_bonus = 2.0 if finding.review_status == FindingReview.CONFIRMED else 0.0
    return level, base + confidence * 8.0 + review_bonus


def group_pathological_teeth(findings: list[DentalFinding]) -> list[ToothCandidate]:
    grouped: dict[str, list[DentalFinding]] = defaultdict(list)
    for finding in findings:
        if is_pathological_finding(finding) and finding.tooth_code:
            grouped[finding.tooth_code].append(finding)

    candidates: list[ToothCandidate] = []
    for tooth_fdi, rows in grouped.items():
        ranked = sorted(rows, key=lambda row: _priority(row)[1], reverse=True)
        primary = ranked[0]
        level, score = _priority(primary)
        candidates.append(
            ToothCandidate(
                tooth_fdi=tooth_fdi,
                primary=primary,
                findings=tuple(ranked),
                priority_level=level,
                priority_score=score,
            )
        )
    return sorted(candidates, key=lambda row: row.priority_score, reverse=True)


def _next_local_contact(timezone_name: str) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_now = datetime.now(UTC).astimezone(zone)
    target_date = local_now.date() + timedelta(days=1)
    return datetime.combine(target_date, time(16, 0), tzinfo=zone).astimezone(UTC)


def _finding_labels(candidate: ToothCandidate) -> str:
    labels = list(
        dict.fromkeys(row.finding_type.replace("_", " ").lower() for row in candidate.findings)
    )
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" and {labels[-1]}"


def _message(language: str, patient_name: str, candidate: ToothCandidate) -> str:
    tooth = candidate.tooth_fdi
    label = _finding_labels(candidate)
    if language == "hy":
        return (
            f"Բարև {patient_name}։ Ձեր OPG-ում {tooth} ատամի շրջանում AI-ն նշել է հնարավոր "
            f"{label}։ Կլինիկայի ատամնաբույժը խորհուրդ է տալիս այս ատամը ստուգել։"
        )
    if language == "ru":
        return (
            f"Здравствуйте, {patient_name}. На OPG в области зуба {tooth} AI отметил возможную "
            f"находку: {label}. Стоматолог клиники рекомендует проверить этот зуб."
        )
    if language == "fa":
        return (
            f"سلام {patient_name}. در OPG شما در ناحیه دندان {tooth} یک یافته احتمالی "
            f"({label}) توسط AI مشخص شده است. دندان‌پزشک کلینیک توصیه می‌کند این دندان بررسی شود."
        )
    if language == "tr":
        return (
            f"Merhaba {patient_name}. OPG görüntünüzde {tooth} numaralı diş bölgesinde AI olası "
            f"bir {label} bulgusu işaretledi. Klinik diş hekiminiz bu dişin kontrolünü öneriyor."
        )
    return (
        f"Hello {patient_name}. On your OPG, AI marked a possible {label} finding around tooth "
        f"{tooth}. Your clinic dentist recommends checking this tooth."
    )


async def generation_readiness(session: AsyncSession, analysis: AIAnalysis) -> dict:
    findings = (
        await session.scalars(
            select(DentalFinding)
            .where(DentalFinding.analysis_id == analysis.id)
            .order_by(DentalFinding.created_at.asc())
        )
    ).all()
    candidates = group_pathological_teeth(list(findings))
    payload = []
    for candidate in candidates:
        primary = candidate.primary
        payload.append(
            {
                "finding_id": str(primary.id),
                "tooth_fdi": candidate.tooth_fdi,
                "finding_type": primary.finding_type,
                "finding_types": [row.finding_type for row in candidate.findings],
                "confidence": primary.confidence,
                "review_status": str(primary.review_status),
                "review_recommended": any(review_recommended(row) for row in candidate.findings),
                "priority_level": candidate.priority_level,
                "priority_score": candidate.priority_score,
            }
        )
    confirmed_count = sum(
        1
        for candidate in candidates
        if all(row.review_status == FindingReview.CONFIRMED for row in candidate.findings)
    )
    review_recommended_count = sum(
        1 for candidate in candidates if any(review_recommended(row) for row in candidate.findings)
    )
    return {
        "analysis_id": str(analysis.id),
        "ready": bool(candidates),
        "candidate_count": len(candidates),
        "confirmed_count": confirmed_count,
        "review_recommended_count": review_recommended_count,
        "candidates": payload,
    }


async def build_followup_plan(session: AsyncSession, analysis: AIAnalysis) -> CarePlan | None:
    patient = await session.get(Patient, analysis.patient_id)
    if not patient:
        return None

    findings = (
        await session.scalars(select(DentalFinding).where(DentalFinding.analysis_id == analysis.id))
    ).all()
    candidates = group_pathological_teeth(list(findings))
    if not candidates:
        return None

    existing = await session.scalar(select(CarePlan).where(CarePlan.analysis_id == analysis.id))
    if existing and existing.status in {"ACTIVE", "PAUSED", "COMPLETED"}:
        return existing

    settings = await settings_for_branch(session, patient.branch_id)
    language = language_for_phone(
        patient.whatsapp_phone or patient.phone,
        settings.default_language,
    )
    patient_name = f"{patient.first_name} {patient.last_name}".strip()
    plan = existing
    if plan is None:
        plan = CarePlan(
            patient_id=patient.id,
            analysis_id=analysis.id,
            branch_id=patient.branch_id,
            doctor_id=analysis.requested_by,
            status="PENDING_APPROVAL",
            language=language,
        )
        session.add(plan)
        await session.flush()
    else:
        plan.status = "PENDING_APPROVAL"
        plan.language = language

    existing_items = (
        await session.scalars(select(CarePlanItem).where(CarePlanItem.care_plan_id == plan.id))
    ).all()
    by_finding = {existing_item.finding_id: existing_item for existing_item in existing_items}
    selected_ids = {candidate.primary.id for candidate in candidates}
    now = datetime.now(UTC)

    for existing_item in existing_items:
        if existing_item.finding_id not in selected_ids:
            existing_item.status = "REJECTED"
            existing_item.outcome = "NOT_SELECTED_FOR_TOOTH_PLAN"
            existing_item.outcome_at = now

    first_start = _next_local_contact(settings.timezone)
    review_count = 0
    for order, candidate in enumerate(candidates, start=1):
        primary = candidate.primary
        timing = timing_for_finding(analysis, primary)
        plan_item = by_finding.get(primary.id)
        if plan_item is None:
            plan_item = CarePlanItem(
                care_plan_id=plan.id,
                finding_id=primary.id,
                tooth_fdi=candidate.tooth_fdi,
                finding_type=primary.finding_type,
                confidence=primary.confidence,
                recommended_window=timing.recommended_window,
                target_followup_at=timing.target_followup_at,
                rationale=timing.timing_reason,
                message_preview=_message(language, patient_name, candidate),
                appointment_required=True,
                image_required=True,
            )
            session.add(plan_item)
        else:
            plan_item.tooth_fdi = candidate.tooth_fdi
            plan_item.finding_type = primary.finding_type
            plan_item.confidence = primary.confidence
            if not plan_item.recommended_window:
                plan_item.recommended_window = timing.recommended_window
            if not plan_item.rationale:
                plan_item.rationale = timing.timing_reason
            if not plan_item.message_preview:
                plan_item.message_preview = _message(language, patient_name, candidate)

        plan_item.sequence_order = order
        plan_item.priority_level = candidate.priority_level
        plan_item.priority_score = candidate.priority_score
        plan_item.outcome = None
        plan_item.outcome_at = None
        if order == 1:
            plan_item.status = "FOLLOWUP_READY"
            if not plan_item.conversation_start_at or plan_item.conversation_start_at <= now:
                plan_item.conversation_start_at = first_start
        else:
            plan_item.status = "WAITING_PREVIOUS_TOOTH"
            plan_item.conversation_start_at = None
        if all(row.review_status == FindingReview.CONFIRMED for row in candidate.findings):
            review_count += 1

    review_recommended_count = len(candidates) - review_count
    plan.summary = (
        f"Sequential follow-up for {len(candidates)} pathological tooth"
        f"{'s' if len(candidates) != 1 else ''}. "
        f"{review_count} fully reviewed; {review_recommended_count} still recommended for clinician review. "
        "Review is recommended but is not required to generate the draft plan."
    )
    await session.flush()
    return plan
