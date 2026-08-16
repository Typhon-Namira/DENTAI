from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    app_secret: str = "development-only-secret-change-me"
    access_token_secret: str = "development-access-secret-change-me"
    refresh_token_secret: str = "development-refresh-secret-change-me"
    control_database_url: str = "sqlite+aiosqlite:///./control.db"
    tenant_dsn_encryption_key: str | None = None
    object_storage_provider: str = "local"
    local_storage_path: Path = Path("storage")
    s3_endpoint: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"
    max_xray_bytes: int = 15 * 1024 * 1024
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    database_pool_size: int = 5
    database_max_overflow: int = 5
    database_pool_timeout_seconds: int = 10
    max_tenant_engines: int = 100
    s3_connect_timeout_seconds: int = 5
    s3_read_timeout_seconds: int = 30
    ai_provider: str = "mock"
    ai_model_artifact_path: Path = Path("model_artifacts/dentai_v5")
    ai_model_manifest_path: Path = Path("artifacts/production/dentai_v5_model_manifest.json")
    ai_worker_poll_seconds: float = 2.0
    ai_worker_heartbeat_seconds: float = 30.0
    ai_config_path: Path = Path("configs/ai/opg_v1.yaml")
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_timeout_seconds: int = 20
    allow_production_mock_ai: bool = False

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        return value.split(",") if isinstance(value, str) else value

    def validate_production(self) -> None:
        if self.app_env == "production":
            secrets = (
                self.app_secret,
                self.access_token_secret,
                self.refresh_token_secret,
            )
            if any(
                "change-me" in value or "development" in value or len(value) < 32
                for value in secrets
            ):
                raise RuntimeError("Production secrets must be unique and at least 32 characters")
            if len(set(secrets)) != len(secrets):
                raise RuntimeError("Production secrets must be unique")
            if not self.tenant_dsn_encryption_key:
                raise RuntimeError("TENANT_DSN_ENCRYPTION_KEY is required in production")
            try:
                Fernet(self.tenant_dsn_encryption_key.encode())
            except (ValueError, TypeError) as exc:
                raise RuntimeError("TENANT_DSN_ENCRYPTION_KEY must be a valid Fernet key") from exc
            if "*" in self.cors_allowed_origins:
                raise RuntimeError("Wildcard CORS is forbidden in production")
            if self.object_storage_provider != "s3":
                raise RuntimeError("Production requires private S3-compatible object storage")
            if not all((self.s3_bucket, self.s3_access_key, self.s3_secret_key)):
                raise RuntimeError("Production S3 configuration is incomplete")
            if self.ai_provider != "real_opg" and not self.allow_production_mock_ai:
                raise RuntimeError("Production requires AI_PROVIDER=real_opg")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings
