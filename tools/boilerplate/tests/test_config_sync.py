"""Generated configuration synchronization gate contracts."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from kt_scaffold.models import Answers
from kt_scaffold.project import project_init

PROFILES = [
    ("python-fastapi", "sqlalchemy-alembic"),
]


def _render(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> Path:
    target = tmp_path / backend
    project_init(
        target,
        answers_factory(backend_profile=backend, persistence_profile=persistence),
    )
    return target


def _check(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/check-config-sync.py"],
        cwd=target,
        check=False,
        capture_output=True,
        text=True,
    )


def _remove_assignment(path: Path, key: str) -> None:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    mutated = [
        line
        for line in lines
        if not line.startswith(f"{key}=") and not line.startswith(f"      {key}:")
    ]
    assert mutated != lines
    path.write_text("".join(mutated), encoding="utf-8")


@pytest.mark.parametrize(("backend", "persistence"), PROFILES)
def test_generated_configuration_contract_is_synchronized(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> None:
    target = _render(tmp_path, answers_factory, backend, persistence)

    result = _check(target)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["ok"] is True
    assert report["backend_profile"] == backend
    assert report["env_prefix"] == "ZZSCF_"
    assert report["checked"]["typed_configuration_keys"] >= 10
    assert report["checked"]["kubernetes_secret_refs"] == 1


@pytest.mark.parametrize(("backend", "persistence"), PROFILES)
def test_configuration_contract_rejects_missing_example_key(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> None:
    target = _render(tmp_path, answers_factory, backend, persistence)
    key = "ZZSCF_JWT_ALGORITHM"
    _remove_assignment(target / "app/backend/.env.example", key)

    result = _check(target)

    assert result.returncode == 1
    assert "typed keys are not represented" in result.stderr
    assert key in result.stderr


@pytest.mark.parametrize(("backend", "persistence"), PROFILES)
def test_configuration_contract_rejects_missing_compose_runtime_key(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> None:
    target = _render(tmp_path, answers_factory, backend, persistence)
    key = "ZZSCF_LOG_LEVEL"
    _remove_assignment(target / "app/infra/docker-compose.local.yml", key)

    result = _check(target)

    assert result.returncode == 1
    assert "runtime settings missing from backend environment" in result.stderr
    assert key in result.stderr


@pytest.mark.parametrize(("backend", "persistence"), PROFILES)
def test_configuration_contract_rejects_an_unapproved_process_environment_read(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> None:
    target = _render(tmp_path, answers_factory, backend, persistence)
    mutation = target / "app/backend/app/services/env_escape.py"
    mutation.write_text(
        'import os\n\nescaped = os.getenv("ZZSCF_JWT_SECRET")\n',
        encoding="utf-8",
    )

    result = _check(target)

    assert result.returncode == 1
    assert "direct process-environment read outside an approved boundary" in result.stderr
    assert mutation.name in result.stderr


@pytest.mark.parametrize(("backend", "persistence"), PROFILES)
def test_configuration_contract_rejects_foreign_prefix_and_per_key_chart_env(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    backend: str,
    persistence: str,
) -> None:
    target = _render(tmp_path, answers_factory, backend, persistence)
    compose = target / "app/infra/docker-compose.local.yml"
    compose_source = compose.read_text(encoding="utf-8")
    compose.write_text(
        compose_source.replace("      ZZSCF_PROJECT_NAME:", "      FOREIGN_PROJECT_NAME:", 1),
        encoding="utf-8",
    )
    deployment = target / "app/devops/charts/app-backend/templates/deployment.yaml"
    deployment_source = deployment.read_text(encoding="utf-8")
    deployment.write_text(
        deployment_source.replace(
            "          envFrom:\n",
            "          env:\n            - name: FORBIDDEN\n              value: forbidden\n"
            "          envFrom:\n",
            1,
        ),
        encoding="utf-8",
    )

    result = _check(target)

    assert result.returncode == 1
    assert "FOREIGN_PROJECT_NAME" in result.stderr
    assert "per-key container env mappings are forbidden" in result.stderr
