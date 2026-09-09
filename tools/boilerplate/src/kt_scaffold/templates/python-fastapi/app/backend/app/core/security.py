"""Password hashing and signed JWT access-token primitives."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings

_password_hash = PasswordHash.recommended()
PASSWORD_MIN_LENGTH = 12


class TokenClaims(BaseModel):
    """Claims trusted by request middleware after signature and audience validation."""

    sub: UUID
    username: str
    tenant_id: UUID
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    is_super_admin: bool = False
    exp: int
    iat: int
    iss: str
    aud: str


def validate_password_strength(password: str) -> None:
    """Apply the baseline bootstrap/password-creation policy."""

    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"password must contain at least {PASSWORD_MIN_LENGTH} characters")
    if not any(character.isupper() for character in password):
        raise ValueError("password must contain an uppercase character")
    if not any(character.islower() for character in password):
        raise ValueError("password must contain a lowercase character")
    if not any(character.isdigit() for character in password):
        raise ValueError("password must contain a digit")


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: UUID,
    username: str,
    tenant_id: UUID,
    roles: list[str],
    permissions: list[str],
    is_super_admin: bool,
) -> str:
    """Create a short-lived access token."""

    settings = get_settings()
    now = datetime.now(UTC)
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "username": username,
        "tenant_id": str(tenant_id),
        "roles": sorted(set(roles)),
        "permissions": sorted(set(permissions)),
        "is_super_admin": is_super_admin,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> TokenClaims:
    """Verify a token completely before exposing claims to authorization code."""

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        return TokenClaims.model_validate(payload)
    except (InvalidTokenError, ValidationError) as exc:
        raise InvalidTokenError("invalid access token") from exc
