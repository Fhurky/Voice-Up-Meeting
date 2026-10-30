"""Evaluation accounts are ordinary, tenant-bound and limited to benchmark permissions."""

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.db.session import async_session_factory, engine
from app.main import app
from app.scripts.create_evaluation_account import (
    EVALUATION_PERMISSIONS,
    ensure_evaluation_account,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def migrated_database(postgres_database_url: str) -> Iterator[None]:
    del postgres_database_url  # the Alembic environment reads the same typed setting
    command.upgrade(Config(str(Path(__file__).resolve().parents[2] / "alembic.ini")), "head")
    yield


async def login(username: str, password: str) -> dict:
    settings = get_settings()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"{settings.api_prefix}/auth/login",
            json={"username": username, "password": password},
        )
    assert response.status_code == 200, response.text
    return response.json()["user"]


@pytest.mark.asyncio
async def test_account_is_ordinary_idempotent_and_tenant_bound(migrated_database: None) -> None:
    suffix = uuid4().hex[:10]
    username, tenant_code = f"eval-user-{suffix}", f"eval-{suffix}"
    async with async_session_factory() as session:
        first = await ensure_evaluation_account(
            session, tenant_code=tenant_code, username=username, password="FirstPassword123"
        )
    async with async_session_factory() as session:
        second = await ensure_evaluation_account(
            session, tenant_code=tenant_code, username=username, password="SecondPassword456"
        )
    assert first.created is True and second.created is False
    assert first.user_public_id == second.user_public_id
    assert first.tenant_public_id == second.tenant_public_id
    user = await login(username, "SecondPassword456")
    assert user["is_super_admin"] is False and "super_admin" not in user["roles"]
    assert set(user["permissions"]) == set(EVALUATION_PERMISSIONS)
    assert user["tenant_id"] == str(first.tenant_public_id)
    async with async_session_factory() as session:
        with pytest.raises(ValueError, match="another tenant"):
            await ensure_evaluation_account(
                session,
                tenant_code=f"eval-other-{suffix}",
                username=username,
                password="ThirdPassword789",
            )
    await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tenant_code", "password", "message"),
    [
        ("platform", "LongEnough1234", "tenant code"),
        ("eval-Upper", "LongEnough1234", "tenant code"),
        ("eval-short-password", "short", "12 characters"),
    ],
)
async def test_invalid_requests_are_rejected_before_writes(
    migrated_database: None, tenant_code: str, password: str, message: str
) -> None:
    async with async_session_factory() as session:
        with pytest.raises(ValueError, match=message):
            await ensure_evaluation_account(
                session, tenant_code=tenant_code, username="eval-invalid", password=password
            )
    await engine.dispose()


@pytest.mark.asyncio
async def test_non_development_environment_is_refused(
    migrated_database: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "staging")
    async with async_session_factory() as session:
        with pytest.raises(ValueError, match="development environment"):
            await ensure_evaluation_account(
                session,
                tenant_code="eval-staging",
                username="eval-staging",
                password="LongEnough1234",
            )
    await engine.dispose()
