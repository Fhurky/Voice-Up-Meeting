"""Typed application settings; this is the only application environment boundary."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_DATABASE_ROOT = "postgresql+asyncpg://postgres:postgres@localhost:5432/"
_DEVELOPMENT_JWT_SECRET = "development-only-change-me-at-least-32-bytes"


class MigrationSettings(BaseSettings):
    """Least-privilege configuration for the schema migration process."""

    model_config = SettingsConfigDict(
        env_prefix="@@ENV_PREFIX@@",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = f"{_DEFAULT_DATABASE_ROOT}@@PRODUCT_SLUG@@"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("database_url must use the postgresql+asyncpg driver")
        return value


class Settings(BaseSettings):
    """Configuration loaded from prefixed environment variables and an optional .env."""

    model_config = SettingsConfigDict(
        env_prefix="@@ENV_PREFIX@@",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    project_name: str = "@@PRODUCT_SLUG@@"

    api_prefix: str = "@@API_PREFIX@@"
    tenant_header: str = "@@TENANT_HEADER@@"
    cors_allow_origins: str = "http://localhost:3000,http://localhost:8080"

    database_url: str = f"{_DEFAULT_DATABASE_ROOT}@@PRODUCT_SLUG@@"

    # Required in every process. Local Compose supplies an explicit development value; a missing
    # key in a pre-created deployment Secret therefore stops startup instead of enabling a known
    # signing key.
    jwt_secret: SecretStr
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "@@PRODUCT_SLUG@@"
    jwt_audience: str = "@@PRODUCT_SLUG@@-api"
    access_token_expire_minutes: int = 60

    bootstrap_super_admin_email: str = "admin@example.invalid"
    bootstrap_super_admin_username: str = "super-admin"
    bootstrap_super_admin_password: SecretStr | None = None

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
