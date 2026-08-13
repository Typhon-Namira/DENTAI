import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AIAnalysis, AIStatus


async def claim_next_analysis(
    session: AsyncSession,
    worker_id: str,
    *,
    stale_after: timedelta = timedelta(minutes=10),
) -> AIAnalysis | None:
    """Atomically claim one eligible job; PostgreSQL workers skip locked rows."""
    now = datetime.now(UTC)
    stale = now - stale_after
    query = (
        select(AIAnalysis)
        .where(
            AIAnalysis.attempt_count < AIAnalysis.max_attempts,
            or_(
                AIAnalysis.status == AIStatus.QUEUED,
                (AIAnalysis.status == AIStatus.PROCESSING) & (AIAnalysis.heartbeat_at < stale),
            ),
            or_(AIAnalysis.retry_at.is_(None), AIAnalysis.retry_at <= now),
        )
        .order_by(AIAnalysis.requested_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = await session.scalar(query)
    if job is None:
        return None
    job.status = AIStatus.PROCESSING
    job.worker_id = worker_id
    job.claimed_at = now
    job.heartbeat_at = now
    job.processing_started_at = job.processing_started_at or now
    job.attempt_count += 1
    await session.commit()
    return job


async def heartbeat(session: AsyncSession, analysis_id: uuid.UUID, worker_id: str) -> bool:
    job = await session.get(AIAnalysis, analysis_id)
    if job is None or job.worker_id != worker_id or job.status != AIStatus.PROCESSING:
        return False
    job.heartbeat_at = datetime.now(UTC)
    await session.commit()
    return True


async def schedule_retry(session: AsyncSession, job: AIAnalysis, error_code: str) -> None:
    now = datetime.now(UTC)
    job.error_code = error_code[:100]
    job.worker_id = None
    job.heartbeat_at = None
    if job.attempt_count >= job.max_attempts:
        job.status = AIStatus.FAILED
        job.failed_at = now
        job.retry_at = None
    else:
        job.status = AIStatus.QUEUED
        job.retry_at = now + timedelta(seconds=min(300, 2**job.attempt_count * 5))
    await session.commit()
