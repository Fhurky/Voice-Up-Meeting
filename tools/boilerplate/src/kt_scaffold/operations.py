"""Transport-neutral implementations of the twelve public operations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Literal, cast

import yaml

from kt_scaffold.agent_platform.compiler import compile_agent_projections
from kt_scaffold.agent_platform.projection_store import render_inert_projections
from kt_scaffold.corpus import find_project_root, load_rules, public_rule
from kt_scaffold.fsops import apply_file_set
from kt_scaffold.models import Answers, ToolResult
from kt_scaffold.project import project_init
from kt_scaffold.render import render_clients
from kt_scaffold.report import TIER_ORDER, report_skeleton
from kt_scaffold.safety import atomic_write, resolved_root, safe_join, safe_relative
from kt_scaffold.update import load_answers, load_manifest, scaffold_update

AgentClientId = Literal[
    "claude-code",
    "codex",
    "cursor",
    "github-copilot-vscode",
]


def project_root(target_dir: str | Path | None = None) -> Path:
    if target_dir is not None:
        root = resolved_root(target_dir)
        if not (root / ".kt-scaffold" / "answers.yml").is_file():
            raise ValueError(f"{root} is not a scaffolded project")
        return root
    detected = find_project_root()
    if detected is None:
        raise ValueError("operation must run inside a scaffolded project or receive target_dir")
    return detected


def init_operation(target_dir: str, **payload: Any) -> dict[str, object]:
    return project_init(target_dir, Answers.model_validate(payload))


def update_operation(
    target_dir: str | None = None, answer_overrides: dict[str, object] | None = None
) -> dict[str, object]:
    return scaffold_update(project_root(target_dir), answer_overrides=answer_overrides)


def rules_list_operation(
    target_dir: str | None = None,
    scope: str | None = None,
    applies_to_path: str | None = None,
    trigger: str | None = None,
) -> dict[str, object]:
    root = project_root(target_dir)
    rules = load_rules(root / "rules")
    if scope:
        rules = [rule for rule in rules if rule.scope == scope]
    if trigger:
        rules = [rule for rule in rules if rule.trigger == trigger]
    if applies_to_path:
        from fnmatch import fnmatch

        rules = [
            rule
            for rule in rules
            if rule.trigger == "always"
            or any(fnmatch(applies_to_path, glob) for glob in rule.applies_to)
        ]
    result = ToolResult(ok=True).as_dict()
    result["rules"] = [public_rule(rule) for rule in rules]
    return result


def rules_get_operation(ids: list[str], target_dir: str | None = None) -> dict[str, object]:
    root = project_root(target_dir)
    index = {rule.id: rule for rule in load_rules(root / "rules")}
    missing = sorted(set(ids) - set(index))
    if missing:
        raise ValueError(f"unknown rule ids: {', '.join(missing)}")
    result = ToolResult(ok=True).as_dict()
    result["rules"] = [public_rule(index[rule_id], include_body=True) for rule_id in ids]
    return result


def clients_render_operation(
    target_dir: str | None = None,
    clients: list[str] | None = None,
    agent_clients: list[AgentClientId] | None = None,
    mode: str = "write",
) -> dict[str, object]:
    root = project_root(target_dir)
    answers = load_answers(root)
    compilation = compile_agent_projections(
        assets_root=root / "agent-platform",
        client_ids=tuple(agent_clients) if agent_clients is not None else None,
    )
    changes, drift = render_clients(
        root, mode=mode, clients=clients, primary_locale=answers.locales[0]
    )
    projection_changes, projection_drift = render_inert_projections(
        root,
        compilation,
        mode=mode,
    )
    projection_conflict = any(change.action == "conflict" for change in projection_changes)
    changes.extend(projection_changes)
    drift.extend(projection_drift)
    operation_ok = not drift if mode == "check" else not projection_conflict
    result = ToolResult(ok=operation_ok, changes=changes).as_dict()
    result.update(
        {
            "drift": drift,
            "lock_updated": mode == "write" and not projection_conflict,
            "agent_projection": {
                "generation_status": compilation.manifest.generation_status,
                "activation_status": compilation.manifest.activation_status,
                "runtime_conformance": compilation.manifest.runtime_conformance,
                "runtime_admission": compilation.manifest.runtime_admission,
                "artifact_count": len(compilation.artifacts),
                "lock_sha256": compilation.lock_sha256,
            },
        }
    )
    return result


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", slug):
        raise ValueError("value cannot be normalized to a safe slug")
    return slug


def _write_result(
    root: Path,
    files: dict[str, bytes],
    *,
    allow_updates: set[str] | None = None,
) -> dict[str, object]:
    changes = apply_file_set(root, files, allow_updates=allow_updates)
    ok = not any(change.action == "conflict" for change in changes)
    return ToolResult(ok=ok, changes=changes).as_dict()


def spec_new_operation(
    domain: str,
    capability: str,
    intent: str,
    mode: str = "lean",
    target_dir: str | None = None,
) -> dict[str, object]:
    root = project_root(target_dir)
    domain = _slug(domain)
    capability = _slug(capability)
    intent = intent.strip()
    if not intent:
        raise ValueError("intent is required")
    if mode not in {"lean", "comprehensive"}:
        raise ValueError("mode must be lean or comprehensive")
    domain_root = safe_join(root, Path("specs") / domain)
    if not (domain_root / "DOMAIN.md").is_file():
        raise ValueError(f"domain context does not exist: specs/{domain}/DOMAIN.md")
    existing = sorted((domain_root / "PRDs").glob("[0-9][0-9][0-9]-*"))
    same = [path for path in existing if path.name.endswith(f"-{capability}")]
    number = same[0].name.split("-", 1)[0] if same else f"{len(existing) + 1:03d}"
    relative_root = Path("specs") / domain / "PRDs" / f"{number}-{capability}"
    prd = (
        f"# PRD — {capability}\n\n"
        "Status: Draft\n\n"
        f"Domain: [{domain}](../../DOMAIN.md)\n\n"
        f"## Intent\n\n{intent}\n\n"
        "## Actors and outcomes\n\n- Define the actor and measurable outcome.\n\n"
        "## Invariants and boundaries\n\n- Define owned data, policy and external boundaries.\n\n"
        "## Acceptance criteria\n\n- [ ] Evidence L1: unit and integration behavior is green.\n"
        "- [ ] Evidence L2: the live HTTP/browser scenario is green.\n\n"
        "## Delivery flow\n\nSpec → Plan → Tasks → Implement\n"
    )
    if mode == "comprehensive":
        prd += "\n## Risks\n\n- Record security, operational and migration risks.\n"
    plan = (
        f"# Plan — {capability}\n\nDerived from [PRD](PRD.md). "
        "Do not implement until the PRD is Accepted.\n"
    )
    tasks = (
        f"# Tasks — {capability}\n\nDerived from [plan](plan.md).\n\n"
        "- [ ] Trace each task to an acceptance criterion.\n"
    )
    roadmap_path = Path("specs") / domain / "roadmap.md"
    roadmap = safe_join(root, roadmap_path).read_text(encoding="utf-8")
    prd_link = relative_root.relative_to(Path("specs") / domain)
    row = f"| {number} | {capability} | [PRD]({prd_link}/PRD.md) | Draft |"
    if row not in roadmap:
        roadmap = roadmap.rstrip() + "\n" + row + "\n"
    files = {
        (relative_root / "PRD.md").as_posix(): prd.encode(),
        (relative_root / "plan.md").as_posix(): plan.encode(),
        (relative_root / "tasks.md").as_posix(): tasks.encode(),
        roadmap_path.as_posix(): roadmap.encode(),
    }
    result = _write_result(root, files, allow_updates={roadmap_path.as_posix()})
    result.update(
        {
            "spec_path": (relative_root / "PRD.md").as_posix(),
            "roadmap_entry": row,
            "sections_emitted": ["intent", "actors", "invariants", "acceptance", "delivery"],
        }
    )
    return result


def _accepted_spec(root: Path, spec_path: str) -> tuple[Path, str]:
    relative = safe_relative(spec_path)
    if relative.name != "PRD.md" or not relative.parts or relative.parts[0] != "specs":
        raise ValueError("spec_path must point to specs/<domain>/PRDs/<capability>/PRD.md")
    path = safe_join(root, relative)
    if not path.is_file():
        raise ValueError(f"spec does not exist: {relative}")
    text = path.read_text(encoding="utf-8")
    if not re.search(r"^Status:\s*Accepted\s*$", text, flags=re.MULTILINE | re.IGNORECASE):
        raise ValueError("business generation requires a PRD whose Status is Accepted")
    capability = _slug(relative.parent.name.split("-", 1)[-1])
    return relative, capability


def _insert_before_marker(text: str, marker: str, line: str) -> str:
    if marker not in text:
        raise ValueError(f"generated registry marker is missing: {marker}")
    if line in text:
        return text
    return text.replace(marker, f"{line}\n{marker}")


def _insert_sorted_python_import(text: str, marker: str, line: str) -> str:
    if marker not in text:
        raise ValueError(f"generated registry marker is missing: {marker}")
    if line in text:
        return text
    lines = text.splitlines()
    marker_index = lines.index(marker)
    while marker_index > 0 and not lines[marker_index - 1]:
        del lines[marker_index - 1]
        marker_index -= 1
    start = marker_index
    while start > 0:
        previous = lines[start - 1]
        if previous.startswith("from app."):
            start -= 1
            continue
        if previous.strip() == ")":
            block_start = start - 2
            while block_start >= 0 and not lines[block_start].startswith("from app."):
                block_start -= 1
            if block_start >= 0 and " import (" in lines[block_start]:
                start = block_start
                continue
        break

    blocks: list[str] = []
    cursor = start
    while cursor < marker_index:
        block = [lines[cursor]]
        if " import (" in lines[cursor]:
            cursor += 1
            while cursor < marker_index:
                block.append(lines[cursor])
                if lines[cursor].strip() == ")":
                    break
                cursor += 1
        blocks.append("\n".join(block))
        cursor += 1
    imports = sorted({*blocks, line})
    flattened = [item for block in imports for item in block.splitlines()]
    lines[start:marker_index] = [*flattened, ""]
    return "\n".join(lines) + "\n"


def _python_import(module: str, imported: str, *, noqa: str | None = None) -> str:
    suffix = f"  # noqa: {noqa}" if noqa else ""
    single = f"from {module} import {imported}{suffix}"
    if len(single) <= 100:
        return single
    return f"from {module} import ({suffix}\n    {imported},\n)"


def _permission_code(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_.-]*:[a-z][a-z0-9_.-]*", value):
        raise ValueError("permission must use the lowercase resource:action form")
    return value


def _python_domain_files(
    root: Path,
    spec: Path,
    capability: str,
    tenant_scoped: bool,
    permission: str,
) -> tuple[dict[str, bytes], set[str]]:
    snake = capability.replace("-", "_")
    class_name = "".join(part.title() for part in capability.split("-"))
    model_path = f"app/backend/app/domain/models/{snake}.py"
    sqlalchemy_names = (
        "BigInteger, ForeignKey, Identity, Index, Text, text"
        if tenant_scoped
        else "BigInteger, Identity, Index, Text, text"
    )
    tenant_import = f"from sqlalchemy import {sqlalchemy_names}"
    tenant_column = (
        "    tenant_id: Mapped[int] = mapped_column(\n"
        "        BigInteger,\n"
        '        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"),\n'
        "        nullable=False,\n"
        "        index=True,\n"
        "    )\n"
        if tenant_scoped
        else ""
    )
    domain_model_import = _python_import(f"app.domain.models.{snake}", class_name)
    repository_class_import = _python_import(
        f"app.infrastructure.repositories.{snake}_repository",
        f"{class_name}Repository",
    )
    response_import = _python_import(
        f"app.schemas.{snake}",
        f"{class_name}Response",
    )
    service_class_import = _python_import(
        f"app.services.{snake}_service",
        f"{class_name}Service",
    )
    model = (
        f'"""Persistence authority generated from {spec.as_posix()}."""\n\n'
        f"{tenant_import}\n"
        "from sqlalchemy.orm import Mapped, mapped_column\n\n"
        "from app.db.base_class import Base\n"
        "from app.domain.models.mixins import AuditSoftDeleteMixin, new_public_id\n\n\n"
        f"class {class_name}(\n"
        "    AuditSoftDeleteMixin,\n"
        "    Base,\n"
        "):\n"
        f'    __tablename__ = "{snake}"\n'
        "    __table_args__ = (\n"
        "        Index(\n"
        f'            "ix_{snake}_active_public_id",\n'
        '            "public_id",\n'
        '            postgresql_where=text("is_deleted = false"),\n'
        "        ),\n"
        "        {\n"
        '            "comment": (\n'
        '                "Domain skeleton traced to "\n'
        f'                "{spec.as_posix()}."\n'
        "            ),\n"
        "        },\n"
        "    )\n\n"
        f"    {snake}_id: Mapped[int] = mapped_column(\n"
        "        BigInteger,\n"
        "        Identity(),\n"
        "        primary_key=True,\n"
        "    )\n"
        "    public_id: Mapped[str] = mapped_column(\n"
        "        Text,\n"
        "        default=new_public_id,\n"
        "        nullable=False,\n"
        "        unique=True,\n"
        "    )\n"
        f"{tenant_column}"
    )
    repository = (
        f'"""Tenant-safe queries for {class_name}."""\n\n'
        "from collections.abc import Sequence\n\n"
        "from sqlalchemy import select\n"
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n"
        f"{domain_model_import}\n"
        + ("from app.domain.models.tenant import Tenant\n" if tenant_scoped else "")
        + "\n\n"
        f"class {class_name}Repository:\n"
        "    async def list_active(\n"
        "        self,\n"
        "        session: AsyncSession,\n"
        "        tenant_public_id: str | None,\n"
        f"    ) -> Sequence[{class_name}]:\n"
        f"        statement = select({class_name}).where(\n"
        f"            {class_name}.is_deleted.is_(False),\n"
        "        )\n"
        + (
            "        if tenant_public_id is None:\n"
            "            return []\n"
            "        statement = statement.join(\n"
            "            Tenant,\n"
            f"            {class_name}.tenant_id == Tenant.tenant_id,\n"
            "        )\n"
            "        statement = statement.where(\n"
            "            Tenant.public_id == tenant_public_id,\n"
            "            Tenant.is_deleted.is_(False),\n"
            "            Tenant.is_active.is_(True),\n"
            "        )\n"
            if tenant_scoped
            else ""
        )
        + "        statement = statement.order_by(\n"
        f"            {class_name}.created_at.desc(),\n"
        f"            {class_name}.{snake}_id.desc(),\n"
        "        ).limit(100)\n"
        "        return (await session.scalars(statement)).all()\n"
    )
    repository_assignment = f"        self.repository = repository or {class_name}Repository()"
    if len(repository_assignment) > 100:
        repository_assignment = (
            "        self.repository = (\n"
            f"            repository or {class_name}Repository()\n"
            "        )"
        )
    service = (
        f'"""Application boundary traced to {spec.as_posix()}."""\n\n'
        "from collections.abc import Sequence\n\n"
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n"
        f"{domain_model_import}\n"
        f"{repository_class_import}\n\n"
        f'REQUIRED_PERMISSION = "{permission}"\n'
        f"TENANT_SCOPED = {tenant_scoped!r}\n\n\n"
        f"class {class_name}Service:\n"
        "    def __init__(\n"
        "        self,\n"
        f"        repository: {class_name}Repository | None = None,\n"
        "    ) -> None:\n"
        f"{repository_assignment}\n\n"
        "    async def list_active(\n"
        "        self,\n"
        "        session: AsyncSession,\n"
        "        tenant_public_id: str | None,\n"
        f"    ) -> Sequence[{class_name}]:\n"
        "        return await self.repository.list_active(session, tenant_public_id)\n"
    )
    schemas = (
        f'"""Public response contract traced to {spec.as_posix()}."""\n\n'
        "from datetime import datetime\n\n"
        "from pydantic import BaseModel, ConfigDict\n\n\n"
        f"class {class_name}Response(BaseModel):\n"
        "    model_config = ConfigDict(from_attributes=True)\n\n"
        "    public_id: str\n"
        "    created_at: datetime\n"
        "    updated_at: datetime\n"
    )
    router_assignment = f'router = APIRouter(prefix="/{capability}", tags=["{capability}"])'
    if len(router_assignment) > 100:
        router_assignment = (
            f'router = APIRouter(\n    prefix="/{capability}",\n    tags=["{capability}"],\n)'
        )
    response_return = (
        f"    return [{class_name}Response.model_validate(record) for record in records]"
    )
    if len(response_return) > 100:
        response_expression = (
            f"        {class_name}Response.model_validate(record) for record in records"
        )
        if len(response_expression) <= 100:
            response_return = f"    return [\n{response_expression}\n    ]"
        else:
            response_return = (
                "    return [\n"
                f"        {class_name}Response.model_validate(record)\n"
                "        for record in records\n"
                "    ]"
            )
    dependencies = f'    dependencies=[Depends(require_permission("{permission}"))],'
    if len(dependencies) > 100:
        dependencies = (
            "    dependencies=[\n"
            "        Depends(\n"
            f'            require_permission("{permission}")\n'
            "        )\n"
            "    ],"
        )
    router = (
        f'"""Protected walking-skeleton endpoint for {spec.as_posix()}."""\n\n'
        "from typing import Annotated\n\n"
        "from fastapi import APIRouter, Depends\n"
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n"
        "from app.api.auth.dependencies import CurrentContext, require_permission\n"
        "from app.db.session import get_db\n"
        f"{response_import}\n"
        f"{service_class_import}\n\n"
        f"{router_assignment}\n"
        f"service = {class_name}Service()\n\n\n"
        "@router.get(\n"
        '    "",\n'
        f"    response_model=list[{class_name}Response],\n"
        f"{dependencies}\n"
        ")\n"
        f"async def list_{snake}(\n"
        "    session: Annotated[AsyncSession, Depends(get_db)],\n"
        "    context: CurrentContext,\n"
        f") -> list[{class_name}Response]:\n"
        "    tenant_id = str(context.tenant_id) if context.tenant_id else None\n"
        "    records = await service.list_active(session, tenant_id)\n"
        f"{response_return}\n"
    )
    repository_behavior_test = (
        "@pytest.mark.asyncio\n"
        "async def test_repository_enforces_tenant_and_soft_delete_filters() -> None:\n"
        "    scalar_result = Mock()\n"
        "    scalar_result.all.return_value = []\n"
        "    session = AsyncMock(spec=AsyncSession)\n"
        "    session.scalars.return_value = scalar_result\n"
        f"    repository = {class_name}Repository()\n\n"
        "    assert await repository.list_active(session, None) == []\n"
        "    session.scalars.assert_not_awaited()\n\n"
        '    assert await repository.list_active(session, "tenant-public-id") == []\n'
        "    statement = session.scalars.await_args.args[0]\n"
        "    sql = str(statement)\n"
        f'    assert "{snake}.is_deleted IS false" in sql\n'
        '    assert "JOIN tenant" in sql\n'
        '    assert "tenant.public_id" in sql\n'
        '    assert "tenant.is_deleted IS false" in sql\n'
        '    assert "tenant.is_active IS true" in sql\n'
        '    assert "tenant-public-id" in statement.compile().params.values()\n\n\n'
        if tenant_scoped
        else (
            "@pytest.mark.asyncio\n"
            "async def test_repository_enforces_soft_delete_filter() -> None:\n"
            "    scalar_result = Mock()\n"
            "    scalar_result.all.return_value = []\n"
            "    session = AsyncMock(spec=AsyncSession)\n"
            "    session.scalars.return_value = scalar_result\n"
            f"    repository = {class_name}Repository()\n\n"
            "    assert await repository.list_active(session, None) == []\n"
            "    statement = session.scalars.await_args.args[0]\n"
            "    sql = str(statement)\n"
            f'    assert "{snake}.is_deleted IS false" in sql\n'
            '    assert "JOIN tenant" not in sql\n\n\n'
        )
    )
    test = (
        f'"""Generated contract tests for {spec.as_posix()}."""\n\n'
        "from unittest.mock import AsyncMock, Mock\n\n"
        "import pytest\n"
        "from sqlalchemy.ext.asyncio import AsyncSession\n\n"
        f"{domain_model_import}\n"
        f"{repository_class_import}\n"
        f"from app.services.{snake}_service import (\n"
        "    REQUIRED_PERMISSION,\n"
        "    TENANT_SCOPED,\n"
        f"    {class_name}Service,\n"
        ")\n\n"
        "pytestmark = pytest.mark.unit\n\n\n"
        "def test_generated_vertical_declares_lifecycle_and_authorization_contract() -> None:\n"
        f"    columns = set({class_name}.__table__.columns.keys())\n"
        "    mandatory = {\n"
        '        "public_id",\n'
        '        "props",\n'
        '        "created_at",\n'
        '        "updated_at",\n'
        '        "created_by",\n'
        '        "updated_by",\n'
        '        "is_deleted",\n'
        '        "deleted_at",\n'
        '        "deleted_by",\n'
        "    }\n"
        "    assert mandatory <= columns\n"
        f"    assert TENANT_SCOPED is {tenant_scoped!r}\n"
        f'    assert REQUIRED_PERMISSION == "{permission}"\n'
        "\n\n"
        f"{repository_behavior_test}"
        "@pytest.mark.asyncio\n"
        "async def test_service_returns_repository_records_for_active_tenant() -> None:\n"
        f'    record = {class_name}(public_id="record-public-id")\n'
        f"    repository = {class_name}Repository()\n"
        "    repository.list_active = AsyncMock(return_value=[record])\n"
        "    session = AsyncMock(spec=AsyncSession)\n"
        f"    service = {class_name}Service(repository)\n\n"
        '    records = await service.list_active(session, "tenant-public-id")\n\n'
        "    assert list(records) == [record]\n"
        '    repository.list_active.assert_awaited_once_with(session, "tenant-public-id")\n'
    )

    models_init_path = "app/backend/app/domain/models/__init__.py"
    models_init = safe_join(root, models_init_path).read_text(encoding="utf-8")
    models_init = _insert_sorted_python_import(
        models_init,
        "# kt-scaffold:model-imports",
        _python_import(f"app.domain.models.{snake}", class_name),
    )
    models_init = _insert_before_marker(
        models_init,
        "    # kt-scaffold:model-exports",
        f'    "{class_name}",',
    )
    base_path = "app/backend/app/db/base.py"
    base = safe_join(root, base_path).read_text(encoding="utf-8")
    base = _insert_sorted_python_import(
        base,
        "# kt-scaffold:model-registry",
        _python_import(
            f"app.domain.models.{snake}",
            class_name,
            noqa="E402,F401",
        ),
    )
    api_registry_path = "app/backend/app/api/router.py"
    api_registry = safe_join(root, api_registry_path).read_text(encoding="utf-8")
    api_registry = _insert_sorted_python_import(
        api_registry,
        "# kt-scaffold:router-imports",
        _python_import(
            f"app.api.{snake}.router",
            f"router as {snake}_router",
        ),
    )
    api_registry = _insert_before_marker(
        api_registry,
        "# kt-scaffold:router-registration",
        f"router.include_router({snake}_router)",
    )
    files = {
        model_path: model.encode(),
        f"app/backend/app/infrastructure/repositories/{snake}_repository.py": repository.encode(),
        f"app/backend/app/services/{snake}_service.py": service.encode(),
        f"app/backend/app/schemas/{snake}.py": schemas.encode(),
        f"app/backend/app/api/{snake}/__init__.py": b'"""Generated domain API package."""\n',
        f"app/backend/app/api/{snake}/router.py": router.encode(),
        f"app/backend/tests/domain/test_{snake}.py": test.encode(),
        models_init_path: models_init.encode(),
        base_path: base.encode(),
        api_registry_path: api_registry.encode(),
    }
    return files, {models_init_path, base_path, api_registry_path}


def backend_domain_new_operation(
    spec_path: str,
    tenant_scoped: bool = True,
    permissions: dict[str, str] | None = None,
    target_dir: str | None = None,
) -> dict[str, object]:
    root = project_root(target_dir)
    spec, capability = _accepted_spec(root, spec_path)
    snake = capability.replace("-", "_")
    permission = _permission_code((permissions or {}).get("read", f"{snake}:read"))
    files, registries = _python_domain_files(root, spec, capability, tenant_scoped, permission)
    result = _write_result(root, files, allow_updates=registries)
    if result["ok"]:
        result["next_steps"] = [
            f"kt-scaffold schema --spec-path {spec.as_posix()} "
            f"--change-summary 'Add {capability} desired state' --migration-name add-{capability}",
            "Review the generated desired-state model and complete the accepted PRD tasks.",
        ]
    result.update(
        {
            "files": sorted(files),
            "permission_sync_todo": [permission],
            "registry_updated": result["ok"],
        }
    )
    return result


def frontend_page_new_operation(
    spec_path: str,
    page: str,
    route: str,
    permission: str | None = None,
    target_dir: str | None = None,
) -> dict[str, object]:
    root = project_root(target_dir)
    spec, capability = _accepted_spec(root, spec_path)
    page_slug = _slug(page)
    component_base = "".join(part.title() for part in page_slug.split("-"))
    component = f"{component_base}Page"
    service_name = f"{component_base}Service"
    record_name = f"{component_base}Record"
    state_name = f"{component_base}State"
    page_constant = page_slug.replace("-", "_").upper()
    endpoint = f"/{capability}"
    if not re.fullmatch(r"/(?:[a-z0-9][a-z0-9_-]*)(?:/[a-z0-9][a-z0-9_-]*)*", route):
        raise ValueError("route must be an absolute lowercase application path")
    effective_permission = _permission_code(
        permission if permission is not None else f"{capability.replace('-', '_')}:read"
    )
    registry_path = "app/frontend/src/generated/routes.tsx"
    registry = safe_join(root, registry_path).read_text(encoding="utf-8")
    import_line = f"import {component} from '@/pages/{component}';"
    route_line = (
        f'      <Route path="{route}" element={{'
        f'<PermissionRoute permission="{effective_permission}">'
        f"<{component} /></PermissionRoute>}} />"
    )
    if import_line not in registry:
        registry = registry.replace(
            "// kt-scaffold:imports", f"{import_line}\n// kt-scaffold:imports"
        )
    if route_line not in registry:
        registry = registry.replace(
            "{/* kt-scaffold:routes */}", f"{route_line}\n      {{/* kt-scaffold:routes */}}"
        )
    service = (
        f"/** Typed active-list boundary generated from {spec.as_posix()}. */\n"
        'import { apiRequest } from "@/lib/apiClient";\n\n'
        f"export interface {record_name} {{\n"
        "  public_id: string;\n"
        "  created_at: string;\n"
        "  updated_at: string;\n"
        "}\n\n"
        f'export const {page_constant}_ENDPOINT = "{endpoint}";\n\n'
        f"export const {service_name} = {{\n"
        f"  listActive(): Promise<{record_name}[]> {{\n"
        f"    return apiRequest<{record_name}[]>({page_constant}_ENDPOINT);\n"
        "  },\n"
        "};\n"
    )
    page_source = (
        f"// Generated from {spec.as_posix()}\n"
        'import { useEffect, useState } from "react";\n'
        'import { useIntl } from "@/contexts/IntlContext";\n'
        f'import {{ {service_name} }} from "@/services/{page_slug}";\n'
        f'import type {{ {record_name} }} from "@/services/{page_slug}";\n\n'
        f"type {state_name} =\n"
        '  | { status: "loading" }\n'
        f'  | {{ status: "ready"; records: {record_name}[] }}\n'
        '  | { status: "error"; message: string };\n\n'
        "function errorMessage(error: unknown): string {\n"
        '  return error instanceof Error ? error.message : "Unknown error";\n'
        "}\n\n"
        f"export default function {component}() {{\n"
        "  const intl = useIntl();\n"
        f'  const [state, setState] = useState<{state_name}>({{ status: "loading" }});\n\n'
        "  useEffect(() => {\n"
        "    let active = true;\n"
        f"    void {service_name}.listActive()\n"
        "      .then((records) => {\n"
        '        if (active) setState({ status: "ready", records });\n'
        "      })\n"
        "      .catch((error: unknown) => {\n"
        '        if (active) setState({ status: "error", message: errorMessage(error) });\n'
        "      });\n"
        "    return () => {\n"
        "      active = false;\n"
        "    };\n"
        "  }, []);\n\n"
        "  return (\n"
        "    <main>\n"
        f'      <h1>{{intl.t("pages.{page_slug}.title")}}</h1>\n'
        '      <section aria-live="polite">\n'
        '        {state.status === "loading" && (\n'
        f'          <p role="status">{{intl.t("pages.{page_slug}.loading")}}</p>\n'
        "        )}\n"
        '        {state.status === "error" && (\n'
        f'          <p role="alert">{{intl.t("pages.{page_slug}.error")}}: {{state.message}}</p>\n'
        "        )}\n"
        '        {state.status === "ready" && state.records.length === 0 && (\n'
        f'          <p>{{intl.t("pages.{page_slug}.empty")}}</p>\n'
        "        )}\n"
        '        {state.status === "ready" && state.records.length > 0 && (\n'
        f'          <ul aria-label={{intl.t("pages.{page_slug}.title")}}>\n'
        "            {state.records.map((record) => (\n"
        "              <li key={record.public_id}>\n"
        "                <strong>{record.public_id}</strong>\n"
        "                <time dateTime={record.updated_at}>{record.updated_at}</time>\n"
        "              </li>\n"
        "            ))}\n"
        "          </ul>\n"
        "        )}\n"
        "      </section>\n"
        "    </main>\n"
        "  );\n"
        "}\n"
    )
    page_test = (
        'import { render, screen } from "@testing-library/react";\n'
        'import { afterEach, describe, expect, it, vi } from "vitest";\n'
        'import { IntlProvider } from "@/contexts/IntlContext";\n'
        f'import {component} from "@/pages/{component}";\n'
        f'import {{ {service_name} }} from "@/services/{page_slug}";\n\n'
        f'describe("{component}", () => {{\n'
        "  afterEach(() => vi.restoreAllMocks());\n\n"
        '  it("loads and renders active records from the generated service", async () => {\n'
        f'    const listActive = vi.spyOn({service_name}, "listActive").mockResolvedValue([\n'
        "      {\n"
        '        public_id: "record-public-id",\n'
        '        created_at: "2026-01-02T03:04:05.000Z",\n'
        '        updated_at: "2026-01-03T03:04:05.000Z",\n'
        "      },\n"
        "    ]);\n\n"
        "    render(\n"
        "      <IntlProvider>\n"
        f"        <{component} />\n"
        "      </IntlProvider>,\n"
        "    );\n\n"
        '    expect(await screen.findByText("record-public-id")).toBeInTheDocument();\n'
        '    expect(screen.getByText("2026-01-03T03:04:05.000Z")).toHaveAttribute(\n'
        '      "datetime",\n'
        '      "2026-01-03T03:04:05.000Z",\n'
        "    );\n"
        "    expect(listActive).toHaveBeenCalledOnce();\n"
        "  });\n\n"
        '  it("renders a closed error state when loading fails", async () => {\n'
        f'    vi.spyOn({service_name}, "listActive").mockRejectedValue(new Error("offline"));\n\n'
        "    render(\n"
        "      <IntlProvider>\n"
        f"        <{component} />\n"
        "      </IntlProvider>,\n"
        "    );\n\n"
        '    expect(await screen.findByRole("alert")).toHaveTextContent("offline");\n'
        "  });\n"
        "});\n"
    )
    service_test = (
        'import { afterEach, describe, expect, it, vi } from "vitest";\n'
        f"import {{ {page_constant}_ENDPOINT, {service_name} }} from "
        f'"@/services/{page_slug}";\n\n'
        f'describe("{service_name}", () => {{\n'
        "  afterEach(() => vi.restoreAllMocks());\n\n"
        '  it("requests and returns the capability active list", async () => {\n'
        "    const records = [\n"
        "      {\n"
        '        public_id: "record-public-id",\n'
        '        created_at: "2026-01-02T03:04:05.000Z",\n'
        '        updated_at: "2026-01-03T03:04:05.000Z",\n'
        "      },\n"
        "    ];\n"
        '    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(\n'
        "      new Response(JSON.stringify(records), {\n"
        "        status: 200,\n"
        '        headers: { "Content-Type": "application/json" },\n'
        "      }),\n"
        "    );\n\n"
        f"    await expect({service_name}.listActive()).resolves.toEqual(records);\n"
        "    expect(String(fetchMock.mock.calls[0]?.[0]).endsWith("
        f"{page_constant}_ENDPOINT)).toBe(true);\n"
        "  });\n"
        "});\n"
    )
    files: dict[str, bytes] = {
        f"app/frontend/src/pages/{component}.tsx": page_source.encode(),
        f"app/frontend/src/pages/{component}.test.tsx": page_test.encode(),
        f"app/frontend/src/services/{page_slug}.ts": service.encode(),
        f"app/frontend/src/services/{page_slug}.test.ts": service_test.encode(),
        registry_path: registry.encode(),
    }
    locale_keys: list[str] = []
    answers = load_answers(root)
    for locale in answers.locales:
        locale_path = f"app/frontend/src/locales/{locale}.json"
        payload = json.loads(safe_join(root, locale_path).read_text(encoding="utf-8"))
        page_messages = payload.setdefault("pages", {}).setdefault(page_slug, {})
        labels = (
            {
                "title": page.replace("-", " ").title(),
                "loading": "Aktif kayıtlar yükleniyor…",
                "error": "Aktif kayıtlar yüklenemedi",
                "empty": "Aktif kayıt bulunamadı.",
            }
            if locale.startswith("tr")
            else {
                "title": page.replace("-", " ").title(),
                "loading": "Loading active records…",
                "error": "Active records could not be loaded",
                "empty": "No active records were found.",
            }
        )
        page_messages.update(labels)
        files[locale_path] = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode()
        locale_keys.extend(
            f"{locale}:pages.{page_slug}.{key}" for key in ("title", "loading", "error", "empty")
        )
    result = _write_result(
        root,
        files,
        allow_updates={
            registry_path,
            *[f"app/frontend/src/locales/{item}.json" for item in answers.locales],
        },
    )
    result.update(
        {
            "files": sorted(files),
            "locale_keys_added": locale_keys,
            "route_registered": result["ok"],
            "endpoint": endpoint,
            "permission": effective_permission,
        }
    )
    return result


def schema_change_prepare_operation(
    spec_path: str,
    change_summary: str,
    migration_name: str,
    target_dir: str | None = None,
) -> dict[str, object]:
    root = project_root(target_dir)
    spec, _ = _accepted_spec(root, spec_path)
    name = _slug(migration_name)
    answers = load_answers(root)
    request_path = f"schema/changes/{name}.yml"
    body = yaml.safe_dump(
        {
            "spec": spec.as_posix(),
            "summary": change_summary,
            "authority": answers.persistence_profile,
            "status": "authority-change-required",
        },
        sort_keys=False,
    ).encode()
    result = _write_result(root, {request_path: body})
    command = f"cd app/backend && alembic revision --autogenerate -m {name}"
    result["warnings"] = [
        "The request is recorded, but no empty migration was forged. Edit the profile-owned "
        "schema authority, then run the returned native generator."
    ]
    result.update(
        {
            "schema_authority_files": ["app/backend/app/domain/models"],
            "generated_migration": None,
            "commands": [command, "scripts/db.sh validate"],
        }
    )
    return result


_GATE_MARKER_VALUE = re.compile(r"^[A-Za-z0-9_.:/-]+$")


def _gate_marker(line: str, prefix: str) -> dict[str, str] | None:
    marker = f"{prefix} "
    if not line.startswith(marker):
        return None
    fields: dict[str, str] = {}
    for token in line[len(marker) :].split():
        key, separator, value = token.partition("=")
        if (
            not separator
            or not re.fullmatch(r"[a-z][a-z0-9_-]*", key)
            or not _GATE_MARKER_VALUE.fullmatch(value)
            or key in fields
        ):
            raise ValueError(f"malformed {prefix} marker: {line}")
        fields[key] = value
    return fields


def _parse_gate_evidence(
    output: str,
    *,
    expected_scope: str,
    include_browser: bool,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int], list[str]]:
    """Parse only the generated gate's machine markers; never infer counts from prose."""

    results: list[dict[str, object]] = []
    tests: list[dict[str, object]] = []
    errors: list[str] = []
    scope_markers: list[dict[str, str]] = []
    current_step: dict[str, object] | None = None
    current_output: list[str] = []

    def finish_output() -> None:
        nonlocal current_output
        if current_step is not None:
            current_step["output_tail"] = "\n".join(current_output)[-8000:]
        current_output = []

    try:
        for line in output.splitlines():
            scope_fields = _gate_marker(line, "KT_GATE_SCOPE")
            if scope_fields is not None:
                scope_markers.append(scope_fields)
                continue
            step_fields = _gate_marker(line, "KT_GATE_STEP")
            if step_fields is not None:
                name = step_fields.get("name", "")
                status = step_fields.get("status", "")
                if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
                    errors.append(f"invalid quality step name: {name or '<missing>'}")
                    continue
                if status == "started":
                    if current_step is not None:
                        finish_output()
                        if current_step.get("status") == "started":
                            current_step["status"] = "incomplete"
                            errors.append(f"quality step never completed: {current_step['step']}")
                    current_step = {
                        "step": name,
                        "command": f"quality-gate:{name}",
                        "status": "started",
                        "output_tail": "",
                    }
                    results.append(current_step)
                    continue
                if status not in {"passed", "failed"}:
                    errors.append(
                        f"invalid status for quality step {name}: {status or '<missing>'}"
                    )
                    continue
                if current_step is None or current_step.get("step") != name:
                    errors.append(f"quality step terminal marker has no matching start: {name}")
                    continue
                finish_output()
                current_step["status"] = status
                if status == "failed":
                    exit_code = step_fields.get("exit_code")
                    if exit_code is None or not exit_code.isdigit():
                        errors.append(f"failed quality step has no numeric exit code: {name}")
                    else:
                        current_step["exit_code"] = int(exit_code)
                current_step = None
                continue
            test_fields = _gate_marker(line, "KT_GATE_TESTS")
            if test_fields is not None:
                required = {"name", "runner", "total", "passed", "failed", "skipped"}
                missing = sorted(required - test_fields.keys())
                if missing:
                    errors.append("quality test marker missing fields: " + ", ".join(missing))
                    continue
                numeric: dict[str, int] = {}
                for key in ("total", "passed", "failed", "skipped"):
                    value = test_fields[key]
                    if not value.isdigit():
                        errors.append(
                            f"quality test marker {test_fields['name']} has invalid {key}"
                        )
                        break
                    numeric[key] = int(value)
                else:
                    if numeric["total"] != (
                        numeric["passed"] + numeric["failed"] + numeric["skipped"]
                    ):
                        errors.append(
                            f"quality test marker {test_fields['name']} has inconsistent counts"
                        )
                        continue
                    tests.append(
                        {
                            "name": test_fields["name"],
                            "runner": test_fields["runner"],
                            **numeric,
                        }
                    )
                continue
            if current_step is not None:
                current_output.append(line)
    except ValueError as exc:
        errors.append(str(exc))

    if current_step is not None:
        finish_output()
        if current_step.get("status") == "started":
            current_step["status"] = "incomplete"
            errors.append(f"quality step never completed: {current_step['step']}")

    if len(scope_markers) != 1:
        errors.append("quality gate must emit exactly one KT_GATE_SCOPE marker")
    elif scope_markers[0].get("scope") != expected_scope:
        errors.append(
            "quality gate scope marker mismatch: "
            f"expected {expected_scope}, got {scope_markers[0].get('scope', '<missing>')}"
        )

    expected_steps = {
        "backend": {
            "configuration",
            "configuration-sync",
            "backend-static",
            "backend-tests",
            "database-validate",
            "openapi-contract",
        },
        "frontend": {
            "configuration",
            "frontend-static",
            "frontend-tests",
            "frontend-types-contract",
        },
        "all": {
            "configuration",
            "configuration-sync",
            "database-test-create",
            "database-migrations-apply",
            "backend-static",
            "backend-tests",
            "database-validate",
            "openapi-contract",
            "frontend-static",
            "frontend-tests",
            "frontend-types-contract",
            "governance-drift",
            "charts-render",
            "database-test-drop",
        },
    }[expected_scope]
    if include_browser:
        expected_steps.update({"browser-readiness", "browser-scenarios"})
    observed_steps = {str(item["step"]) for item in results}
    missing_steps = sorted(expected_steps - observed_steps)
    if missing_steps:
        errors.append("quality gate omitted logical steps: " + ", ".join(missing_steps))

    expected_tests = {
        "backend": {"backend-tests"},
        "frontend": {"frontend-tests"},
        "all": {"backend-tests", "frontend-tests"},
    }[expected_scope]
    if include_browser:
        expected_tests.add("browser-scenarios")
    observed_names = [str(item["name"]) for item in tests]
    duplicates = sorted({name for name in observed_names if observed_names.count(name) > 1})
    if duplicates:
        errors.append("duplicate quality test markers: " + ", ".join(duplicates))
    missing_tests = sorted(expected_tests - set(observed_names))
    if missing_tests:
        errors.append("quality gate omitted test evidence: " + ", ".join(missing_tests))

    counts = {
        "unit": sum(
            cast(int, item["passed"]) for item in tests if item["name"] != "browser-scenarios"
        ),
        "browser": sum(
            cast(int, item["passed"]) for item in tests if item["name"] == "browser-scenarios"
        ),
        "skipped": sum(cast(int, item["skipped"]) for item in tests),
    }
    return results, tests, counts, errors


