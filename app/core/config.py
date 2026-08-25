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
    ai_release_registry_path: Path = Path("configs/ai/models.yaml")
    ai_dataset_manifest_dir: Path = Path("ai_engine/data/manifests")
    ai_worker_poll_seconds: float = 2.0
    ai_worker_heartbeat_seconds: float = 30.0
    ai_config_path: Path = Path("configs/ai/opg_v1.yaml")
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_timeout_seconds: int = 20
    allow_production_mock_ai: bool = False
    whatsapp_service_url: str | None = None
    whatsapp_service_token: str | None = None
    whatsapp_service_timeout_seconds: int = 20
    whatsapp_session_dir: Path = Path("/app/data/whatsapp_sessions")
    whatsapp_followup_timezone: str = "Asia/Yerevan"
    whatsapp_reminder_lead_days: int = 7
    whatsapp_send_hour: int = 10
    whatsapp_worker_poll_seconds: float = 5.0
    whatsapp_connection_retry_seconds: int = 60
    whatsapp_claim_timeout_seconds: int = 300
    whatsapp_max_attempts: int = 5

    # Armenia Patient Radar operational runtime.
    radar_enabled: bool = True
    radar_worker_poll_seconds: float = 5.0
    radar_worker_concurrency: int = 8
    radar_worker_heartbeat_seconds: int = 30
    radar_claim_seconds: int = 180
    radar_http_timeout_seconds: int = 20
    radar_http_max_bytes: int = 2 * 1024 * 1024
    radar_max_items_per_poll: int = 300
    radar_user_agent: str = "DENTAI-Patient-Radar/1.0 (+read-only intelligence)"
    radar_llm_enabled: bool = True
    radar_llm_batch_size: int = 32
    radar_semantic_min_relevance: float = 0.45
    radar_collector_url: str | None = None
    radar_collector_token: str | None = None
    radar_collector_timeout_seconds: int = 30
    radar_session_encryption_key: str | None = None
    radar_signal_retention_days: int = 90
    radar_ignored_retention_days: int = 14
    radar_cleanup_interval_seconds: int = 3600
    radar_discovery_auto_promote_score: int = 82
    radar_source_quality_lookback_days: int = 30
    radar_meta_app_id: str | None = None
    radar_meta_app_secret: str | None = None
    radar_meta_redirect_uri: str | None = None
    radar_meta_api_version: str = "v23.0"
    radar_telegram_api_id: int | None = None
    radar_telegram_api_hash: str | None = None

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        return value.split(",") if isinstance(value, str) else value

    @staticmethod
    def _is_loopback_whatsapp_url(value: str | None) -> bool:
        url = (value or "").strip().lower()
        return (
            url.startswith("http://127.0.0.1:")
            or url.startswith("http://localhost:")
            or url.startswith("http://[::1]:")
        )

    @staticmethod
    def _is_loopback_radar_collector_url(value: str | None) -> bool:
        url = (value or "").strip().lower()
        return (
            url.startswith("http://127.0.0.1:")
            or url.startswith("http://localhost:")
            or url.startswith("http://[::1]:")
        )

    @staticmethod
    def _validate_fernet(value: str | None, *, name: str) -> None:
        if not value:
            raise RuntimeError(f"{name} is required in production")
        try:
            Fernet(value.encode())
        except (ValueError, TypeError) as exc:
            raise RuntimeError(f"{name} must be a valid Fernet key") from exc

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
            self._validate_fernet(self.tenant_dsn_encryption_key, name="TENANT_DSN_ENCRYPTION_KEY")
            if "*" in self.cors_allowed_origins:
                raise RuntimeError("Wildcard CORS is forbidden in production")
            if self.object_storage_provider != "s3":
                raise RuntimeError("Production requires private S3-compatible object storage")
            if not all((self.s3_bucket, self.s3_access_key, self.s3_secret_key)):
                raise RuntimeError("Production S3 configuration is incomplete")
            if self.ai_provider != "real_opg" and not self.allow_production_mock_ai:
                raise RuntimeError("Production requires AI_PROVIDER=real_opg")
            if (
                self.whatsapp_service_url
                and not self.whatsapp_service_token
                and not self._is_loopback_whatsapp_url(self.whatsapp_service_url)
            ):
                raise RuntimeError(
                    "WHATSAPP_SERVICE_TOKEN is required for a non-loopback WhatsApp service"
                )
            if self.radar_enabled:
                self._validate_fernet(
                    self.radar_session_encryption_key,
                    name="RADAR_SESSION_ENCRYPTION_KEY",
                )
            if (
                self.radar_collector_url
                and not self.radar_collector_token
                and not self._is_loopback_radar_collector_url(self.radar_collector_url)
            ):
                raise RuntimeError(
                    "RADAR_COLLECTOR_TOKEN is required for a non-loopback Radar collector"
                )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production()
    return settings
