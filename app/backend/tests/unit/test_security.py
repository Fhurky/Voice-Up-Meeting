"""Password and JWT contract tests."""

from uuid import uuid4

import pytest
from jwt import InvalidTokenError
from pydantic import ValidationError

from app.core.config import MigrationSettings, Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_missing_jwt_secret_fails_configuration_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VOICEUP_JWT_SECRET", raising=False)

    with pytest.raises(ValidationError, match="jwt_secret"):
        Settings(_env_file=None)


def test_migration_settings_require_only_the_database_boundary() -> None:
    settings = MigrationSettings(
        database_url="postgresql+asyncpg://app:password@postgres:5432/app_test",
        _env_file=None,
    )

    assert settings.database_url.endswith("/app_test")


def test_password_hash_round_trip() -> None:
    encoded = hash_password("StrongPassword123")
    assert encoded != "StrongPassword123"
    assert verify_password("StrongPassword123", encoded)
    assert not verify_password("WrongPassword123", encoded)


def test_weak_password_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("short")


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    tenant_id = uuid4()
    token = create_access_token(
        subject=user_id,
        username="admin",
        tenant_id=tenant_id,
        roles=["super_admin"],
        permissions=["platform:access"],
        is_super_admin=True,
    )
    claims = decode_access_token(token)
    assert claims.sub == user_id
    assert claims.tenant_id == tenant_id
    assert claims.is_super_admin is True


def test_tampered_token_is_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not.a.valid-token")
