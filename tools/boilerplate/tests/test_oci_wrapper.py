"""Fail-closed boundary contracts for the offline OCI MCP/CLI wrapper."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

WRAPPER = Path("packaging/kt-scaffold-oci.in").resolve()


def _executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _environment(tmp_path: Path, *, workspace: Path, target: Path) -> tuple[dict[str, str], Path]:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(exist_ok=True)
    log = tmp_path / "docker.log"
    _executable(
        fake_bin / "id",
        "#!/usr/bin/env sh\ncase \"${1:-}\" in -u|-g) printf '10001\\n' ;; *) exit 2 ;; esac\n",
    )
    _executable(
        fake_bin / "docker",
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        ': "${OCI_WRAPPER_TEST_LOG:?}"\n'
        'printf \'%s\\n\' "$@" > "$OCI_WRAPPER_TEST_LOG"\n',
    )
    environment = {
        **os.environ,
        "HOME": str(tmp_path / "operator-home"),
        "KT_SCAFFOLD_TARGET": str(target),
        "KT_SCAFFOLD_WORKSPACE_ROOT": str(workspace),
        "OCI_WRAPPER_TEST_LOG": str(log),
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
    }
    Path(environment["HOME"]).mkdir(exist_ok=True)
    return environment, log


def _run(environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/sh", str(WRAPPER), "--version"],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize("existing_scaffold", [False, True])
def test_wrapper_mounts_only_an_empty_or_marked_exact_target(
    tmp_path: Path,
    existing_scaffold: bool,
) -> None:
    workspace = (tmp_path / "approved-workspace").resolve()
    target = workspace / ("existing" if existing_scaffold else "empty-init[1]")
    target.mkdir(parents=True)
    if existing_scaffold:
        metadata = target / ".kt-scaffold"
        metadata.mkdir()
        (metadata / "answers.yml").write_text("backend_profile: python-fastapi\n", encoding="utf-8")
        (metadata / "manifest.json").write_text('{"format":1}\n', encoding="utf-8")
        (target / "owned-source.txt").write_text("allowed\n", encoding="utf-8")
    environment, log = _environment(tmp_path, workspace=workspace, target=target)

    completed = _run(environment)

    assert completed.returncode == 0, completed.stderr
    arguments = log.read_text(encoding="utf-8").splitlines()
    assert arguments[:2] == ["run", "--rm"]
    assert arguments[arguments.index("--network") : arguments.index("--network") + 2] == [
        "--network",
        "none",
    ]
    assert arguments[arguments.index("--volume") : arguments.index("--volume") + 2] == [
        "--volume",
        f"{target.resolve()}:/out:rw",
    ]
    assert "--read-only" in arguments
    assert "no-new-privileges" in arguments
    assert "@@GENERATOR_IMAGE_ID@@" in arguments
    assert arguments[-1] == "--version"


def test_wrapper_requires_an_absolute_canonical_workspace_root(tmp_path: Path) -> None:
    workspace = (tmp_path / "approved-workspace").resolve()
    target = workspace / "target"
    target.mkdir(parents=True)
    environment, log = _environment(tmp_path, workspace=workspace, target=target)

    for invalid in ("relative/workspace", f"{workspace}/"):
        attempted = _run({**environment, "KT_SCAFFOLD_WORKSPACE_ROOT": invalid})
        assert attempted.returncode == 2
        assert (
            "absolute canonical" in attempted.stderr or "already be canonical" in attempted.stderr
        )
        assert not log.exists()

    missing = environment.copy()
    missing.pop("KT_SCAFFOLD_WORKSPACE_ROOT")
    attempted = _run(missing)
    assert attempted.returncode == 2
    assert "KT_SCAFFOLD_WORKSPACE_ROOT" in attempted.stderr
    assert not log.exists()


def test_wrapper_rejects_root_and_home_as_workspace_boundaries(tmp_path: Path) -> None:
    workspace = (tmp_path / "approved-workspace").resolve()
    target = workspace / "target"
    target.mkdir(parents=True)
    environment, log = _environment(tmp_path, workspace=workspace, target=target)

    root_boundary = _run({**environment, "KT_SCAFFOLD_WORKSPACE_ROOT": "/"})
    assert root_boundary.returncode == 2
    assert "workspace root must not be /" in root_boundary.stderr
    assert not log.exists()

    home_boundary = _run({**environment, "HOME": str(workspace)})
    assert home_boundary.returncode == 2
    assert "workspace root must not be HOME" in home_boundary.stderr
    assert not log.exists()


@pytest.mark.parametrize("broad_target", ["root", "home", "workspace"])
def test_wrapper_rejects_broad_writable_mounts(
    tmp_path: Path,
    broad_target: str,
) -> None:
    workspace = (tmp_path / "approved-workspace").resolve()
    workspace.mkdir()
    operator_home = workspace / "operator-home"
    operator_home.mkdir()
    environment, log = _environment(tmp_path, workspace=workspace, target=workspace)
    environment["HOME"] = str(operator_home)
    environment["KT_SCAFFOLD_TARGET"] = {
        "root": "/",
        "home": str(operator_home),
        "workspace": str(workspace),
    }[broad_target]

    completed = _run(environment)

    assert completed.returncode == 2
    assert "target" in completed.stderr
    assert not log.exists()


def test_wrapper_rejects_targets_outside_the_workspace_and_symlink_targets(
    tmp_path: Path,
) -> None:
    workspace = (tmp_path / "approved-workspace").resolve()
    target = workspace / "real-target"
    outside = tmp_path / "outside"
    target.mkdir(parents=True)
    outside.mkdir()
    link = workspace / "linked-target"
    link.symlink_to(target, target_is_directory=True)
    environment, log = _environment(tmp_path, workspace=workspace, target=target)

    outside_run = _run({**environment, "KT_SCAFFOLD_TARGET": str(outside)})
    assert outside_run.returncode == 2
    assert "strict descendant" in outside_run.stderr
    assert not log.exists()

    symlink_run = _run({**environment, "KT_SCAFFOLD_TARGET": str(link)})
    assert symlink_run.returncode == 2
    assert "symbolic link" in symlink_run.stderr
    assert not log.exists()


@pytest.mark.parametrize("marker_to_omit", ["answers.yml", "manifest.json"])
def test_wrapper_rejects_nonempty_targets_without_both_regular_markers(
    tmp_path: Path,
    marker_to_omit: str,
) -> None:
    workspace = (tmp_path / "approved-workspace").resolve()
    target = workspace / "untrusted-nonempty"
    metadata = target / ".kt-scaffold"
    metadata.mkdir(parents=True)
    for marker in ("answers.yml", "manifest.json"):
        if marker != marker_to_omit:
            (metadata / marker).write_text("{}\n", encoding="utf-8")
    (target / "payload.sh").write_text("untrusted\n", encoding="utf-8")
    environment, log = _environment(tmp_path, workspace=workspace, target=target)

    completed = _run(environment)

    assert completed.returncode == 2
    assert "empty or contain regular" in completed.stderr
    assert not log.exists()


def test_wrapper_rejects_symlinked_scaffold_markers(tmp_path: Path) -> None:
    workspace = (tmp_path / "approved-workspace").resolve()
    target = workspace / "untrusted-marker"
    metadata = target / ".kt-scaffold"
    metadata.mkdir(parents=True)
    real_answers = target / "real-answers.yml"
    real_answers.write_text("backend_profile: python-fastapi\n", encoding="utf-8")
    (metadata / "answers.yml").symlink_to(real_answers)
    (metadata / "manifest.json").write_text('{"format":1}\n', encoding="utf-8")
    environment, log = _environment(tmp_path, workspace=workspace, target=target)

    completed = _run(environment)

    assert completed.returncode == 2
    assert "empty or contain regular" in completed.stderr
    assert not log.exists()