def _quality_gate_contract(
    root: Path,
    scope: str,
    include_browser: bool,
) -> tuple[list[str], list[str], str]:
    if scope not in {"backend", "frontend", "all"}:
        raise ValueError("scope must be backend, frontend or all")
    gate_relative = "scripts/quality-gate.sh"
    gate_path = safe_join(root, gate_relative)
    if not gate_path.is_file():
        raise ValueError("quality gate script is missing or is not a regular file")
    manifest = load_manifest(root)
    managed = cast(dict[str, str], manifest["managed"])
    expected_digest = managed.get(gate_relative)
    actual_digest = hashlib.sha256(gate_path.read_bytes()).hexdigest()
    if expected_digest is None or actual_digest != expected_digest:
        raise ValueError(
            "quality gate script differs from the scaffold manifest; review and resolve the "
            "generated-file conflict before execution"
        )
    command = [gate_relative, scope]
    execution_command = [str(gate_path), scope]
    if include_browser:
        command.append("--include-browser")
        execution_command.append("--include-browser")
    return command, execution_command, actual_digest


def quality_gate_prepare_operation(
    scope: str = "all",
    include_browser: bool = False,
    target_dir: str | None = None,
) -> dict[str, object]:
    """Prepare a content-bound command for execution in the caller workspace."""

    root = project_root(target_dir)
    command, _, gate_digest = _quality_gate_contract(root, scope, include_browser)
    metadata_path = safe_join(root, ".kt-scaffold/project-manifest.json")
    if not metadata_path.is_file():
        raise ValueError("bounded project manifest is missing")
    metadata_digest = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
    challenge_input = {
        "format": 1,
        "project_metadata_sha256": metadata_digest,
        "gate_sha256": gate_digest,
        "command": command,
    }
    challenge = hashlib.sha256(
        json.dumps(challenge_input, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    result = ToolResult(ok=True).as_dict()
    result.update(
        {
            "phase": "prepare",
            "challenge": challenge,
            "project_metadata_sha256": metadata_digest,
            "gate_sha256": gate_digest,
            "command": command,
            "shell_command": " ".join(command),
            "provenance_expected": "client-reported",
        }
    )
    return result


def _quality_gate_result(
    *,
    root: Path,
    scope: str,
    include_browser: bool,
    command: list[str],
    output: str,
    exit_code: int,
    provenance: str,
    challenge: str | None,
) -> dict[str, object]:
    if len(output.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("quality evidence output exceeds 2097152 bytes")
    if provenance not in {"local-executed", "client-reported", "runner-attested"}:
        raise ValueError("unsupported quality evidence provenance")
    answers = load_answers(root)
    results, test_runs, counts, protocol_errors = _parse_gate_evidence(
        output,
        expected_scope=scope,
        include_browser=include_browser,
    )
    evidence_path = root / ".kt-scaffold" / "evidence.json"
    observed_failures = any(cast(int, item["failed"]) > 0 for item in test_runs)
    failed_steps = any(item["status"] != "passed" for item in results)
    gate_ok = exit_code == 0 and not protocol_errors and not observed_failures and not failed_steps
    full_gate_passed = gate_ok and scope == "all"
    evidence = {
        "tier": "L2"
        if full_gate_passed and include_browser and counts["browser"] > 0
        else "L1"
        if full_gate_passed
        else "L0",
        "scope": scope,
        "browser": gate_ok and include_browser and counts["browser"] > 0,
        "command": " ".join(command),
        "counts": counts,
        "results": results,
        "test_runs": test_runs,
        "protocol_errors": protocol_errors,
        "provenance": provenance,
        "challenge": challenge,
    }
    atomic_write(
        root,
        evidence_path.relative_to(root),
        (json.dumps(evidence, indent=2) + "\n").encode(),
    )
    report = report_skeleton(
        locale=answers.locales[0],
        verdict="PASS" if gate_ok else "FAIL",
        ran=[" ".join(command)],
        counts=counts,
        defects=([] if exit_code == 0 else [f"quality gate exited {exit_code}"]) + protocol_errors,
    )
    result = ToolResult(ok=gate_ok, warnings=protocol_errors).as_dict()
    result.update(
        {
            "results": results,
            "test_runs": test_runs,
            "counts": counts,
            "tier_reached": evidence["tier"],
            "provenance": provenance,
            "report_skeleton": report,
        }
    )
    return result


def quality_gate_finalize_operation(
    *,
    scope: str,
    include_browser: bool,
    evidence_output: str,
    exit_code: int,
    challenge: str,
    target_dir: str | None = None,
) -> dict[str, object]:
    """Validate client-run evidence and record its explicitly untrusted provenance."""

    if not re.fullmatch(r"[0-9a-f]{64}", challenge):
        raise ValueError("quality gate challenge must be a SHA-256 digest")
    root = project_root(target_dir)
    prepared = quality_gate_prepare_operation(scope, include_browser, str(root))
    if challenge != prepared["challenge"]:
        raise ValueError("quality gate challenge does not match the project metadata")
    command = cast(list[str], prepared["command"])
    result = _quality_gate_result(
        root=root,
        scope=scope,
        include_browser=include_browser,
        command=command,
        output=evidence_output,
        exit_code=exit_code,
        provenance="client-reported",
        challenge=challenge,
    )
    result["phase"] = "finalize"
    return result


def quality_gate_operation(
    scope: str = "all",
    include_browser: bool = False,
    target_dir: str | None = None,
    *,
    allow_project_code_execution: bool = False,
) -> dict[str, object]:
    root = project_root(target_dir)
    if not allow_project_code_execution:
        raise ValueError(
            "quality_gate executes project-owned scripts; set "
            "allow_project_code_execution=true only after trusting this target"
        )
    command, execution_command, _ = _quality_gate_contract(root, scope, include_browser)
    answers = load_answers(root)
    safe_names = {
        "APP_HTTP_PORT",
        "CI",
        "DEPENDENCY_MODE",
        "DOCKER_HOST",
        "GRAFANA_ADMIN_PASSWORD",
        "HOME",
        "JWT_SECRET",
        "LANG",
        "LC_ALL",
        "LOGNAME",
        "NPM_CACHE_CONTEXT",
        "PATH",
        "POSTGRES_PASSWORD",
        "PYTHON_WHEELHOUSE_CONTEXT",
        "RUN_POSTGRES_INTEGRATION",
        "SHELL",
        "TERM",
        "TMPDIR",
        "USER",
        "XDG_RUNTIME_DIR",
    }
    safe_prefixes: tuple[str, ...] = (
        cast(str, answers.env_prefix),
        "APP_E2E_",
        "KT_SCAFFOLD_",
        "NPM_",
        "PIP_",
        "PLAYWRIGHT_",
        "PYTHON",
        "npm_config_",
    )
    execution_environment = {
        key: value
        for key, value in os.environ.items()
        if key in safe_names or key.startswith(safe_prefixes)
    }
    completed = subprocess.run(
        execution_command,
        cwd=root,
        env=execution_environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=1800,
    )
    output = (completed.stdout or "").strip()
    return _quality_gate_result(
        root=root,
        scope=scope,
        include_browser=include_browser,
        command=command,
        output=output,
        exit_code=completed.returncode,
        provenance="local-executed",
        challenge=None,
    )


def browser_scenario_new_operation(
    spec_path: str,
    suite: str,
    scenario_title: str,
    acceptance_points: list[str],
    target_dir: str | None = None,
) -> dict[str, object]:
    root = project_root(target_dir)
    spec, _ = _accepted_spec(root, spec_path)
    suite = _slug(suite)
    scenario = _slug(scenario_title)
    clean_points = [" ".join(point.split()) for point in acceptance_points if point.strip()]
    if not clean_points:
        raise ValueError("at least one acceptance point is required")
    suite_dir = safe_join(root, Path("e2e") / suite)
    existing = sorted(suite_dir.glob("[0-9][0-9]-*.mjs")) if suite_dir.exists() else []
    same = [path for path in existing if path.name.endswith(f"-{scenario}.mjs")]
    number = same[0].name.split("-", 1)[0] if same else f"{len(existing) + 1:02d}"
    scenario_path = f"e2e/{suite}/{number}-{scenario}.mjs"
    assertions = "\n".join(f"  // Acceptance: {point}" for point in clean_points)
    pending_message = "Implement executable assertions for: " + "; ".join(clean_points)
    body = (
        f"// Generated from {spec.as_posix()}\n"
        "import {runScenario} from '../shared/harness.mjs';\n\n"
        f"await runScenario({json.dumps(scenario_title)}, async ({{page, expect}}) => {{\n"
        f"{assertions}\n"
        "  void page;\n"
        "  void expect;\n"
        f"  throw new Error({json.dumps(pending_message)});\n"
        "});\n"
    )
    scenario_names = sorted({path.name for path in existing} | {Path(scenario_path).name})
    runner_path = f"e2e/{suite}/run-all.mjs"
    runner = "".join(f"await import('./{name}');\n" for name in scenario_names)
    runner += f"console.log('{len(scenario_names)} {suite} scenario(s) passed');\n"

    package_path = "e2e/package.json"
    package_payload = json.loads(safe_join(root, package_path).read_text(encoding="utf-8"))
    scripts = package_payload.setdefault("scripts", {})
    if not isinstance(scripts, dict):
        raise ValueError("e2e/package.json scripts must be an object")
    scripts[suite] = f"node {suite}/run-all.mjs"

    manifest_path = "e2e/QUALITY_MANIFEST.md"
    manifest = safe_join(root, manifest_path).read_text(encoding="utf-8")
    evidence = "; ".join(clean_points)
    manifest_row = (
        f"| {suite} | {scenario_path.removeprefix('e2e/')} | {evidence} · {spec.as_posix()} |"
    )
    if manifest_row not in manifest:
        marker = "\n\nDomain rows are added only by accepted PRDs."
        if marker in manifest:
            manifest = manifest.replace(marker, f"\n{manifest_row}{marker}")
        else:
            manifest = manifest.rstrip() + "\n" + manifest_row + "\n"

    files = {
        scenario_path: body.encode(),
        runner_path: runner.encode(),
        package_path: (json.dumps(package_payload, indent=2, sort_keys=True) + "\n").encode(),
        manifest_path: manifest.encode(),
    }
    result = _write_result(
        root,
        files,
        allow_updates={runner_path, package_path, manifest_path},
    )
    result.update(
        {
            "scenario_path": scenario_path,
            "runner_updated": result["ok"],
            "package_script": f"{suite}: node {suite}/run-all.mjs",
            "manifest_row": manifest_row,
            "executable_assertions_required": True,
        }
    )
    result["warnings"] = [
        "Acceptance prose is not treated as test evidence. Replace the generated failing guard "
        "with executable browser assertions before claiming L2."
    ]
    result["next_steps"] = [f"Implement assertions in {scenario_path}"]
    return result


def done_report_operation(
    change_summary: str,
    claimed_tier: str,
    target_dir: str | None = None,
) -> dict[str, object]:
    root = project_root(target_dir)
    if claimed_tier not in TIER_ORDER:
        raise ValueError("claimed_tier must be L0, L1, L2 or L3")
    evidence_path = root / ".kt-scaffold" / "evidence.json"
    supported = "L0"
    evidence: list[str] = ["change is written"]
    observed_counts = {"unit": 0, "browser": 0, "skipped": 0}
    provenance = "unrecorded"
    if evidence_path.is_file():
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        candidate_provenance = payload.get("provenance")
        if candidate_provenance in {"local-executed", "client-reported", "runner-attested"}:
            provenance = str(candidate_provenance)
        candidate_tier = payload.get("tier", "L0")
        candidate_counts = payload.get("counts", {})
        if candidate_tier in TIER_ORDER and isinstance(candidate_counts, dict):
            valid_counts = {
                key: candidate_counts.get(key) for key in ("unit", "browser", "skipped")
            }
            if all(
                isinstance(value, int) and not isinstance(value, bool) and value >= 0
                for value in valid_counts.values()
            ):
                observed_counts = {key: cast(int, value) for key, value in valid_counts.items()}
                supported = str(candidate_tier)
                if TIER_ORDER[supported] >= TIER_ORDER["L1"] and observed_counts["unit"] == 0:
                    supported = "L0"
                if supported == "L2" and observed_counts["browser"] == 0:
                    supported = "L1"
        command = payload.get("command")
        if isinstance(command, str) and command:
            evidence.append(command)
        evidence.append(f"evidence provenance: {provenance}")
    missing: list[str] = []
    if TIER_ORDER[supported] < TIER_ORDER[claimed_tier]:
        missing.append(f"claimed {claimed_tier}, but observed evidence supports {supported}")
    labels_locale = load_answers(root).locales[0]
    decision = "← KARAR" if labels_locale.startswith("tr") else "← DECISION"
    defects = [f"{item} {decision}" for item in missing]
    report = report_skeleton(
        locale=labels_locale,
        verdict=f"{change_summary}: supported {supported}, claimed {claimed_tier}",
        ran=evidence,
        counts=observed_counts,
        defects=defects,
        open_items=missing,
    )
    result = ToolResult(ok=True).as_dict()
    result.update(
        {
            "tier_supported": supported,
            "evidence": evidence,
            "missing": missing,
            "verdict": "supported" if not missing else "unsupported claim reported",
            "provenance": provenance,
            "report_skeleton": report,
        }
    )
    return result
