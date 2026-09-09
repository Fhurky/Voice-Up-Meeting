"""Fail-closed contracts for generated release, CI and migration surfaces."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from kt_scaffold.models import Answers
from kt_scaffold.project import project_init


@pytest.mark.parametrize(
    ("backend_profile", "persistence_profile"),
    [
        ("python-fastapi", "sqlalchemy-alembic"),
    ],
)
def test_generated_ci_builds_only_from_an_admitted_offline_bundle(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend_profile: str,
    persistence_profile: str,
) -> None:
    target = tmp_path / backend_profile
    project_init(
        target,
        answers_factory(
            backend_profile=backend_profile,
            persistence_profile=persistence_profile,
        ),
    )

    verifier = target / "scripts/verify-offline-bundle.sh"
    assert verifier.stat().st_mode & 0o100
    subprocess.run(["sh", "-n", str(verifier)], check=True)
    for workflow_name in ("backend-test.yml", "frontend-test.yml", "schema-check.yml"):
        workflow = (target / ".github/workflows" / workflow_name).read_text(encoding="utf-8")
        assert 'DEPENDENCY_MODE: "offline"' in workflow
        assert "vars.KT_SCAFFOLD_OFFLINE_BUNDLE" in workflow
        assert "vars.KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256" in workflow
        assert "scripts/verify-offline-bundle.sh" in workflow
        assert "PYTHON_WHEELHOUSE_CONTEXT=" in workflow
        assert "NPM_CACHE_CONTEXT=" in workflow
        assert "PRISMA_ENGINES_CONTEXT=" not in workflow
        assert 'docker load --input "$KT_SCAFFOLD_OFFLINE_BUNDLE/runtime-images.tar"' in workflow


@pytest.mark.parametrize(
    ("backend_profile", "persistence_profile"),
    [
        ("python-fastapi", "sqlalchemy-alembic"),
    ],
)
def test_release_context_and_processes_are_secret_safe_and_non_root(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend_profile: str,
    persistence_profile: str,
) -> None:
    target = tmp_path / backend_profile
    project_init(
        target,
        answers_factory(
            backend_profile=backend_profile,
            persistence_profile=persistence_profile,
        ),
    )

    root_ignore = (target / ".dockerignore").read_text(encoding="utf-8")
    frontend_ignore = (target / "app/frontend/.dockerignore").read_text(encoding="utf-8")
    for pattern in ("**/.env", "**/.env.*", "**/.npmrc", "**/*.pem", "**/node_modules"):
        assert pattern in root_ignore
    for pattern in (".env", ".env.*", ".npmrc", "node_modules"):
        assert pattern in frontend_ignore

    backend = (target / "app/infra/Dockerfile.backend.release").read_text(encoding="utf-8")
    migrate = (target / "app/infra/Dockerfile.migrate.release").read_text(encoding="utf-8")
    frontend = (target / "app/infra/Dockerfile.frontend.release").read_text(encoding="utf-8")
    assert "USER " in backend and "USER " in migrate and "USER 101:101" in frontend
    assert "start:dev" not in backend and "--reload" not in backend
    assert "ARG DEPENDENCY_MODE=offline" in frontend
    assert "from=npm_cache" in frontend

    frontend_dev = (target / "app/frontend/Dockerfile.dev").read_text(encoding="utf-8")
    compose = (target / "app/infra/docker-compose.local.yml").read_text(encoding="utf-8")
    assert "USER node" in frontend_dev
    assert "../frontend/src:/app/src:ro" in compose
    assert "../frontend/package.json:/app/package.json:ro" in compose
    assert "../frontend:/app:ro" not in compose

    assert 'ENTRYPOINT ["python", "-m", "uvicorn"' in backend
    assert 'ENTRYPOINT ["alembic", "upgrade", "head"]' in migrate
    alembic_env = (target / "schema/alembic/env.py").read_text(encoding="utf-8")
    assert "get_migration_settings().database_url" in alembic_env
    assert "get_settings" not in alembic_env
