"""Executable contracts for disposable database evidence in generated quality gates."""

from __future__ import annotations

import os
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

from kt_scaffold.models import Answers
from kt_scaffold.operations import init_operation


def _render(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
    *,
    backend: str = "python-fastapi",
) -> Path:
    target = tmp_path / backend
    answers = answers_factory()
    init_operation(str(target), **answers.model_dump(mode="json"))
    return target


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _install_fake_commands(target: Path) -> None:
    stack = """#!/usr/bin/env sh
set -eu
printf 'stack %s\\n' "$*" >> "$KT_TEST_LOG"
if [ -n "${KT_FAIL_MATCH:-}" ]; then
  case "$*" in
    *"$KT_FAIL_MATCH"*) exit "${KT_FAIL_CODE:-9}" ;;
  esac
fi
"""
    database = """#!/usr/bin/env sh
set -eu
override="${KT_SCAFFOLD_DATABASE_URL_OVERRIDE:-}"
printf 'db action=%s override=%s\\n' "${1:-}" "$override" >> "$KT_TEST_LOG"
"""
    no_op = """#!/usr/bin/env sh
set -eu
printf 'script %s %s\\n' "$(basename "$0")" "$*" >> "$KT_TEST_LOG"
"""
    _write_executable(target / "scripts/stack.sh", stack)
    _write_executable(target / "scripts/db.sh", database)
    for name in (
        "export-openapi.sh",
        "generate-types.sh",
        "render-clients.sh",
        "render-charts.sh",
    ):
        _write_executable(target / f"scripts/{name}", no_op)


def _run_gate(
    target: Path,
    scope: str,
    log: Path,
    **environment: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(target / "scripts/quality-gate.sh"), scope],
        cwd=target,
        env={**os.environ, "KT_TEST_LOG": str(log), **environment},
        check=False,
        capture_output=True,
        text=True,
    )


def test_all_scope_uses_and_removes_profile_specific_test_database(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    backend = "python-fastapi"
    target = _render(tmp_path, answers_factory)
    _install_fake_commands(target)
    log = tmp_path / f"{backend}.log"

    completed = _run_gate(target, "all", log)

    assert completed.returncode == 0, completed.stderr
    assert (
        "KT_GATE_SCOPE scope=all postgres_integration=required database_mode=disposable-test"
    ) in completed.stdout
    for step in (
        "configuration-sync",
        "database-test-create",
        "database-migrations-apply",
        "backend-tests",
        "database-validate",
        "database-test-drop",
    ):
        assert f"KT_GATE_STEP name={step} status=passed" in completed.stdout

    observed = log.read_text(encoding="utf-8")
    assert "-e RUN_POSTGRES_INTEGRATION=1 backend" in observed
    assert "db action=apply override=" in observed
    assert "db action=validate override=" in observed
    assert "_test" in observed
    assert "ZZSCF_DATABASE_URL=postgresql+asyncpg://" in observed
    assert "_python_gate_" in observed
    assert observed.count('DROP DATABASE IF EXISTS "ledger_') == 2
    assert 'CREATE DATABASE "ledger_' in observed


def test_backend_scope_is_read_only_and_skips_live_postgres(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _render(tmp_path, answers_factory)
    _install_fake_commands(target)
    log = tmp_path / "backend.log"

    completed = _run_gate(target, "backend", log)

    assert completed.returncode == 0, completed.stderr
    assert (
        "KT_GATE_SCOPE scope=backend postgres_integration=skipped "
        "database_mode=configured-read-only"
    ) in completed.stdout
    assert "database-test-create" not in completed.stdout
    assert "database-migrations-apply" not in completed.stdout
    assert "database-test-drop" not in completed.stdout
    assert "KT_GATE_STEP name=configuration-sync status=passed" in completed.stdout
    observed = log.read_text(encoding="utf-8")
    assert "RUN_POSTGRES_INTEGRATION=1" not in observed
    assert "CREATE DATABASE" not in observed
    assert "DROP DATABASE" not in observed
    assert "db action=validate override=" in observed


def test_all_scope_drops_test_database_after_backend_failure(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _render(tmp_path, answers_factory, backend="python-fastapi")
    _install_fake_commands(target)
    log = tmp_path / "failure.log"

    completed = _run_gate(
        target,
        "all",
        log,
        KT_FAIL_MATCH="ruff check",
        KT_FAIL_CODE="9",
    )

    assert completed.returncode == 9
    assert "KT_GATE_STEP name=backend-static status=failed exit_code=9" in completed.stdout
    assert "KT_GATE_STEP name=database-test-drop status=passed" in completed.stdout
    observed = log.read_text(encoding="utf-8")
    assert 'CREATE DATABASE "ledger_' in observed
    assert observed.count('DROP DATABASE IF EXISTS "ledger_') == 2
