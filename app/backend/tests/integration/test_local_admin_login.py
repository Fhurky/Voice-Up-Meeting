"""Read-only local login with real PostgreSQL users, grants, JWTs and HTTP routing."""

import hashlib
import json
import secrets
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.domain.models.role import SUPER_ADMIN_ROLE, Role, UserRole
from app.domain.models.speaker_identity import SpeakerProfile
from app.domain.models.tenant import Tenant
from app.domain.models.user import User
from app.domain.speaker_identity import MODEL_ID, MODEL_REVISION
from app.main import create_application
from app.scripts.create_super_admin import ensure_super_admin

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def migrated_local_auth_database(postgres_database_url: str) -> Iterator[None]:
    del postgres_database_url
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    command.upgrade(config, "head")
    command.check(config)
    yield


@dataclass
class LocalAdmin:
    client: AsyncClient
    application: FastAPI
    session: AsyncSession
    settings: Settings
    user: User
    tenant: Tenant
    role: Role
    assignment: UserRole
    password: str

    def select_username(self, username: str) -> None:
        configured = Settings.model_validate(
            {**self.settings.model_dump(), "local_admin_username": username}
        )
        self.application.dependency_overrides[get_settings] = lambda: configured

    async def snapshot(self) -> str:
        records = {}
        for model in (User, Tenant, Role, UserRole, SpeakerProfile):
            table = model.__table__
            rows = await self.session.execute(select(table).order_by(*table.primary_key))
            records[table.name] = [dict(row) for row in rows.mappings()]
        # A failure compares only digests, never password hashes or stored vectors.
        return hashlib.sha256(json.dumps(records, sort_keys=True, default=str).encode()).hexdigest()


@pytest.fixture
async def local_admin(
    migrated_local_auth_database: None, postgres_database_url: str
) -> AsyncIterator[LocalAdmin]:
    engine = create_async_engine(postgres_database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        outer = await connection.begin()
        async with AsyncSession(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        ) as session:
            # Other integration modules may have committed test admins. Hide their grants only
            # inside this rolled-back transaction so the global single-admin query is isolated.
            role = (await session.scalars(select(Role).where(Role.code == SUPER_ADMIN_ROLE))).one()
            await session.execute(
                update(UserRole).where(UserRole.role_id == role.role_id).values(is_deleted=True)
            )
            suffix = uuid4().hex
            password = "Aa1-" + secrets.token_urlsafe(32)
            result = await ensure_super_admin(
                session,
                email=f"{suffix}@example.invalid",
                username=f"local-admin-{suffix}",
                password=password,
                tenant_code=f"local-admin-{suffix}",
            )
            user = (
                await session.scalars(
                    select(User).where(User.public_id == str(result.user_public_id))
                )
            ).one()
            tenant = await session.get(Tenant, user.home_tenant_id)
            assert tenant is not None
            assignment = await session.get(UserRole, (user.user_id, role.role_id, tenant.tenant_id))
            assert assignment is not None
            session.add(
                SpeakerProfile(
                    tenant_id=tenant.tenant_id,
                    name="Unchanged technical fixture",
                    sample_count=1,
                    model_id=MODEL_ID,
                    model_revision=MODEL_REVISION,
                    embedding=[1.0] + [0.0] * 191,
                    source_sha256="0" * 64,
                )
            )
            await session.flush()
            configured = Settings.model_validate(
                {
                    **get_settings().model_dump(),
                    "environment": "development",
                    "local_admin_login_enabled": True,
                    "local_admin_username": "",
                }
            )
            application = create_application()

            async def db() -> AsyncIterator[AsyncSession]:
                yield session

            application.dependency_overrides[get_db] = db
            application.dependency_overrides[get_settings] = lambda: configured
            try:
                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://127.0.0.1:8081/api/voiceup/v1/auth/",
                    headers={"Origin": "http://127.0.0.1:8081", "Sec-Fetch-Site": "same-origin"},
                ) as client:
                    yield LocalAdmin(
                        client,
                        application,
                        session,
                        configured,
                        user,
                        tenant,
                        role,
                        assignment,
                        password,
                    )
            finally:
                application.dependency_overrides.clear()
                await session.rollback()
        await outer.rollback()
    await engine.dispose()


async def assert_unavailable(fixture: LocalAdmin) -> None:
    before = await fixture.snapshot()
    response = await fixture.client.post("local-admin")
    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "local_admin_unavailable",
            "message": "An unambiguous active local administrator is unavailable.",
        }
    }
    assert response.headers["cache-control"] == "no-store"
    assert await fixture.snapshot() == before


