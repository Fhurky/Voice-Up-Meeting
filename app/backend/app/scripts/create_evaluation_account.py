"""Create an ordinary evaluation account in its own tenant for local benchmark runs."""

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.base  # noqa: F401  # populate mapper metadata before any write
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import async_session_factory
from app.domain.models.permission import Permission, RolePermission
from app.domain.models.role import Role, UserRole
from app.domain.models.tenant import Tenant
from app.domain.models.user import User

EVALUATION_ROLE = "evaluation_operator"
EVALUATION_PERMISSIONS = (
    "meeting_analysis:read",
    "meeting_analysis:run",
    "speaker_profiles:read",
    "speaker_profiles:write",
)
TENANT_CODE = re.compile(r"eval-[a-z0-9][a-z0-9-]{0,39}")


@dataclass(frozen=True, slots=True)
class EvaluationAccount:
    user_public_id: UUID
    tenant_public_id: UUID
    created: bool


def _restore(row: Role | RolePermission | UserRole | Tenant | User) -> None:
    row.is_deleted = False
    row.deleted_at = None
    row.deleted_by = None


async def ensure_evaluation_account(
    session: AsyncSession, *, tenant_code: str, username: str, password: str
) -> EvaluationAccount:
    """Grant only the benchmark permissions; never the super_admin role or another tenant."""

    if get_settings().environment != "development":
        raise ValueError("evaluation accounts are limited to the development environment")
    if TENANT_CODE.fullmatch(tenant_code) is None:
        raise ValueError("tenant code must match eval-<lowercase-name>")
    normalized_username = username.strip().lower()
    if not normalized_username:
        raise ValueError("username is required")
    if len(password) < 12:
        raise ValueError("password must contain at least 12 characters")

    permissions = (
        await session.scalars(
            select(Permission).where(
                Permission.code.in_(EVALUATION_PERMISSIONS), Permission.is_deleted.is_(False)
            )
        )
    ).all()
    if {permission.code for permission in permissions} != set(EVALUATION_PERMISSIONS):
        raise RuntimeError("evaluation permissions are missing; run Alembic migrations first")

    role = (
        await session.execute(select(Role).where(Role.code == EVALUATION_ROLE))
    ).scalar_one_or_none()
    if role is None:
        role = Role(code=EVALUATION_ROLE, name="Local evaluation operator", scope="tenant")
        session.add(role)
        await session.flush()
    elif role.is_system:
        raise RuntimeError("evaluation role code is reserved by a system role")
    _restore(role)
    granted = {
        grant.permission_id: grant
        for grant in (
            await session.scalars(
                select(RolePermission).where(RolePermission.role_id == role.role_id)
            )
        ).all()
    }
    audited: list[Role | RolePermission | UserRole | Tenant | User] = [role]
    for permission in permissions:
        grant = granted.pop(permission.permission_id, None)
        if grant is None:
            grant = RolePermission(role_id=role.role_id, permission_id=permission.permission_id)
            session.add(grant)
        else:
            _restore(grant)
        audited.append(grant)
    for extra in granted.values():
        extra.is_deleted = True

    tenant = (
        await session.execute(select(Tenant).where(Tenant.code == tenant_code))
    ).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(code=tenant_code, name=f"Evaluation {tenant_code}")
        session.add(tenant)
        await session.flush()
    _restore(tenant)
    tenant.is_active = True

    user = (
        await session.execute(select(User).where(User.username == normalized_username))
    ).scalar_one_or_none()
    created = user is None
    if user is None:
        user = User(
            home_tenant_id=tenant.tenant_id,
            username=normalized_username,
            email=f"{normalized_username}@evaluation.invalid",
            display_name="Evaluation operator",
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
        await session.flush()
    elif user.home_tenant_id != tenant.tenant_id:
        raise ValueError("username already belongs to another tenant")
    else:
        user.password_hash = hash_password(password)
        user.is_active = True
        _restore(user)

    assignments = (
        await session.scalars(select(UserRole).where(UserRole.user_id == user.user_id))
    ).all()
    current = None
    for assignment in assignments:
        if assignment.role_id == role.role_id and assignment.tenant_id == tenant.tenant_id:
            current = assignment
            _restore(assignment)
        else:
            assignment.is_deleted = True
    if current is None:
        current = UserRole(user_id=user.user_id, role_id=role.role_id, tenant_id=tenant.tenant_id)
        session.add(current)
    for row in (*audited, tenant, user, current):
        row.created_by = row.created_by or user.user_id
        row.updated_by = user.user_id
    await session.commit()
    return EvaluationAccount(UUID(user.public_id), UUID(tenant.public_id), created)


async def _run(args: argparse.Namespace) -> EvaluationAccount:
    password = sys.stdin.readline().rstrip("\r\n")
    async with async_session_factory() as session:
        return await ensure_evaluation_account(
            session, tenant_code=args.tenant_code, username=args.username, password=password
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-code", required=True, help="eval-<lowercase-name>")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    result = asyncio.run(_run(args))
    action = "created" if result.created else "updated"
    print(
        f"evaluation account {action}: user={result.user_public_id} tenant={result.tenant_public_id}"
    )


if __name__ == "__main__":
    main()
