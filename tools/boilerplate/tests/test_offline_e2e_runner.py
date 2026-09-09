"""Fail-closed contracts for the generated offline browser entry point."""

from __future__ import annotations

import hashlib
import os
import platform
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

from kt_scaffold.models import Answers
from kt_scaffold.project import project_init


def _executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _host_platform() -> str:
    machine = platform.machine().lower()
    architecture = "amd64" if machine in {"amd64", "x86_64"} else "arm64"
    return f"{platform.system().lower()}/{architecture}"


def _seal_bundle(bundle: Path) -> None:
    entries: list[str] = []
    for path in sorted(bundle.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            relative = path.relative_to(bundle).as_posix()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append(f"{digest}  ./{relative}")
    (bundle / "SHA256SUMS").write_text("\n".join(entries) + "\n", encoding="utf-8")


def _manifest_digest(bundle: Path) -> str:
    return hashlib.sha256((bundle / "SHA256SUMS").read_bytes()).hexdigest()


def _bundle(tmp_path: Path) -> tuple[Path, Path]:
    bundle = tmp_path / "admitted-bundle"
    npm_cache = bundle / "npm-cache"
    browser = bundle / "playwright" / "chromium-test" / "chrome"
    npm_cache.mkdir(parents=True)
    browser.parent.mkdir(parents=True)
    (npm_cache / "cache-entry").write_text("approved npm content\n", encoding="utf-8")
    _executable(browser, "#!/usr/bin/env sh\nexit 0\n")
    (bundle / "BUILD-MATRIX").write_text(
        f"oci-platform={_host_platform()}\n",
        encoding="utf-8",
    )
    _seal_bundle(bundle)
    return bundle, browser


def _project(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> Path:
    target = tmp_path / "project"
    project_init(target, answers_factory())
    return target


def test_e2e_runner_defaults_offline_and_refuses_a_missing_bundle(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    environment = os.environ.copy()
    environment.pop("KT_SCAFFOLD_E2E_MODE", None)
    environment.pop("KT_SCAFFOLD_OFFLINE_BUNDLE", None)

    completed = subprocess.run(
        [str(target / "scripts/e2e.sh")],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "KT_SCAFFOLD_OFFLINE_BUNDLE" in completed.stderr
    assert "admitted, platform-matched bundle" in completed.stderr


def test_e2e_runner_verifies_bundle_and_wires_offline_npm_and_chromium(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    bundle, chromium = _bundle(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    log = tmp_path / "commands.log"
    _executable(
        fake_bin / "npm",
        "#!/usr/bin/env sh\n"
        'printf \'npm|%s|browser=%s\\n\' "$*" "${PLAYWRIGHT_BROWSERS_PATH:-}" '
        '>> "$E2E_TEST_LOG"\n',
    )
    _executable(
        fake_bin / "node",
        "#!/usr/bin/env sh\n"
        "printf 'node|browser=%s\\n' \"${PLAYWRIGHT_BROWSERS_PATH:-}\" "
        '>> "$E2E_TEST_LOG"\n'
        'printf %s "$E2E_FAKE_CHROMIUM"\n',
    )
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{environment['PATH']}",
            "KT_SCAFFOLD_OFFLINE_BUNDLE": str(bundle),
            "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256": _manifest_digest(bundle),
            "E2E_TEST_LOG": str(log),
            "E2E_FAKE_CHROMIUM": str(chromium),
        }
    )
    environment.pop("KT_SCAFFOLD_E2E_MODE", None)

    completed = subprocess.run(
        [str(target / "scripts/e2e.sh"), "auth"],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    commands = log.read_text(encoding="utf-8").splitlines()
    assert commands == [
        (
            "npm|ci --offline --ignore-scripts --no-audit --no-fund "
            f"--cache {bundle / 'npm-cache'}|browser="
        ),
        f"node|browser={bundle / 'playwright'}",
        f"npm|run auth|browser={bundle / 'playwright'}",
    ]


def test_e2e_runner_rejects_bundle_corruption_before_npm(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    bundle, _ = _bundle(tmp_path)
    (bundle / "npm-cache/cache-entry").write_text("tampered\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["KT_SCAFFOLD_OFFLINE_BUNDLE"] = str(bundle)
    environment["KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256"] = _manifest_digest(bundle)
    environment.pop("KT_SCAFFOLD_E2E_MODE", None)

    completed = subprocess.run(
        [str(target / "scripts/e2e.sh"), "auth"],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "checksum verification failed" in completed.stderr


def test_e2e_runner_rejects_a_wrong_platform_bundle(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    bundle, _ = _bundle(tmp_path)
    matrix = bundle / "BUILD-MATRIX"
    host = _host_platform()
    wrong = "linux/arm64" if host != "linux/arm64" else "linux/amd64"
    matrix.write_text(f"oci-platform={wrong}\n", encoding="utf-8")
    _seal_bundle(bundle)
    environment = os.environ.copy()
    environment["KT_SCAFFOLD_OFFLINE_BUNDLE"] = str(bundle)
    environment["KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256"] = _manifest_digest(bundle)
    environment.pop("KT_SCAFFOLD_E2E_MODE", None)

    completed = subprocess.run(
        [str(target / "scripts/e2e.sh"), "auth"],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert f"does not match host {host}" in completed.stderr


def test_e2e_runner_rejects_a_rewritten_manifest_without_bank_readmission(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    bundle, _ = _bundle(tmp_path)
    admitted_digest = _manifest_digest(bundle)
    (bundle / "npm-cache/cache-entry").write_text("attacker replacement\n", encoding="utf-8")
    _seal_bundle(bundle)
    environment = os.environ.copy()
    environment.update(
        {
            "KT_SCAFFOLD_OFFLINE_BUNDLE": str(bundle),
            "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256": admitted_digest,
        }
    )

    completed = subprocess.run(
        [str(target / "scripts/e2e.sh"), "auth"],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "does not match the bank admission digest" in completed.stderr


def test_e2e_runner_rejects_an_unsealed_bundle_file(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    bundle, _ = _bundle(tmp_path)
    (bundle / "npm-cache/injected-package").write_text("unsealed\n", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "KT_SCAFFOLD_OFFLINE_BUNDLE": str(bundle),
            "KT_SCAFFOLD_OFFLINE_BUNDLE_SHA256": _manifest_digest(bundle),
        }
    )

    completed = subprocess.run(
        [str(target / "scripts/e2e.sh"), "auth"],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "unsealed or missing files" in completed.stderr


def test_private_index_mode_refuses_public_registry(
    tmp_path: Path,
    answers_factory: Callable[..., Answers],
) -> None:
    target = _project(tmp_path, answers_factory)
    environment = os.environ.copy()
    environment.update(
        {
            "KT_SCAFFOLD_E2E_MODE": "private-index",
            "KT_SCAFFOLD_NPM_REGISTRY": "https://registry.npmjs.org",
            "PLAYWRIGHT_BROWSERS_PATH": str(tmp_path / "approved-browser"),
        }
    )

    completed = subprocess.run(
        [str(target / "scripts/e2e.sh"), "auth"],
        cwd=target,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "public npm registries are forbidden" in completed.stderr
