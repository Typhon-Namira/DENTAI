import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.control_models import SalesManager
from app.platform.sales_manager_service import (
    SCORE_CLINIC_POINTS,
    SCORE_GROWTH_POINTS,
    SCORE_REPORT_POINTS,
    SCORE_TARGET_CLINICS,
    SCORE_TARGET_GROWTH,
    SCORE_TARGET_REPORTS,
    add_score_event,
    sales_score_summary,
)


def manager(email: str) -> SalesManager:
    now = datetime.now(UTC)
    return SalesManager(
        id=uuid.uuid4(),
        username=email.split("@")[0],
        email=email,
        password_hash="hash",
        first_name="Sales",
        last_name="Manager",
        title="Sales Manager",
        is_active=True,
        is_public=False,
        must_change_password=False,
        token_version=1,
        created_at=now,
        updated_at=now,
    )


async def add_category_points(
    session,
    *,
    manager_id: uuid.UUID,
    category: str,
    unit_points: int,
    count: int,
    source_prefix: str,
) -> None:
    for index in range(count):
        await add_score_event(
            session,
            manager_id=manager_id,
            category=category,
            points=unit_points,
            source_type=source_prefix,
            source_id=f"{manager_id}:{index}",
            description=f"{category} event {index}",
        )


@pytest.mark.asyncio
async def test_score_categories_are_capped_and_first_1000_manager_wins_once():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        first = manager("first@example.com")
        second = manager("second@example.com")
        session.add_all([first, second])
        await session.flush()

        for row in (first, second):
            await add_category_points(
                session,
                manager_id=row.id,
                category="REPORTS",
                unit_points=SCORE_REPORT_POINTS,
                count=SCORE_TARGET_REPORTS // SCORE_REPORT_POINTS,
                source_prefix="TEST_REPORT",
            )
            await add_category_points(
                session,
                manager_id=row.id,
                category="CLINICS",
                unit_points=SCORE_CLINIC_POINTS,
                count=SCORE_TARGET_CLINICS // SCORE_CLINIC_POINTS,
                source_prefix="TEST_CLINIC",
            )
            await add_category_points(
                session,
                manager_id=row.id,
                category="GROWTH",
                unit_points=SCORE_GROWTH_POINTS,
                count=SCORE_TARGET_GROWTH // SCORE_GROWTH_POINTS,
                source_prefix="TEST_GROWTH",
            )

        first_score = await sales_score_summary(session, first.id)
        second_score = await sales_score_summary(session, second.id)

        assert first_score["total"] == 1000
        assert first_score["all_complete"] is True
        assert first_score["categories"]["reports"]["points"] == SCORE_TARGET_REPORTS
        assert first_score["categories"]["clinics"]["points"] == SCORE_TARGET_CLINICS
        assert first_score["categories"]["growth"]["points"] == SCORE_TARGET_GROWTH
        assert first_score["award"]["is_winner"] is True

        assert second_score["total"] == 1000
        assert second_score["all_complete"] is True
        assert second_score["award"]["is_winner"] is False
        assert second_score["award"]["manager_id"] == str(first.id)

        await add_score_event(
            session,
            manager_id=first.id,
            category="REPORTS",
            points=SCORE_REPORT_POINTS,
            source_type="TEST_EXTRA_REPORT",
            source_id=str(uuid.uuid4()),
            description="Extra report after category completion",
        )
        capped = await sales_score_summary(session, first.id)
        assert capped["categories"]["reports"]["raw_points"] > SCORE_TARGET_REPORTS
        assert capped["categories"]["reports"]["points"] == SCORE_TARGET_REPORTS
        assert capped["total"] == 1000

    await engine.dispose()