async def test_local_login_reuses_jwt_me_and_password_login_without_writes(local_admin: LocalAdmin):
    before = await local_admin.snapshot()
    for _ in range(2):
        response = await local_admin.client.post("local-admin")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        payload = response.json()
        assert set(payload) == {"access_token", "token_type", "user"}
        assert payload["token_type"] == "bearer"
        claims = decode_access_token(payload["access_token"])
        assert claims.sub == UUID(local_admin.user.public_id)
        assert claims.tenant_id == UUID(local_admin.tenant.public_id)
        assert claims.is_super_admin and "super_admin" in claims.roles
        assert claims.exp > claims.iat
        me = await local_admin.client.get(
            "me",
            headers={
                "Authorization": f"Bearer {payload['access_token']}",
                local_admin.settings.tenant_header: local_admin.tenant.public_id,
            },
        )
        assert me.status_code == 200 and me.json() == payload["user"]
    normal = await local_admin.client.post(
        "login", json={"username": local_admin.user.username, "password": local_admin.password}
    )
    assert normal.status_code == 200
    wrong = await local_admin.client.post(
        "login", json={"username": local_admin.user.username, "password": "invalid"}
    )
    assert wrong.status_code == 401
    assert await local_admin.snapshot() == before


async def test_explicit_username_selects_one_admin_and_never_falls_back(local_admin: LocalAdmin):
    second = User(
        home_tenant_id=local_admin.tenant.tenant_id,
        username=f"other-{uuid4().hex}",
        email=f"{uuid4().hex}@example.invalid",
        display_name="Other administrator",
        password_hash=local_admin.user.password_hash,
    )
    local_admin.session.add(second)
    await local_admin.session.flush()
    local_admin.session.add(
        UserRole(
            user_id=second.user_id,
            role_id=local_admin.role.role_id,
            tenant_id=local_admin.tenant.tenant_id,
        )
    )
    await local_admin.session.flush()
    await assert_unavailable(local_admin)
    before = await local_admin.snapshot()
    local_admin.select_username("  " + local_admin.user.username.upper() + "  ")
    response = await local_admin.client.post("local-admin")
    assert response.status_code == 200
    assert response.json()["user"]["public_id"] == local_admin.user.public_id
    assert await local_admin.snapshot() == before
    local_admin.select_username("missing-account")
    await assert_unavailable(local_admin)
    local_admin.select_username(local_admin.user.email)
    await assert_unavailable(local_admin)


@pytest.mark.parametrize("selector", ["missing", "email", "nonadmin", "deleted", "inactive"])
async def test_explicit_selector_cannot_fall_back_to_the_single_active_admin(
    local_admin: LocalAdmin, selector: str
):
    if selector == "missing":
        selected = "missing-account"
    elif selector == "email":
        selected = local_admin.user.email
    else:
        target = User(
            home_tenant_id=local_admin.tenant.tenant_id,
            username=f"unavailable-{uuid4().hex}",
            email=f"{uuid4().hex}@example.invalid",
            display_name="Unavailable local identity",
            password_hash=local_admin.user.password_hash,
            is_active=selector != "inactive",
            is_deleted=selector == "deleted",
        )
        local_admin.session.add(target)
        await local_admin.session.flush()
        if selector != "nonadmin":
            local_admin.session.add(
                UserRole(
                    user_id=target.user_id,
                    role_id=local_admin.role.role_id,
                    tenant_id=local_admin.tenant.tenant_id,
                )
            )
        await local_admin.session.flush()
        selected = target.username
    local_admin.select_username(selected)
    await assert_unavailable(local_admin)


@pytest.mark.parametrize(
    "invalid_state",
    [
        "inactive_user",
        "deleted_user",
        "inactive_tenant",
        "deleted_tenant",
        "deleted_role",
        "deleted_assignment",
        "missing_assignment",
        "other_tenant_assignment",
    ],
)
async def test_inactive_or_nonadmin_records_are_not_revived(local_admin: LocalAdmin, invalid_state):
    if invalid_state == "inactive_user":
        local_admin.user.is_active = False
    elif invalid_state == "deleted_user":
        local_admin.user.is_deleted = True
    elif invalid_state == "inactive_tenant":
        local_admin.tenant.is_active = False
    elif invalid_state == "deleted_tenant":
        local_admin.tenant.is_deleted = True
    elif invalid_state == "deleted_role":
        local_admin.role.is_deleted = True
    elif invalid_state == "deleted_assignment":
        local_admin.assignment.is_deleted = True
    elif invalid_state == "missing_assignment":
        await local_admin.session.delete(local_admin.assignment)
    else:
        other = Tenant(code=f"other-{uuid4().hex}", name="Other tenant")
        local_admin.session.add(other)
        await local_admin.session.flush()
        local_admin.assignment.tenant_id = other.tenant_id
    await local_admin.session.flush()
    await assert_unavailable(local_admin)
    local_admin.select_username(local_admin.user.username)
    await assert_unavailable(local_admin)


async def test_new_local_login_observes_removed_admin_grant(local_admin: LocalAdmin):
    assert (await local_admin.client.post("local-admin")).status_code == 200
    local_admin.assignment.is_deleted = True
    await local_admin.session.flush()
    await assert_unavailable(local_admin)
