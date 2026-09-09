"""The standalone service's sole typed environment boundary."""

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VOICEUP_INFERENCE_", extra="ignore", hide_input_in_errors=True
    )

    internal_key: SecretStr
    model_dir: Path = Path("/models/speaker")
    device: str = Field(default="cuda:0", pattern=r"^cuda:[0-9]+$")
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, gt=0, le=50 * 1024 * 1024)
    max_duration_seconds: float = Field(default=120, gt=0, le=120, allow_inf_nan=False)
    host: str = "0.0.0.0"
    port: int = Field(default=8090, ge=1024, le=65535)

    @field_validator("internal_key")
    @classmethod
    def validate_internal_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("internal_key must contain at least 32 bytes")
        return value


def load_settings() -> Settings:
    return Settings()
