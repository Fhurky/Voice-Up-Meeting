"""Typed application settings; this is the only application environment boundary."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_DATABASE_ROOT = "postgresql+asyncpg://postgres:postgres@localhost:5432/"
_DEVELOPMENT_JWT_SECRET = "development-only-change-me-at-least-32-bytes"


class MigrationSettings(BaseSettings):
    """Least-privilege configuration for the schema migration process."""

    model_config = SettingsConfigDict(
        env_prefix="VOICEUP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: str = f"{_DEFAULT_DATABASE_ROOT}voiceup"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use the postgresql+asyncpg driver")
        return value


class Settings(BaseSettings):
    """Configuration loaded from prefixed environment variables and an optional .env."""

    model_config = SettingsConfigDict(
        env_prefix="VOICEUP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    project_name: str = "voiceup"

    api_prefix: str = "/api/voiceup/v1"
    tenant_header: str = "x-tenant-id"
    cors_allow_origins: str = "http://localhost:3000,http://localhost:8080"

    database_url: str = f"{_DEFAULT_DATABASE_ROOT}voiceup"

    # Required in every process. Local Compose supplies an explicit development value; a missing
    # key in a pre-created deployment Secret therefore stops startup instead of enabling a known
    # signing key.
    jwt_secret: SecretStr
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "voiceup"
    jwt_audience: str = "voiceup-api"
    access_token_expire_minutes: int = 60
    local_admin_login_enabled: bool = False
    local_admin_username: str = Field(default="", max_length=120)

    bootstrap_super_admin_email: str = "admin@example.invalid"
    bootstrap_super_admin_username: str = "super-admin"
    bootstrap_super_admin_password: SecretStr | None = None

    audio_storage_path: Path = Path("/data/audio")
    audio_max_bytes: int = Field(default=52428800, ge=1024, le=52428800)
    audio_max_seconds: int = Field(default=120, ge=1, le=120)
    audio_retention_hours: int = Field(default=24, ge=1, le=24)
    job_retention_days: int = Field(default=7, ge=7, le=7)
    inference_url: str = "http://inference:8090"
    inference_key: SecretStr | None = None
    job_timeout_seconds: int = Field(default=300, ge=1, le=300)
    worker_poll_seconds: float = Field(default=2.0, ge=0.1, le=30.0)
    cleanup_interval_seconds: int = Field(default=3600, ge=60, le=3600)
    speaker_match_threshold: float = Field(default=0.55, ge=-1.0, le=1.0)
    speaker_new_threshold: float = Field(default=0.45, ge=-1.0, le=1.0)
    speaker_match_margin: float = Field(default=0.10, ge=0.0, le=2.0)

    @field_validator("inference_key")
    @classmethod
    def validate_inference_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("inference_key must contain at least 32 bytes")
        return value

    @field_validator("local_admin_username")
    @classmethod
    def normalize_local_admin_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("inference_url")
    @classmethod
    def validate_inference_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("inference_url must be an HTTP service origin without credentials")
        if parsed.path not in {"", "/"}:
            raise ValueError("inference_url must not contain a path")
        return value.rstrip("/")

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/"):
            raise ValueError("api_prefix must begin with '/'")
        return normalized

    @field_validator("tenant_header")
    @classmethod
    def validate_tenant_header(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized or "_" in normalized:
            raise ValueError("tenant_header must be a non-empty HTTP header name using hyphens")
        return normalized

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use the postgresql+asyncpg driver")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("jwt_secret must contain at least 32 bytes")
        return value

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_access_token_expiry(cls, value: int) -> int:
        if not 1 <= value <= 1440:
            raise ValueError("access_token_expire_minutes must be between 1 and 1440")
        return value

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def reject_development_secret_in_deployed_environments(self) -> "Settings":
        if self.local_admin_login_enabled and self.environment != "development":
            raise ValueError("local_admin_login_enabled requires the development environment")
        if self.speaker_new_threshold >= self.speaker_match_threshold:
            raise ValueError("speaker_new_threshold must be below speaker_match_threshold")
        if (
            self.environment in {"staging", "production"}
            and self.jwt_secret.get_secret_value() == _DEVELOPMENT_JWT_SECRET
        ):
            raise ValueError("a deployment-specific JWT secret is required")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings view."""

    # BaseSettings resolves the required secret from its configured environment source at runtime;
    # static type checkers cannot model that source injection.
    return Settings()  # type: ignore[call-arg]


@lru_cache
def get_migration_settings() -> MigrationSettings:
    """Return the DB-only settings view used by Alembic jobs."""

    return MigrationSettings()
