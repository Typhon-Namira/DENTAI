import pytest

from app.core.config import get_settings
from app.core.errors import AppError
from app.platform.service import _tenant_url_for_slug, tenant_auto_provisioning_configured


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_tenant_url_is_derived_from_postgresql_control_database(monkeypatch):
    monkeypatch.setenv(
        "CONTROL_DATABASE_URL",
        "postgresql+asyncpg://app:p%40ss@db.example:5432/control?ssl=require",
    )
    monkeypatch.delenv("TENANT_DATABASE_URL_TEMPLATE", raising=False)

    assert _tenant_url_for_slug("Bright-Smile") == (
        "postgresql+asyncpg://app:p%40ss@db.example:5432/teta2_bright_smile?ssl=require"
    )
    assert tenant_auto_provisioning_configured() is True


def test_explicit_tenant_template_takes_precedence(monkeypatch):
    monkeypatch.setenv("CONTROL_DATABASE_URL", "postgresql+asyncpg://app:pw@control/db")
    monkeypatch.setenv(
        "TENANT_DATABASE_URL_TEMPLATE",
        "postgresql+asyncpg://tenant:pw@tenant-host/{database}",
    )

    assert _tenant_url_for_slug("My Clinic") == (
        "postgresql+asyncpg://tenant:pw@tenant-host/teta2_my_clinic"
    )


def test_non_postgresql_control_database_still_requires_template(monkeypatch):
    monkeypatch.setenv("CONTROL_DATABASE_URL", "sqlite+aiosqlite:///./control.db")
    monkeypatch.delenv("TENANT_DATABASE_URL_TEMPLATE", raising=False)

    with pytest.raises(AppError) as error:
        _tenant_url_for_slug("My Clinic")

    assert error.value.code == "TENANT_DATABASE_TEMPLATE_REQUIRED"
    assert tenant_auto_provisioning_configured() is False
