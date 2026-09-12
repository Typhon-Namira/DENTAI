import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.api.v1.auth import change_password, me
from app.auth.schemas import PasswordChangeRequest
from app.auth.security import hash_password, verify_password
from app.core.errors import AppError
from app.database.models import Role


class RecordingSession:
    def __init__(self):
        self.added = []
        self.executed = []
        self.committed = False

    async def execute(self, statement):
        self.executed.append(statement)

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True


def context(*, password: str = "current-password-value", expires_at=None):
    user = SimpleNamespace(
        id=uuid.uuid4(),
        username="director",
        email="director@example.com",
        role=Role.DIRECTOR,
        password_hash=hash_password(password),
        token_version=1,
    )
    clinic = SimpleNamespace(
        id=uuid.uuid4(),
        subscription_plan="TETA2_CARE",
        subscription_starts_at=datetime.now(UTC) - timedelta(hours=1),
        subscription_expires_at=expires_at,
    )
    return SimpleNamespace(
        user=user,
        clinic=clinic,
        branch_ids={uuid.uuid4()},
        session=RecordingSession(),
    )


@pytest.mark.asyncio
async def test_me_returns_subscription_countdown():
    ctx = context(expires_at=datetime.now(UTC) + timedelta(days=29, hours=23))

    response = await me(ctx)

    assert response.subscription_plan == "TETA2_CARE"
    assert response.subscription_days_remaining == 30
    assert response.subscription_expires_at == ctx.clinic.subscription_expires_at


@pytest.mark.asyncio
async def test_password_change_hashes_password_revokes_sessions_and_audits():
    ctx = context()

    await change_password(
        PasswordChangeRequest(
            current_password="current-password-value",
            new_password="new-password-value-123",
        ),
        ctx,
    )

    assert verify_password("new-password-value-123", ctx.user.password_hash)
    assert not verify_password("current-password-value", ctx.user.password_hash)
    assert ctx.user.token_version == 2
    assert len(ctx.session.executed) == 1
    assert ctx.session.committed is True
    assert ctx.session.added[0].action == "PASSWORD_CHANGED"
    assert ctx.session.added[0].audit_metadata == {"sessions_revoked": True}


@pytest.mark.asyncio
async def test_password_change_rejects_wrong_current_password_without_writes():
    ctx = context()

    with pytest.raises(AppError) as error:
        await change_password(
            PasswordChangeRequest(
                current_password="incorrect-password",
                new_password="new-password-value-123",
            ),
            ctx,
        )

    assert error.value.code == "CURRENT_PASSWORD_INVALID"
    assert ctx.user.token_version == 1
    assert ctx.session.executed == []
    assert ctx.session.added == []
    assert ctx.session.committed is False
